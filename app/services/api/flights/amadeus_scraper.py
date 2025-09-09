import requests
from typing import Dict, Any, Optional, List, Tuple, Protocol
import datetime
import time
import hashlib
from collections import deque
from threading import Lock
from abc import ABC, abstractmethod
import json
import re


class RateLimiterProtocol(Protocol):
    """Protocol for rate limiting functionality"""
    def wait_if_needed(self) -> None:
        ...


class HTTPClientProtocol(Protocol):
    """Protocol for HTTP client functionality"""
    def post(self, url: str, **kwargs) -> requests.Response:
        ...
    
    def get(self, url: str, **kwargs) -> requests.Response:
        ...


class SimpleAmadeusRateLimiter:
    """Simple rate limiter for Amadeus API requests"""
    
    def __init__(self, min_interval: float = 0.11, max_requests_per_second: int = 8):
        self.last_request_time = 0
        self.min_interval = min_interval
        self.request_count = 0
        self.lock = Lock()
        
        # Track requests in last second
        self.recent_requests = deque()
        self.max_requests_per_second = max_requests_per_second
    
    def wait_if_needed(self) -> None:
        """Call this before each Amadeus API request"""
        with self.lock:
            now = time.time()
            
            # Clean old requests (older than 1 second)
            while self.recent_requests and now - self.recent_requests[0] > 1.0:
                self.recent_requests.popleft()
            
            # Check requests per second
            if len(self.recent_requests) >= self.max_requests_per_second:
                wait_time = 1.0 - (now - self.recent_requests[0])
                if wait_time > 0:
                    print(f"Rate limit: waiting {wait_time:.2f}s")
                    time.sleep(wait_time)
                    now = time.time()
            
            # Check minimum interval
            time_since_last = now - self.last_request_time
            if time_since_last < self.min_interval:
                wait_time = self.min_interval - time_since_last
                print(f"Rate limit: waiting {wait_time:.2f}s")
                time.sleep(wait_time)
                now = time.time()
            
            # Record this request
            self.last_request_time = now
            self.recent_requests.append(now)
            self.request_count += 1


class AmadeusAPIError(Exception):
    """Custom exception for Amadeus API errors"""
    pass


class AmadeusAuthenticationError(AmadeusAPIError):
    """Raised when authentication fails"""
    pass


class AmadeusValidationError(AmadeusAPIError):
    """Raised when input validation fails"""
    pass


class AmadeusConnectionError(AmadeusAPIError):
    """Raised when connection to Amadeus API fails"""
    pass


class DateValidator:
    """Handles date validation logic"""
    
    @staticmethod
    def validate_dates(departure_date: str, return_date: Optional[str] = None) -> Optional[Dict[str, str]]:
        """
        Validates departure and return dates.
        Returns error dict if validation fails, None if valid.
        """
        try:
            dep_dt = datetime.datetime.strptime(departure_date, "%Y-%m-%d").date()
        except ValueError:
            return {
                "error": "The departure date is not in the correct format (YYYY-MM-DD). "
                        "Please check the date and try again."
            }

        if dep_dt < datetime.date.today():
            return {
                "error": f"The departure date cannot be in the past. "
                        f"You entered '{dep_dt}', but today is '{datetime.date.today()}'."
            }

        if return_date:
            try:
                ret_dt = datetime.datetime.strptime(return_date, "%Y-%m-%d").date()
            except ValueError:
                return {
                    "error": "The return date is not in the correct format (YYYY-MM-DD). "
                            "Please check the date and try again."
                }

            if ret_dt < dep_dt:
                return {
                    "error": "The return date cannot be before the departure date."
                }
        
        return None

class FlightOfferProcessor:
    """Fixed flight offer processor with correct duration and routing logic"""
    
    def __init__(self):
        pass
    
    def parse_duration_to_minutes(self, duration_str: Optional[str] = None) -> Optional[int]:
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
    
    def generate_flight_offer_id(self, offer: Dict, index: int) -> str:
        """Generate unique flight offer ID"""
        if offer.get("id"):
            amadeus_id = offer["id"]
            return f"FO_{amadeus_id}_{index}"
        else:
            first_segment = offer["itineraries"][0]["segments"][0]
            signature = (
                f"{first_segment['departure']['iataCode']}-"
                f"{first_segment['arrival']['iataCode']}-"
                f"{offer['price']['grandTotal']}-{index}-{int(time.time())}"
            )
            hash_id = hashlib.md5(signature.encode()).hexdigest()[:8].upper()
            return f"FO_{hash_id}_{index}"
    
    def determine_trip_type(self, itineraries: List[Dict]) -> str:
        """Determine trip type based on itineraries"""
        if len(itineraries) == 1:
            segments = itineraries[0]["segments"]
            return "one_way_direct" if len(segments) == 1 else "one_way_connecting"
        elif len(itineraries) == 2:
            outbound_origin = itineraries[0]["segments"][0]["departure"]["iataCode"]
            outbound_dest = itineraries[0]["segments"][-1]["arrival"]["iataCode"]
            return_origin = itineraries[1]["segments"][0]["departure"]["iataCode"]
            return_dest = itineraries[1]["segments"][-1]["arrival"]["iataCode"]
            
            if outbound_origin == return_dest and outbound_dest == return_origin:
                return "round_trip"
            else:
                return "multi_city"
        else:
            return "multi_city"
    
    def process_api_response(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """Process and optimize API response data"""
        flights = []
        
        # Dictionaries for lookups
        airline_dict = api_response.get("dictionaries", {}).get("carriers", {})
        aircraft_dict = api_response.get("dictionaries", {}).get("aircraft", {})

        for offer_idx, offer in enumerate(api_response.get("data", [])):
            try:
                processed_flight = self._process_single_offer(
                    offer, offer_idx, airline_dict, aircraft_dict
                )
                flights.append(processed_flight)
            except Exception as e:
                print(f"Error processing offer {offer_idx}: {e}")
                continue

        # Sort by price
        flights.sort(key=lambda x: x.get("price_total", float('inf')))
        
        return {
            "flights": flights,
            "search_summary": self._create_search_summary(flights)
        }
    
    def _process_single_offer(self, offer: Dict, offer_idx: int, 
                             airline_dict: Dict, aircraft_dict: Dict) -> Dict[str, Any]:
        """Process a single flight offer - FIXED VERSION"""
        # Generate IDs
        amadeus_offer_id = offer.get("id")
        our_flight_offer_id = self.generate_flight_offer_id(offer, offer_idx)
        
        # Process itineraries
        itineraries = []
        all_segments = []
        total_duration_minutes = 0
        total_stops = 0
        
        for itinerary_idx, itinerary in enumerate(offer.get("itineraries", [])):
            segments = []
            itinerary_duration = self.parse_duration_to_minutes(itinerary.get("duration"))
            
            for segment in itinerary.get("segments", []):
                processed_segment = self._process_segment(segment, airline_dict, aircraft_dict)
                segments.append(processed_segment)
                all_segments.append(processed_segment)
                
                # Count stops (direct flight has 0 stops)
                stops = segment.get("numberOfStops", 0)
                total_stops += stops
            
            # Add total duration for this itinerary
            if itinerary_duration:
                total_duration_minutes += itinerary_duration
            
            itineraries.append({
                "type": "outbound" if itinerary_idx == 0 else "return",
                "duration": itinerary.get("duration"),
                "duration_minutes": itinerary_duration,
                "segments": segments
            })
        
        # Process pricing
        price_info = offer.get("price", {})
        
        # Process baggage
        baggage_info = self._process_baggage_info(offer.get("travelerPricings", []))
        
        # Get route information from first and last segments
        first_segment = all_segments[0] if all_segments else {}
        last_segment = all_segments[-1] if all_segments else {}
        
        # Calculate total flight duration (excluding layovers for multi-segment)
        flight_duration_minutes = sum(
            self.parse_duration_to_minutes(seg.get("duration", "")) or 0 
            for seg in all_segments
        )
        
        return {
            # Critical IDs
            "flight_offer_id": our_flight_offer_id,
            "amadeus_offer_id": amadeus_offer_id,
            
            # Price info
            "price_total": float(price_info.get("grandTotal", 0)),
            "base_price": float(price_info.get("base", 0)),
            "currency": price_info.get("currency", "USD"),
            
            # Route info
            "origin": first_segment.get("departure_iata"),
            "destination": last_segment.get("arrival_iata"),
            "departure_time": first_segment.get("departure_time"),
            "arrival_time": last_segment.get("arrival_time"),
            
            # Trip details
            "trip_type": self.determine_trip_type(offer.get("itineraries", [])),
            "duration": itineraries[0].get("duration") if itineraries else None,
            "duration_minutes": total_duration_minutes,  # FIXED: Now calculated correctly
            "flight_duration_minutes": flight_duration_minutes,  # Pure flight time
            "total_segments": len(all_segments),
            "stops": total_stops,  # FIXED: Use 'stops' not 'stops_total'
            
            # Airline info (from first segment)
            "airline_code": first_segment.get("airline_code"),
            "airline_name": first_segment.get("airline_name"),
            "airlines": list(set(seg.get("airline_code") for seg in all_segments if seg.get("airline_code"))),  # All unique airlines
            
            # Segments
            "segments": all_segments,
            
            # Baggage
            "checked_bags": baggage_info.get("checked_bags", 0),
            "cabin_bags": baggage_info.get("cabin_bags", 1),
            
            # Booking constraints
            "seats_available": offer.get("numberOfBookableSeats"),
            "instant_ticketing": offer.get("instantTicketingRequired", False),
            "last_ticketing_date": offer.get("lastTicketingDate"),
            
            # Full data for booking
            "_full_amadeus_data": {
                "offer_id": amadeus_offer_id,
                "complete_offer": offer,
                "itineraries_detailed": itineraries,
                "traveler_pricings": offer.get("travelerPricings", []),
                "validating_airlines": offer.get("validatingAirlineCodes", [])
            }
        }
    
    def _process_segment(self, segment: Dict, airline_dict: Dict, aircraft_dict: Dict) -> Dict[str, Any]:
        """Process a single flight segment - FIXED VERSION"""
        airline_code = segment.get("carrierCode")
        aircraft_code = segment.get("aircraft", {}).get("code")
        duration_minutes = self.parse_duration_to_minutes(segment.get("duration"))
        
        return {
            # Basic flight info
            "airline_code": airline_code,
            "airline_name": airline_dict.get(airline_code, "Unknown"),
            "flight_number": segment.get("number"),
            
            # Route info
            "departure_iata": segment["departure"]["iataCode"],
            "arrival_iata": segment["arrival"]["iataCode"],
            "departure_terminal": segment["departure"].get("terminal"),
            "arrival_terminal": segment["arrival"].get("terminal"),
            "departure_time": segment["departure"]["at"],
            "arrival_time": segment["arrival"]["at"],
            
            # Flight details
            "duration": segment.get("duration"),
            "duration_minutes": duration_minutes,  # FIXED: Now parsed correctly
            "stops": segment.get("numberOfStops", 0),
            
            # Aircraft info
            "aircraft_code": aircraft_code,
            "aircraft_name": aircraft_dict.get(aircraft_code, "Unknown") if aircraft_code else "Unknown",
            
            # Operating info
            "operating_carrier": segment.get("operating", {}).get("carrierCode", airline_code),
            "operating_carrier_name": segment.get("operating", {}).get("carrierName", ""),
            
            # Segment ID for reference
            "segment_id": segment.get("id")
        }
    
    def _process_baggage_info(self, traveler_pricings: List[Dict]) -> Dict[str, int]:
        """Process baggage information"""
        baggage_info = {"checked_bags": 0, "cabin_bags": 1}  # Default values
        
        if traveler_pricings:
            fare_details = traveler_pricings[0].get("fareDetailsBySegment", [])
            if fare_details:
                first_segment_fare = fare_details[0]
                
                if "includedCheckedBags" in first_segment_fare:
                    baggage_info["checked_bags"] = first_segment_fare["includedCheckedBags"].get("quantity", 0)
                
                if "includedCabinBags" in first_segment_fare:
                    baggage_info["cabin_bags"] = first_segment_fare["includedCabinBags"].get("quantity", 1)
        
        return baggage_info
    
    def _create_search_summary(self, flights: List[Dict]) -> Dict[str, Any]:
        """Create search summary from processed flights"""
        if not flights:
            return {
                "total_offers": 0,
                "price_range": {"min": 0, "max": 0, "currency": "USD"},
                "airlines": [],
                "routes_available": 0
            }
        
        # Get all unique airlines across all flights
        all_airlines = set()
        for flight in flights:
            if flight.get("airlines"):
                all_airlines.update(flight["airlines"])
            elif flight.get("airline_code"):
                all_airlines.add(flight["airline_code"])
        
        return {
            "total_offers": len(flights),
            "price_range": {
                "min": flights[0]["price_total"],
                "max": flights[-1]["price_total"],
                "currency": flights[0]["currency"]
            },
            "airlines": list(all_airlines),
            "routes_available": len(set(
                f"{f['origin']}-{f['destination']}" 
                for f in flights 
                if f.get('origin') and f.get('destination')
            ))
        }
    
    def extract_model_response(self, full_response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract only essential data for model response"""
        if 'flights' not in full_response:
            return full_response
        
        # Only include top 3-5 flights
        flights = full_response['flights'][:3]
        
        minimal_flights = []
        for flight in flights:
            # Format duration nicely
            duration_str = ""
            if flight.get('duration'):
                duration_str = flight['duration'].replace('PT', '').replace('H', 'h ').replace('M', 'm')
            
            # Format stops
            stops = flight.get('stops', 0)
            stops_text = "Direct" if stops == 0 else f"{stops} stop{'s' if stops > 1 else ''}"
            
            minimal_flight = {
                'id': flight.get('flight_offer_id'),
                'price': f"${flight.get('price_total', 0):.0f}",
                'airline': flight.get('airline_name', 'Unknown'),
                'route': f"{flight.get('origin')} → {flight.get('destination')}",
                'departure': flight.get('departure_time', '').split('T')[1][:5] if 'T' in flight.get('departure_time', '') else '',
                'arrival': flight.get('arrival_time', '').split('T')[1][:5] if 'T' in flight.get('arrival_time', '') else '',
                'duration': duration_str,
                'stops': stops_text
            }
            minimal_flights.append(minimal_flight)
        
        # Simplified search summary
        summary = full_response.get('search_summary', {})
        minimal_summary = {
            'total_found': summary.get('total_offers', 0),
            'price_range': f"${summary.get('price_range', {}).get('min', 0):.0f}-${summary.get('price_range', {}).get('max', 0):.0f}",
            'airlines': summary.get('airlines', [])[:3]
        }
        
        return {
            'search_id': full_response.get('search_id'),
            'flights': minimal_flights,
            'summary': minimal_summary
        }


class AmadeusFlightScraper:
    """Main flight scraper class with improved testability"""
    
    def __init__(self, 
                 client_id: Optional[str] = None,
                 client_secret: Optional[str] = None,
                 rate_limiter: Optional[RateLimiterProtocol] = None,
                 http_client: Optional[HTTPClientProtocol] = None,
                 date_validator: Optional[DateValidator] = None,
                 flight_processor: Optional[FlightOfferProcessor] = None):
        
        # Dependency injection for testability
        self.client_id = client_id or self._get_env_var("AMADEUS_CLIENT_ID")
        self.client_secret = client_secret or self._get_env_var("AMADEUS_CLIENT_SECRET")
        
        if not self.client_id or not self.client_secret:
            raise AmadeusAuthenticationError("Amadeus credentials not found.")
        
        self.rate_limiter = rate_limiter or SimpleAmadeusRateLimiter()
        self.http_client = http_client or requests
        self.date_validator = date_validator or DateValidator()
        self.flight_processor = flight_processor or FlightOfferProcessor()
        
        self.token = None
        self.headers = {}
        
        # Initialize token on creation
        try:
            self._authenticate()
        except Exception as e:
            raise AmadeusAuthenticationError(f"Failed to authenticate: {e}")
    
    def _get_env_var(self, key: str) -> Optional[str]:
        """Get environment variable - separated for testing"""
        from os import getenv
        return getenv(key)
    
    def _authenticate(self) -> None:
        """Authenticate with Amadeus API"""
        self.token = self._get_access_token()
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def _get_access_token(self) -> str:
        """Fetch access token from Amadeus API"""
        url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            response = self.http_client.post(url, data=data)
            response.raise_for_status()
            return response.json()["access_token"]
        except requests.exceptions.RequestException as e:
            raise AmadeusAuthenticationError(f"Error fetching Amadeus token: {e}")
    
    def search_flights(self,
                      origin: str,
                      destination: str,
                      departure_date: str,
                      return_date: Optional[str] = None,
                      adults: int = 1,
                      children: int = 0,
                      infants: int = 0,
                      travel_class: str = "ECONOMY",
                      currency: str = "USD",
                      max_results: int = 5) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Search for flight offers
        Returns (model_response, full_response) tuple
        """
        # Input validation
        origin = origin.upper().strip()
        destination = destination.upper().strip()
        
        if not origin or not destination:
            return {"error": "Origin and destination are required"}, {}
        
        # Date validation
        validation_error = self.date_validator.validate_dates(departure_date, return_date)
        if validation_error:
            return validation_error, {}
        
        # Rate limiting
        self.rate_limiter.wait_if_needed()
        
        # Prepare API request
        url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "adults": adults,
            "children": children,
            "infants": infants,
            "travelClass": travel_class,
            "currencyCode": currency,
            "max": max_results,
        }
        
        if return_date:
            params["returnDate"] = return_date
        
        try:
            response = self.http_client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            # Process response
            api_response = response.json()
            print(f"DEBUG: Raw API response for {departure_date}:")
            print(f"  - Status: {response.status_code}")
            print(f"  - Data count: {len(api_response.get('data', []))}")
            print(f"  - Has errors: {'errors' in api_response}")
            if 'errors' in api_response:
                print(f"  - Errors: {api_response['errors']}")
            print("FINISHED FLIGHT SEARCH DEBUG")
            
            full_response = self.flight_processor.process_api_response(api_response)
            model_response = self.flight_processor.extract_model_response(full_response)
            
            print(f"Processed {len(full_response.get('flights', []))} flight offers")
            
            print("The model reponse for the flight")
            print(json.dumps(model_response, indent=4))
            
            return model_response, full_response
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 400:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get('errors', [{}])[0].get('detail', 'Bad request')
                return {"error": f"Search failed: {error_msg}"}, {}
            raise AmadeusConnectionError(f"API request failed: {e}")
        except requests.exceptions.RequestException as e:
            raise AmadeusConnectionError(f"Connection error: {e}")
        except Exception as e:
            return {"error": "An unexpected error occurred during flight search"}, {}
    
    def get_full_flight_details(self, flight_offer_id: str, cached_results: Dict) -> Optional[Dict[str, Any]]:
        """Retrieve full flight details for booking"""
        for flight in cached_results.get("flights", []):
            if flight.get("flight_offer_id") == flight_offer_id:
                full_data = flight.get("_full_amadeus_data", {})
                
                return {
                    "flight_offer_id": flight_offer_id,
                    "amadeus_offer_id": full_data.get("offer_id"),
                    "complete_amadeus_offer": full_data.get("complete_offer"),
                    "detailed_itineraries": full_data.get("itineraries_detailed"),
                    "traveler_pricings": full_data.get("traveler_pricings"),
                    "validating_airlines": full_data.get("validating_airlines"),
                    "basic_info": {
                        "price_total": flight.get("price_total"),
                        "origin": flight.get("origin"),
                        "destination": flight.get("destination"),
                        "departure_time": flight.get("departure_time"),
                        "airline_name": flight.get("airline_name")
                    }
                }
        
        return None
    
    def price_flight_offers(self, flight_offers_data: List[Dict]) -> Dict[str, Any]:
        """Get confirmed pricing for flight offers"""
        self.rate_limiter.wait_if_needed()
        
        url = "https://test.api.amadeus.com/v1/shopping/flight-offers/pricing"
        
        # Extract Amadeus offer data
        amadeus_offers = []
        for offer_data in flight_offers_data:
            full_data = offer_data.get('_full_amadeus_data', {})
            complete_offer = full_data.get('complete_offer')
            
            if not complete_offer:
                raise AmadeusValidationError("Missing complete Amadeus offer data for pricing")
            
            amadeus_offers.append(complete_offer)
        
        pricing_request = {
            "data": {
                "type": "flight-offers-pricing",
                "flightOffers": amadeus_offers
            }
        }
        
        try:
            response = self.http_client.post(url, headers=self.headers, json=pricing_request)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise AmadeusConnectionError(f"Failed to get flight pricing: {e}")
    
    def create_flight_booking(self, 
                            priced_offers: List[Dict], 
                            passengers_data: List[Dict], 
                            booking_reference: str) -> Dict[str, Any]:
        """Create flight booking/PNR"""
        self.rate_limiter.wait_if_needed()
        
        url = "https://test.api.amadeus.com/v1/booking/flight-orders"
        
        # Prepare travelers data
        travelers = self._prepare_travelers_data(passengers_data)
        
        # Prepare booking request
        booking_request = {
            "data": {
                "type": "flight-order",
                "flightOffers": priced_offers,
                "travelers": travelers,
                "remarks": {
                    "general": [{
                        "subType": "GENERAL_MISCELLANEOUS",
                        "text": f"Booking via Rafiki - Ref: {booking_reference}"
                    }]
                }
            }
        }
        
        try:
            response = self.http_client.post(url, headers=self.headers, json=booking_request)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 400:
                error_details = response.json() if response.content else {}
                raise AmadeusValidationError(f"Booking validation failed: {error_details}")
            raise AmadeusConnectionError(f"Failed to create booking: {e}")
        except requests.exceptions.RequestException as e:
            raise AmadeusConnectionError(f"Booking request failed: {e}")
    
    def _prepare_travelers_data(self, passengers_data: List[Dict]) -> List[Dict]:
        """Prepare travelers data in Amadeus format"""
        travelers = []
        
        for idx, passenger in enumerate(passengers_data):
            traveler = {
                "id": str(idx + 1),
                "dateOfBirth": passenger.get('date_of_birth', '1990-01-01'),
                "name": {
                    "firstName": passenger.get('first_name', ''),
                    "lastName": passenger.get('last_name', '')
                },
                "gender": passenger.get('gender', 'UNKNOWN'),
                "contact": {
                    "emailAddress": passenger.get('email', ''),
                    "phones": []
                }
            }
            
            # Add phone if available
            if passenger.get('phone'):
                traveler["contact"]["phones"] = [{
                    "deviceType": "MOBILE",
                    "countryCallingCode": "1",
                    "number": passenger['phone']
                }]
            
            # Add documents if available
            if passenger.get('document_number'):
                traveler["documents"] = [{
                    "documentType": "PASSPORT",
                    "number": passenger['document_number'],
                    "expiryDate": passenger.get('document_expiry', '2030-12-31'),
                    "issuanceCountry": passenger.get('nationality', 'US'),
                    "validityCountry": passenger.get('nationality', 'US'),
                    "nationality": passenger.get('nationality', 'US'),
                    "holder": True
                }]
            
            travelers.append(traveler)
        
        return travelers


# Factory function for easy instantiation
def create_amadeus_scraper(**kwargs) -> AmadeusFlightScraper:
    """Factory function to create AmadeusFlightScraper instance"""
    return AmadeusFlightScraper(**kwargs)


# For backward compatibility
amadeus_limiter = SimpleAmadeusRateLimiter()