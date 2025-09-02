# services/flight_details_service.py
from typing import Dict, Any, Optional, List, Union
from decimal import Decimal
from app.storage.services.flight_storage_service import FlightStorageService, FlightOffer

class FlightDetailsService:
    """
    Service for retrieving detailed flight information
    """
    
    def __init__(self, flight_storage: FlightStorageService):
        self.flight_storage = flight_storage
    
    def get_flight_details(self, flight_id: str) -> Dict[str, Any]:
        """
        Get comprehensive flight details by flight ID
        
        Args:
            flight_id: Could be either:
                - Flight offer ID from search results
                - Custom flight identifier (airline + flight number)
        
        Returns:
            Dictionary with detailed flight information
        """
        
        # Try to get flight offer first (most common case)
        flight_offer = self.flight_storage.get_flight_offer(flight_id)
        
        if flight_offer:
            return self._format_flight_offer_details(flight_offer)
        
        # If not found as offer ID, try parsing as airline flight number
        flight_details = self._parse_flight_identifier(flight_id)
        if flight_details:
            return self._get_flight_by_airline_number(**flight_details) # type: ignore
        
        return {
            'error': f'Flight not found: {flight_id}',
            'flight_id': flight_id,
            'available': False
        }
    
    def _format_flight_offer_details(self, offer: FlightOffer) -> Dict[str, Any]:
        """Format flight offer into detailed response"""
        
        # Extract detailed information from complete_offer_data
        offer_data = offer.complete_offer_data
        
        # Basic flight information
        details = {
            'flight_id': offer.flight_offer_id,
            'offer_id': offer.id,
            'available': True,
            'bookable_until': offer.bookable_until.isoformat() if offer.bookable_until else None,
            
            # Pricing
            'pricing': {
                'base_price': float(offer.base_price),
                'taxes_and_fees': float(offer.taxes_and_fees),
                'total_price': float(offer.total_price),
                'currency': offer.currency
            },
            
            # Route information
            'route': {
                'summary': offer.route_summary,
                'airlines': offer.airline_codes,
                'total_duration_minutes': offer.total_duration_minutes,
                'stops_count': offer.stops_count
            },
            
            # Availability
            'availability': {
                'seats_available': offer.seats_available,
                'last_updated': offer.created_at.isoformat()
            }
        }
        
        # Add detailed segments if available in offer data
        if 'segments' in offer_data:
            details['segments'] = self._format_flight_segments(offer_data['segments'])
        
        # Add baggage information if available
        if 'baggage' in offer_data:
            details['baggage'] = offer_data['baggage']
        else:
            details['baggage'] = self._get_default_baggage_info(offer.airline_codes)
        
        # Add fare rules
        details['fare_rules'] = offer.fare_rules
        
        # Add seat selection info if available
        if 'seats' in offer_data:
            details['seat_selection'] = offer_data['seats']
        else:
            details['seat_selection'] = {
                'available': True,
                'fee_required': True,
                'selection_at_booking': True
            }
        
        # Add booking requirements
        details['booking_requirements'] = self._get_booking_requirements(offer)
        
        return details
    
    def _format_flight_segments(self, segments: List[Dict]) -> List[Dict[str, Any]]:
        """Format flight segments with detailed information"""
        formatted_segments = []
        
        for segment in segments:
            formatted_segment = {
                'departure': {
                    'airport': segment.get('departure', {}).get('iataCode', ''),
                    'terminal': segment.get('departure', {}).get('terminal'),
                    'datetime': segment.get('departure', {}).get('at'),
                },
                'arrival': {
                    'airport': segment.get('arrival', {}).get('iataCode', ''),
                    'terminal': segment.get('arrival', {}).get('terminal'),
                    'datetime': segment.get('arrival', {}).get('at'),
                },
                'flight': {
                    'airline': segment.get('carrierCode', ''),
                    'flight_number': segment.get('number', ''),
                    'aircraft': segment.get('aircraft', {}).get('code', ''),
                    'operating_airline': segment.get('operating', {}).get('carrierCode')
                },
                'duration': segment.get('duration', ''),
                'stops': segment.get('numberOfStops', 0)
            }
            formatted_segments.append(formatted_segment)
        
        return formatted_segments
    
    def _get_default_baggage_info(self, airline_codes: List[str]) -> Dict[str, Any]:
        """Get default baggage information based on airlines"""
        
        # This would ideally come from a database or API
        # For now, return reasonable defaults
        return {
            'checked_bags': {
                'included': 0,
                'fee_per_bag': 30.00,
                'weight_limit_kg': 23,
                'size_limits': '158cm (62in) total dimensions'
            },
            'carry_on': {
                'included': 1,
                'weight_limit_kg': 7,
                'size_limits': '55x40x20cm'
            },
            'personal_item': {
                'included': 1,
                'size_limits': '40x30x20cm'
            }
        }
    
    def _get_booking_requirements(self, offer: FlightOffer) -> Dict[str, Any]:
        """Get booking requirements for this flight"""
        
        # Determine if international flight
        is_international = self._is_international_flight(offer)
        
        requirements = {
            'passenger_info_required': [
                'first_name',
                'last_name',
                'date_of_birth',
                'gender'
            ],
            'documents_required': [],
            'advance_booking_required': True,
            'cancellation_allowed': True,
            'changes_allowed': True,
            'special_requests': [
                'meal_preference',
                'seat_selection',
                'special_assistance'
            ]
        }
        
        if is_international:
            requirements['documents_required'].extend([
                'passport_number',
                'passport_expiry',
                'nationality'
            ])
        else:
            requirements['documents_required'].append('id_document')
        
        return requirements
    
    def _is_international_flight(self, offer: FlightOffer) -> bool:
        """Determine if this is an international flight"""
        
        # This would need to be enhanced with actual airport/country mapping
        # For now, assume flights with multiple airline codes or certain patterns are international
        if len(offer.airline_codes) > 1:
            return True
        
        # Check route summary for international indicators
        if offer.route_summary:
            international_indicators = ['international', 'USA-', 'US-', 'Europe', 'Asia']
            return any(indicator in offer.route_summary for indicator in international_indicators)
        
        return False
    
    def _parse_flight_identifier(self, flight_id: str) -> Optional[Dict[str, Union[str, List[str], None]]]:
        """Parse flight identifier like 'UA123_SFO_LAX' or 'UA123'"""
        
        # Handle format: UA123_SFO_LAX
        if '_' in flight_id:
            parts = flight_id.split('_')
            if len(parts) >= 1:
                airline_flight = parts[0]
                if len(airline_flight) >= 3:
                    airline_code = airline_flight[:2]
                    flight_number = airline_flight[2:]
                    return {
                        'airline_code': airline_code, # This is a str
                        'flight_number': flight_number, # This is a str
                        'route': parts[1:] if len(parts) > 1 else None # This is a list[str] or None
                    }
        
        # Handle format: UA123
        elif len(flight_id) >= 3 and flight_id[:2].isalpha() and flight_id[2:].isdigit():
            return {
                'airline_code': flight_id[:2],
                'flight_number': flight_id[2:],
                'route': None
            }
        
        return None
    
    def _get_flight_by_airline_number(self, airline_code: str, flight_number: str, route: List[str] = []) -> Dict[str, Any]:
        """Get flight details by airline and flight number"""
        
        # This would query external APIs or databases for real-time flight info
        # For now, return a placeholder response
        return {
            'flight_id': f"{airline_code}{flight_number}",
            'available': False,
            'error': f'Real-time flight data not available for {airline_code}{flight_number}',
            'suggestion': 'Please use flight offers from search results instead'
        }
    
    def get_flight_segments(self, flight_id: str) -> List[Dict[str, Any]]:
        """Get detailed segment information for a flight"""
        
        flight_details = self.get_flight_details(flight_id)
        
        if flight_details.get('available') and 'segments' in flight_details:
            return flight_details['segments']
        
        return []
    
    def get_flight_pricing_breakdown(self, flight_id: str) -> Dict[str, Any]:
        """Get detailed pricing breakdown for a flight"""
        
        flight_offer = self.flight_storage.get_flight_offer(flight_id)
        
        if not flight_offer:
            return {'error': 'Flight not found'}
        
        return {
            'flight_id': flight_id,
            'base_fare': float(flight_offer.base_price),
            'taxes_and_fees': float(flight_offer.taxes_and_fees),
            'total_price': float(flight_offer.total_price),
            'currency': flight_offer.currency,
            'fare_basis': flight_offer.fare_rules.get('fare_basis', 'Unknown'),
            'refundable': flight_offer.fare_rules.get('refundable', False),
            'changeable': flight_offer.fare_rules.get('changeable', True),
            'last_updated': flight_offer.created_at.isoformat()
        }