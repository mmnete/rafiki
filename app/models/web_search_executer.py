from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional
import time
import threading
from app.models.web_search_strategy import SearchStrategy
from app.models.web_search_data import SearchRequest
from app.models.web_search_data_manager import data_manager
from app.services.api.flights.response_models import Passenger, PassengerType
from app.services.api.flights.amadeus_provider import AmadeusProvider
import logging
import psutil
import os
from datetime import datetime

logger = logging.getLogger(__name__)


# Rate limiting configuration
class RateLimiter:
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
                logger.debug(f"⏱️ Rate limiting: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)

            self.last_request_time = time.time()


# Global rate limiter instance
rate_limiter = RateLimiter(max_requests_per_second=2)


@dataclass
class SearchResult:
    strategy: SearchStrategy
    flights: List[Dict]
    success: bool
    error_message: Optional[str] = None


def execute_flight_searches(
    strategies: List[SearchStrategy], search_request: SearchRequest
) -> Dict:
    """Execute all search strategies in parallel with rate limiting"""
    
    # === ADD TIMING AND MEMORY LOGGING HERE ===
    request_start = datetime.now()
    process = psutil.Process(os.getpid())
    mem_start = process.memory_info().rss / 1024 / 1024  # MB
    
    logger.info(f"🚀 Starting flight search at {request_start}")
    logger.info(f"💾 Memory at start: {mem_start:.2f} MB")
    logger.info(f"📊 Processing {len(strategies)} strategies (rate limited to 2 req/sec)")
    
    search_results = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_strategy = {}
        for strategy in strategies:
            future = executor.submit(_execute_single_search, strategy, search_request)
            future_to_strategy[future] = strategy

        for future in future_to_strategy:
            strategy = future_to_strategy[future]
            try:
                # === ADD TIMING PER STRATEGY ===
                strategy_start = datetime.now()
                logger.debug(f"⏳ Waiting for strategy '{strategy.strategy_type}': {strategy.explanation}")
                
                flights = future.result(
                    timeout=60
                )  # Increased for multi-segment searches
                
                strategy_duration = (datetime.now() - strategy_start).total_seconds()
                logger.debug(f"⏱️ Strategy '{strategy.strategy_type}' completed in {strategy_duration:.2f}s")
                
                enriched_flights = _enrich_flight_results(
                    flights, strategy, search_request
                )
                search_results.append(SearchResult(strategy, enriched_flights, True))
                logger.debug(
                    f"✅ Strategy '{strategy.strategy_type}' returned {len(enriched_flights)} flights"
                )
                
                # === LOG MEMORY AFTER EACH STRATEGY ===
                mem_current = process.memory_info().rss / 1024 / 1024
                mem_delta = mem_current - mem_start
                logger.debug(f"💾 Memory now: {mem_current:.2f} MB (Δ +{mem_delta:.2f} MB)")
                
            except Exception as e:
                strategy_duration = (datetime.now() - strategy_start).total_seconds()
                logger.warning(
                    f"❌ Strategy '{strategy.strategy_type}' failed after {strategy_duration:.2f}s: {str(e)}"
                )
                search_results.append(SearchResult(strategy, [], False, str(e)))

    # === ADD FINAL TIMING AND MEMORY LOGGING ===
    total_duration = (datetime.now() - request_start).total_seconds()
    mem_end = process.memory_info().rss / 1024 / 1024
    mem_total_delta = mem_end - mem_start
    
    logger.info(f"⏱️ Total search duration: {total_duration:.2f}s")
    logger.info(f"💾 Memory at end: {mem_end:.2f} MB (Δ +{mem_total_delta:.2f} MB)")
    logger.info(f"✅ Completed {len([r for r in search_results if r.success])}/{len(search_results)} strategies successfully")
    
    # Warn if approaching timeout
    if total_duration > 25:
        logger.warning(f"⚠️ Search took {total_duration:.2f}s - approaching timeout threshold!")

    return _process_search_results(search_results, search_request)


def _execute_single_search(
    strategy: SearchStrategy, search_request: SearchRequest
) -> List[Dict]:
    """Execute a single search strategy using your existing Amadeus service with rate limiting"""

    logger.debug(f"🔍 Executing search for strategy: {strategy.explanation}")

    passengers = _convert_search_request_to_passengers(search_request)
    amadeus_service = AmadeusProvider()

    if search_request.is_roundtrip:
        return _search_roundtrip_strategy(
            amadeus_service, strategy, search_request, passengers
        )
    else:
        return _search_oneway_strategy(
            amadeus_service, strategy, search_request, passengers
        )


def _convert_search_request_to_passengers(
    search_request: SearchRequest,
) -> List[Passenger]:
    """Convert SearchRequest to list of Passenger objects for Amadeus"""
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
    amadeus_service: AmadeusProvider,
    strategy: SearchStrategy,
    search_request: SearchRequest,
    passengers: List[Passenger],
) -> List[Dict]:
    """Search one-way flights with support for hub connections"""

    if len(strategy.outbound_route) == 2:
        # Direct flight
        return _search_direct_flight(
            amadeus_service, strategy, search_request, passengers
        )

    elif len(strategy.outbound_route) == 3:
        # Hub connection: Origin → Hub → Destination
        return _search_hub_connection(
            amadeus_service, strategy, search_request, passengers
        )

    else:
        logger.warning(
            f"🚧 Unsupported route complexity: {len(strategy.outbound_route)} segments"
        )
        return []


def _search_direct_flight(
    amadeus_service: AmadeusProvider,
    strategy: SearchStrategy,
    search_request: SearchRequest,
    passengers: List[Passenger],
) -> List[Dict]:
    """Search direct flights"""
    rate_limiter.wait_if_needed()

    try:
        origin, destination = strategy.outbound_route
        logger.debug(f"📡 Direct API call: {origin} → {destination}")

        simplified_response, full_response = amadeus_service.search_flights(
            origin=origin,
            destination=destination,
            departure_date=search_request.departure_date,
            return_date=None,
            passengers=passengers,
            travel_class=search_request.travel_class.upper(),
        )

        if full_response.success:
            logger.debug(
                f"✅ Direct flight success: {len(full_response.flights)} flights found"
            )
            return [offer.__dict__ for offer in full_response.flights]
        else:
            logger.debug(f"⚠️ Direct flight: no results")
            return []
    except Exception as e:
        logger.error(f"💥 Direct flight API call failed: {str(e)}")
        raise


def _search_hub_connection(
    amadeus_service: AmadeusProvider,
    strategy: SearchStrategy,
    search_request: SearchRequest,
    passengers: List[Passenger],
) -> List[Dict]:
    """Search hub connections by finding compatible flight pairs"""

    origin, hub, destination = strategy.outbound_route
    departure_date = datetime.strptime(search_request.departure_date, "%Y-%m-%d")

    logger.debug(f"🔄 Hub connection: {origin} → {hub} → {destination}")

    # Search first segment: Origin → Hub
    rate_limiter.wait_if_needed()
    try:
        logger.debug(f"📡 Hub API call 1/2: {origin} → {hub}")
        _, first_leg_response = amadeus_service.search_flights(
            origin=origin,
            destination=hub,
            departure_date=search_request.departure_date,
            return_date=None,
            passengers=passengers,
            travel_class=search_request.travel_class.upper(),
        )

        if not first_leg_response.success or not first_leg_response.flights:
            logger.debug(f"⚠️ No flights found for first leg: {origin} → {hub}")
            return []
    
    except Exception as e:
        logger.error(f"💥 First leg API call failed: {str(e)}")
        return []

    # Search second segment: Hub → Destination (same day + next day for connections)
    rate_limiter.wait_if_needed()
    try:
        logger.debug(f"📡 Hub API call 2/2: {hub} → {destination}")
        _, second_leg_response = amadeus_service.search_flights(
            origin=hub,
            destination=destination,
            departure_date=search_request.departure_date,
            return_date=None,
            passengers=passengers,
            travel_class=search_request.travel_class.upper(),
        )

        if not second_leg_response.success or not second_leg_response.flights:
            logger.debug(f"⚠️ No flights found for second leg: {hub} → {destination}")
            return []
    
    except Exception as e:
        logger.error(f"💥 Second leg API call failed: {str(e)}")
        return []

    # Find compatible connections
    compatible_connections = _find_compatible_connections(
        first_leg_response.flights,
        second_leg_response.flights,
        min_layover_minutes=60,  # Minimum 1 hour layover
        max_layover_minutes=480,  # Maximum 8 hour layover
    )

    logger.debug(f"🔗 Found {len(compatible_connections)} compatible hub connections")

    # Convert to combined flight offers
    combined_flights = []
    for first_flight, second_flight in compatible_connections:
        combined_flight = _create_combined_flight_offer(
            first_flight, second_flight, hub
        )
        combined_flights.append(
            combined_flight
        )  # Already a dictionary, no need for .__dict__

    return combined_flights


def _find_compatible_connections(
    first_leg_flights,
    second_leg_flights,
    min_layover_minutes=60,
    max_layover_minutes=720,
):
    """Find first and second leg flights that have compatible timing"""
    compatible_pairs = []
    
    logger.debug(f"🔍 Analyzing connections: {len(first_leg_flights)} first leg × {len(second_leg_flights)} second leg flights")
    
    for i, first_flight in enumerate(first_leg_flights):
        # Get arrival time at hub - use the flight's arrival_time or last segment
        first_arrival = None
        first_flight_id = getattr(first_flight, 'offer_id', f'first_flight_{i}')
        
        if hasattr(first_flight, "arrival_time") and first_flight.arrival_time:
            first_arrival = first_flight.arrival_time
            logger.debug(f"📍 First leg {first_flight_id}: using flight-level arrival_time = {first_arrival}")
        elif hasattr(first_flight, "segments") and first_flight.segments:
            # Get last segment's arrival time
            last_segment = first_flight.segments[-1]
            if hasattr(last_segment, "arrival_time"):
                first_arrival = last_segment.arrival_time
                logger.debug(f"📍 First leg {first_flight_id}: using last segment arrival_time = {first_arrival}")
            else:
                logger.debug(f"📍 First leg {first_flight_id}: last segment has no arrival_time attribute")
        else:
            logger.debug(f"📍 First leg {first_flight_id}: no segments found")

        if not first_arrival:
            logger.debug(f"⚠️ SKIP: No arrival time found for first leg flight {first_flight_id}")
            continue

        for j, second_flight in enumerate(second_leg_flights):
            # Get departure time from hub - use the flight's departure_time or first segment
            second_departure = None
            second_flight_id = getattr(second_flight, 'offer_id', f'second_flight_{j}')
            
            if hasattr(second_flight, "departure_time") and second_flight.departure_time:
                second_departure = second_flight.departure_time
                logger.debug(f"📍 Second leg {second_flight_id}: using flight-level departure_time = {second_departure}")
            elif hasattr(second_flight, "segments") and second_flight.segments:
                # Get first segment's departure time
                first_segment = second_flight.segments[0]
                if hasattr(first_segment, "departure_time"):
                    second_departure = first_segment.departure_time
                    logger.debug(f"📍 Second leg {second_flight_id}: using first segment departure_time = {second_departure}")
                else:
                    logger.debug(f"📍 Second leg {second_flight_id}: first segment has no departure_time attribute")
            else:
                logger.debug(f"📍 Second leg {second_flight_id}: no segments found")

            if not second_departure:
                logger.debug(f"⚠️ SKIP: No departure time found for second leg flight {second_flight_id}")
                continue

            # Calculate layover time (both should already be datetime objects)
            try:
                # Log the raw times before any conversion
                logger.debug(f"🕐 Raw times - Arrival: {first_arrival} (type: {type(first_arrival).__name__}), Departure: {second_departure} (type: {type(second_departure).__name__})")
                
                # Convert string times to datetime if needed
                arrival_dt = first_arrival
                departure_dt = second_departure
                
                if isinstance(first_arrival, str):
                    arrival_dt = datetime.fromisoformat(first_arrival.replace("Z", "+00:00"))
                    logger.debug(f"🔄 Converted arrival string to datetime: {arrival_dt}")
                    
                if isinstance(second_departure, str):
                    departure_dt = datetime.fromisoformat(second_departure.replace("Z", "+00:00"))
                    logger.debug(f"🔄 Converted departure string to datetime: {departure_dt}")

                # Check timezone consistency only after conversion to datetime
                if isinstance(arrival_dt, datetime) and isinstance(departure_dt, datetime):
                    if arrival_dt.tzinfo is None and departure_dt.tzinfo is not None:
                        logger.debug("⚠️ Timezone mismatch: arrival is naive, departure is aware")
                    elif arrival_dt.tzinfo is not None and departure_dt.tzinfo is None:
                        logger.debug("⚠️ Timezone mismatch: arrival is aware, departure is naive")
                    elif arrival_dt.tzinfo is None and departure_dt.tzinfo is None:
                        logger.debug("📍 Both times are timezone-naive")
                    else:
                        logger.debug("📍 Both times are timezone-aware")

                # Validate that we have datetime objects
                if not isinstance(arrival_dt, datetime) or not isinstance(departure_dt, datetime):
                    logger.error(f"💥 Time conversion failed - arrival_dt: {type(arrival_dt)}, departure_dt: {type(departure_dt)}")
                    continue

                layover_minutes = (departure_dt - arrival_dt).total_seconds() / 60
                
                logger.debug(f"⏱️ Connection analysis: {first_flight_id} → {second_flight_id}")
                logger.debug(f"   📥 Arrives at hub: {arrival_dt}")
                logger.debug(f"   📤 Departs from hub: {departure_dt}")
                logger.debug(f"   ⏳ Layover duration: {layover_minutes:.1f} minutes")
                logger.debug(f"   📋 Valid range: {min_layover_minutes}-{max_layover_minutes} minutes")

                # Check if layover is within acceptable range
                if min_layover_minutes <= layover_minutes <= max_layover_minutes:
                    compatible_pairs.append((first_flight, second_flight))
                    logger.info(f"✅ COMPATIBLE: {first_flight_id} + {second_flight_id} with {layover_minutes:.1f}min layover")
                elif layover_minutes < min_layover_minutes:
                    logger.debug(f"❌ TOO SHORT: {layover_minutes:.1f}min < {min_layover_minutes}min minimum")
                elif layover_minutes > max_layover_minutes:
                    logger.debug(f"❌ TOO LONG: {layover_minutes:.1f}min > {max_layover_minutes}min maximum")
                else:
                    logger.debug(f"❌ INVALID: {layover_minutes:.1f}min layover")
                    
            except Exception as e:
                logger.error(f"💥 Error calculating layover time for {first_flight_id} + {second_flight_id}: {e}")
                logger.debug(f"   First arrival (raw): {first_arrival}")
                logger.debug(f"   Second departure (raw): {second_departure}")
                logger.debug(f"   Error details: {str(e)}")
                continue

    logger.info(f"🎯 Connection summary: {len(compatible_pairs)} compatible connections found from {len(first_leg_flights) * len(second_leg_flights)} possible combinations")
    
    return compatible_pairs

def _create_combined_flight_offer(first_flight, second_flight, hub_code):
    """Create a combined flight offer from two separate flights"""
    # Create a new combined flight offer using your FlightOffer structure
    combined_segments = []

    # Add segments from both flights
    if hasattr(first_flight, "segments") and first_flight.segments:
        combined_segments.extend(first_flight.segments)
    if hasattr(second_flight, "segments") and second_flight.segments:
        combined_segments.extend(second_flight.segments)

    # Calculate total price
    total_price = Decimal("0")
    currency = "USD"

    if hasattr(first_flight, "pricing") and hasattr(second_flight, "pricing"):
        total_price = (
            first_flight.pricing.price_total + second_flight.pricing.price_total
        )
        currency = first_flight.pricing.currency

    # Get flight details
    first_id = getattr(first_flight, "offer_id", "unknown")
    second_id = getattr(second_flight, "offer_id", "unknown")

    # Calculate total duration and other details
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

    # Calculate total duration
    if hasattr(first_flight, "duration_minutes") and hasattr(
        second_flight, "duration_minutes"
    ):
        total_duration = first_flight.duration_minutes + second_flight.duration_minutes
        # Add layover time
        if departure_time and arrival_time:
            total_time = (arrival_time - departure_time).total_seconds() / 60
            total_duration = int(total_time)

    # Create a simplified combined flight object (dictionary format for easier handling)
    combined_flight = {
        "offer_id": f"{first_id}-{second_id}",
        "id": f"{first_id}-{second_id}",  # Add id for compatibility
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
            "base_price": str(total_price * Decimal("0.8")),  # Approximate
            "tax_amount": str(total_price * Decimal("0.2")),  # Approximate
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
    """Split an Amadeus round-trip FlightOffer into outbound and return flights"""
    offer_dict = offer.__dict__
    
    # Amadeus returns segments in order: outbound segments first, then return segments
    # We need to identify where outbound ends and return begins
    segments = offer_dict.get("segments", [])
    
    if not segments:
        logger.warning(f"No segments found in offer {offer_dict.get('offer_id')}")
        return _create_empty_roundtrip_structure(offer_dict)
    
    # Find the split point: where we arrive at destination (end of outbound)
    # and then depart from destination (start of return)
    split_index = None
    for i, segment in enumerate(segments):
        # Check if this segment arrives at the destination
        arrival_iata = getattr(segment, "arrival_iata", None)
        if arrival_iata == destination:
            # Next segment should be the start of return journey
            split_index = i + 1
            break
    
    if split_index is None or split_index >= len(segments):
        # Fallback: split in half if we can't determine
        split_index = len(segments) // 2
        logger.warning(f"Could not determine segment split point, using midpoint: {split_index}")
    
    outbound_segments = segments[:split_index]
    return_segments = segments[split_index:]
    
    logger.debug(f"Split offer into {len(outbound_segments)} outbound + {len(return_segments)} return segments")
    
    # Calculate prices (split proportionally or use full price for each if not specified)
    total_price = 0
    if hasattr(offer_dict.get("pricing"), "price_total"):
        total_price = float(offer_dict["pricing"].price_total)
    elif isinstance(offer_dict.get("pricing"), dict):
        total_price = float(offer_dict["pricing"]["price_total"])
    
    # For simplicity, assign half the price to each direction
    # (Amadeus doesn't split pricing, so this is an approximation)
    half_price = total_price / 2
    
    # Create outbound flight object
    outbound_flight = {
        "offer_id": f"{offer_dict.get('offer_id', offer_dict.get('id'))}_outbound",
        "id": f"{offer_dict.get('offer_id', offer_dict.get('id'))}_outbound",
        "origin": origin,
        "destination": destination,
        "departure_time": outbound_segments[0].departure_time if outbound_segments else None,
        "arrival_time": outbound_segments[-1].arrival_time if outbound_segments else None,
        "duration_minutes": offer_dict.get("duration_minutes", 0) // 2,  # Approximate
        "trip_type": "ONE_WAY" if len(outbound_segments) == 1 else "ONE_WAY_CONNECTING",
        "total_segments": len(outbound_segments),
        "stops": len(outbound_segments) - 1,
        "airline_code": getattr(outbound_segments[0], "airline_code", "MULTI") if outbound_segments else "MULTI",
        "segments": outbound_segments,
        "pricing": {
            "price_total": str(half_price),
            "currency": offer_dict.get("pricing", {}).get("currency", "USD") if isinstance(offer_dict.get("pricing"), dict) else getattr(offer_dict.get("pricing"), "currency", "USD"),
            "base_price": str(half_price * 0.8),
            "tax_amount": str(half_price * 0.2),
        },
        "baggage": offer_dict.get("baggage"),
        "fare_details": offer_dict.get("fare_details"),
        "ancillary_services": offer_dict.get("ancillary_services"),
    }
    
    # Create return flight object
    return_flight = {
        "offer_id": f"{offer_dict.get('offer_id', offer_dict.get('id'))}_return",
        "id": f"{offer_dict.get('offer_id', offer_dict.get('id'))}_return",
        "origin": destination,
        "destination": origin,
        "departure_time": return_segments[0].departure_time if return_segments else None,
        "arrival_time": return_segments[-1].arrival_time if return_segments else None,
        "duration_minutes": offer_dict.get("duration_minutes", 0) // 2,  # Approximate
        "trip_type": "ONE_WAY" if len(return_segments) == 1 else "ONE_WAY_CONNECTING",
        "total_segments": len(return_segments),
        "stops": len(return_segments) - 1,
        "airline_code": getattr(return_segments[0], "airline_code", "MULTI") if return_segments else "MULTI",
        "segments": return_segments,
        "pricing": {
            "price_total": str(half_price),
            "currency": offer_dict.get("pricing", {}).get("currency", "USD") if isinstance(offer_dict.get("pricing"), dict) else getattr(offer_dict.get("pricing"), "currency", "USD"),
            "base_price": str(half_price * 0.8),
            "tax_amount": str(half_price * 0.2),
        },
        "baggage": offer_dict.get("baggage"),
        "fare_details": offer_dict.get("fare_details"),
        "ancillary_services": offer_dict.get("ancillary_services"),
    }
    
    # Create the combined structure
    return {
        "offer_id": offer_dict.get("offer_id", offer_dict.get("id")),
        "id": offer_dict.get("offer_id", offer_dict.get("id")),
        "outbound_flight": outbound_flight,
        "return_flight": return_flight,
        "is_hub_roundtrip": False,
        "pricing": {
            "price_total": str(total_price),
            "currency": offer_dict.get("pricing", {}).get("currency", "USD") if isinstance(offer_dict.get("pricing"), dict) else getattr(offer_dict.get("pricing"), "currency", "USD"),
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
    amadeus_service: AmadeusProvider,
    strategy: SearchStrategy,
    search_request: SearchRequest,
    passengers: List[Passenger],
) -> List[Dict]:
    """Search round-trip flights with hub support"""

    if (
        len(strategy.outbound_route) == 2
        and strategy.return_route
        and len(strategy.return_route) == 2
    ):
        # Simple round-trip - get Amadeus data and split it
        rate_limiter.wait_if_needed()
        try:
            origin, destination = strategy.outbound_route
            logger.debug(f"📡 Round-trip API call: {origin} ⇄ {destination}")

            simplified_response, full_response = amadeus_service.search_flights(
                origin=origin,
                destination=destination,
                departure_date=search_request.departure_date,
                return_date=search_request.return_date,
                passengers=passengers,
                travel_class=search_request.travel_class.upper(),
            )

            if full_response.success:
                logger.debug(
                    f"✅ Round-trip success: {len(full_response.flights)} flights found"
                )
                
                # Split Amadeus round-trip offers into outbound/return structure
                split_roundtrips = []
                for offer in full_response.flights:
                    split_offer = _split_roundtrip_offer(offer, origin, destination)
                    split_roundtrips.append(split_offer)
                
                return split_roundtrips
            else:
                logger.debug(f"⚠️ Round-trip: no results")
                return []
        except Exception as e:
            logger.error(f"💥 Round-trip API call failed: {str(e)}")
            raise

    elif (
        len(strategy.outbound_route) == 3
        and strategy.return_route
        and len(strategy.return_route) == 3
    ):
        # Hub round-trip - search outbound and return separately, then combine
        logger.debug("🔄 Hub round-trip connection")

        # Create temporary one-way requests
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
            departure_date=search_request.return_date,  # type: ignore
            return_date=None,
            adults=search_request.adults,
            children=search_request.children,
            infants=search_request.infants,
            travel_class=search_request.travel_class,
        )

        # Search both directions
        outbound_flights = _search_hub_connection(
            amadeus_service, strategy, outbound_request, passengers
        )

        # Create return strategy
        return_strategy = SearchStrategy(
            outbound_route=strategy.return_route,
            strategy_type=strategy.strategy_type,
            extra_transport_cost=0,
            explanation=f"Return via {strategy.return_route[1]}",
        )

        return_flights = _search_hub_connection(
            amadeus_service, return_strategy, return_request, passengers
        )

        # Combine outbound and return flights (simplified - you may want more sophisticated pairing)
        combined_roundtrips = []
        for outbound in outbound_flights[:10]:  # ✅ Increase from 4 to 10
            for return_flight in return_flights[:10]:  # ✅ Increase from 4 to 10
                # Calculate total price for round trip
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

                # Create combined round-trip offer
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

        return combined_roundtrips

    else:
        logger.debug("🚧 Complex round-trip search not implemented yet")
        return []


def _enrich_flight_results(
    flights: List[Dict], strategy: SearchStrategy, search_request: SearchRequest
) -> List[Dict]:
    """Enhanced enrichment that works with your Amadeus FlightOffer objects"""
    enriched_flights = []

    for flight_dict in flights:
        try:
            enriched_flight = flight_dict.copy()

            # Add strategy context
            enriched_flight["search_strategy"] = strategy.strategy_type
            enriched_flight["strategy_explanation"] = strategy.explanation
            enriched_flight["routing_used"] = strategy.outbound_route

            # Add total cost including transport
            if "pricing" in enriched_flight and enriched_flight["pricing"]:
                if isinstance(enriched_flight["pricing"], dict):
                    # Dictionary format (from combined flights)
                    base_price = float(enriched_flight["pricing"]["price_total"])
                else:
                    # Object format (from Amadeus FlightOffer)
                    base_price = float(enriched_flight["pricing"].price_total)
                enriched_flight["total_cost_with_transport"] = (
                    base_price + strategy.extra_transport_cost
                )
            elif "total_price" in enriched_flight:  # For hub connections
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
    search_results: List[SearchResult], search_request: SearchRequest
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
    all_flights.sort(key=lambda x: x["total_cost_with_transport"])

    logger.info(
        f"🎯 Search completed: {successful_searches}/{len(search_results)} strategies successful, "
        f"{len(all_flights)} total flights found"
    )

    return {
        "search_summary": {
            "total_strategies_attempted": len(search_results),
            "successful_searches": successful_searches,
            "total_flights_found": len(all_flights),
            "search_request": search_request.__dict__,
        },
        "results": {
            # "best_deals": all_flights[:5],
            "direct_flights": [
                f for f in all_flights if f["search_strategy"] == "direct"
            ][:3],
            "nearby_airport_options": [
                f for f in all_flights if f["search_strategy"] == "nearby"
            ][:3],
            "hub_connections": [
                f for f in all_flights if f["search_strategy"] == "hub"
            ][:3],
        },
        "debug_info": {"failed_searches": failed_searches},
    }
