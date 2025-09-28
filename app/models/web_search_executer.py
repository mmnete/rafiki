from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional
from app.models.web_search_strategy import SearchStrategy
from app.models.web_search_data import SearchRequest
from app.models.web_search_data_manager import data_manager
from app.services.api.flights.response_models import Passenger, PassengerType
from app.services.api.flights.amadeus_provider import AmadeusProvider
import logging

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    strategy: SearchStrategy
    flights: List[Dict]
    success: bool
    error_message: Optional[str] = None

def execute_flight_searches(strategies: List[SearchStrategy], search_request: SearchRequest) -> Dict:
    """Execute all search strategies in parallel"""
    search_results = []
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all searches
        future_to_strategy = {}
        for strategy in strategies:
            future = executor.submit(_execute_single_search, strategy, search_request)
            future_to_strategy[future] = strategy
        
        # Collect results
        for future in future_to_strategy:
            strategy = future_to_strategy[future]
            try:
                flights = future.result(timeout=30)
                enriched_flights = _enrich_flight_results(flights, strategy, search_request)
                search_results.append(SearchResult(strategy, enriched_flights, True)) # type: ignore
            except Exception as e:
                search_results.append(SearchResult(strategy, [], False, str(e))) # type: ignore
    
    # Process and group results
    return _process_search_results(search_results, search_request)

def _execute_single_search(strategy: SearchStrategy, search_request: SearchRequest) -> List[Dict]:
    """Execute a single search strategy using your existing Amadeus service"""
    
    # Convert SearchRequest to Passenger objects for Amadeus
    passengers = _convert_search_request_to_passengers(search_request)
    
    amadeus_service = AmadeusProvider()
    
    if search_request.is_roundtrip:
        return _search_roundtrip_strategy(amadeus_service, strategy, search_request, passengers)
    else:
        return _search_oneway_strategy(amadeus_service, strategy, search_request, passengers)

def _convert_search_request_to_passengers(search_request: SearchRequest) -> List[Passenger]:
    """Convert SearchRequest to list of Passenger objects for Amadeus"""
    
    passengers = []
    
    # Add adults
    for i in range(search_request.adults):
        passengers.append(Passenger(
            passenger_type=PassengerType.ADULT,
            first_name=f"Adult{i+1}",  # Placeholder names
            last_name="Passenger",
            date_of_birth=datetime(1990, 1, 1),  # Default DOB
            gender="",
            nationality="US",
            email="",
            phone=""
        ))
    
    # Add children  
    for i in range(search_request.children):
        passengers.append(Passenger(
            passenger_type=PassengerType.CHILD,
            first_name=f"Child{i+1}",
            last_name="Passenger", 
            date_of_birth=datetime(2015, 1, 1),  # Default child DOB
            gender="",
            nationality="US",
            email="",
            phone=""
        ))
    
    # Add infants
    for i in range(search_request.infants):
        passengers.append(Passenger(
            passenger_type=PassengerType.INFANT,
            first_name=f"Infant{i+1}",
            last_name="Passenger",
            date_of_birth=datetime(2023, 1, 1),  # Default infant DOB
            gender="",
            nationality="US", 
            email="",
            phone=""
        ))
    
    return passengers

def _search_oneway_strategy(amadeus_service: AmadeusProvider, strategy: SearchStrategy, search_request: SearchRequest, passengers: List[Passenger]) -> List[Dict]:
    """Search one-way flights using existing Amadeus service"""
    
    if len(strategy.outbound_route) == 2:
        # Direct flight - use your existing service as-is
        simplified_response, full_response = amadeus_service.search_flights(
            origin=strategy.outbound_route[0],
            destination=strategy.outbound_route[1], 
            departure_date=search_request.departure_date,
            return_date=None,  # One-way
            passengers=passengers,
            travel_class=search_request.travel_class.upper()
        )
        
        if full_response.success:
            return [offer.__dict__ for offer in full_response.flights]
        else:
            return []
    
    else:
        # Multi-segment flight - we'll handle this by searching each segment
        # For now, return empty (you can enhance this later)
        return []

def _search_roundtrip_strategy(amadeus_service: AmadeusProvider, strategy: SearchStrategy, search_request: SearchRequest, passengers: List[Passenger]) -> List[Dict]:
    """Search round-trip flights using existing Amadeus service"""
    
    if len(strategy.outbound_route) == 2 and strategy.return_route and len(strategy.return_route) == 2:
        # Simple round-trip
        simplified_response, full_response = amadeus_service.search_flights(
            origin=strategy.outbound_route[0],
            destination=strategy.outbound_route[1],
            departure_date=search_request.departure_date,
            return_date=search_request.return_date,
            passengers=passengers,
            travel_class=search_request.travel_class.upper()
        )
        
        if full_response.success:
            return [offer.__dict__ for offer in full_response.flights]
        else:
            return []
    
    else:
        # Complex multi-segment round-trip - handle later
        return []


def _enrich_flight_results(flights: List[Dict], strategy: SearchStrategy, search_request: SearchRequest) -> List[Dict]:
    """Enhanced enrichment that works with your Amadeus FlightOffer objects"""
    enriched_flights = []

    for flight_dict in flights:
        try:
            # Create a copy to avoid modifying original
            enriched_flight = flight_dict.copy()

            # Add strategy context
            enriched_flight['search_strategy'] = strategy.strategy_type
            enriched_flight['strategy_explanation'] = strategy.explanation
            enriched_flight['routing_used'] = strategy.outbound_route

            # Add total cost including transport
            if 'pricing' in enriched_flight and enriched_flight['pricing']:
                # The error is here. The 'pricing' object is not a dictionary.
                # You must use dot notation to access its attributes.
                # The corrected line is below.
                base_price = float(enriched_flight['pricing'].price_total)
                enriched_flight['total_cost_with_transport'] = base_price + strategy.extra_transport_cost
            else:
                enriched_flight['total_cost_with_transport'] = strategy.extra_transport_cost

            # Add airline policies from data manager (your existing logic)
            if 'airline_code' in enriched_flight:
                airline_code = enriched_flight['airline_code']
                enriched_flight['baggage_policy'] = data_manager.get_airline_policy(airline_code, 'baggage_policies')
                enriched_flight['cancellation_policy'] = data_manager.get_airline_policy(airline_code, 'cancellation_policies')
            
            enriched_flights.append(enriched_flight)
        
        except Exception as e:
            # Log the full exception with traceback and the problematic data
            logger.error(
                f"Error processing flight enrichment for flight ID '{flight_dict.get('id', 'N/A')}'. "
                f"Error: {e}",
                exc_info=True,  # This logs the full traceback
                extra={'flight_data': flight_dict} # Logs the entire dictionary for inspection
            )
            # You can choose to append the original flight or just continue
            # For this case, we'll continue to process the other flights.
            continue
    
    return enriched_flights

def _process_search_results(search_results: List[SearchResult], search_request: SearchRequest) -> Dict:
    """Process and group all search results"""
    all_flights = []
    successful_searches = 0
    failed_searches = []
    
    for result in search_results:
        if result.success:
            successful_searches += 1
            all_flights.extend(result.flights)
        else:
            failed_searches.append({
                'strategy': result.strategy.explanation,
                'error': result.error_message
            })
    
    # Sort by total cost with transport
    all_flights.sort(key=lambda x: x['total_cost_with_transport'])
    
    return {
        'search_summary': {
            'total_strategies_attempted': len(search_results),
            'successful_searches': successful_searches,
            'total_flights_found': len(all_flights),
            'search_request': search_request.__dict__
        },
        'results': {
            'best_deals': all_flights[:5],
            'direct_flights': [f for f in all_flights if f['search_strategy'] == 'direct'][:3],
            'nearby_airport_options': [f for f in all_flights if f['search_strategy'] == 'nearby'][:3],
            'hub_connections': [f for f in all_flights if f['search_strategy'] == 'hub'][:3]
        },
        'debug_info': {
            'failed_searches': failed_searches
        }
    }
