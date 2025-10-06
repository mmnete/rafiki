from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
import math

@dataclass
class SearchRequest:
    origin: str
    destination: str
    departure_date: str  # "2024-03-15"
    return_date: Optional[str] = None
    adults: int = 1
    children: int = 0
    infants: int = 0
    flexible_days: int = 0
    travel_class: str = "economy"  # economy, premium_economy, business, first
    special_needs: List[str] = field(default_factory=list)
    
    # def __post_init__(self):
    #     if self.special_needs is None:
    #         self.special_needs = []
    
    @property
    def is_roundtrip(self) -> bool:
        return self.return_date is not None
    
    @property
    def total_passengers(self) -> int:
        return self.adults + self.children + self.infants


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate great circle distance in miles using Haversine formula"""
    R = 3959  # Earth's radius in miles
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

def is_hub_sensible(origin_coords, hub_coords, dest_coords, tolerance=1.2):
    """
    Check if hub is geographically sensible
    tolerance=1.2 means hub route can be up to 20% longer than direct
    """
    # Distance direct
    direct_distance = calculate_distance(
        origin_coords['lat'], origin_coords['lng'],
        dest_coords['lat'], dest_coords['lng']
    )
    
    # Distance via hub
    via_hub_distance = (
        calculate_distance(
            origin_coords['lat'], origin_coords['lng'],
            hub_coords['lat'], hub_coords['lng']
        ) +
        calculate_distance(
            hub_coords['lat'], hub_coords['lng'],
            dest_coords['lat'], dest_coords['lng']
        )
    )
    
    # Hub is sensible if detour isn't too big
    return via_hub_distance <= (direct_distance * tolerance)