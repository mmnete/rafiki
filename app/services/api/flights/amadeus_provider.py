from typing import List, Optional, Tuple, Dict, Any
import requests
import json
import re
import time
import hashlib
from datetime import datetime
from .base_provider import FlightProvider
from .response_models import (
    FlightSearchResponse, ModelSearchResponse, PricingResponse, 
    BookingResponse, CancellationResponse, Passenger,
    FlightOffer, FlightSegment, FlightSearchSummary, ModelFlightOffer,
    create_error_search_response, create_error_model_response,
    create_error_pricing_response, create_error_booking_response,
    create_error_cancellation_response
)


class AmadeusProvider(FlightProvider):
    """Amadeus implementation of FlightProvider without the scraper dependency"""
    
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        try:
            self.client_id = client_id or self._get_env_var("AMADEUS_CLIENT_ID")
            self.client_secret = client_secret or self._get_env_var("AMADEUS_CLIENT_SECRET")
            
            if not self.client_id or not self.client_secret:
                raise ValueError("Amadeus credentials are required")
            
            self.base_url = "https://test.api.amadeus.com"  # Use test environment
            self.token = None
            self.headers = {}
            
            # Initialize authentication
            self._authenticate()
            
        except Exception as e:
            raise ValueError(f"Failed to initialize Amadeus client: {e}")
    
    def _get_env_var(self, key: str) -> str:
        from os import getenv
        return getenv(key) or ""
    
    def _authenticate(self) -> None:
        """Authenticate with Amadeus API"""
        url = f"{self.base_url}/v1/security/oauth2/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            response = requests.post(url, data=data)
            response.raise_for_status()
            token_data = response.json()
            self.token = token_data["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Amadeus authentication failed: {e}")
    
    def search_flights(self, origin: str, destination: str, departure_date: str,
                      return_date: Optional[str] = None, passengers: List[Passenger] = [],
                      travel_class: str = "ECONOMY") -> Tuple[ModelSearchResponse, FlightSearchResponse]:
        """Search flights using Amadeus API"""
        try:
            passengers = passengers or [Passenger(
                passenger_type="adult", first_name="", last_name="", 
                date_of_birth="1990-01-01", gender="", email="", 
                phone="", nationality=""
            )]
            
            # Count passenger types
            adults = sum(1 for p in passengers if p.passenger_type == "adult")
            children = sum(1 for p in passengers if p.passenger_type == "child")
            infants = sum(1 for p in passengers if p.passenger_type == "infant")
            
            # Prepare API request
            url = f"{self.base_url}/v2/shopping/flight-offers"
            params = {
                "originLocationCode": origin.upper(),
                "destinationLocationCode": destination.upper(),
                "departureDate": departure_date,
                "adults": adults,
                "children": children,
                "infants": infants,
                "travelClass": travel_class,
                "currencyCode": "USD",
                "max": 10,
            }
            
            if return_date:
                params["returnDate"] = return_date
            
            # Make API request
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            # Process response
            api_response = response.json()
            return self._transform_amadeus_response(api_response)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Amadeus search failed: {str(e)}"
            return (
                create_error_model_response(error_msg),
                create_error_search_response(error_msg, "amadeus")
            )
        except Exception as e:
            error_msg = f"Amadeus search error: {str(e)}"
            return (
                create_error_model_response(error_msg),
                create_error_search_response(error_msg, "amadeus")
            )
    
    def get_final_price(self, offer_id: str) -> PricingResponse:
        """Get final confirmed pricing using Amadeus pricing endpoint"""
        try:
            # For Amadeus, we need the full offer data for pricing
            # This is a limitation - in real implementation, you'd need to store
            # the full offer data and retrieve it by offer_id
            
            # For now, return an error indicating this needs to be implemented
            # with proper offer data storage
            return create_error_pricing_response(
                offer_id, 
                "Amadeus pricing requires full offer data - implement offer storage"
            )
            
        except Exception as e:
            return create_error_pricing_response(offer_id, f"Amadeus pricing error: {str(e)}")
    
    def create_booking(self, offer_id: str, passengers: List[Passenger], 
                      booking_reference: str) -> BookingResponse:
        """Create actual booking using Amadeus booking endpoint"""
        try:
            # Transform passengers to Amadeus format
            amadeus_travelers = self._transform_passengers_to_amadeus(passengers)
            
            # Note: This is a simplified implementation
            # In reality, you'd need the full priced offer data
            booking_data = {
                "data": {
                    "type": "flight-order",
                    "flightOffers": [],  # Would contain full priced offers
                    "travelers": amadeus_travelers,
                    "remarks": {
                        "general": [{
                            "subType": "GENERAL_MISCELLANEOUS",
                            "text": f"Booking ref: {booking_reference}"
                        }]
                    }
                }
            }
            
            # This would be the actual booking call
            # response = requests.post(f"{self.base_url}/v1/booking/flight-orders", 
            #                         headers=self.headers, json=booking_data)
            
            # For now, return an error indicating this needs full implementation
            return create_error_booking_response(
                "Amadeus booking requires full offer data and proper implementation"
            )
            
        except Exception as e:
            return create_error_booking_response(f"Amadeus booking error: {str(e)}")
    
    def cancel_booking(self, booking_reference: str) -> CancellationResponse:
        """Cancel booking with Amadeus"""
        # Amadeus doesn't have a standard cancellation API
        # This would need to be implemented with airline-specific logic
        return create_error_cancellation_response(
            "Amadeus cancellation requires custom implementation per airline"
        )
    
    def get_provider_name(self) -> str:
        return "amadeus"
    
    # Helper methods
    def _transform_passengers_to_amadeus(self, passengers: List[Passenger]) -> List[Dict]:
        """Transform passengers to Amadeus format"""
        amadeus_travelers = []
        
        for idx, passenger in enumerate(passengers):
            traveler = {
                "id": str(idx + 1),
                "dateOfBirth": passenger.date_of_birth,
                "name": {
                    "firstName": passenger.first_name,
                    "lastName": passenger.last_name
                },
                "gender": passenger.gender.upper() if passenger.gender else "UNKNOWN",
                "contact": {
                    "emailAddress": passenger.email,
                    "phones": []
                }
            }
            
            # Add phone if available
            if passenger.phone:
                traveler["contact"]["phones"] = [{
                    "deviceType": "MOBILE",
                    "countryCallingCode": "1",
                    "number": passenger.phone
                }]
            
            # Add documents if available
            if passenger.passport_number:
                traveler["documents"] = [{
                    "documentType": "PASSPORT",
                    "number": passenger.passport_number,
                    "expiryDate": passenger.passport_expiry or "2030-12-31",
                    "issuanceCountry": passenger.nationality or "US",
                    "validityCountry": passenger.nationality or "US",
                    "nationality": passenger.nationality or "US",
                    "holder": True
                }]
            
            amadeus_travelers.append(traveler)
        
        return amadeus_travelers
    
    def _transform_amadeus_response(self, api_response: Dict) -> Tuple[ModelSearchResponse, FlightSearchResponse]:
        """Transform Amadeus response to our standard format"""
        try:
            offers = api_response.get("data", [])
            
            if not offers:
                error_msg = "No flights found for your search criteria"
                return (
                    create_error_model_response(error_msg),
                    create_error_search_response(error_msg, "amadeus")
                )
            
            # Get dictionaries for lookups
            dictionaries = api_response.get("dictionaries", {})
            airline_dict = dictionaries.get("carriers", {})
            aircraft_dict = dictionaries.get("aircraft", {})
            
            # Process offers
            flight_offers = []
            model_offers = []
            
            for idx, offer in enumerate(offers):
                try:
                    flight_offer = self._process_amadeus_offer(offer, idx, airline_dict, aircraft_dict)
                    model_offer = self._create_model_offer(flight_offer)
                    
                    flight_offers.append(flight_offer)
                    model_offers.append(model_offer)
                except Exception as e:
                    print(f"Error processing Amadeus offer: {e}")
                    continue
            
            # Create summary
            if flight_offers:
                prices = [offer.price_total for offer in flight_offers]
                airlines = list(set([offer.airline_code for offer in flight_offers]))
                
                search_summary = FlightSearchSummary(
                    total_offers=len(flight_offers),
                    price_range_min=min(prices),
                    price_range_max=max(prices),
                    currency=flight_offers[0].currency,
                    airlines=airlines,
                    routes_available=1
                )
            else:
                search_summary = FlightSearchSummary(
                    total_offers=0, price_range_min=0.0, price_range_max=0.0,
                    currency="USD", airlines=[], routes_available=0
                )
            
            # Create responses
            full_response = FlightSearchResponse(
                success=True,
                flights=flight_offers,
                search_summary=search_summary,
                provider_name="amadeus"
            )
            
            model_response = ModelSearchResponse(
                success=True,
                flights=model_offers,
                summary={
                    "total_found": len(flight_offers),
                    "price_range": f"${search_summary.price_range_min:.0f}-${search_summary.price_range_max:.0f}",
                    "airlines": airlines[:3]
                }
            )
            
            return model_response, full_response
            
        except Exception as e:
            error_msg = f"Amadeus response transformation error: {str(e)}"
            return (
                create_error_model_response(error_msg),
                create_error_search_response(error_msg, "amadeus")
            )
    
    def _process_amadeus_offer(self, offer: Dict, offer_idx: int, 
                              airline_dict: Dict, aircraft_dict: Dict) -> FlightOffer:
        """Process a single Amadeus offer"""
        # Generate offer ID
        offer_id = offer.get("id") or f"amadeus_{offer_idx}_{int(time.time())}"
        
        # Process pricing
        price_info = offer.get("price", {})
        total_amount = float(price_info.get("grandTotal", 0))
        base_amount = float(price_info.get("base", 0))
        currency = price_info.get("currency", "USD")
        
        # Process itineraries and segments
        all_segments = []
        airlines = set()
        total_stops = 0
        
        for itinerary in offer.get("itineraries", []):
            for segment in itinerary.get("segments", []):
                flight_segment = self._process_amadeus_segment(segment, airline_dict, aircraft_dict)
                all_segments.append(flight_segment)
                airlines.add(flight_segment.airline_code)
                total_stops += segment.get("numberOfStops", 0)
        
        # Get route info
        first_segment = all_segments[0] if all_segments else None
        last_segment = all_segments[-1] if all_segments else None
        
        # Determine trip type
        num_itineraries = len(offer.get("itineraries", []))
        trip_type = "round_trip" if num_itineraries > 1 else "one_way"
        if total_stops == 0:
            trip_type += "_direct" if trip_type == "one_way" else ""
        else:
            trip_type += "_connecting" if trip_type == "one_way" else ""
        
        # Calculate duration
        first_itinerary = offer.get("itineraries", [{}])[0]
        duration = first_itinerary.get("duration", "")
        duration_minutes = self._parse_duration_to_minutes(duration)
        
        return FlightOffer(
            flight_offer_id=f"amadeus_{offer_id}",
            provider_offer_id=offer_id,
            price_total=total_amount,
            base_price=base_amount,
            currency=currency,
            origin=first_segment.departure_iata if first_segment else "",
            destination=last_segment.arrival_iata if last_segment else "",
            departure_time=first_segment.departure_time if first_segment else "",
            arrival_time=last_segment.arrival_time if last_segment else "",
            trip_type=trip_type,
            duration=duration,
            duration_minutes=duration_minutes or 0,
            flight_duration_minutes=duration_minutes or 0,
            total_segments=len(all_segments),
            stops=total_stops,
            airline_code=first_segment.airline_code if first_segment else "",
            airline_name=first_segment.airline_name if first_segment else "",
            airlines=list(airlines),
            segments=all_segments,
            checked_bags=0,  # Would need to parse from travelerPricings
            cabin_bags=1,    # Default assumption
            seats_available=offer.get("numberOfBookableSeats"),
            instant_ticketing=offer.get("instantTicketingRequired", False),
            last_ticketing_date=offer.get("lastTicketingDate"),
            provider_data={"full_offer": offer}
        )
    
    def _process_amadeus_segment(self, segment: Dict, airline_dict: Dict, aircraft_dict: Dict) -> FlightSegment:
        """Process a single Amadeus segment"""
        airline_code = segment.get("carrierCode")
        aircraft_code = segment.get("aircraft", {}).get("code")
        duration_minutes = self._parse_duration_to_minutes(segment.get("duration"))
        
        return FlightSegment(
            airline_code=airline_code or "",
            airline_name=airline_dict.get(airline_code, "Unknown"),
            flight_number=segment.get("number", ""),
            departure_iata=segment.get("departure", {}).get("iataCode", ""),
            arrival_iata=segment.get("arrival", {}).get("iataCode", ""),
            departure_terminal=segment.get("departure", {}).get("terminal"),
            arrival_terminal=segment.get("arrival", {}).get("terminal"),
            departure_time=segment.get("departure", {}).get("at", ""),
            arrival_time=segment.get("arrival", {}).get("at", ""),
            duration=segment.get("duration", ""),
            duration_minutes=duration_minutes or 0,
            stops=segment.get("numberOfStops", 0),
            aircraft_code=aircraft_code,
            aircraft_name=aircraft_dict.get(aircraft_code, "Unknown") if aircraft_code else "Unknown",
            operating_carrier=segment.get("operating", {}).get("carrierCode", airline_code),
            segment_id=segment.get("id")
        )
    
    def _create_model_offer(self, flight_offer: FlightOffer) -> ModelFlightOffer:
        """Create simplified model offer from full flight offer"""
        # Format duration nicely
        duration_str = self._format_duration(flight_offer.duration) # type: ignore
        
        # Format stops
        stops_text = "Direct" if flight_offer.stops == 0 else f"{flight_offer.stops} stop{'s' if flight_offer.stops > 1 else ''}"
        
        # Extract time from datetime strings
        departure_time = ""
        arrival_time = ""
        
        if flight_offer.departure_time:
            try:
                departure_time = flight_offer.departure_time.split('T')[1][:5] if 'T' in flight_offer.departure_time else flight_offer.departure_time[:5]
            except:
                departure_time = ""
        
        if flight_offer.arrival_time:
            try:
                arrival_time = flight_offer.arrival_time.split('T')[1][:5] if 'T' in flight_offer.arrival_time else flight_offer.arrival_time[:5]
            except:
                arrival_time = ""
        
        return ModelFlightOffer(
            id=flight_offer.flight_offer_id,
            price=f"${flight_offer.price_total:.0f}",
            airline=flight_offer.airline_name,
            route=f"{flight_offer.origin} → {flight_offer.destination}",
            departure=departure_time,
            arrival=arrival_time,
            duration=duration_str,
            stops=stops_text
        )
    
    def _parse_duration_to_minutes(self, duration_str: Optional[str]) -> Optional[int]:
        """Parse ISO 8601 duration to minutes (PT1H55M -> 115)"""
        if not duration_str:
            return None
            
        # Parse PT1H55M format
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?'
        match = re.match(pattern, duration_str)
        if not match:
            return None
            
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        return hours * 60 + minutes
    
    def _format_duration(self, duration_str: str) -> str:
        """Format duration string for display"""
        if not duration_str:
            return ""
            
        # Parse PT1H55M format
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?'
        match = re.match(pattern, duration_str)
        if not match:
            return duration_str
            
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        
        if hours and minutes:
            return f"{hours}h {minutes}m"
        elif hours:
            return f"{hours}h"
        elif minutes:
            return f"{minutes}m"
        else:
            return ""