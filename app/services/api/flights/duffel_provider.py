from typing import List, Optional, Tuple, Dict, Any
import requests
import json
import re
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


class DuffelProvider(FlightProvider):
    """Duffel implementation of FlightProvider based on official API documentation"""
    
    def __init__(self, access_token: Optional[str] = None):
        try:
            self.access_token = access_token or self._get_env_var("DUFFEL_ACCESS_TOKEN")
            if not self.access_token:
                raise ValueError("Duffel access token is required")
            
            self.base_url = "https://api.duffel.com"
            self.headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        except Exception as e:
            raise ValueError(f"Failed to initialize Duffel client: {e}")
    
    def _get_env_var(self, key: str) -> str:
        from os import getenv
        return getenv(key) or ""
    
    def search_flights(self, origin: str, destination: str, departure_date: str,
                  return_date: Optional[str] = None, passengers: List[Passenger] = [],
                  travel_class: str = "ECONOMY") -> Tuple[ModelSearchResponse, FlightSearchResponse]:
        """Search flights using Duffel API based on official documentation"""
        try:
            passengers = passengers or [Passenger(
                passenger_type="adult", first_name="", last_name="", 
                date_of_birth="1990-01-01", gender="", email="", 
                phone="", nationality=""
            )]
            
            # Build slices for the journey
            slices = [
                {
                    "origin": origin.upper(),
                    "destination": destination.upper(), 
                    "departure_date": departure_date
                }
            ]
            
            # Add return slice if round trip
            if return_date:
                slices.append({
                    "origin": destination.upper(),
                    "destination": origin.upper(),
                    "departure_date": return_date
                })
            
            # Transform passengers to Duffel format (minimal for search)
            duffel_passengers = []
            for passenger in passengers:
                p_data = {"type": passenger.passenger_type}
                
                # Add age if specified (for children/infants)
                if passenger.age:
                    p_data["age"] = int(passenger.age) # type: ignore
                
                duffel_passengers.append(p_data)
            
            # Create offer request
            offer_request_data = {
                "data": {
                    "slices": slices,
                    "passengers": duffel_passengers,
                    "cabin_class": self._map_travel_class(travel_class)
                }
            }
            
            # Update headers to include Duffel-Version
            headers = self.headers.copy()
            headers["Duffel-Version"] = "v2"
            headers["Accept-Encoding"] = "gzip"
            
            # Make API request - KEY FIX: Use return_offers=false and then fetch offers separately
            response = requests.post(
                f"{self.base_url}/air/offer_requests",
                headers=headers,
                json=offer_request_data,
                params={"return_offers": "false", "supplier_timeout": "10000"}
            )
            response.raise_for_status()
            
            offer_request = response.json()
            offer_request_id = offer_request.get("data", {}).get("id")
            
            if not offer_request_id:
                raise Exception("No offer request ID returned")
            
            # Now fetch the offers separately (this is the correct Duffel pattern)
            offers_response = requests.get(
                f"{self.base_url}/air/offers",
                headers=headers,
                params={"offer_request_id": offer_request_id}
            )
            offers_response.raise_for_status()
            
            offers_data = offers_response.json()
            
            # Transform response to our standard format
            return self._transform_duffel_response(offers_data)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Duffel search failed: {str(e)}"
            return (
                create_error_model_response(error_msg),
                create_error_search_response(error_msg, "duffel")
            )
        except Exception as e:
            error_msg = f"Duffel search error: {str(e)}"
            return (
                create_error_model_response(error_msg),
                create_error_search_response(error_msg, "duffel")
            )
    
    
    def get_final_price(self, offer_id: str) -> PricingResponse:
        """Get final confirmed pricing using Duffel's Get single offer endpoint"""
        try:
            # Get fresh pricing from Duffel
            response = requests.get(
                f"{self.base_url}/air/offers/{offer_id}",
                headers=self.headers,
                params={"return_available_services": "true"}
            )
            response.raise_for_status()
            
            offer_data = response.json()
            offer = offer_data.get("data")
            
            if not offer:
                return create_error_pricing_response(offer_id, "Offer not found")
            
            return PricingResponse(
                success=True,
                offer_id=offer["id"],
                total_amount=float(offer["total_amount"]) / 100,  # Duffel uses cents
                base_amount=float(offer["base_amount"]) / 100,
                tax_amount=float(offer["tax_amount"]) / 100,
                currency=offer["total_currency"],
                provider_data={"full_offer": offer}
            )
        except requests.exceptions.RequestException as e:
            return create_error_pricing_response(offer_id, f"Duffel pricing failed: {str(e)}")
        except Exception as e:
            return create_error_pricing_response(offer_id, f"Pricing error: {str(e)}")
    
    def create_booking(self, offer_id: str, passengers: List[Passenger], 
                      booking_reference: str) -> BookingResponse:
        """Create actual booking using Duffel's Create order endpoint"""
        try:
            # Transform passengers to Duffel format with full details
            duffel_passengers = self._transform_passengers_to_duffel_full(passengers)
            
            # Create order data
            order_data = {
                "data": {
                    "selected_offers": [offer_id],
                    "passengers": duffel_passengers,
                    "payments": [
                        {
                            "type": "balance",  # Using Duffel balance
                            "amount": None,     # Will be auto-calculated
                            "currency": None    # Will be auto-set
                        }
                    ],
                    "metadata": {
                        "booking_reference": booking_reference
                    }
                }
            }
            
            # Create order
            response = requests.post(
                f"{self.base_url}/air/orders",
                headers=self.headers,
                json=order_data
            )
            response.raise_for_status()
            
            order_data = response.json()
            order = order_data.get("data")
            
            if not order:
                return create_error_booking_response("Order creation failed - no data returned")
            
            return BookingResponse(
                success=True,
                booking_id=order["id"],
                booking_reference=order.get("booking_reference", ""),
                total_amount=float(order["total_amount"]) / 100,  # Duffel uses cents
                currency=order["total_currency"],
                created_at=order["created_at"],
                provider_data={"order": order}
            )
        except requests.exceptions.RequestException as e:
            return create_error_booking_response(f"Duffel booking failed: {str(e)}")
        except Exception as e:
            return create_error_booking_response(f"Booking error: {str(e)}")
    
    def cancel_booking(self, booking_reference: str) -> CancellationResponse:
        """Cancel booking using Duffel's Order cancellation endpoints"""
        try:
            # First, get the order ID from booking reference
            order_id = self._get_order_id_from_booking_reference(booking_reference)
            
            if not order_id:
                return create_error_cancellation_response("Could not find order for booking reference")
            
            # Create order cancellation to get quote
            cancellation_data = {
                "data": {
                    "order_id": order_id
                }
            }
            
            response = requests.post(
                f"{self.base_url}/air/order_cancellations",
                headers=self.headers,
                json=cancellation_data
            )
            response.raise_for_status()
            
            cancellation_quote = response.json()
            cancellation = cancellation_quote.get("data")
            
            if not cancellation:
                return create_error_cancellation_response("Failed to get cancellation quote")
            
            # Confirm the cancellation
            cancellation_id = cancellation["id"]
            confirm_response = requests.post(
                f"{self.base_url}/air/order_cancellations/{cancellation_id}/actions/confirm",
                headers=self.headers
            )
            confirm_response.raise_for_status()
            
            confirmed_cancellation = confirm_response.json()
            confirmed_data = confirmed_cancellation.get("data")
            
            return CancellationResponse(
                success=True,
                cancellation_id=confirmed_data["id"],
                refund_amount=float(confirmed_data.get("refund_amount", 0)) / 100,
                refund_currency=confirmed_data.get("refund_currency", "USD"),
                cancellation_confirmed_at=confirmed_data.get("confirmed_at"),
                provider_data={"cancellation": confirmed_data}
            )
            
        except requests.exceptions.RequestException as e:
            return create_error_cancellation_response(f"Duffel cancellation failed: {str(e)}")
        except Exception as e:
            return create_error_cancellation_response(f"Cancellation error: {str(e)}")
    
    def get_provider_name(self) -> str:
        return "duffel"
    
    # Helper methods
    def _map_travel_class(self, travel_class: str) -> str:
        """Map generic travel class to Duffel cabin class"""
        mapping = {
            "ECONOMY": "economy",
            "PREMIUM_ECONOMY": "premium_economy", 
            "BUSINESS": "business",
            "FIRST": "first"
        }
        return mapping.get(travel_class.upper(), "economy")
    
    def _transform_passengers_to_duffel_full(self, passengers: List[Passenger]) -> List[Dict]:
        """Transform passengers with FULL details for booking"""
        duffel_passengers = []
        
        for passenger in passengers:
            duffel_passenger = {
                "type": passenger.passenger_type,
                "given_name": passenger.first_name,
                "family_name": passenger.last_name,
                "born_on": passenger.date_of_birth,
                "email": passenger.email,
                "phone_number": passenger.phone,
                "loyalty_programme_accounts": [],
                "identity_documents": []
            }
            
            # Add passport/identity document if provided
            if passenger.passport_number:
                duffel_passenger["identity_documents"].append({
                    "type": "passport",
                    "number": passenger.passport_number,
                    "expires_on": passenger.passport_expiry or "2030-12-31",
                    "issuing_country_code": passenger.nationality or "US"
                })
            
            duffel_passengers.append(duffel_passenger)
        
        return duffel_passengers
    
    def _get_order_id_from_booking_reference(self, booking_reference: str) -> Optional[str]:
        """Get order ID from booking reference"""
        try:
            # Search for orders with this booking reference
            response = requests.get(
                f"{self.base_url}/air/orders",
                headers=self.headers,
                params={"booking_reference": booking_reference}
            )
            response.raise_for_status()
            
            orders_data = response.json()
            orders = orders_data.get("data", [])
            
            if orders:
                return orders[0]["id"]
            
            return None
        except:
            return None
    
    def _transform_duffel_response(self, offers_response: Dict) -> Tuple[ModelSearchResponse, FlightSearchResponse]:
        """Transform Duffel response to our standard format"""
        try:
            offers = offers_response.get("data", [])
            
            if not offers:
                error_msg = "No flights found for your search criteria"
                return (
                    create_error_model_response(error_msg),
                    create_error_search_response(error_msg, "duffel")
                )
            
            # Process offers into our format
            flight_offers = []
            model_offers = []
            
            for offer in offers[:10]:  # Limit to 10 offers
                try:
                    flight_offer = self._process_duffel_offer(offer)
                    model_offer = self._create_model_offer(flight_offer)
                    
                    flight_offers.append(flight_offer)
                    model_offers.append(model_offer)
                except Exception as e:
                    print(f"Error processing offer: {e}")
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
                provider_name="duffel"
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
            error_msg = f"Response transformation error: {str(e)}"
            return (
                create_error_model_response(error_msg),
                create_error_search_response(error_msg, "duffel")
            )
    
    def _process_duffel_offer(self, offer: Dict) -> FlightOffer:
        """Process a single Duffel offer into our format"""
        # Extract basic info
        offer_id = offer["id"]
        total_amount = float(offer["total_amount"]) / 100  # Duffel uses cents
        base_amount = float(offer["base_amount"]) / 100
        currency = offer["total_currency"]
        
        # Process slices to get segments
        all_segments = []
        airlines = set()
        total_stops = 0
        
        for slice_data in offer.get("slices", []):
            for segment in slice_data.get("segments", []):
                flight_segment = self._process_duffel_segment(segment)
                all_segments.append(flight_segment)
                airlines.add(flight_segment.airline_code)
                total_stops += flight_segment.stops
        
        # Get first and last segments for route info
        first_segment = all_segments[0] if all_segments else None
        last_segment = all_segments[-1] if all_segments else None
        
        # Determine trip type
        trip_type = "round_trip" if len(offer.get("slices", [])) > 1 else "one_way"
        if total_stops == 0:
            trip_type += "_direct" if trip_type == "one_way" else ""
        else:
            trip_type += "_connecting" if trip_type == "one_way" else ""
        
        # Calculate duration
        total_duration = offer.get("total_duration", "")
        duration_minutes = self._parse_duration_to_minutes(total_duration)
        
        return FlightOffer(
            flight_offer_id=f"duffel_{offer_id}",
            provider_offer_id=offer_id,
            price_total=total_amount,
            base_price=base_amount,
            currency=currency,
            origin=first_segment.departure_iata if first_segment else "",
            destination=last_segment.arrival_iata if last_segment else "",
            departure_time=first_segment.departure_time if first_segment else "",
            arrival_time=last_segment.arrival_time if last_segment else "",
            trip_type=trip_type,
            duration=total_duration,
            duration_minutes=duration_minutes or 0,
            flight_duration_minutes=duration_minutes or 0,
            total_segments=len(all_segments),
            stops=total_stops,
            airline_code=first_segment.airline_code if first_segment else "",
            airline_name=first_segment.airline_name if first_segment else "",
            airlines=list(airlines),
            segments=all_segments,
            checked_bags=0,  # Would need to parse from conditions
            cabin_bags=1,    # Default assumption
            seats_available=None,
            instant_ticketing=False,
            last_ticketing_date=None,
            provider_data={"full_offer": offer}
        )
    
    def _process_duffel_segment(self, segment: Dict) -> FlightSegment:
        """Process a single Duffel segment"""
        operating_carrier = segment.get("operating_carrier", {})
        aircraft = segment.get("aircraft", {})
        
        duration_minutes = self._parse_duration_to_minutes(segment.get("duration", ""))
        
        return FlightSegment(
            airline_code=operating_carrier.get("iata_code", ""),
            airline_name=operating_carrier.get("name", ""),
            flight_number=segment.get("flight_number", ""),
            departure_iata=segment.get("origin", {}).get("iata_code", ""),
            arrival_iata=segment.get("destination", {}).get("iata_code", ""),
            departure_terminal=segment.get("origin", {}).get("terminal"),
            arrival_terminal=segment.get("destination", {}).get("terminal"),
            departure_time=segment.get("departing_at", ""),
            arrival_time=segment.get("arriving_at", ""),
            duration=segment.get("duration", ""),
            duration_minutes=duration_minutes or 0,
            stops=0,  # Duffel segments are individual flights, stops are between segments
            aircraft_code=aircraft.get("iata_code"),
            aircraft_name=aircraft.get("name"),
            operating_carrier=operating_carrier.get("iata_code"),
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
    
    def _parse_duration_to_minutes(self, duration_str: str) -> Optional[int]:
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
    