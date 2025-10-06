from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
import time
import threading
from app.models.web_search_strategy import SearchStrategy
from app.models.web_search_data import SearchRequest
from app.models.web_search_data_manager import data_manager
from app.services.api.flights.response_models import Passenger, PassengerType
from app.services.api.flights.amadeus_provider import AmadeusProvider
from app.services.api.flights.serpapi_provider import SerpApiProvider
import logging
import psutil
import os

logger = logging.getLogger(__name__)

USE_SERPAPI = os.getenv("USE_SERPAPI", "false").lower() == "true"


class RateLimiter:
    """Rate limiting for API requests"""
    def __init__(self, max_requests_per_second=2):
        self.max_requests_per_second = max_requests_per_second
        self.min_interval = 1.0 / max_requests_per_second
        self.last_request_time = 0
        self.lock = threading.Lock()

    def wait_if_needed(self):
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time

            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)

            self.last_request_time = time.time()


# Global rate limiter instance
RATE_LIMIT = 5 if USE_SERPAPI else 2
rate_limiter = RateLimiter(max_requests_per_second=RATE_LIMIT)


@dataclass
class SearchResult:
    """Result from a single search strategy"""
    strategy: SearchStrategy
    flights: List[Dict]
    success: bool
    error_message: Optional[str] = None
    budget_alternatives: List[Dict] = field(default_factory=list)
    google_flights_url: Optional[str] = None

def execute_flight_searches(
    strategies: List[SearchStrategy], search_request: SearchRequest
) -> Dict:
    """Execute all search strategies in parallel with rate limiting"""

    request_start = datetime.now()
    process = psutil.Process(os.getpid())
    mem_start = process.memory_info().rss / 1024 / 1024

    logger.info(f"Starting flight search at {request_start}")
    logger.info(f"Memory at start: {mem_start:.2f} MB")
    logger.info(
        f"Processing {len(strategies)} strategies (rate limited to {RATE_LIMIT} req/sec)"
    )

    search_results = []
    all_budget_alternatives = []
    google_flights_urls = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_strategy = {}
        for strategy in strategies:
            future = executor.submit(_execute_single_search, strategy, search_request)
            future_to_strategy[future] = strategy

        for future in future_to_strategy:
            strategy = future_to_strategy[future]
            try:
                strategy_start = datetime.now()
                logger.debug(
                    f"Waiting for strategy '{strategy.strategy_type}': {strategy.explanation}"
                )

                flights, budget_alternatives, google_url = future.result(timeout=60)

                # Collect budget alternatives
                if budget_alternatives:
                    all_budget_alternatives.extend(budget_alternatives)

                # Collect Google Flights URLs
                if google_url:
                    google_flights_urls.append(google_url)

                strategy_duration = (datetime.now() - strategy_start).total_seconds()
                logger.debug(
                    f"Strategy '{strategy.strategy_type}' completed in {strategy_duration:.2f}s"
                )

                enriched_flights = _enrich_flight_results(
                    flights, strategy, search_request, google_url
                )
                search_results.append(
                    SearchResult(
                        strategy=strategy,
                        flights=enriched_flights,
                        success=True,
                        budget_alternatives=budget_alternatives,
                        google_flights_url=google_url,
                    )
                )
                logger.debug(
                    f"Strategy '{strategy.strategy_type}' returned {len(enriched_flights)} flights"
                )

                mem_current = process.memory_info().rss / 1024 / 1024
                mem_delta = mem_current - mem_start
                logger.debug(
                    f"Memory now: {mem_current:.2f} MB (delta +{mem_delta:.2f} MB)"
                )

            except Exception as e:
                strategy_duration = (datetime.now() - strategy_start).total_seconds()
                logger.warning(
                    f"Strategy '{strategy.strategy_type}' failed after {strategy_duration:.2f}s: {str(e)}"
                )
                search_results.append(SearchResult(strategy, [], False, str(e)))

    total_duration = (datetime.now() - request_start).total_seconds()
    mem_end = process.memory_info().rss / 1024 / 1024
    mem_total_delta = mem_end - mem_start

    logger.info(f"Total search duration: {total_duration:.2f}s")
    logger.info(f"Memory at end: {mem_end:.2f} MB (delta +{mem_total_delta:.2f} MB)")
    logger.info(
        f"Completed {len([r for r in search_results if r.success])}/{len(search_results)} strategies successfully"
    )

    if total_duration > 25:
        logger.warning(
            f"Search took {total_duration:.2f}s - approaching timeout threshold!"
        )

    # Deduplicate budget alternatives by airline code
    unique_budget = {
        alt["airline_code"]: alt
        for alt in all_budget_alternatives
        if "airline_code" in alt
    }
    budget_alternatives_list = list(unique_budget.values())

    # Use the first available Google Flights URL (typically from direct search)
    primary_google_url = google_flights_urls[0] if google_flights_urls else None

    return _process_search_results(
        search_results, search_request, budget_alternatives_list, primary_google_url
    )


def _execute_single_search(
    strategy: SearchStrategy, search_request: SearchRequest
) -> Tuple[List[Dict], List[Dict], Optional[str]]:
    """Execute a single search strategy using configured provider with rate limiting"""

    logger.debug(f"Executing search for strategy: {strategy.explanation}")

    passengers = _convert_search_request_to_passengers(search_request)

    # Select provider based on configuration
    if USE_SERPAPI:
        provider = SerpApiProvider()
        logger.debug("Using SerpAPI provider")
    else:
        provider = AmadeusProvider()
        logger.debug("Using Amadeus provider")

    if search_request.is_roundtrip:
        return _search_roundtrip_strategy(
            provider, strategy, search_request, passengers
        )
    else:
        return _search_oneway_strategy(provider, strategy, search_request, passengers)


def _convert_search_request_to_passengers(
    search_request: SearchRequest,
) -> List[Passenger]:
    """Convert SearchRequest to list of Passenger objects"""
    passengers = []

    for i in range(search_request.adults):
        passengers.append(
            Passenger(
                passenger_type=PassengerType.ADULT,
                first_name=f"Adult{i+1}",
                last_name="Passenger",
                date_of_birth=datetime(1990, 1, 1),
                gender="",
                nationality="US",
                email="",
                phone="",
            )
        )

    for i in range(search_request.children):
        passengers.append(
            Passenger(
                passenger_type=PassengerType.CHILD,
                first_name=f"Child{i+1}",
                last_name="Passenger",
                date_of_birth=datetime(2015, 1, 1),
                gender="",
                nationality="US",
                email="",
                phone="",
            )
        )

    for i in range(search_request.infants):
        passengers.append(
            Passenger(
                passenger_type=PassengerType.INFANT,
                first_name=f"Infant{i+1}",
                last_name="Passenger",
                date_of_birth=datetime(2023, 1, 1),
                gender="",
                nationality="US",
                email="",
                phone="",
            )
        )

    return passengers


def _search_oneway_strategy(
    provider,
    strategy: SearchStrategy,
    search_request: SearchRequest,
    passengers: List[Passenger],
) -> Tuple[List[Dict], List[Dict], Optional[str]]:
    """Search one-way flights with support for hub connections"""

    if len(strategy.outbound_route) == 2:
        # Direct flight - returns budget alternatives and Google Flights URL
        return _search_direct_flight(provider, strategy, search_request, passengers)

    elif len(strategy.outbound_route) == 3:
        # Hub connection: Origin → Hub → Destination
        flights = _search_hub_connection(provider, strategy, search_request, passengers)
        return flights, [], None  # Hub connections don't have budget alternatives or URLs

    else:
        logger.warning(
            f"Unsupported route complexity: {len(strategy.outbound_route)} segments"
        )
        return [], [], None

def _validate_route(origin: str, destination: str) -> bool:
    """
    Validate that origin and destination are different.
    Returns True if valid, False if invalid.
    """
    if origin == destination:
        logger.warning(f"Invalid route: origin and destination are the same ({origin})")
        return False
    return True

def _search_direct_flight(
    provider,
    strategy: SearchStrategy,
    search_request: SearchRequest,
    passengers: List[Passenger],
) -> Tuple[List[Dict], List[Dict], Optional[str]]:
    """Search direct flights and return budget airline alternatives + Google Flights URL"""
    
    origin, destination = strategy.outbound_route
    
    # Validate route before making API call
    if not _validate_route(origin, destination):
        logger.info(f"Skipping search for {origin} -> {destination} (same airport)")
        return [], [], None
    
    rate_limiter.wait_if_needed()

    try:
        origin, destination = strategy.outbound_route
        logger.debug(f"Direct API call: {origin} -> {destination}")

        simplified_response, full_response = provider.search_flights(
            origin=origin,
            destination=destination,
            departure_date=search_request.departure_date,
            return_date=None,
            passengers=passengers,
            travel_class=search_request.travel_class.upper(),
        )

        if full_response.success:
            logger.debug(
                f"Direct flight success: {len(full_response.flights)} flights found"
            )
            flights = [offer.__dict__ for offer in full_response.flights]
            budget_alternatives = full_response.budget_airline_alternatives or []
            google_flights_url = getattr(full_response, 'google_flights_url', None)

            if budget_alternatives:
                logger.info(
                    f"Found {len(budget_alternatives)} budget airline alternatives for {origin} -> {destination}"
                )

            if google_flights_url:
                logger.info(f"Google Flights URL: {google_flights_url}")

            return flights, budget_alternatives, google_flights_url
        else:
            logger.debug("Direct flight: no results")
            return [], [], None

    except Exception as e:
        logger.error(f"Direct flight API call failed: {str(e)}")
        raise

def _search_hub_connection(
    provider,
    strategy: SearchStrategy,
    search_request: SearchRequest,
    passengers: List[Passenger],
) -> List[Dict]:
    """Search hub connections by finding compatible flight pairs"""

    origin, hub, destination = strategy.outbound_route
    
    # Validate all segments
    if not _validate_route(origin, hub):
        logger.info(f"Skipping hub connection: invalid first leg {origin} -> {hub}")
        return []
    
    if not _validate_route(hub, destination):
        logger.info(f"Skipping hub connection: invalid second leg {hub} -> {destination}")
        return []
    
    # Additional validation: ensure hub is different from both origin and destination
    if origin == hub or hub == destination:
        logger.info(f"Skipping hub connection: hub {hub} equals origin or destination")
        return []

    departure_date = datetime.strptime(search_request.departure_date, "%Y-%m-%d")

    logger.debug(f"Hub connection: {origin} -> {hub} -> {destination}")

    # Search first segment: Origin → Hub
    rate_limiter.wait_if_needed()
    try:
        logger.debug(f"Hub API call 1/2: {origin} -> {hub}")
        _, first_leg_response = provider.search_flights(
            origin=origin,
            destination=hub,
            departure_date=search_request.departure_date,
            return_date=None,
            passengers=passengers,
            travel_class=search_request.travel_class.upper(),
        )

        if not first_leg_response.success or not first_leg_response.flights:
            logger.debug(f"No flights found for first leg: {origin} -> {hub}")
            return []

    except Exception as e:
        logger.error(f"First leg API call failed: {str(e)}")
        return []

    # Search second segment: Hub → Destination
    rate_limiter.wait_if_needed()
    try:
        logger.debug(f"Hub API call 2/2: {hub} -> {destination}")
        _, second_leg_response = provider.search_flights(
            origin=hub,
            destination=destination,
            departure_date=search_request.departure_date,
            return_date=None,
            passengers=passengers,
            travel_class=search_request.travel_class.upper(),
        )

        if not second_leg_response.success or not second_leg_response.flights:
            logger.debug(f"No flights found for second leg: {hub} -> {destination}")
            return []

    except Exception as e:
        logger.error(f"Second leg API call failed: {str(e)}")
        return []

    # Find compatible connections
    compatible_connections = _find_compatible_connections(
        first_leg_response.flights,
        second_leg_response.flights,
        min_layover_minutes=60,
        max_layover_minutes=480,
    )

    logger.debug(f"Found {len(compatible_connections)} compatible hub connections")

    # Convert to combined flight offers
    combined_flights = []
    for first_flight, second_flight in compatible_connections:
        combined_flight = _create_combined_flight_offer(
            first_flight, second_flight, hub
        )
        combined_flights.append(combined_flight)

    return combined_flights

def _find_compatible_connections(
    first_leg_flights,
    second_leg_flights,
    min_layover_minutes=60,
    max_layover_minutes=720,
):
    """Find first and second leg flights that have compatible timing"""
    compatible_pairs = []

    logger.debug(
        f"Analyzing connections: {len(first_leg_flights)} first leg x {len(second_leg_flights)} second leg flights"
    )

    for i, first_flight in enumerate(first_leg_flights):
        first_arrival = None
        first_flight_id = getattr(first_flight, "offer_id", f"first_flight_{i}")

        if hasattr(first_flight, "arrival_time") and first_flight.arrival_time:
            first_arrival = first_flight.arrival_time
        elif hasattr(first_flight, "segments") and first_flight.segments:
            last_segment = first_flight.segments[-1]
            if hasattr(last_segment, "arrival_time"):
                first_arrival = last_segment.arrival_time

        if not first_arrival:
            logger.debug(
                f"SKIP: No arrival time found for first leg flight {first_flight_id}"
            )
            continue

        for j, second_flight in enumerate(second_leg_flights):
            second_departure = None
            second_flight_id = getattr(second_flight, "offer_id", f"second_flight_{j}")

            if (
                hasattr(second_flight, "departure_time")
                and second_flight.departure_time
            ):
                second_departure = second_flight.departure_time
            elif hasattr(second_flight, "segments") and second_flight.segments:
                first_segment = second_flight.segments[0]
                if hasattr(first_segment, "departure_time"):
                    second_departure = first_segment.departure_time

            if not second_departure:
                logger.debug(
                    f"SKIP: No departure time found for second leg flight {second_flight_id}"
                )
                continue

            try:
                arrival_dt = first_arrival
                departure_dt = second_departure

                if isinstance(first_arrival, str):
                    arrival_dt = datetime.fromisoformat(
                        first_arrival.replace("Z", "+00:00")
                    )

                if isinstance(second_departure, str):
                    departure_dt = datetime.fromisoformat(
                        second_departure.replace("Z", "+00:00")
                    )

                if not isinstance(arrival_dt, datetime) or not isinstance(
                    departure_dt, datetime
                ):
                    logger.error(
                        f"Time conversion failed - arrival_dt: {type(arrival_dt)}, departure_dt: {type(departure_dt)}"
                    )
                    continue

                layover_minutes = (departure_dt - arrival_dt).total_seconds() / 60

                if min_layover_minutes <= layover_minutes <= max_layover_minutes:
                    compatible_pairs.append((first_flight, second_flight))
                    logger.info(
                        f"COMPATIBLE: {first_flight_id} + {second_flight_id} with {layover_minutes:.1f}min layover"
                    )

            except Exception as e:
                logger.error(
                    f"Error calculating layover time for {first_flight_id} + {second_flight_id}: {e}"
                )
                continue

    logger.info(
        f"Connection summary: {len(compatible_pairs)} compatible connections found from {len(first_leg_flights) * len(second_leg_flights)} possible combinations"
    )

    return compatible_pairs


def _create_combined_flight_offer(first_flight, second_flight, hub_code):
    """Create a combined flight offer from two separate flights"""
    combined_segments = []

    if hasattr(first_flight, "segments") and first_flight.segments:
        combined_segments.extend(first_flight.segments)
    if hasattr(second_flight, "segments") and second_flight.segments:
        combined_segments.extend(second_flight.segments)

    total_price = Decimal("0")
    currency = "USD"

    if hasattr(first_flight, "pricing") and hasattr(second_flight, "pricing"):
        total_price = (
            first_flight.pricing.price_total + second_flight.pricing.price_total
        )
        currency = first_flight.pricing.currency

    first_id = getattr(first_flight, "offer_id", "unknown")
    second_id = getattr(second_flight, "offer_id", "unknown")

    total_duration = 0
    departure_time = None
    arrival_time = None
    origin = None
    destination = None

    if hasattr(first_flight, "departure_time"):
        departure_time = first_flight.departure_time
    if hasattr(second_flight, "arrival_time"):
        arrival_time = second_flight.arrival_time
    if hasattr(first_flight, "origin"):
        origin = first_flight.origin
    if hasattr(second_flight, "destination"):
        destination = second_flight.destination

    if hasattr(first_flight, "duration_minutes") and hasattr(
        second_flight, "duration_minutes"
    ):
        total_duration = first_flight.duration_minutes + second_flight.duration_minutes
        if departure_time and arrival_time:
            total_time = (arrival_time - departure_time).total_seconds() / 60
            total_duration = int(total_time)

    combined_flight = {
        "offer_id": f"{first_id}-{second_id}",
        "id": f"{first_id}-{second_id}",
        "origin": origin or "UNK",
        "destination": destination or "UNK",
        "departure_time": departure_time,
        "arrival_time": arrival_time,
        "duration_minutes": total_duration,
        "trip_type": "ONE_WAY_CONNECTING",
        "total_segments": len(combined_segments),
        "stops": len(combined_segments) - 1,
        "airline_code": getattr(first_flight, "airline_code", "MULTI"),
        "segments": combined_segments,
        "pricing": {
            "price_total": str(total_price),
            "currency": currency,
            "base_price": str(total_price * Decimal("0.8")),
            "tax_amount": str(total_price * Decimal("0.2")),
        },
        "is_hub_connection": True,
        "hub_airport": hub_code,
        "component_flights": [first_id, second_id],
        "baggage": getattr(first_flight, "baggage", None),
        "fare_details": getattr(first_flight, "fare_details", None),
        "ancillary_services": getattr(first_flight, "ancillary_services", None),
    }

    return combined_flight


def _split_roundtrip_offer(offer, origin, destination):
    """Split a round-trip FlightOffer into outbound and return flights"""
    offer_dict = offer.__dict__

    segments = offer_dict.get("segments", [])

    if not segments:
        logger.warning(f"No segments found in offer {offer_dict.get('offer_id')}")
        return _create_empty_roundtrip_structure(offer_dict)

    split_index = None
    for i, segment in enumerate(segments):
        arrival_iata = getattr(segment, "arrival_iata", None)
        if arrival_iata == destination:
            split_index = i + 1
            break

    if split_index is None or split_index >= len(segments):
        split_index = len(segments) // 2
        logger.warning(
            f"Could not determine segment split point, using midpoint: {split_index}"
        )

    outbound_segments = segments[:split_index]
    return_segments = segments[split_index:]

    logger.debug(
        f"Split offer into {len(outbound_segments)} outbound + {len(return_segments)} return segments"
    )

    total_price = 0
    if hasattr(offer_dict.get("pricing"), "price_total"):
        total_price = float(offer_dict["pricing"].price_total)
    elif isinstance(offer_dict.get("pricing"), dict):
        total_price = float(offer_dict["pricing"]["price_total"])

    half_price = total_price / 2

    outbound_flight = {
        "offer_id": f"{offer_dict.get('offer_id', offer_dict.get('id'))}_outbound",
        "id": f"{offer_dict.get('offer_id', offer_dict.get('id'))}_outbound",
        "origin": origin,
        "destination": destination,
        "departure_time": (
            outbound_segments[0].departure_time if outbound_segments else None
        ),
        "arrival_time": (
            outbound_segments[-1].arrival_time if outbound_segments else None
        ),
        "duration_minutes": offer_dict.get("duration_minutes", 0) // 2,
        "trip_type": "ONE_WAY" if len(outbound_segments) == 1 else "ONE_WAY_CONNECTING",
        "total_segments": len(outbound_segments),
        "stops": len(outbound_segments) - 1,
        "airline_code": (
            getattr(outbound_segments[0], "airline_code", "MULTI")
            if outbound_segments
            else "MULTI"
        ),
        "segments": outbound_segments,
        "pricing": {
            "price_total": str(half_price),
            "currency": (
                offer_dict.get("pricing", {}).get("currency", "USD")
                if isinstance(offer_dict.get("pricing"), dict)
                else getattr(offer_dict.get("pricing"), "currency", "USD")
            ),
            "base_price": str(half_price * 0.8),
            "tax_amount": str(half_price * 0.2),
        },
        "baggage": offer_dict.get("baggage"),
        "fare_details": offer_dict.get("fare_details"),
        "ancillary_services": offer_dict.get("ancillary_services"),
    }

    return_flight = {
        "offer_id": f"{offer_dict.get('offer_id', offer_dict.get('id'))}_return",
        "id": f"{offer_dict.get('offer_id', offer_dict.get('id'))}_return",
        "origin": destination,
        "destination": origin,
        "departure_time": (
            return_segments[0].departure_time if return_segments else None
        ),
        "arrival_time": return_segments[-1].arrival_time if return_segments else None,
        "duration_minutes": offer_dict.get("duration_minutes", 0) // 2,
        "trip_type": "ONE_WAY" if len(return_segments) == 1 else "ONE_WAY_CONNECTING",
        "total_segments": len(return_segments),
        "stops": len(return_segments) - 1,
        "airline_code": (
            getattr(return_segments[0], "airline_code", "MULTI")
            if return_segments
            else "MULTI"
        ),
        "segments": return_segments,
        "pricing": {
            "price_total": str(half_price),
            "currency": (
                offer_dict.get("pricing", {}).get("currency", "USD")
                if isinstance(offer_dict.get("pricing"), dict)
                else getattr(offer_dict.get("pricing"), "currency", "USD")
            ),
            "base_price": str(half_price * 0.8),
            "tax_amount": str(half_price * 0.2),
        },
        "baggage": offer_dict.get("baggage"),
        "fare_details": offer_dict.get("fare_details"),
        "ancillary_services": offer_dict.get("ancillary_services"),
    }

    return {
        "offer_id": offer_dict.get("offer_id", offer_dict.get("id")),
        "id": offer_dict.get("offer_id", offer_dict.get("id")),
        "outbound_flight": outbound_flight,
        "return_flight": return_flight,
        "is_hub_roundtrip": False,
        "pricing": {
            "price_total": str(total_price),
            "currency": (
                offer_dict.get("pricing", {}).get("currency", "USD")
                if isinstance(offer_dict.get("pricing"), dict)
                else getattr(offer_dict.get("pricing"), "currency", "USD")
            ),
        },
        "total_price": total_price,
    }


def _create_empty_roundtrip_structure(offer_dict):
    """Create an empty roundtrip structure when segments are missing"""
    return {
        "offer_id": offer_dict.get("offer_id", offer_dict.get("id")),
        "id": offer_dict.get("offer_id", offer_dict.get("id")),
        "outbound_flight": None,
        "return_flight": None,
        "is_hub_roundtrip": False,
        "pricing": offer_dict.get("pricing"),
        "total_price": 0,
    }


def _search_roundtrip_strategy(
    provider,
    strategy: SearchStrategy,
    search_request: SearchRequest,
    passengers: List[Passenger],
) -> Tuple[List[Dict], List[Dict], Optional[str]]:
    """Search round-trip flights with hub support"""

    if (
        len(strategy.outbound_route) == 2
        and strategy.return_route
        and len(strategy.return_route) == 2
    ):
        # Simple round-trip
        rate_limiter.wait_if_needed()
        try:
            origin, destination = strategy.outbound_route
            origin, destination = strategy.outbound_route
        
            if not _validate_route(origin, destination):
                logger.info(f"Skipping round-trip search for {origin} <-> {destination} (same airport)")
                return [], [], None
            logger.debug(f"Round-trip API call: {origin} <-> {destination}")

            simplified_response, full_response = provider.search_flights(
                origin=origin,
                destination=destination,
                departure_date=search_request.departure_date,
                return_date=search_request.return_date,
                passengers=passengers,
                travel_class=search_request.travel_class.upper(),
            )

            if full_response.success:
                logger.debug(
                    f"Round-trip success: {len(full_response.flights)} flights found"
                )

                split_roundtrips = []
                for offer in full_response.flights:
                    if isinstance(offer, dict) and "outbound_flight" in offer:
                        split_roundtrips.append(offer)
                    else:
                        split_offer = _split_roundtrip_offer(offer, origin, destination)
                        split_roundtrips.append(split_offer)

                budget_alternatives = full_response.budget_airline_alternatives or []
                google_flights_url = getattr(full_response, 'google_flights_url', None)

                if budget_alternatives:
                    logger.info(
                        f"Found {len(budget_alternatives)} budget airline alternatives for round-trip {origin} <-> {destination}"
                    )

                if google_flights_url:
                    logger.info(f"Google Flights URL: {google_flights_url}")

                return split_roundtrips, budget_alternatives, google_flights_url
            else:
                logger.debug("Round-trip: no results")
                return [], [], None

        except Exception as e:
            logger.error(f"Round-trip API call failed: {str(e)}")
            raise

    elif (
        len(strategy.outbound_route) == 3
        and strategy.return_route
        and len(strategy.return_route) == 3
    ):
        # Hub round-trip - no budget alternatives or URLs for complex routes
        logger.debug("Hub round-trip connection")

        outbound_request = SearchRequest(
            origin=search_request.origin,
            destination=search_request.destination,
            departure_date=search_request.departure_date,
            return_date=None,
            adults=search_request.adults,
            children=search_request.children,
            infants=search_request.infants,
            travel_class=search_request.travel_class,
        )

        return_request = SearchRequest(
            origin=search_request.destination,
            destination=search_request.origin,
            departure_date=search_request.return_date, # type: ignore
            return_date=None,
            adults=search_request.adults,
            children=search_request.children,
            infants=search_request.infants,
            travel_class=search_request.travel_class,
        )

        outbound_flights = _search_hub_connection(
            provider, strategy, outbound_request, passengers
        )

        return_strategy = SearchStrategy(
            outbound_route=strategy.return_route,
            strategy_type=strategy.strategy_type,
            extra_transport_cost=0,
            explanation=f"Return via {strategy.return_route[1]}",
        )

        return_flights = _search_hub_connection(
            provider, return_strategy, return_request, passengers
        )

        combined_roundtrips = []
        for outbound in outbound_flights[:10]:
            for return_flight in return_flights[:10]:
                outbound_price = 0
                return_price = 0

                if "pricing" in outbound and outbound["pricing"]:
                    outbound_price = (
                        float(outbound["pricing"]["price_total"])
                        if isinstance(outbound["pricing"]["price_total"], str)
                        else float(outbound["pricing"].price_total)
                    )
                elif "total_price" in outbound:
                    outbound_price = float(outbound["total_price"])

                if "pricing" in return_flight and return_flight["pricing"]:
                    return_price = (
                        float(return_flight["pricing"]["price_total"])
                        if isinstance(return_flight["pricing"]["price_total"], str)
                        else float(return_flight["pricing"].price_total)
                    )
                elif "total_price" in return_flight:
                    return_price = float(return_flight["total_price"])

                combined_roundtrips.append(
                    {
                        "offer_id": f"{outbound.get('offer_id', outbound.get('id', 'unk'))}-{return_flight.get('offer_id', return_flight.get('id', 'unk'))}",
                        "id": f"{outbound.get('offer_id', outbound.get('id', 'unk'))}-{return_flight.get('offer_id', return_flight.get('id', 'unk'))}",
                        "outbound_flight": outbound,
                        "return_flight": return_flight,
                        "is_hub_roundtrip": True,
                        "pricing": {
                            "price_total": str(outbound_price + return_price),
                            "currency": "USD",
                        },
                        "total_price": outbound_price + return_price,
                    }
                )

        return combined_roundtrips, [], None

    else:
        logger.debug("Complex round-trip search not implemented yet")
        return [], [], None


def _enrich_flight_results(
    flights: List[Dict], 
    strategy: SearchStrategy, 
    search_request: SearchRequest,
    google_flights_url: Optional[str] = None  # ✨ Add parameter
) -> List[Dict]:
    """Enhanced enrichment that works with FlightOffer objects"""
    enriched_flights = []

    for flight_dict in flights:
        try:
            enriched_flight = flight_dict.copy()

            enriched_flight["search_strategy"] = strategy.strategy_type
            enriched_flight["strategy_explanation"] = strategy.explanation
            enriched_flight["routing_used"] = strategy.outbound_route
            enriched_flight["google_flights_url"] = google_flights_url  # ✨ Add URL to each flight

            if "pricing" in enriched_flight and enriched_flight["pricing"]:
                if isinstance(enriched_flight["pricing"], dict):
                    base_price = float(enriched_flight["pricing"]["price_total"])
                else:
                    base_price = float(enriched_flight["pricing"].price_total)
                enriched_flight["total_cost_with_transport"] = (
                    base_price + strategy.extra_transport_cost
                )
            elif "total_price" in enriched_flight:
                enriched_flight["total_cost_with_transport"] = (
                    enriched_flight["total_price"] + strategy.extra_transport_cost
                )
            else:
                enriched_flight["total_cost_with_transport"] = (
                    strategy.extra_transport_cost
                )

            # Add airline policies from data manager
            if "airline_code" in enriched_flight:
                airline_code = enriched_flight["airline_code"]
                enriched_flight["baggage_policy"] = data_manager.get_airline_policy(
                    airline_code, "baggage_policies"
                )
                enriched_flight["cancellation_policy"] = (
                    data_manager.get_airline_policy(
                        airline_code, "cancellation_policies"
                    )
                )

            enriched_flights.append(enriched_flight)

        except Exception as e:
            logger.error(
                f"Error processing flight enrichment for flight ID '{flight_dict.get('id', 'N/A')}'. "
                f"Error: {e}",
                exc_info=True,
                extra={"flight_data": flight_dict},
            )
            continue

    return enriched_flights


def _process_search_results(
    search_results: List[SearchResult],
    search_request: SearchRequest,
    budget_alternatives: List[Dict],
    google_flights_url: Optional[str] = None,
) -> Dict:
    """Process and group all search results"""
    all_flights = []
    successful_searches = 0
    failed_searches = []

    for result in search_results:
        if result.success:
            successful_searches += 1
            all_flights.extend(result.flights)
        else:
            failed_searches.append(
                {"strategy": result.strategy.explanation, "error": result.error_message}
            )

    # Sort by total cost with transport
    all_flights.sort(key=lambda x: x.get("total_cost_with_transport", float('inf')))

    logger.info(
        f"Search completed: {successful_searches}/{len(search_results)} strategies successful, "
        f"{len(all_flights)} total flights found"
    )

    if budget_alternatives:
        logger.info(f"Returning {len(budget_alternatives)} budget airline alternatives")

    if google_flights_url:
        logger.info(f"Including Google Flights URL in response: {google_flights_url}")

    response = {
        "search_summary": {
            "total_strategies_attempted": len(search_results),
            "successful_searches": successful_searches,
            "total_flights_found": len(all_flights),
            "search_request": search_request.__dict__,
            "budget_airlines_checked": len(budget_alternatives) > 0,
        },
        "results": {
            "direct_flights": [
                f for f in all_flights if f.get("search_strategy") == "direct"
            ][:3],
            "nearby_airport_options": [
                f for f in all_flights if f.get("search_strategy") == "nearby"
            ][:3],
            "hub_connections": [
                f for f in all_flights if f.get("search_strategy") == "hub"
            ][:3],
        },
        "budget_airline_alternatives": budget_alternatives,
        "primary_google_flights_url": google_flights_url,
        "debug_info": {"failed_searches": failed_searches},
    }

    return response
