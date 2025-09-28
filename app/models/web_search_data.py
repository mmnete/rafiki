from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime

@dataclass
class SearchRequest:
    origin: str
    destination: str
    departure_date: str  # "2024-03-15"
    return_date: Optional[str] = None
    adults: int = 1
    children: int = 0
    infants: int = 0
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
