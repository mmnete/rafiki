import json
import logging
from typing import Dict, List, Optional
from pathlib import Path
import threading

class DataManager:
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls):
        """Ensure only one instance exists (thread-safe singleton)"""
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    cls._instance = super(DataManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, data_directory: str = "data"):
        """Initialize only once, even if __init__ is called multiple times"""
        # Skip initialization if already done
        if self._initialized:
            return
            
        with self._lock:
            if self._initialized:
                return
                
            module_dir = Path(__file__).parent
            self.data_dir = module_dir / data_directory
            self.airports = {}
            self.airline_policies = {}
            self.load_all_data()
            self._initialized = True
    
    
    def load_all_data(self):
        """Load all data files into memory for fast lookups"""
        try:
            self._load_airports()
            self._load_airline_policies()
            logging.info(f"Data loaded: {len(self.airports)} airports, {len(self.airline_policies)} airlines")
        except Exception as e:
            logging.error(f"Failed to load data: {e}")
            raise
    
    def _load_airports(self):
        """Load airports.json with nearby airports and hub information"""
        airports_file = self.data_dir / "airports.json"
        
        if not airports_file.exists():
            logging.warning(f"Airport data file not found: {airports_file}")
            self.airports = self._create_minimal_airports()
            return
        
        with open(airports_file, 'r', encoding='utf-8') as f:
            self.airports = json.load(f)
    
    def _load_airline_policies(self):
        """Load airline_policies.json with baggage, cancellation policies"""
        policies_file = self.data_dir / "airline_policies.json"
        
        if not policies_file.exists():
            logging.warning(f"Airline policies file not found: {policies_file}")
            self.airline_policies = self._create_minimal_policies()
            return
        
        with open(policies_file, 'r', encoding='utf-8') as f:
            self.airline_policies = json.load(f)
    
    def _create_minimal_airports(self) -> Dict:
        """Create minimal airport data for testing"""
        return {
            "SFO": {
                "name": "San Francisco International",
                "city": "San Francisco",
                "country": "US",
                "nearby_airports": [
                    {
                        "code": "OAK",
                        "distance_km": 20,
                        "transport_options": {
                            "uber": {"cost_usd": 45, "time_min": 35},
                            "bart": {"cost_usd": 8, "time_min": 45}
                        }
                    },
                    {
                        "code": "SJC",
                        "distance_km": 60,
                        "transport_options": {
                            "uber": {"cost_usd": 75, "time_min": 65}
                        }
                    }
                ],
                "reachable_hubs": [
                    {"code": "LAX", "flight_cost_typical": 150, "flight_time_min": 90},
                    {"code": "DEN", "flight_cost_typical": 180, "flight_time_min": 150},
                    {"code": "SEA", "flight_cost_typical": 200, "flight_time_min": 120}
                ]
            },
            "JFK": {
                "name": "John F. Kennedy International",
                "city": "New York",
                "country": "US",
                "nearby_airports": [
                    {
                        "code": "LGA",
                        "distance_km": 15,
                        "transport_options": {
                            "uber": {"cost_usd": 35, "time_min": 25}
                        }
                    },
                    {
                        "code": "EWR",
                        "distance_km": 30,
                        "transport_options": {
                            "uber": {"cost_usd": 55, "time_min": 45}
                        }
                    }
                ],
                "reachable_hubs": [
                    {"code": "BOS", "flight_cost_typical": 120, "flight_time_min": 75},
                    {"code": "DCA", "flight_cost_typical": 140, "flight_time_min": 85}
                ]
            }
        }
    
    def _create_minimal_policies(self) -> Dict:
        """Create minimal airline policies for testing"""
        return {
            "UA": {
                "name": "United Airlines",
                "baggage_policies": {
                    "economy": {"carry_on": "free", "checked_1": 35, "checked_2": 45},
                    "business": {"carry_on": "free", "checked_1": "free", "checked_2": "free"}
                },
                "cancellation_policies": {
                    "basic_economy": "no_changes",
                    "economy": "24h_free_cancel",
                    "business": "flexible_cancel"
                }
            },
            "DL": {
                "name": "Delta Air Lines",
                "baggage_policies": {
                    "economy": {"carry_on": "free", "checked_1": 30, "checked_2": 40},
                    "business": {"carry_on": "free", "checked_1": "free", "checked_2": "free"}
                },
                "cancellation_policies": {
                    "basic_economy": "no_changes",
                    "economy": "24h_free_cancel",
                    "business": "flexible_cancel"
                }
            }
        }
    
    def get_hub_destinations(self, hub_code: str) -> List[str]:
        """
        Get list of destination airport codes reachable from this hub.
        Currently returns destinations from reachable_hubs field.
        """
        hub_info = self.get_airport_info(hub_code)
        if not hub_info:
            return []
        
        # Extract destination codes from reachable_hubs
        reachable = hub_info.get('reachable_hubs', [])
        return [hub['code'] for hub in reachable]
    
    # Public API methods
    def get_airport_info(self, airport_code: str) -> Optional[Dict]:
        """Get full airport information"""
        return self.airports.get(airport_code.upper())
    
    def get_nearby_airports(self, airport_code: str) -> List[Dict]:
        """Get nearby airports for a given airport code"""
        airport_data = self.airports.get(airport_code.upper(), {})
        return airport_data.get('nearby_airports', [])
    
    def get_reachable_hubs(self, airport_code: str) -> List[Dict]:
        """Get reachable hub airports for a given airport code"""
        airport_data = self.airports.get(airport_code.upper(), {})
        return airport_data.get('reachable_hubs', [])
    
    def get_airline_policy(self, airline_code: str, policy_type: str) -> Dict:
        """Get specific airline policy (baggage_policies, cancellation_policies, etc.)"""
        airline_data = self.airline_policies.get(airline_code.upper(), {})
        return airline_data.get(policy_type, {})
    
    def get_all_airline_policies(self, airline_code: str) -> Dict:
        """Get all policies for a specific airline"""
        return self.airline_policies.get(airline_code.upper(), {})
    
    def airport_exists(self, airport_code: str) -> bool:
        """Check if airport code exists in our data"""
        return airport_code.upper() in self.airports
    
    def airline_exists(self, airline_code: str) -> bool:
        """Check if airline code exists in our data"""
        return airline_code.upper() in self.airline_policies
    
    def get_transport_cost(self, from_airport: str, to_airport: str, transport_type: str = "uber") -> Optional[float]:
        """Get transport cost between airports (if one is nearby the other)"""
        airport_data = self.airports.get(from_airport.upper(), {})
        
        for nearby in airport_data.get('nearby_airports', []):
            if nearby['code'] == to_airport.upper():
                transport_options = nearby.get('transport_options', {})
                if transport_type in transport_options:
                    return transport_options[transport_type].get('cost_usd', 0)
        
        return None
    
    def reload_data(self):
        """Reload all data from files (useful for development)"""
        logging.info("Reloading data from files...")
        self.load_all_data()
    
    def get_stats(self) -> Dict:
        """Get data statistics for debugging"""
        total_nearby = sum(len(airport.get('nearby_airports', [])) for airport in self.airports.values())
        total_hubs = sum(len(airport.get('reachable_hubs', [])) for airport in self.airports.values())
        
        return {
            'total_airports': len(self.airports),
            'total_airlines': len(self.airline_policies),
            'total_nearby_connections': total_nearby,
            'total_hub_connections': total_hubs,
            'airports_with_nearby': len([a for a in self.airports.values() if a.get('nearby_airports')]),
            'airports_with_hubs': len([a for a in self.airports.values() if a.get('reachable_hubs')])
        }

# Create global instance
data_manager = DataManager()
