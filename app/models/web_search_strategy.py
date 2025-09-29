from dataclasses import dataclass
from typing import List, Optional
import logging
from app.models.web_search_data import SearchRequest
from pydantic import ValidationError

# Set up logger
logger = logging.getLogger(__name__)

@dataclass
class SearchStrategy:
    outbound_route: List[str]  # ["SFO", "BKK"] or ["SFO", "NRT", "BKK"]
    return_route: Optional[List[str]] = None  # ["BKK", "SFO"] for round-trip
    strategy_type: str = "direct"  # direct, nearby, hub, creative
    extra_transport_cost: float = 0.0  # Ground transport cost
    explanation: str = ""

def validate_search_input(data):
    logger.info(f"Validating search input: {data}")
    
    required_fields = ["origin", "destination", "departure_date"]
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        logger.error(f"Missing required fields: {missing_fields}")
        raise ValidationError(f"Missing required field: {missing_fields[0]}")
    
    search_request = SearchRequest(
        origin=data["origin"],
        destination=data["destination"],
        departure_date=data["departure_date"],
        return_date=data.get("return_date"),  # Optional for one-way
        adults=data.get("adults", 1),
        children=data.get("children", 0),
        infants=data.get("infants", 0),
        travel_class=data.get("travel_class", "economy"),
        special_needs=data.get("special_needs", [])
    )
    
    logger.info(f"✓ Search request validated: {search_request.origin} → {search_request.destination}, "
               f"{'round-trip' if search_request.return_date else 'one-way'}, "
               f"{search_request.adults + search_request.children + search_request.infants} passengers")
    
    return search_request

def generate_search_strategies(search_request: SearchRequest) -> List[SearchStrategy]:
    """Generate all search strategies for a given request"""
    logger.info(f"🔍 Generating search strategies for {search_request.origin} → {search_request.destination}")
    
    strategies = []
    
    if search_request.is_roundtrip:
        logger.info("📍 Generating round-trip strategies")
        strategies.extend(_generate_roundtrip_strategies(search_request))
    else:
        logger.info("📍 Generating one-way strategies")
        strategies.extend(_generate_oneway_strategies(search_request))
    
    ranked_strategies = _rank_strategies(strategies)
    
    logger.info(f"✅ Generated {len(ranked_strategies)} total strategies")
    logger.debug("Strategy summary:")
    for i, strategy in enumerate(ranked_strategies[:5]):  # Log top 5 strategies
        route_str = " → ".join(strategy.outbound_route)
        if strategy.return_route:
            route_str += f" | Return: {' → '.join(strategy.return_route)}"
        logger.debug(f"  {i+1}. [{strategy.strategy_type.upper()}] {route_str} "
                    f"(+${strategy.extra_transport_cost}) - {strategy.explanation}")
    
    return ranked_strategies

def _generate_oneway_strategies(search_request: SearchRequest) -> List[SearchStrategy]:
    from app.models.web_search_data_manager import data_manager

    strategies = []
    origin = search_request.origin
    destination = search_request.destination
    
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
        uber_cost = nearby['transport_options']['uber']['cost_usd']
        strategies.append(SearchStrategy(
            outbound_route=[nearby['code'], destination],
            strategy_type="nearby",
            extra_transport_cost=uber_cost,
            explanation=f"Fly from {nearby['code']} (+${uber_cost} transport)"
        ))
        logger.debug(f"✓ Added nearby airport strategy: {nearby['code']} → {destination} (+${uber_cost})")
    
    # 3. Hub routing
    reachable_hubs = data_manager.get_reachable_hubs(origin)
    logger.debug(f"Found {len(reachable_hubs)} reachable hubs from {origin}")
    
    for hub in reachable_hubs:
        strategies.append(SearchStrategy(
            outbound_route=[origin, hub['code'], destination],
            strategy_type="hub",
            explanation=f"Connect via {hub['code']}"
        ))
        logger.debug(f"✓ Added hub strategy: {origin} → {hub['code']} → {destination}")
    
    # 4. Creative: nearby + hub
    creative_count = 0
    for nearby in nearby_airports:
        hubs_from_nearby = data_manager.get_reachable_hubs(nearby['code'])
        for hub in hubs_from_nearby:
            uber_cost = nearby['transport_options']['uber']['cost_usd']
            strategies.append(SearchStrategy(
                outbound_route=[nearby['code'], hub['code'], destination],
                strategy_type="creative",
                extra_transport_cost=uber_cost,
                explanation=f"From {nearby['code']} via {hub['code']} (+${uber_cost})"
            ))
            creative_count += 1
    
    if creative_count > 0:
        logger.debug(f"✓ Added {creative_count} creative routing strategies")
    
    logger.info(f"📊 One-way strategies generated: "
               f"1 direct, {len(nearby_airports)} nearby, {len(reachable_hubs)} hub, {creative_count} creative")
    
    return strategies

def _generate_roundtrip_strategies(search_request: SearchRequest) -> List[SearchStrategy]:
    from app.models.web_search_data_manager import data_manager

    strategies = []
    origin = search_request.origin
    destination = search_request.destination
    
    logger.debug(f"Building round-trip strategies from {origin} to {destination}")
    
    # 1. Direct round-trip (same airports)
    strategies.append(SearchStrategy(
        outbound_route=[origin, destination],
        return_route=[destination, origin],
        strategy_type="direct",
        explanation="Direct round-trip"
    ))
    logger.debug(f"✓ Added direct round-trip: {origin} ⇄ {destination}")
    
    # 2. Nearby airports (consistent for both directions)
    nearby_airports = data_manager.get_nearby_airports(origin)
    logger.debug(f"Found {len(nearby_airports)} nearby airports for round-trip from {origin}")
    
    for nearby in nearby_airports:
        uber_cost = nearby['transport_options']['uber']['cost_usd']
        strategies.append(SearchStrategy(
            outbound_route=[nearby['code'], destination],
            return_route=[destination, nearby['code']],
            strategy_type="nearby",
            extra_transport_cost=uber_cost,  # Only charge once for round-trip
            explanation=f"Round-trip via {nearby['code']} (+${uber_cost} transport)"
        ))
        logger.debug(f"✓ Added nearby round-trip: {nearby['code']} ⇄ {destination} (+${uber_cost})")
    
    # 3. Hub routing (same hub both ways)
    reachable_hubs = data_manager.get_reachable_hubs(origin)
    logger.debug(f"Found {len(reachable_hubs)} reachable hubs for round-trip from {origin}")
    
    for hub in reachable_hubs:
        strategies.append(SearchStrategy(
            outbound_route=[origin, hub['code'], destination],
            return_route=[destination, hub['code'], origin],
            strategy_type="hub",
            explanation=f"Round-trip via {hub['code']} hub"
        ))
        logger.debug(f"✓ Added hub round-trip: {origin} ⇄ {destination} via {hub['code']}")
    
    logger.info(f"📊 Round-trip strategies generated: "
               f"1 direct, {len(nearby_airports)} nearby, {len(reachable_hubs)} hub")
    
    return strategies

def _rank_strategies(strategies: List[SearchStrategy]) -> List[SearchStrategy]:
    """Rank strategies by likely success (simple heuristic)"""
    logger.debug(f"🏆 Ranking {len(strategies)} strategies by priority")
    
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
