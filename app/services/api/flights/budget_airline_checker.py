# budget_airline_checker.py
import asyncio
import aiohttp
import logging
from typing import List, Dict, Optional, Union, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class BudgetAirlineChecker:
    """Check budget airline availability across regions"""
    
    # Major budget airlines by region with their route networks
    BUDGET_AIRLINES = {
        'ryanair': {
            'name': 'Ryanair',
            'code': 'FR',
            'regions': ['europe'],
            'base_url': 'https://www.ryanair.com',
            'api_available': True
        },
        'wizz': {
            'name': 'Wizz Air',
            'code': 'W6',
            'regions': ['europe'],
            'base_url': 'https://wizzair.com',
            'api_available': False
        },
        'easyjet': {
            'name': 'easyJet',
            'code': 'U2',
            'regions': ['europe'],
            'base_url': 'https://www.easyjet.com',
            'api_available': False
        },
        'spirit': {
            'name': 'Spirit Airlines',
            'code': 'NK',
            'regions': ['us', 'caribbean'],
            'base_url': 'https://www.spirit.com',
            'api_available': False
        },
        'frontier': {
            'name': 'Frontier Airlines',
            'code': 'F9',
            'regions': ['us'],
            'base_url': 'https://www.flyfrontier.com',
            'api_available': False
        },
        'allegiant': {
            'name': 'Allegiant Air',
            'code': 'G4',
            'regions': ['us'],
            'base_url': 'https://www.allegiantair.com',
            'api_available': False
        },
        'airasia': {
            'name': 'AirAsia',
            'code': 'AK',
            'regions': ['asia'],
            'base_url': 'https://www.airasia.com',
            'api_available': False
        },
        'scoot': {
            'name': 'Scoot',
            'code': 'TR',
            'regions': ['asia'],
            'base_url': 'https://www.flyscoot.com',
            'api_available': False
        },
        'vietjet': {
            'name': 'VietJet Air',
            'code': 'VJ',
            'regions': ['asia'],
            'base_url': 'https://www.vietjetair.com',
            'api_available': False
        },
        'indigo': {
            'name': 'IndiGo',
            'code': '6E',
            'regions': ['asia'],
            'base_url': 'https://www.goindigo.in',
            'api_available': False
        },
        'fastjet': {
            'name': 'Fastjet',
            'code': 'FN',
            'regions': ['africa'],
            'base_url': 'https://www.fastjet.com',
            'api_available': False
        },
        'flysafair': {
            'name': 'FlySafair',
            'code': 'FA',
            'regions': ['africa'],
            'base_url': 'https://www.flysafair.co.za',
            'api_available': False
        }
    }
    
    # Cache for route availability (to avoid repeated checks)
    _route_cache = {}
    _cache_ttl = 86400  # 24 hours
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    async def check_budget_airlines_async(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:  # More specific type hint
        """
        Check budget airlines asynchronously (non-blocking).
        Returns list of budget airline options with check URLs.
        """
        try:
            tasks = []
            
            # Check Ryanair (has public API)
            tasks.append(self._check_ryanair(origin, destination, departure_date, return_date))
            
            # Check other airlines based on route geography
            region = self._detect_region(origin, destination)
            
            for airline_key, airline_info in self.BUDGET_AIRLINES.items():
                if airline_key == 'ryanair':
                    continue  # Already handled
                    
                if region in airline_info['regions']:
                    tasks.append(
                        self._check_airline_generic(
                            airline_info,
                            origin,
                            destination,
                            departure_date,
                            return_date
                        )
                    )
            
            # Run all checks concurrently with timeout
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=3.0  # 3 second timeout for all checks
            )
            
            # Filter out None and exceptions with explicit type checking
            valid_results: List[Dict[str, Any]] = []
            for r in results:
                if r is not None and not isinstance(r, Exception) and isinstance(r, dict):
                    valid_results.append(r)
            
            return valid_results
            
        except asyncio.TimeoutError:
            logger.warning("Budget airline checks timed out")
            return []
        except Exception as e:
            logger.error(f"Budget airline check error: {e}")
            return []
    
    def check_budget_airlines_sync(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None
    ) -> List[Dict]:
        """Synchronous wrapper for async check"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(
                self.check_budget_airlines_async(origin, destination, departure_date, return_date)
            )
        finally:
            loop.close()
    
    async def _check_ryanair(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None
    ) -> Optional[Dict]:
        """Check Ryanair using their public routes API"""
        try:
            cache_key = f"ryanair_{origin}_{destination}"
            
            # Check cache first
            if cache_key in self._route_cache:
                cached = self._route_cache[cache_key]
                if (datetime.now().timestamp() - cached['timestamp']) < self._cache_ttl:
                    if not cached['available']:
                        return None
            
            async with aiohttp.ClientSession() as session:
                # Check if route exists
                async with session.get(
                    "https://www.ryanair.com/api/locate/v1/routes",
                    timeout=aiohttp.ClientTimeout(total=2)
                ) as response:
                    if response.status == 200:
                        routes = await response.json()
                        
                        # Check if route exists
                        route_exists = any(
                            r.get('departureAirportIataCode') == origin and 
                            r.get('arrivalAirportIataCode') == destination
                            for r in routes
                        )
                        
                        # Cache result
                        self._route_cache[cache_key] = {
                            'available': route_exists,
                            'timestamp': datetime.now().timestamp()
                        }
                        
                        if route_exists:
                            # Format date for Ryanair (YYYY-MM-DD)
                            booking_url = self._build_ryanair_url(
                                origin, destination, departure_date, return_date
                            )
                            
                            return {
                                'airline': 'Ryanair',
                                'airline_code': 'FR',
                                'check_url': booking_url,
                                'note': 'Often 30-50% cheaper than aggregators',
                                'regions': ['europe'],
                                'confidence': 'high'
                            }
            
            return None
            
        except Exception as e:
            logger.debug(f"Ryanair check failed: {e}")
            return None
    
    async def _check_airline_generic(
        self,
        airline_info: Dict,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None
    ) -> Optional[Dict]:
        """Generic check for airlines without public APIs"""
        try:
            # Build search URL
            booking_url = self._build_generic_url(
                airline_info,
                origin,
                destination,
                departure_date,
                return_date
            )
            
            return {
                'airline': airline_info['name'],
                'airline_code': airline_info['code'],
                'check_url': booking_url,
                'note': f"Check {airline_info['name']} for potential savings",
                'regions': airline_info['regions'],
                'confidence': 'medium'
            }
            
        except Exception as e:
            logger.debug(f"{airline_info['name']} check failed: {e}")
            return None
    
    def _detect_region(self, origin: str, destination: str) -> str:
        """Detect geographic region based on airport codes"""
        # European airports
        european_airports = [
            'LHR', 'LGW', 'STN', 'LTN', 'CDG', 'ORY', 'FRA', 'MUC', 'BCN', 'MAD',
            'FCO', 'MXP', 'AMS', 'BRU', 'VIE', 'ZRH', 'CPH', 'ARN', 'OSL', 'DUB',
            'CRL', 'EIN', 'ANR', 'LGG', 'ATH', 'LIS', 'OPO', 'PRG', 'WAW', 'BUD'
        ]
        
        # US airports
        us_airports = [
            'JFK', 'LAX', 'ORD', 'DFW', 'ATL', 'DEN', 'SFO', 'SEA', 'LAS', 'MCO',
            'MIA', 'BOS', 'IAH', 'EWR', 'CLT', 'PHX', 'IAD', 'MSP', 'DTW', 'PHL'
        ]
        
        # Asian airports
        asian_airports = [
            'BKK', 'SIN', 'HKG', 'NRT', 'ICN', 'PVG', 'DEL', 'BOM', 'KUL', 'CGK',
            'MNL', 'HAN', 'SGN', 'BLR', 'DPS', 'DMK'
        ]
        
        # African airports
        african_airports = [
            'JNB', 'CPT', 'NBO', 'CAI', 'ADD', 'LOS', 'DAR', 'ACC', 'CMN', 'TUN'
        ]
        
        if origin in european_airports or destination in european_airports:
            return 'europe'
        elif origin in us_airports or destination in us_airports:
            return 'us'
        elif origin in asian_airports or destination in asian_airports:
            return 'asia'
        elif origin in african_airports or destination in african_airports:
            return 'africa'
        
        return 'unknown'
    
    def _build_ryanair_url(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None
    ) -> str:
        """Build Ryanair booking URL"""
        base = "https://www.ryanair.com/gb/en/booking/home"
        
        if return_date:
            return f"{base}/{origin}/{destination}/{departure_date}/{return_date}/1/0/0"
        else:
            return f"{base}/{origin}/{destination}/{departure_date}//1/0/0"
    
    def _build_generic_url(
        self,
        airline_info: Dict,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None
    ) -> str:
        """Build generic booking URL for airlines"""
        # Most airlines have similar URL structures
        base = airline_info['base_url']
        
        # Format varies by airline, but most accept these params
        if airline_info['code'] == 'W6':  # Wizz Air
            return f"{base}/en-gb/flights/{origin}/{destination}"
        elif airline_info['code'] == 'U2':  # easyJet
            return f"{base}/en/cheap-flights/{origin}-to-{destination}"
        elif airline_info['code'] == 'NK':  # Spirit
            return f"{base}/book/flights"
        elif airline_info['code'] == 'F9':  # Frontier
            return f"{base}/flights-from-{origin}-to-{destination}"
        elif airline_info['code'] == 'AK':  # AirAsia
            return f"{base}/flights/from-{origin}-to-{destination}"
        else:
            return base