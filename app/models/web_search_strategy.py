from dataclasses import dataclass
from typing import List, Optional, Tuple
import logging
from app.models.web_search_data import SearchRequest, is_hub_sensible
from pydantic import ValidationError
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime, timedelta

# Set up logger
logger = logging.getLogger(__name__)

@dataclass
class SearchStrategy:
    outbound_route: List[str]  # ["SFO", "BKK"] or ["SFO", "NRT", "BKK"]
    return_route: Optional[List[str]] = None  # ["BKK", "SFO"] for round-trip
    strategy_type: str = "direct"  # direct, nearby, hub, creative
    extra_transport_cost: float = 0.0  # Ground transport cost
    explanation: str = ""
    departure_date: Optional[str] = None  # Store the actual departure date
    return_date: Optional[str] = None  # Store the actual return date

def validate_search_input(data):
    logger.info(f"Validating search input: {data}")
    
    required_fields = ["origin", "destination", "departure_date"]
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        logger.error(f"Missing required fields: {missing_fields}")
        raise ValidationError(f"Missing required field: {missing_fields[0]}")
    
    # Get flexible dates from the data parameter, not from request
    flexible_dates = data.get('flexible_dates', False)  # Boolean checkbox
    flexible_days = 3 if flexible_dates else 0  # ±3 days = 7 total dates
    
    search_request = SearchRequest(
        origin=data["origin"],
        destination=data["destination"],
        departure_date=data["departure_date"],
        return_date=data.get("return_date"),  # Optional for one-way
        adults=data.get("adults", 1),
        children=data.get("children", 0),
        infants=data.get("infants", 0),
        travel_class=data.get("travel_class", "economy"),
        special_needs=data.get("special_needs", []),
        flexible_days=flexible_days  # Make sure SearchRequest has this field
    )
    
    logger.info(f"✓ Search request validated: {search_request.origin} → {search_request.destination}, "
               f"{'round-trip' if search_request.return_date else 'one-way'}, "
               f"{search_request.adults + search_request.children + search_request.infants} passengers"
               f"{f', flexible ±{flexible_days} days' if flexible_days > 0 else ''}")
    
    return search_request

def generate_search_strategies(search_request: SearchRequest) -> List[SearchStrategy]:
    """Generate all search strategies for a given request"""
    logger.info(f"Generating search strategies for {search_request.origin} → {search_request.destination}")
    
    strategies = []
    
    # Check if flexible dates are enabled
    if search_request.flexible_days > 0:
        logger.info(f"Generating flexible date strategies (±{search_request.flexible_days} days)")
        strategies.extend(_generate_flexible_date_strategies(search_request))
    else:
        # Normal single-date search
        if search_request.is_roundtrip:
            logger.info("Generating round-trip strategies")
            strategies.extend(_generate_roundtrip_strategies(search_request))
        else:
            logger.info("Generating one-way strategies")
            strategies.extend(_generate_oneway_strategies(search_request))
    
    ranked_strategies = _rank_strategies(strategies)
    
    logger.info(f"Generated {len(ranked_strategies)} total strategies")
    logger.debug("Strategy summary:")
    for i, strategy in enumerate(ranked_strategies[:5]):  # Log top 5 strategies
        route_str = " → ".join(strategy.outbound_route)
        if strategy.return_route:
            route_str += f" | Return: {' → '.join(strategy.return_route)}"
        logger.debug(f"  {i+1}. [{strategy.strategy_type.upper()}] {route_str} "
                    f"(+${strategy.extra_transport_cost}) - {strategy.explanation}")
    
    return ranked_strategies

def _generate_flexible_date_strategies(search_request: SearchRequest) -> List[SearchStrategy]:
    """
    Generate search strategies for flexible dates.
    For ±3 days, searches departure_date -3, -2, -1, 0, +1, +2, +3
    """
    all_strategies = []
    base_departure = datetime.strptime(search_request.departure_date, "%Y-%m-%d")
    
    # Calculate trip duration if round-trip
    trip_duration = None
    if search_request.return_date:
        base_return = datetime.strptime(search_request.return_date, "%Y-%m-%d")
        trip_duration = (base_return - base_departure).days
    
    logger.info(f"Generating flexible date strategies: ±{search_request.flexible_days} days "
               f"({'round-trip' if trip_duration else 'one-way'})")
    
    # Generate strategies for each date in the range
    for day_offset in range(-search_request.flexible_days, search_request.flexible_days + 1):
        new_departure = base_departure + timedelta(days=day_offset)
        new_return = None
        
        if trip_duration is not None:
            new_return = new_departure + timedelta(days=trip_duration)
        
        # Create modified search request for this date
        modified_request = SearchRequest(
            origin=search_request.origin,
            destination=search_request.destination,
            departure_date=new_departure.strftime("%Y-%m-%d"),
            return_date=new_return.strftime("%Y-%m-%d") if new_return else None,
            adults=search_request.adults,
            children=search_request.children,
            infants=search_request.infants,
            travel_class=search_request.travel_class,
            special_needs=search_request.special_needs,
            flexible_days=0  # Don't recurse
        )
        
        # Generate strategies for this specific date
        if modified_request.is_roundtrip:
            date_strategies = _generate_roundtrip_strategies(modified_request)
        else:
            date_strategies = _generate_oneway_strategies(modified_request)
        
        # Store actual dates and add date label to explanation
        date_label = new_departure.strftime('%b %d')
        for strategy in date_strategies:
            strategy.departure_date = new_departure.strftime("%Y-%m-%d")
            strategy.return_date = new_return.strftime("%Y-%m-%d") if new_return else None
            
            if day_offset != 0:
                if new_return:
                    return_label = new_return.strftime('%b %d')
                    strategy.explanation += f" [Out: {date_label}, Back: {return_label}]"
                else:
                    strategy.explanation += f" [Depart: {date_label}]"
        
        all_strategies.extend(date_strategies)
        
        logger.debug(f"Added {len(date_strategies)} strategies for departure {date_label}")
    
    total_dates = (2 * search_request.flexible_days) + 1
    logger.info(f"Generated {len(all_strategies)} total strategies across {total_dates} dates "
               f"({len(all_strategies) // total_dates} strategies per date)")
    
    return all_strategies

def _generate_oneway_strategies(search_request: SearchRequest) -> List[SearchStrategy]:
    from app.models.web_search_data_manager import data_manager

    strategies = []
    origin = search_request.origin
    destination = search_request.destination
    
    origin_airport = data_manager.get_airport_info(origin)
    dest_airport = data_manager.get_airport_info(destination)
    
    if not origin_airport or not dest_airport:
        logger.warning(f"Missing airport data for {origin} or {destination}")
        return strategies
    
    origin_coords = origin_airport.get('coordinates')
    dest_coords = dest_airport.get('coordinates')
    
    logger.debug(f"Building one-way strategies from {origin} to {destination}")
    
    # 1. Direct route
    strategies.append(SearchStrategy(
        outbound_route=[origin, destination],
        strategy_type="direct",
        explanation="Direct flight"
    ))
    logger.debug(f"✓ Added direct route: {origin} → {destination}")
    
    # 2. From nearby origin airports
    nearby_airports = data_manager.get_nearby_airports(origin)
    logger.debug(f"Found {len(nearby_airports)} nearby airports for {origin}")
    
    for nearby in nearby_airports:
        # Safely get transport cost
        transport_options = nearby.get('transport_options', {})
        uber_cost = 0
        
        if 'uber' in transport_options:
            uber_cost = transport_options['uber'].get('cost_usd', 0)
        elif 'bus' in transport_options:
            uber_cost = transport_options['bus'].get('cost_usd', 0)
        elif 'train' in transport_options:
            uber_cost = transport_options['train'].get('cost_usd', 0)
        
        strategies.append(SearchStrategy(
            outbound_route=[nearby['code'], destination],
            strategy_type="nearby",
            extra_transport_cost=uber_cost,
            explanation=f"Fly from {nearby['code']} (+${uber_cost} transport)"
        ))
        logger.debug(f"✓ Added nearby airport strategy: {nearby['code']} → {destination} (+${uber_cost})")
    
    # 3. Single hub routing - IMPROVED VERSION
    sensible_hubs = _find_sensible_single_hubs(
        origin, destination, origin_coords, dest_coords, data_manager
    )
    
    logger.debug(f"Found {len(sensible_hubs)} sensible hubs")
    
    for hub_code, score in sensible_hubs:
        strategies.append(SearchStrategy(
            outbound_route=[origin, hub_code, destination],
            strategy_type="hub",
            explanation=f"Connect via {hub_code}"
        ))
        logger.debug(f"✓ Added hub strategy: {origin} → {hub_code} → {destination} (score: {score:.2f})")
    
    # 4. Double hub routing - FOR REALLY CHEAP OPTIONS
    if len(sensible_hubs) > 0:
        double_hub_strategies = _find_sensible_double_hubs(
            origin, destination, origin_coords, dest_coords, 
            sensible_hubs, data_manager
        )
        
        logger.debug(f"Found {len(double_hub_strategies)} double hub strategies")
        
        for route, explanation in double_hub_strategies:
            strategies.append(SearchStrategy(
                outbound_route=route,
                strategy_type="creative",
                explanation=explanation
            ))
            logger.debug(f"✓ Added double hub: {' → '.join(route)}")
    
    # 5. Creative: nearby + hub
    creative_count = 0
    for nearby in nearby_airports[:3]:  # Limit to top 3 nearby airports
        nearby_airport = data_manager.get_airport_info(nearby['code'])
        if not nearby_airport:
            continue
            
        nearby_coords = nearby_airport.get('coordinates')
        if not nearby_coords:
            continue
        
        # Find hubs sensible from the nearby airport
        nearby_sensible_hubs = _find_sensible_single_hubs(
            nearby['code'], destination, nearby_coords, dest_coords, data_manager
        )
        
        for hub_code, score in nearby_sensible_hubs[:3]:
            # Safely get transport cost
            transport_options = nearby.get('transport_options', {})
            uber_cost = 0
            
            if 'uber' in transport_options:
                uber_cost = transport_options['uber'].get('cost_usd', 0)
            elif 'bus' in transport_options:
                uber_cost = transport_options['bus'].get('cost_usd', 0)
            elif 'train' in transport_options:
                uber_cost = transport_options['train'].get('cost_usd', 0)
            
            strategies.append(SearchStrategy(
                outbound_route=[nearby['code'], hub_code, destination],
                strategy_type="creative",
                extra_transport_cost=uber_cost,
                explanation=f"From {nearby['code']} via {hub_code} (+${uber_cost})"
            ))
            creative_count += 1
            logger.debug(f"✓ Added creative: {nearby['code']} → {hub_code} → {destination}")
    
    logger.info(f"One-way strategies generated: "
               f"1 direct, {len(nearby_airports)} nearby, "
               f"{len(sensible_hubs)} hub, "
               f"{len([s for s in strategies if s.strategy_type == 'creative'])} creative")
    
    return strategies

def _generate_roundtrip_strategies(search_request: SearchRequest) -> List[SearchStrategy]:
    from app.models.web_search_data_manager import data_manager

    strategies = []
    origin = search_request.origin
    destination = search_request.destination
    
    origin_airport = data_manager.get_airport_info(origin)
    dest_airport = data_manager.get_airport_info(destination)
    
    if not origin_airport or not dest_airport:
        logger.warning(f"Missing airport data for {origin} or {destination}")
        return strategies
    
    origin_coords = origin_airport.get('coordinates')
    dest_coords = dest_airport.get('coordinates')
    
    logger.debug(f"Building round-trip strategies from {origin} to {destination}")
    
    # 1. Direct round-trip
    strategies.append(SearchStrategy(
        outbound_route=[origin, destination],
        return_route=[destination, origin],
        strategy_type="direct",
        explanation="Direct round-trip"
    ))
    logger.debug(f"✓ Added direct round-trip: {origin} ⇄ {destination}")
    
    # 2. Nearby airports (symmetric - same airport both ways)
    nearby_airports = data_manager.get_nearby_airports(origin)
    logger.debug(f"Found {len(nearby_airports)} nearby airports for round-trip from {origin}")
    
    for nearby in nearby_airports:
        # Safely get transport cost
        transport_options = nearby.get('transport_options', {})
        uber_cost = 0
        
        if 'uber' in transport_options:
            uber_cost = transport_options['uber'].get('cost_usd', 0)
        elif 'bus' in transport_options:
            uber_cost = transport_options['bus'].get('cost_usd', 0)
        elif 'train' in transport_options:
            uber_cost = transport_options['train'].get('cost_usd', 0)
        
        # Only charge transport once for round-trip (you return to same nearby airport)
        strategies.append(SearchStrategy(
            outbound_route=[nearby['code'], destination],
            return_route=[destination, nearby['code']],
            strategy_type="nearby",
            extra_transport_cost=uber_cost,
            explanation=f"Round-trip via {nearby['code']} (+${uber_cost} transport)"
        ))
        logger.debug(f"✓ Added nearby round-trip: {nearby['code']} ⇄ {destination} (+${uber_cost})")
    
    # 3. Single hub routing - SYMMETRIC (same hub both ways)
    sensible_hubs = _find_sensible_single_hubs(
        origin, destination, origin_coords, dest_coords, data_manager
    )
    
    logger.debug(f"Found {len(sensible_hubs)} sensible hubs for round-trip")
    
    for hub_code, score in sensible_hubs:
        strategies.append(SearchStrategy(
            outbound_route=[origin, hub_code, destination],
            return_route=[destination, hub_code, origin],
            strategy_type="hub",
            explanation=f"Round-trip via {hub_code} hub"
        ))
        logger.debug(f"✓ Added symmetric hub round-trip: {origin} ⇄ {destination} via {hub_code}")
    
    # 4. Single hub routing - ASYMMETRIC (different hubs each way)
    if len(sensible_hubs) >= 2:
        asymmetric_strategies = _find_asymmetric_hub_routes(
            origin, destination, origin_coords, dest_coords,
            sensible_hubs, data_manager
        )
        
        logger.debug(f"Found {len(asymmetric_strategies)} asymmetric hub strategies")
        strategies.extend(asymmetric_strategies)
    
    # 5. Double hub routing - SYMMETRIC (same path both ways)
    if len(sensible_hubs) > 0:
        double_hub_strategies = _find_sensible_double_hubs_roundtrip(
            origin, destination, origin_coords, dest_coords,
            sensible_hubs, data_manager
        )
        
        logger.debug(f"Found {len(double_hub_strategies)} double hub round-trip strategies")
        strategies.extend(double_hub_strategies)
    
    # 6. Creative: nearby + hub (symmetric)
    creative_count = 0
    for nearby in nearby_airports[:3]:  # Limit nearby airports
        nearby_airport = data_manager.get_airport_info(nearby['code'])
        if not nearby_airport:
            continue
            
        nearby_coords = nearby_airport.get('coordinates')
        if not nearby_coords:
            continue
        
        nearby_sensible_hubs = _find_sensible_single_hubs(
            nearby['code'], destination, nearby_coords, dest_coords, data_manager
        )
        
        for hub_code, score in nearby_sensible_hubs[:2]:  # Top 2 hubs
            # Safely get transport cost
            transport_options = nearby.get('transport_options', {})
            uber_cost = 0
            
            if 'uber' in transport_options:
                uber_cost = transport_options['uber'].get('cost_usd', 0)
            elif 'bus' in transport_options:
                uber_cost = transport_options['bus'].get('cost_usd', 0)
            elif 'train' in transport_options:
                uber_cost = transport_options['train'].get('cost_usd', 0)
            
            strategies.append(SearchStrategy(
                outbound_route=[nearby['code'], hub_code, destination],
                return_route=[destination, hub_code, nearby['code']],
                strategy_type="creative",
                extra_transport_cost=uber_cost,
                explanation=f"Round-trip from {nearby['code']} via {hub_code} (+${uber_cost})"
            ))
            creative_count += 1
            logger.debug(f"✓ Added creative round-trip: {nearby['code']} ⇄ {destination} via {hub_code}")
    
    logger.info(f"Round-trip strategies: "
               f"1 direct, {len(nearby_airports)} nearby, "
               f"{len(sensible_hubs)} symmetric hubs, "
               f"{len([s for s in strategies if 'Out via' in s.explanation])} asymmetric, "
               f"{creative_count} creative")
    
    return strategies

def _find_sensible_single_hubs(origin, destination, origin_coords, dest_coords, 
                                data_manager, max_hubs=5):
    """Find hubs that make geographic AND connectivity sense"""
    
    reachable_hubs = data_manager.get_reachable_hubs(origin)
    scored_hubs = []
    
    for hub in reachable_hubs:
        hub_code = hub['code']
        hub_airport = data_manager.get_airport_info(hub_code)
        
        if not hub_airport:
            continue
            
        hub_coords = hub_airport.get('coordinates')
        if not hub_coords or not origin_coords or not dest_coords:
            continue
        
        # Calculate geographic efficiency
        if not is_hub_sensible(origin_coords, hub_coords, dest_coords, tolerance=1.4):
            continue
        
        # Score the hub based on multiple factors
        score = _score_hub_quality(
            origin, hub_code, destination,
            origin_coords, hub_coords, dest_coords,
            hub_airport, data_manager
        )
        
        scored_hubs.append((hub_code, score))
    
    # Sort by score (lower is better) and return top hubs
    scored_hubs.sort(key=lambda x: x[1])
    return scored_hubs[:max_hubs]

def _score_hub_quality(origin, hub_code, destination, 
                       origin_coords, hub_coords, dest_coords,
                       hub_airport, data_manager):
    """Score a hub based on multiple quality factors. Lower score = better hub."""

    # Normalize coordinates (in case they are dicts)
    if isinstance(origin_coords, dict):
        origin_coords = [origin_coords.get("lat"), origin_coords.get("lng")]  # ✓ Fixed
    if isinstance(hub_coords, dict):
        hub_coords = [hub_coords.get("lat"), hub_coords.get("lng")]           # ✓ Fixed
    if isinstance(dest_coords, dict):
        dest_coords = [dest_coords.get("lat"), dest_coords.get("lng")]        # ✓ Fixed

    # 1. Geographic efficiency
    direct_distance = _haversine_distance(origin_coords, dest_coords)
    via_hub_distance = (_haversine_distance(origin_coords, hub_coords) + 
                        _haversine_distance(hub_coords, dest_coords))
    detour_ratio = via_hub_distance / direct_distance if direct_distance > 0 else 999

    # 2. Hub size
    hub_size_score = 1.0 / (hub_airport.get('annual_passengers_millions', 1) + 1)

    # 3. Connectivity
    hub_destinations = data_manager.get_hub_destinations(hub_code)
    has_connection = destination in hub_destinations if hub_destinations else False
    connection_penalty = 0 if has_connection else 0.5

    # 4. Direction
    origin_to_hub_lat = hub_coords[0] - origin_coords[0] # type: ignore
    origin_to_dest_lat = dest_coords[0] - origin_coords[0] # type: ignore
    same_direction = (origin_to_hub_lat * origin_to_dest_lat) >= 0
    direction_bonus = 0 if same_direction else 0.3

    # Combined score
    score = (detour_ratio * 0.5) + hub_size_score + connection_penalty + direction_bonus
    return score

def _find_sensible_double_hubs(origin, destination, origin_coords, dest_coords,
                               single_hubs, data_manager, max_routes=3):
    """
    Find 2-stop routes that might be cheaper than 1-stop.
    Only consider if both hubs make sense geographically.
    """
    double_hub_routes = []
    
    direct_distance = _haversine_distance(origin_coords, dest_coords)
    
    # Only consider double hubs for routes > 3000km
    if direct_distance < 3000:
        return []
    
    # Try combinations of the best single hubs
    for hub1_code, hub1_score in single_hubs[:3]:
        hub1_airport = data_manager.get_airport_info(hub1_code)
        if not hub1_airport:
            continue
            
        hub1_coords = hub1_airport.get('coordinates')
        if not hub1_coords:
            continue
        
        # Find hubs reachable from hub1 that also reach destination
        hubs_from_hub1 = data_manager.get_reachable_hubs(hub1_code)
        
        for hub2_info in hubs_from_hub1[:5]:
            hub2_code = hub2_info['code']
            
            # Don't repeat hubs
            if hub2_code == hub1_code:
                continue
            
            hub2_airport = data_manager.get_airport_info(hub2_code)
            if not hub2_airport:
                continue
                
            hub2_coords = hub2_airport.get('coordinates')
            if not hub2_coords:
                continue
            
            # Check if hub2 -> destination makes sense
            if not is_hub_sensible(hub1_coords, hub2_coords, dest_coords, tolerance=1.4):
                continue
            
            # Check total detour isn't too large
            total_distance = (
                _haversine_distance(origin_coords, hub1_coords) +
                _haversine_distance(hub1_coords, hub2_coords) +
                _haversine_distance(hub2_coords, dest_coords)
            )
            
            detour_ratio = total_distance / direct_distance
            
            # Only accept if detour is reasonable (< 1.6x direct distance)
            if detour_ratio > 1.6:
                continue
            
            route = [origin, hub1_code, hub2_code, destination]
            explanation = f"Via {hub1_code} and {hub2_code} (2 stops)"
            
            double_hub_routes.append((route, explanation))
            
            if len(double_hub_routes) >= max_routes:
                return double_hub_routes
    
    return double_hub_routes

def _find_asymmetric_hub_routes(origin, destination, origin_coords, dest_coords,
                                sensible_hubs, data_manager, max_routes=5):
    """
    Find round-trip routes where outbound and return use different hubs.
    Example: SFO -> DFW -> BKK outbound, BKK -> NRT -> SFO return
    
    This can sometimes find cheaper combinations.
    """
    strategies = []
    
    # Try different hub combinations
    for outbound_hub, out_score in sensible_hubs[:4]:
        for return_hub, ret_score in sensible_hubs[:4]:
            # Skip if same hub (that's already covered by symmetric routes)
            if outbound_hub == return_hub:
                continue
            
            # Check if this combination makes sense
            outbound_hub_airport = data_manager.get_airport_info(outbound_hub)
            return_hub_airport = data_manager.get_airport_info(return_hub)
            
            if not outbound_hub_airport or not return_hub_airport:
                continue
            
            strategies.append(SearchStrategy(
                outbound_route=[origin, outbound_hub, destination],
                return_route=[destination, return_hub, origin],
                strategy_type="hub",
                explanation=f"Out via {outbound_hub}, return via {return_hub}"
            ))
            
            logger.debug(f"✓ Added asymmetric: Out via {outbound_hub}, return via {return_hub}")
            
            if len(strategies) >= max_routes:
                return strategies
    
    return strategies

def _find_sensible_double_hubs_roundtrip(origin, destination, origin_coords, dest_coords,
                                         single_hubs, data_manager, max_routes=2):
    """
    Find 2-stop round-trip routes (symmetric - same path both ways).
    Only for very long routes where ultra-budget options might exist.
    """
    
    direct_distance = _haversine_distance(origin_coords, dest_coords)
    
    # Only consider double hubs for routes > 4000km (longer threshold for round-trip)
    if direct_distance < 4000:
        return []
    
    strategies = []
    
    # Try combinations of best single hubs
    for hub1_code, hub1_score in single_hubs[:3]:
        hub1_airport = data_manager.get_airport_info(hub1_code)
        if not hub1_airport:
            continue
            
        hub1_coords = hub1_airport.get('coordinates')
        if not hub1_coords:
            continue
        
        hubs_from_hub1 = data_manager.get_reachable_hubs(hub1_code)
        
        for hub2_info in hubs_from_hub1[:5]:
            hub2_code = hub2_info['code']
            
            if hub2_code == hub1_code:
                continue
            
            hub2_airport = data_manager.get_airport_info(hub2_code)
            if not hub2_airport:
                continue
                
            hub2_coords = hub2_airport.get('coordinates')
            if not hub2_coords:
                continue
            
            # Check geographic sensibility
            if not is_hub_sensible(hub1_coords, hub2_coords, dest_coords, tolerance=1.4):
                continue
            
            # Check total detour
            total_distance = (
                _haversine_distance(origin_coords, hub1_coords) +
                _haversine_distance(hub1_coords, hub2_coords) +
                _haversine_distance(hub2_coords, dest_coords)
            )
            
            detour_ratio = total_distance / direct_distance
            
            if detour_ratio > 1.6:
                continue
            
            strategies.append(SearchStrategy(
                outbound_route=[origin, hub1_code, hub2_code, destination],
                return_route=[destination, hub2_code, hub1_code, origin],
                strategy_type="creative",
                explanation=f"Round-trip via {hub1_code} and {hub2_code} (2 stops each way)"
            ))
            
            logger.debug(f"✓ Added double hub round-trip: via {hub1_code} and {hub2_code}")
            
            if len(strategies) >= max_routes:
                return strategies
    
    return strategies

def _haversine_distance(coord1, coord2):
    """Calculate great circle distance in km between two coordinates"""
    # Handle both dict format {'lat': x, 'lng': y} and tuple format (lat, lng)
    if isinstance(coord1, dict):
        lat1, lon1 = radians(coord1['lat']), radians(coord1['lng'])
    else:
        logger.debug(f"coord1: {coord1}")
        logger.debug(f"coord2: {coord2}")
        lat1, lon1 = radians(coord1[0]), radians(coord1[1])
    
    if isinstance(coord2, dict):
        lat2, lon2 = radians(coord2['lat']), radians(coord2['lng'])
    else:
        lat2, lon2 = radians(coord2[0]), radians(coord2[1])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return 6371 * c  # Earth radius in km

def _rank_strategies(strategies: List[SearchStrategy]) -> List[SearchStrategy]:
    """Rank strategies by likely success (simple heuristic)"""
    logger.debug(f"Ranking {len(strategies)} strategies by priority")
    
    def strategy_priority(strategy):
        # Lower number = higher priority
        priority_map = {"direct": 1, "nearby": 2, "hub": 3, "creative": 4}
        route_complexity = len(strategy.outbound_route) - 1  # 0 for direct, 1 for 1-stop
        return (priority_map.get(strategy.strategy_type, 5), route_complexity, strategy.extra_transport_cost)
    
    ranked = sorted(strategies, key=strategy_priority)
    
    # Log ranking breakdown
    ranking_stats = {}
    for strategy in ranked:
        ranking_stats[strategy.strategy_type] = ranking_stats.get(strategy.strategy_type, 0) + 1
    
    logger.debug(f"Ranking breakdown: {dict(ranking_stats)}")
    
    return ranked
