from typing import Dict, Any, List, Optional, Tuple
import uuid
import json
from datetime import datetime, timedelta
from decimal import Decimal

from app.storage.services.flight_storage_service import FlightStorageService
from app.storage.services.booking_storage_service import BookingStorageService
from app.storage.services.user_storage_service import UserStorageService
from app.services.api.flights.amadeus_scraper import AmadeusFlightScraper
from app.services.redis_storage_manager import implemented_redis_storage_manager

class FlightService:
    """Flight search and booking management service"""
    
    def __init__(self, flight_storage: FlightStorageService, 
                 booking_storage: BookingStorageService,
                 user_storage: UserStorageService):
        self.flight_storage = flight_storage
        self.booking_storage = booking_storage  
        self.user_storage = user_storage
        self._flight_scraper = AmadeusFlightScraper()

    def search_flights(self, origin: str, destination: str, departure_date: str,
                      return_date: Optional[str] = None, 
                      adults: int = 1, children: int = 0, infants: int = 0,
                      travel_class: str = "ECONOMY", user_id: Optional[int] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Search flights and store results for caching"""
        
        # Call the scraper
        summarized_results, raw_results = self._flight_scraper.search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            adults=adults,
            children=children,
            infants=infants,
            travel_class=travel_class
        )
        
        # Store search results if we have a user
        if user_id and raw_results:
            try:
                # Create search record
                search_params = {
                    'origin': origin,
                    'destination': destination,
                    'departure_date': departure_date,
                    'return_date': return_date,
                    'passengers': {'adults': adults, 'children': children, 'infants': infants},
                    'travel_class': travel_class
                }
                
                trip_type = 'round_trip' if return_date else 'one_way'
                custom_search_id = f"search_{user_id}_{origin}_{destination}_{departure_date}_{uuid.uuid4().hex[:8]}"
                
                # Store flight search
                search_id = self.flight_storage.create_flight_search(
                    user_id=user_id,
                    custom_search_id=custom_search_id,
                    search_type=trip_type,
                    search_params=search_params,
                    raw_results=raw_results,
                    processed_results=summarized_results,
                    result_count=len(raw_results) if isinstance(raw_results, list) else 0,
                    apis_used=['amadeus'],
                    cache_hit=False
                )
                
                # Store individual flight offers
                if search_id and isinstance(raw_results, list):
                    for flight in raw_results:
                        if isinstance(flight, dict):
                            self.flight_storage.add_flight_offer(
                                search_id=search_id,
                                flight_offer_id=flight.get('flight_offer_id', str(uuid.uuid4())),
                                base_price=Decimal(str(flight.get('price_total', 0))),
                                total_price=Decimal(str(flight.get('price_total', 0))),
                                airline_codes=flight.get('airlines', []),
                                route_summary=f"{flight.get('origin')} -> {flight.get('destination')}",
                                total_duration_minutes=flight.get('duration_minutes'),
                                stops_count=flight.get('stops', 0),
                                complete_offer_data=flight
                            )
                
                # Add search_id to results for reference
                if isinstance(summarized_results, dict):
                    summarized_results['search_id'] = search_id
                    
            except Exception as e:
                print(f"Error storing search results: {e}")
        
        return summarized_results, raw_results

    def create_booking(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Create booking using proper storage services"""
        print("Making booking with enhanced flight data")
        
        user_id = kwargs.get('user_id')
        search_id = kwargs.get('search_id')
        flight_offer_ids = kwargs.get('flight_offer_ids', [])
        
        # Validate required parameters
        if not flight_offer_ids or not search_id:
            return {"error": "Missing flight selection or search reference"}
        
        if not user_id:
            return {"error": "Missing user ID"}
        
        try:
            # Get flight search record
            flight_search = self.flight_storage.get_flight_search(search_id)
            if not flight_search:
                return {"error": "Samahani, maelezo ya ndege hayapatikani tena. Tafadhali tafuta tena."}
            
            # Get selected flight offers
            selected_offers = []
            for offer_id in flight_offer_ids:
                offers = self.flight_storage.get_search_offers(search_id)
                matching_offer = next((o for o in offers if o.flight_offer_id == offer_id), None)
                if matching_offer:
                    selected_offers.append(matching_offer)
            
            if not selected_offers:
                return {"error": "Selected flights not found"}
            
            # Calculate total pricing
            total_base_price = sum(offer.total_price for offer in selected_offers)
            service_fee = Decimal('5.00')
            total_amount = total_base_price + service_fee
            
            # Create booking
            booking_id = self.booking_storage.create_booking(
                primary_user_id=user_id,
                search_id=search_id,
                selected_flight_offers=[{
                    'flight_offer_id': offer.flight_offer_id,
                    'price': float(offer.total_price),
                    'offer_data': offer.complete_offer_data
                } for offer in selected_offers],
                trip_type=flight_search.search_type,
                origin_airport=flight_search.search_params.get('origin'),
                destination_airport=flight_search.search_params.get('destination'),
                departure_date=flight_search.search_params.get('departure_date'),
                return_date=flight_search.search_params.get('return_date'),
                base_price=total_base_price,
                service_fee=service_fee,
                total_amount=total_amount,
                travel_insurance=kwargs.get('travel_insurance', False),
                special_requests=kwargs.get('special_requests')
            )
            
            if booking_id:
                # Add flight segments to booking
                for i, offer in enumerate(selected_offers):
                    offer_data = offer.complete_offer_data
                    segments = offer_data.get('segments', [offer_data])  # Handle both formats
                    
                    for j, segment in enumerate(segments):
                        self.booking_storage.add_flight_segment(
                            booking_id=booking_id,
                            flight_offer_id=offer.flight_offer_id,
                            airline_code=segment.get('airline_code', ''),
                            flight_number=segment.get('flight_number', ''),
                            departure_airport=segment.get('origin', ''),
                            arrival_airport=segment.get('destination', ''),
                            departure_time=datetime.fromisoformat(segment.get('departure_time', '').replace('Z', '+00:00')),
                            arrival_time=datetime.fromisoformat(segment.get('arrival_time', '').replace('Z', '+00:00')),
                            duration_minutes=segment.get('duration_minutes'),
                            flight_status='scheduled'
                        )
                
                return {"success": True, "booking_id": booking_id, "total_amount": float(total_amount)}
            
            return {"error": "Failed to create booking"}
            
        except Exception as e:
            print(f"Error creating booking: {e}")
            import traceback
            traceback.print_exc()
            return {"error": "Samahani, kuna tatizo la muunganisho wa mfumo. Jaribu tena."}

    def get_user_bookings(self, user_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get user's bookings using booking storage service"""
        bookings = self.booking_storage.get_bookings_for_user(user_id)
        
        # Filter by status if provided
        if status:
            bookings = [b for b in bookings if b.booking_status == status]
        
        # Convert to dict format for compatibility
        return [{
            'id': booking.id,
            'booking_reference': booking.booking_reference,
            'status': booking.booking_status,
            'total_amount': float(booking.total_amount),
            'currency': booking.currency,
            'departure_date': booking.departure_date.isoformat() if booking.departure_date else None,
            'origin_airport': booking.origin_airport,
            'destination_airport': booking.destination_airport,
            'created_at': booking.created_at.isoformat() if booking.created_at else None
        } for booking in bookings]

    def add_passengers_to_booking(self, booking_id: str, passengers_data: List[Dict[str, Any]]) -> bool:
        """Add passengers to booking"""
        try:
            for passenger_data in passengers_data:
                self.booking_storage.add_passenger_to_booking(
                    booking_id=booking_id,
                    passenger_type=passenger_data.get('type', 'adult'),
                    booking_first_name=passenger_data.get('first_name'),
                    booking_last_name=passenger_data.get('last_name'),
                    booking_document_number=passenger_data.get('document_number'),
                    booking_seat_preference=passenger_data.get('seat_preference'),
                    booking_meal_preference=passenger_data.get('meal_preference')
                )
            return True
        except Exception as e:
            print(f"Error adding passengers: {e}")
            return False

    def update_booking_status(self, booking_id: str, status: str, **updates) -> bool:
        """Update booking status"""
        return self.booking_storage.update_booking_status(booking_id, status)

    def get_booking_details(self, booking_id: str) -> Optional[Dict[str, Any]]:
        """Get complete booking details"""
        booking = self.booking_storage.get_booking(booking_id)
        if not booking:
            return None
        
        passengers = self.booking_storage.get_booking_passengers(booking_id)
        segments = self.booking_storage.get_booking_flight_segments(booking_id)
        
        return {
            'booking': {
                'id': booking.id,
                'reference': booking.booking_reference,
                'status': booking.booking_status,
                'total_amount': float(booking.total_amount),
                'currency': booking.currency,
                # ... add other booking fields
            },
            'passengers': [{
                'name': f"{p.booking_first_name} {p.booking_last_name}",
                'type': p.passenger_type,
                'seat_preference': p.booking_seat_preference
            } for p in passengers],
            'segments': [{
                'airline': s.airline_code,
                'flight_number': s.flight_number,
                'departure': {
                    'airport': s.departure_airport,
                    'time': s.departure_time.isoformat() if s.departure_time else None
                },
                'arrival': {
                    'airport': s.arrival_airport, 
                    'time': s.arrival_time.isoformat() if s.arrival_time else None
                }
            } for s in segments]
        }

    def cache_flight_details(self, user_id, flight_id, flight_data, search_params):
        """Keep Redis caching for quick access if needed"""
        if not user_id:
            return
        
        cache_key = f"flight_cache:{user_id}:{flight_id}"
        cache_data = {
            'flight': flight_data,
            'search_params': search_params,
            'cached_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=2)).isoformat()
        }
        
        try:
            implemented_redis_storage_manager.set_data(cache_key, cache_data, ttl=7200)
        except Exception as e:
            print(f"Error caching flight: {e}")