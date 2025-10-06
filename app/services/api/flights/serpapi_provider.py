from typing import List, Optional, Tuple, Dict, Any
import requests
import hashlib
import time
from datetime import datetime
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from .base_provider import FlightProvider
from .response_models import (
    FlightSearchResponse,
    SimplifiedSearchResponse,
    PricingResponse,
    BookingResponse,
    CancellationResponse,
    Passenger,
    FlightOffer,
    FlightSegment,
    FlightSearchSummary,
    SimplifiedFlightOffer,
    Pricing,
    Baggage,
    FareDetails,
    AncillaryServices,
    CabinClass,
    TripType,
    PassengerType,
    create_error_search_response,
    create_error_model_response,
    create_error_pricing_response,
    create_error_booking_response,
    create_error_cancellation_response,
)
import logging
from .budget_airline_checker import BudgetAirlineChecker

logger = logging.getLogger(__name__)


class SerpApiProvider(FlightProvider):
    """SerpAPI implementation for Google Flights scraping"""

    def __init__(self, api_key: Optional[str] = None):
        try:
            self.api_key = api_key or self._get_env_var("SERPAPI_API_KEY")

            if not self.api_key:
                raise ValueError("SerpAPI key is required")

            self.base_url = "https://serpapi.com/search"
            self.budget_checker = BudgetAirlineChecker()
            self.executor = ThreadPoolExecutor(max_workers=3)

        except Exception as e:
            raise ValueError(f"Failed to initialize SerpAPI client: {e}")

    def _get_env_var(self, key: str) -> str:
        from os import getenv

        return getenv(key) or ""

    def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        passengers: List[Passenger] = [],
        travel_class: str = "ECONOMY",
    ) -> Tuple[SimplifiedSearchResponse, FlightSearchResponse]:
        """Search flights using SerpAPI (Google Flights)"""
        try:
            if not passengers:
                passengers = [
                    Passenger(
                        passenger_type=PassengerType.ADULT,
                        first_name="",
                        last_name="",
                        date_of_birth=datetime(1990, 1, 1),
                        gender="",
                        email="",
                        phone="",
                        nationality="",
                    )
                ]

            adults = sum(
                1 for p in passengers if p.passenger_type == PassengerType.ADULT
            )
            children = sum(
                1 for p in passengers if p.passenger_type == PassengerType.CHILD
            )
            infants = sum(
                1 for p in passengers if p.passenger_type == PassengerType.INFANT
            )

            # Map travel class to Google Flights values
            class_mapping = {
                "ECONOMY": "1",
                "PREMIUM_ECONOMY": "2",
                "BUSINESS": "3",
                "FIRST": "4",
            }
            travel_class_code = class_mapping.get(travel_class.upper(), "1")

            params = {
                "engine": "google_flights",
                "departure_id": origin.upper(),
                "arrival_id": destination.upper(),
                "outbound_date": departure_date,
                "currency": "USD",
                "hl": "en",
                "adults": adults,
                "children": children,
                "infants_in_seat": infants,
                "travel_class": travel_class_code,
                "api_key": self.api_key,
                "type": "1" if return_date else "2",  # 2=one-way, 1=round-trip
                "no_cache": "true",
                "deep_search": "true",
                "show_hidden": "true",
            }

            if return_date:
                params["return_date"] = return_date

            response = requests.get(self.base_url, params=params)
            response.raise_for_status()

            api_response = response.json()

            # Transform main SerpAPI response
            model_response, full_response = self._transform_serpapi_response(
                api_response, origin, destination, return_date
            )

            # Check budget airlines in background (non-blocking)
            budget_options: List[Dict[str, Any]] = []
            try:
                # Run budget check with timeout
                future = self.executor.submit(
                    self.budget_checker.check_budget_airlines_sync,
                    origin,
                    destination,
                    departure_date,
                    return_date,
                )
                budget_options = future.result(timeout=3.0)  # 3 second timeout

                if budget_options:
                    logger.info(
                        f"Found {len(budget_options)} budget airline alternatives"
                    )

            except Exception as e:
                logger.debug(f"Budget airline check failed: {e}")

            # Add budget options to both responses
            if budget_options:
                full_response.budget_airline_alternatives = budget_options
                model_response.budget_airline_alternatives = budget_options

            return model_response, full_response

        except requests.exceptions.RequestException as e:
            error_msg = f"SerpAPI search failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return (
                create_error_model_response(error_msg),
                create_error_search_response(error_msg, "serpapi"),
            )
        except Exception as e:
            error_msg = f"SerpAPI search error: {str(e)}"
            logger.exception(error_msg)
            return (
                create_error_model_response(error_msg),
                create_error_search_response(error_msg, "serpapi"),
            )

    def get_final_price(
        self,
        offer_id: str,
        additional_baggage: Optional[Dict] = None,
        selected_seats: Optional[Dict] = None,
    ) -> PricingResponse:
        """Get final confirmed pricing - SerpAPI shows final prices already"""
        return create_error_pricing_response(
            offer_id,
            "SerpAPI returns final prices in search. Use search results directly.",
        )

    def create_booking(
        self,
        offer_id: str,
        passengers: List[Passenger],
        booking_reference: str,
        emergency_contact: Optional[Any] = None,
    ) -> BookingResponse:
        """SerpAPI doesn't support booking - redirects to airline"""
        return create_error_booking_response(
            "SerpAPI provides search only. Book directly with the airline."
        )

    def cancel_booking(self, booking_reference: str) -> CancellationResponse:
        """SerpAPI doesn't support booking cancellation"""
        return create_error_cancellation_response(
            "SerpAPI doesn't support bookings. Cancel with the airline directly."
        )

    def get_provider_name(self) -> str:
        return "serpapi"

    def _transform_serpapi_response(
        self,
        api_response: Dict,
        origin: str,
        destination: str,
        return_date: Optional[str],
    ) -> Tuple[SimplifiedSearchResponse, FlightSearchResponse]:
        """Transform SerpAPI response to match Amadeus structure"""
        try:
            # Check for errors
            if "error" in api_response:
                error_msg = api_response.get("error", "Unknown SerpAPI error")
                return (
                    create_error_model_response(error_msg),
                    create_error_search_response(error_msg, "serpapi"),
                )
            
            google_flights_url = None
        
            # Method 1: From search_metadata (most reliable)
            if "search_metadata" in api_response:
                google_flights_url = api_response["search_metadata"].get("google_flights_url")
            
            # Method 2: From search_parameters as fallback
            if not google_flights_url and "search_parameters" in api_response:
                search_params = api_response["search_parameters"]
                if "google_flights_url" in search_params:
                    google_flights_url = search_params["google_flights_url"]
            
            # Method 3: Construct from raw_html_link if available
            if not google_flights_url and "search_metadata" in api_response:
                raw_link = api_response["search_metadata"].get("raw_html_link")
                if raw_link and "google.com/travel/flights" in raw_link:
                    google_flights_url = raw_link
            
            # Log the URL for debugging
            if google_flights_url:
                logger.info(f"Google Flights URL: {google_flights_url}")
            else:
                logger.warning("Could not extract Google Flights URL from SerpAPI response")

            # Get flight results
            best_flights = api_response.get("best_flights", [])
            other_flights = api_response.get("other_flights", [])
            all_flights = best_flights + other_flights

            if not all_flights:
                error_msg = "No flights found for your search criteria"
                return (
                    create_error_model_response(error_msg),
                    create_error_search_response(error_msg, "serpapi"),
                )

            # Process flights
            flight_offers = []
            model_offers = []

            for idx, flight_data in enumerate(all_flights):
                try:
                    flight_offer = self._process_serpapi_flight(
                        flight_data, idx, origin, destination, return_date
                    )
                    model_offer = self._create_model_offer(flight_offer)

                    flight_offers.append(flight_offer)
                    model_offers.append(model_offer)
                except Exception as e:
                    logger.warning(f"Error processing SerpAPI flight {idx}: {e}")
                    continue

            if not flight_offers:
                error_msg = "Failed to process any flights from results"
                return (
                    create_error_model_response(error_msg),
                    create_error_search_response(error_msg, "serpapi"),
                )

            # Create summary
            prices = [flight.pricing.price_total for flight in flight_offers]
            airlines = list(set([flight.airline_code for flight in flight_offers]))

            search_summary = FlightSearchSummary(
                total_offers=len(flight_offers),
                price_range_min=min(prices),
                price_range_max=max(prices),
                currency=flight_offers[0].pricing.currency,
                routes_available=1,
                airlines=airlines,
            )

            # Create responses
            full_response = FlightSearchResponse(
                success=True,
                search_summary=search_summary,
                flights=flight_offers,
                provider_name="serpapi",
                google_flights_url=google_flights_url,
            )

            model_response = SimplifiedSearchResponse(
                success=True,
                summary={
                    "total_found": len(flight_offers),
                    "price_range": f"${float(search_summary.price_range_min):.0f}-${float(search_summary.price_range_max):.0f}",
                    "airlines": airlines[:3],
                    "direct_flights": len([f for f in flight_offers if f.stops == 0]),
                    "connecting_flights": len(
                        [f for f in flight_offers if f.stops > 0]
                    ),
                },
                flights=model_offers,
                google_flights_url=google_flights_url,
            )

            return model_response, full_response

        except Exception as e:
            error_msg = f"SerpAPI response transformation error: {str(e)}"
            logger.exception(error_msg)
            return (
                create_error_model_response(error_msg),
                create_error_search_response(error_msg, "serpapi"),
            )

    def _process_serpapi_flight(
        self,
        flight_data: Dict,
        idx: int,
        origin: str,
        destination: str,
        return_date: Optional[str],
    ) -> FlightOffer:
        """Process single SerpAPI flight to match Amadeus structure"""

        # Generate unique offer ID
        flight_hash = hashlib.md5(str(flight_data).encode()).hexdigest()[:8]
        offer_id = f"serpapi_{idx}_{flight_hash}"

        # Extract pricing
        price = flight_data.get("price", 0)
        total_price = Decimal(str(price))
        base_price = total_price * Decimal("0.85")
        tax_amount = total_price - base_price

        pricing = Pricing(
            price_total=total_price,
            base_price=base_price,
            currency="USD",
            tax_amount=tax_amount,
        )

        # Process flight segments
        flights = flight_data.get("flights", [])
        segments = []

        for seg_idx, seg_data in enumerate(flights):
            segment = self._process_serpapi_segment(seg_data, seg_idx)
            segments.append(segment)

        if not segments:
            raise ValueError("No segments found in flight data")

        # Get layover information
        layovers = flight_data.get("layovers", [])

        # Calculate stops
        num_stops = len(layovers)

        # First and last segment for overall times
        first_segment = segments[0]
        last_segment = segments[-1]

        # Get total duration
        total_duration = flight_data.get("total_duration", 0)

        # Determine trip type
        if return_date:
            trip_type = TripType.ROUND_TRIP
        elif num_stops > 0:
            trip_type = TripType.ONE_WAY_CONNECTING
        else:
            trip_type = TripType.ONE_WAY_DIRECT

        # Extract carbon emissions
        carbon_data = flight_data.get("carbon_emissions", {})
        carbon_emissions_kg = (
            carbon_data.get("this_flight", 0) / 1000 if carbon_data else None
        )

        # Extract baggage, fare, and ancillary info
        baggage = self._extract_baggage_serpapi(flight_data)
        fare_details = self._extract_fare_details_serpapi(flight_data)
        ancillary_services = self._extract_ancillary_serpapi(flight_data)

        # Store additional provider data
        provider_data = {
            "full_offer": flight_data,
            "layovers": layovers,
            "carbon_emissions": carbon_data,
            "airline_logo": flight_data.get("airline_logo"),
            "departure_token": flight_data.get("departure_token"),
            "often_delayed": any(
                seg.get("often_delayed_by_over_30_min") for seg in flights
            ),
        }

        return FlightOffer(
            offer_id=offer_id,
            provider_offer_id=offer_id,
            origin=first_segment.departure_iata,
            destination=last_segment.arrival_iata,
            departure_time=first_segment.departure_time,
            arrival_time=last_segment.arrival_time,
            duration_minutes=total_duration,
            trip_type=trip_type,
            total_segments=len(segments),
            stops=num_stops,
            airline_code=first_segment.airline_code,
            pricing=pricing,
            baggage=baggage,
            fare_details=fare_details,
            ancillary_services=ancillary_services,
            segments=segments,
            provider_data=provider_data,
        )

    def _process_serpapi_segment(self, seg_data: Dict, seg_idx: int) -> FlightSegment:
        """Process single flight segment from SerpAPI"""

        # Parse departure and arrival times
        departure_airport = seg_data.get("departure_airport", {})
        arrival_airport = seg_data.get("arrival_airport", {})

        departure_time_str = departure_airport.get("time")
        arrival_time_str = arrival_airport.get("time")

        departure_time = (
            self._parse_serpapi_datetime(departure_time_str)
            if departure_time_str
            else datetime.now()
        )
        arrival_time = (
            self._parse_serpapi_datetime(arrival_time_str)
            if arrival_time_str
            else datetime.now()
        )

        # Calculate duration
        duration = seg_data.get("duration", 0)

        # Extract airline info
        airline = seg_data.get("airline", "")
        airline_logo = seg_data.get("airline_logo", "")
        flight_number = seg_data.get("flight_number", "")

        airline_code = (
            flight_number.split()[0] if flight_number else airline[:2].upper()
        )

        # Extract aircraft info
        airplane = seg_data.get("airplane", "Unknown")

        # Determine cabin class
        travel_class = seg_data.get("travel_class", "Economy")
        cabin_class = self._map_cabin_class_serpapi(travel_class)

        # Extract amenities
        extensions = seg_data.get("extensions", [])
        wifi_available = any("Wi-Fi" in ext or "WiFi" in ext for ext in extensions)
        power_outlets = any("power" in ext.lower() for ext in extensions)
        entertainment = any("entertainment" in ext.lower() for ext in extensions)

        meal_options = []
        for ext in extensions:
            if "meal" in ext.lower() or "food" in ext.lower():
                meal_options.append(ext)

        return FlightSegment(
            airline_code=airline_code,
            airline_name=airline,
            flight_number=flight_number,
            departure_iata=departure_airport.get("id", ""),
            arrival_iata=arrival_airport.get("id", ""),
            departure_time=departure_time,
            arrival_time=arrival_time,
            duration_minutes=duration,
            stops=0,
            cabin_class=cabin_class,
            departure_terminal=None,
            arrival_terminal=None,
            aircraft_code=airplane,
            aircraft_name=airplane,
            operating_carrier=airline_code,
            segment_id=f"seg_{seg_idx}",
            wifi_available=wifi_available,
            power_outlets=power_outlets,
            entertainment=entertainment,
            meal_options=meal_options,
        )

    def _extract_baggage_serpapi(self, flight_data: Dict) -> Baggage:
        """Extract baggage info from SerpAPI response"""
        extensions = []
        for flight in flight_data.get("flights", []):
            extensions.extend(flight.get("extensions", []))

        carry_on_included = any("carry-on bag" in ext.lower() for ext in extensions)
        checked_bags = sum(1 for ext in extensions if "checked bag" in ext.lower())

        return Baggage(
            checked_bags_included=checked_bags,
            cabin_bags_included=1 if carry_on_included else 0,
            carry_on_included=carry_on_included,
            baggage_policy={"extensions": extensions},
        )

    def _extract_fare_details_serpapi(self, flight_data: Dict) -> FareDetails:
        """Extract fare details from SerpAPI"""
        extensions = []
        for flight in flight_data.get("flights", []):
            extensions.extend(flight.get("extensions", []))

        fare_class = "Economy"
        for flight in flight_data.get("flights", []):
            travel_class = flight.get("travel_class", "")
            if travel_class:
                fare_class = travel_class
                break

        refundable = False
        changeable = True

        return FareDetails(
            fare_class=fare_class, refundable=refundable, changeable=changeable
        )

    def _extract_ancillary_serpapi(self, flight_data: Dict) -> AncillaryServices:
        """Extract ancillary services from SerpAPI"""
        extensions = []
        for flight in flight_data.get("flights", []):
            extensions.extend(flight.get("extensions", []))

        wifi_available = any("Wi-Fi" in ext or "WiFi" in ext for ext in extensions)

        return AncillaryServices(
            seat_selection_available=True,
            wifi_cost="Available" if wifi_available else None,
        )

    def _map_cabin_class_serpapi(self, travel_class: str) -> CabinClass:
        """Map SerpAPI travel class to CabinClass enum"""
        mapping = {
            "economy": CabinClass.ECONOMY,
            "premium economy": CabinClass.PREMIUM_ECONOMY,
            "business": CabinClass.BUSINESS,
            "first": CabinClass.FIRST,
        }
        return mapping.get(travel_class.lower(), CabinClass.ECONOMY)

    def _parse_serpapi_datetime(self, datetime_str: str) -> datetime:
        """Parse SerpAPI datetime string"""
        try:
            return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        except ValueError:
            try:
                return datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
            except:
                logger.warning(f"Failed to parse datetime: {datetime_str}")
                return datetime.now()

    def _create_model_offer(self, flight_offer: FlightOffer) -> SimplifiedFlightOffer:
        """Create simplified model offer"""
        duration_str = self._format_duration_minutes(flight_offer.duration_minutes)

        if flight_offer.stops == 0:
            stops_text = "Direct"
        else:
            stops_text = (
                f"{flight_offer.stops} stop{'s' if flight_offer.stops > 1 else ''}"
            )

        departure_time = flight_offer.departure_time.strftime("%H:%M")
        arrival_time = flight_offer.arrival_time.strftime("%H:%M")

        if flight_offer.arrival_time.date() > flight_offer.departure_time.date():
            arrival_time += "+1"

        airline_name = (
            flight_offer.segments[0].airline_name
            if flight_offer.segments
            else "Unknown"
        )

        return SimplifiedFlightOffer(
            id=flight_offer.offer_id,
            price=f"${float(flight_offer.pricing.price_total):.0f}",
            airline=airline_name,
            route=f"{flight_offer.origin} → {flight_offer.destination}",
            departure=departure_time,
            arrival=arrival_time,
            duration=duration_str,
            stops=stops_text,
        )

    def _format_duration_minutes(self, duration_minutes: int) -> str:
        """Format duration to readable string"""
        if not duration_minutes:
            return ""

        hours = duration_minutes // 60
        minutes = duration_minutes % 60

        if hours and minutes:
            return f"{hours}h {minutes}m"
        elif hours:
            return f"{hours}h"
        else:
            return f"{minutes}m"
