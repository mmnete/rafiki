

from dataclasses import dataclass
from typing import List, Optional
from app.models.web_search_data import SearchRequest
from pydantic import ValidationError

@dataclass
class SearchStrategy:
    outbound_route: List[str]  # ["SFO", "BKK"] or ["SFO", "NRT", "BKK"]
    return_route: Optional[List[str]] = None  # ["BKK", "SFO"] for round-trip
    strategy_type: str = "direct"  # direct, nearby, hub, creative
    extra_transport_cost: float = 0.0  # Ground transport cost
    explanation: str = ""

def validate_search_input(data):
    required_fields = ["origin", "destination", "departure_date"]
    for field in required_fields:
        if field not in data:
            raise ValidationError(f"Missing required field: {field}")
    
    return SearchRequest(
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

def generate_search_strategies(search_request: SearchRequest) -> List[SearchStrategy]:
    """Generate all search strategies for a given request"""
    strategies = []
    
    if search_request.is_roundtrip:
        strategies.extend(_generate_roundtrip_strategies(search_request))
    else:
        strategies.extend(_generate_oneway_strategies(search_request))
    
    return _rank_strategies(strategies)

def _generate_oneway_strategies(search_request: SearchRequest) -> List[SearchStrategy]:
    from app.models.web_search_data_manager import data_manager

    strategies = []
    origin = search_request.origin
    destination = search_request.destination
    
    # 1. Direct route
    strategies.append(SearchStrategy(
        outbound_route=[origin, destination],
        strategy_type="direct",
        explanation="Direct flight"
    ))
    
    # 2. From nearby origin airports
    for nearby in data_manager.get_nearby_airports(origin):
        uber_cost = nearby['transport_options']['uber']['cost_usd']
        strategies.append(SearchStrategy(
            outbound_route=[nearby['code'], destination],
            strategy_type="nearby",
            extra_transport_cost=uber_cost,
            explanation=f"Fly from {nearby['code']} (+${uber_cost} transport)"
        ))
    
    # 3. Hub routing
    for hub in data_manager.get_reachable_hubs(origin):
        strategies.append(SearchStrategy(
            outbound_route=[origin, hub['code'], destination],
            strategy_type="hub",
            explanation=f"Connect via {hub['code']}"
        ))
    
    # 4. Creative: nearby + hub
    for nearby in data_manager.get_nearby_airports(origin):
        for hub in data_manager.get_reachable_hubs(nearby['code']):
            uber_cost = nearby['transport_options']['uber']['cost_usd']
            strategies.append(SearchStrategy(
                outbound_route=[nearby['code'], hub['code'], destination],
                strategy_type="creative",
                extra_transport_cost=uber_cost,
                explanation=f"From {nearby['code']} via {hub['code']} (+${uber_cost})"
            ))
    
    return strategies

def _generate_roundtrip_strategies(search_request: SearchRequest) -> List[SearchStrategy]:
    from app.models.web_search_data_manager import data_manager

    strategies = []
    origin = search_request.origin
    destination = search_request.destination
    
    # 1. Direct round-trip (same airports)
    strategies.append(SearchStrategy(
        outbound_route=[origin, destination],
        return_route=[destination, origin],
        strategy_type="direct",
        explanation="Direct round-trip"
    ))
    
    # 2. Nearby airports (consistent for both directions)
    for nearby in data_manager.get_nearby_airports(origin):
        uber_cost = nearby['transport_options']['uber']['cost_usd']
        strategies.append(SearchStrategy(
            outbound_route=[nearby['code'], destination],
            return_route=[destination, nearby['code']],
            strategy_type="nearby",
            extra_transport_cost=uber_cost,  # Only charge once for round-trip
            explanation=f"Round-trip via {nearby['code']} (+${uber_cost} transport)"
        ))
    
    # 3. Hub routing (same hub both ways)
    for hub in data_manager.get_reachable_hubs(origin):
        strategies.append(SearchStrategy(
            outbound_route=[origin, hub['code'], destination],
            return_route=[destination, hub['code'], origin],
            strategy_type="hub",
            explanation=f"Round-trip via {hub['code']} hub"
        ))
    
    return strategies

def _rank_strategies(strategies: List[SearchStrategy]) -> List[SearchStrategy]:
    """Rank strategies by likely success (simple heuristic)"""
    def strategy_priority(strategy):
        # Lower number = higher priority
        priority_map = {"direct": 1, "nearby": 2, "hub": 3, "creative": 4}
        route_complexity = len(strategy.outbound_route) - 1  # 0 for direct, 1 for 1-stop
        return (priority_map.get(strategy.strategy_type, 5), route_complexity, strategy.extra_transport_cost)
    
    return sorted(strategies, key=strategy_priority)