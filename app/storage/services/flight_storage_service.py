# ==============================================================================
# app/storage/services/flight_storage_service.py
# ==============================================================================
from typing import Dict, Any, List, Optional, Tuple
import json
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from decimal import Decimal
from app.storage.db_service import StorageService

@dataclass
class FlightSearch:
    id: str
    user_id: int
    custom_search_id: str
    search_type: str
    search_params: Dict[str, Any]
    raw_results: List[Dict[str, Any]]
    processed_results: List[Dict[str, Any]]
    result_count: int
    apis_used: List[str]
    search_duration_ms: Optional[int]
    cache_hit: bool
    created_at: datetime
    expires_at: datetime
    accessed_at: datetime
    access_count: int

@dataclass
class FlightOffer:
    id: str
    search_id: str
    flight_offer_id: str
    amadeus_offer_id: Optional[str]
    base_price: Decimal
    taxes_and_fees: Decimal
    total_price: Decimal
    currency: str
    airline_codes: List[str]
    route_summary: Optional[str]
    total_duration_minutes: Optional[int]
    stops_count: int
    bookable_until: Optional[datetime]
    seats_available: Optional[int]
    fare_rules: Dict[str, Any]
    complete_offer_data: Dict[str, Any]
    created_at: datetime

@dataclass
class FlightStatusUpdate:
    id: int
    airline_code: str
    flight_number: str
    scheduled_departure_date: date
    current_status: str
    delay_minutes: int
    new_departure_time: Optional[datetime]
    new_arrival_time: Optional[datetime]
    gate: Optional[str]
    terminal: Optional[str]
    status_message: Optional[str]
    update_source: Optional[str]
    created_at: datetime

class FlightStorageService:
    """
    Service for managing flight searches, offers, and status updates
    
    Responsibilities:
    - Store and retrieve flight search results with caching
    - Manage flight offers with pricing and availability
    - Track flight status updates for real-time information
    - Handle search result expiration and cleanup
    - Optimize search performance through proper indexing
    """
    
    def __init__(self, storage: StorageService):
        self.storage = storage
    
    def create_flight_search(self, user_id: int, custom_search_id: str, 
                           search_type: str, search_params: Dict[str, Any],
                           **additional_data) -> Optional[str]:
        """Create a new flight search record"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                # Check if custom_search_id already exists
                existing_search = self.get_search_by_custom_id(custom_search_id)
                if existing_search:
                    # Update access time and return existing ID
                    self.update_search_access(existing_search.id)
                    return existing_search.id
                
                # Build insert data
                insert_data = {
                    'user_id': user_id,
                    'custom_search_id': custom_search_id,
                    'search_type': search_type,
                    'search_params': json.dumps(search_params)
                }
                
                # Add optional fields
                for key in ['raw_results', 'processed_results', 'result_count', 
                           'apis_used', 'search_duration_ms', 'cache_hit', 'expires_at']:
                    if key in additional_data:
                        if key in ['raw_results', 'processed_results', 'apis_used']:
                            insert_data[key] = json.dumps(additional_data[key])
                        else:
                            insert_data[key] = additional_data[key]
                
                # Build query
                fields = list(insert_data.keys())
                placeholders = ', '.join(['%s'] * len(fields))
                field_names = ', '.join(fields)
                
                cur.execute(f"""
                    INSERT INTO flight_searches ({field_names})
                    VALUES ({placeholders})
                    RETURNING id;
                """, list(insert_data.values()))

                result = cur.fetchone()
                if result:
                    return result[0]
                else:
                    print("Create flight search returned no result")
                    return None
                
        except Exception as e:
            print(f"Error creating flight search: {e}")
            return None
    
    def get_flight_search(self, search_id: str) -> Optional[FlightSearch]:
        """Get flight search by ID"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, user_id, custom_search_id, search_type, search_params,
                           raw_results, processed_results, result_count, apis_used,
                           search_duration_ms, cache_hit, created_at, expires_at,
                           accessed_at, access_count
                    FROM flight_searches WHERE id = %s;
                """, (search_id,))
                
                row = cur.fetchone()
                if row:
                    return FlightSearch(
                        id=row[0],
                        user_id=row[1],
                        custom_search_id=row[2],
                        search_type=row[3],
                        search_params=json.loads(row[4]) if row[4] else {},
                        raw_results=json.loads(row[5]) if row[5] else [],
                        processed_results=json.loads(row[6]) if row[6] else [],
                        result_count=row[7],
                        apis_used=json.loads(row[8]) if row[8] else [],
                        search_duration_ms=row[9],
                        cache_hit=row[10],
                        created_at=row[11],
                        expires_at=row[12],
                        accessed_at=row[13],
                        access_count=row[14]
                    )
                return None
                
        except Exception as e:
            print(f"Error getting flight search: {e}")
            return None
    
    def get_search_by_custom_id(self, custom_search_id: str) -> Optional[FlightSearch]:
        """Get flight search by custom search ID"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, user_id, custom_search_id, search_type, search_params,
                           raw_results, processed_results, result_count, apis_used,
                           search_duration_ms, cache_hit, created_at, expires_at,
                           accessed_at, access_count
                    FROM flight_searches 
                    WHERE custom_search_id = %s AND expires_at > CURRENT_TIMESTAMP;
                """, (custom_search_id,))
                
                row = cur.fetchone()
                if row:
                    return FlightSearch(
                        id=row[0], user_id=row[1], custom_search_id=row[2],
                        search_type=row[3], search_params=json.loads(row[4]) if row[4] else {},
                        raw_results=json.loads(row[5]) if row[5] else [],
                        processed_results=json.loads(row[6]) if row[6] else [],
                        result_count=row[7], apis_used=json.loads(row[8]) if row[8] else [],
                        search_duration_ms=row[9], cache_hit=row[10], created_at=row[11],
                        expires_at=row[12], accessed_at=row[13], access_count=row[14]
                    )
                return None
                
        except Exception as e:
            print(f"Error getting search by custom ID: {e}")
            return None
    
    def update_search_access(self, search_id: str) -> bool:
        """Update search access time and count"""
        if not self.storage.conn:
            return False
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    UPDATE flight_searches 
                    SET accessed_at = CURRENT_TIMESTAMP, 
                        access_count = access_count + 1
                    WHERE id = %s;
                """, (search_id,))
                
                return cur.rowcount > 0
                
        except Exception as e:
            print(f"Error updating search access: {e}")
            return False
    
    def get_user_searches(self, user_id: int, limit: int = 20) -> List[FlightSearch]:
        """Get recent searches for a user"""
        if not self.storage.conn:
            return []
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, user_id, custom_search_id, search_type, search_params,
                           raw_results, processed_results, result_count, apis_used,
                           search_duration_ms, cache_hit, created_at, expires_at,
                           accessed_at, access_count
                    FROM flight_searches 
                    WHERE user_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s;
                """, (user_id, limit))
                
                return [
                    FlightSearch(
                        id=row[0], user_id=row[1], custom_search_id=row[2],
                        search_type=row[3], search_params=json.loads(row[4]) if row[4] else {},
                        raw_results=json.loads(row[5]) if row[5] else [],
                        processed_results=json.loads(row[6]) if row[6] else [],
                        result_count=row[7], apis_used=json.loads(row[8]) if row[8] else [],
                        search_duration_ms=row[9], cache_hit=row[10], created_at=row[11],
                        expires_at=row[12], accessed_at=row[13], access_count=row[14]
                    )
                    for row in cur.fetchall()
                ]
                
        except Exception as e:
            print(f"Error getting user searches: {e}")
            return []
    
    def add_flight_offer(self, search_id: str, flight_offer_id: str,
                        base_price: Decimal, total_price: Decimal,
                        **offer_data) -> Optional[str]:
        """Add a flight offer to a search"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                # Build insert data
                insert_data = {
                    'search_id': search_id,
                    'flight_offer_id': flight_offer_id,
                    'base_price': base_price,
                    'total_price': total_price
                }
                
                # Add optional fields with defaults
                insert_data.update({
                    'taxes_and_fees': offer_data.get('taxes_and_fees', Decimal('0.00')),
                    'currency': offer_data.get('currency', 'USD'),
                    'airline_codes': json.dumps(offer_data.get('airline_codes', [])),
                    'route_summary': offer_data.get('route_summary'),
                    'total_duration_minutes': offer_data.get('total_duration_minutes'),
                    'stops_count': offer_data.get('stops_count', 0),
                    'bookable_until': offer_data.get('bookable_until'),
                    'seats_available': offer_data.get('seats_available'),
                    'fare_rules': json.dumps(offer_data.get('fare_rules', {})),
                    'complete_offer_data': json.dumps(offer_data.get('complete_offer_data', {})),
                    'amadeus_offer_id': offer_data.get('amadeus_offer_id')
                })
                
                # Build query
                fields = list(insert_data.keys())
                placeholders = ', '.join(['%s'] * len(fields))
                field_names = ', '.join(fields)
                
                cur.execute(f"""
                    INSERT INTO flight_offers ({field_names})
                    VALUES ({placeholders})
                    RETURNING id;
                """, list(insert_data.values()))
                
                result = cur.fetchone()
                if result:
                    return result[0]
                else:
                    print("Add flight offer returned no result")
                    return None
                
        except Exception as e:
            print(f"Error adding flight offer: {e}")
            return None
    
    def get_search_offers(self, search_id: str, sort_by: str = 'price') -> List[FlightOffer]:
        """Get flight offers for a search"""
        if not self.storage.conn:
            return []
        
        try:
            # Determine sort order
            order_clause = {
                'price': 'total_price ASC',
                'duration': 'total_duration_minutes ASC',
                'stops': 'stops_count ASC, total_price ASC',
                'departure': 'created_at DESC'
            }.get(sort_by, 'total_price ASC')
            
            with self.storage.conn.cursor() as cur:
                cur.execute(f"""
                    SELECT id, search_id, flight_offer_id, amadeus_offer_id,
                           base_price, taxes_and_fees, total_price, currency,
                           airline_codes, route_summary, total_duration_minutes,
                           stops_count, bookable_until, seats_available,
                           fare_rules, complete_offer_data, created_at
                    FROM flight_offers 
                    WHERE search_id = %s 
                    ORDER BY {order_clause};
                """, (search_id,))
                
                return [
                    FlightOffer(
                        id=row[0], search_id=row[1], flight_offer_id=row[2],
                        amadeus_offer_id=row[3], base_price=row[4], taxes_and_fees=row[5],
                        total_price=row[6], currency=row[7],
                        airline_codes=json.loads(row[8]) if row[8] else [],
                        route_summary=row[9], total_duration_minutes=row[10],
                        stops_count=row[11], bookable_until=row[12],
                        seats_available=row[13],
                        fare_rules=json.loads(row[14]) if row[14] else {},
                        complete_offer_data=json.loads(row[15]) if row[15] else {},
                        created_at=row[16]
                    )
                    for row in cur.fetchall()
                ]
                
        except Exception as e:
            print(f"Error getting search offers: {e}")
            return []
    
    def get_flight_offer(self, offer_id: str) -> Optional[FlightOffer]:
        """Get specific flight offer by ID"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, search_id, flight_offer_id, amadeus_offer_id,
                           base_price, taxes_and_fees, total_price, currency,
                           airline_codes, route_summary, total_duration_minutes,
                           stops_count, bookable_until, seats_available,
                           fare_rules, complete_offer_data, created_at
                    FROM flight_offers WHERE id = %s;
                """, (offer_id,))
                
                row = cur.fetchone()
                if row:
                    return FlightOffer(
                        id=row[0], search_id=row[1], flight_offer_id=row[2],
                        amadeus_offer_id=row[3], base_price=row[4], taxes_and_fees=row[5],
                        total_price=row[6], currency=row[7],
                        airline_codes=json.loads(row[8]) if row[8] else [],
                        route_summary=row[9], total_duration_minutes=row[10],
                        stops_count=row[11], bookable_until=row[12],
                        seats_available=row[13],
                        fare_rules=json.loads(row[14]) if row[14] else {},
                        complete_offer_data=json.loads(row[15]) if row[15] else {},
                        created_at=row[16]
                    )
                return None
                
        except Exception as e:
            print(f"Error getting flight offer: {e}")
            return None
    
    def add_flight_status_update(self, airline_code: str, flight_number: str,
                               scheduled_departure_date: date, current_status: str,
                               **status_data) -> Optional[int]:
        """Add flight status update"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                insert_data = {
                    'airline_code': airline_code,
                    'flight_number': flight_number,
                    'scheduled_departure_date': scheduled_departure_date,
                    'current_status': current_status,
                    'delay_minutes': status_data.get('delay_minutes', 0),
                    'new_departure_time': status_data.get('new_departure_time'),
                    'new_arrival_time': status_data.get('new_arrival_time'),
                    'gate': status_data.get('gate'),
                    'terminal': status_data.get('terminal'),
                    'status_message': status_data.get('status_message'),
                    'update_source': status_data.get('update_source')
                }
                
                fields = list(insert_data.keys())
                placeholders = ', '.join(['%s'] * len(fields))
                field_names = ', '.join(fields)
                
                cur.execute(f"""
                    INSERT INTO flight_status_updates ({field_names})
                    VALUES ({placeholders})
                    RETURNING id;
                """, list(insert_data.values()))
                
                result = cur.fetchone()
                if result:
                    return result[0]
                else:
                    print("Add flight status returned no result")
                    return None
                
        except Exception as e:
            print(f"Error adding flight status update: {e}")
            return None
    
    def get_flight_status(self, airline_code: str, flight_number: str,
                         departure_date: date) -> Optional[FlightStatusUpdate]:
        """Get latest flight status"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, airline_code, flight_number, scheduled_departure_date,
                           current_status, delay_minutes, new_departure_time,
                           new_arrival_time, gate, terminal, status_message,
                           update_source, created_at
                    FROM flight_status_updates 
                    WHERE airline_code = %s AND flight_number = %s 
                      AND scheduled_departure_date = %s
                    ORDER BY created_at DESC 
                    LIMIT 1;
                """, (airline_code, flight_number, departure_date))
                
                row = cur.fetchone()
                if row:
                    return FlightStatusUpdate(
                        id=row[0], airline_code=row[1], flight_number=row[2],
                        scheduled_departure_date=row[3], current_status=row[4],
                        delay_minutes=row[5], new_departure_time=row[6],
                        new_arrival_time=row[7], gate=row[8], terminal=row[9],
                        status_message=row[10], update_source=row[11], created_at=row[12]
                    )
                return None
                
        except Exception as e:
            print(f"Error getting flight status: {e}")
            return None
    
    def cleanup_expired_searches(self, days_old: int = 7) -> int:
        """Clean up expired search records"""
        if not self.storage.conn:
            return 0
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM flight_searches 
                    WHERE expires_at < %s OR created_at < %s;
                """, (datetime.now(), cutoff_date))
                
                return cur.rowcount
                
        except Exception as e:
            print(f"Error cleaning up expired searches: {e}")
            return 0
    
    def get_search_statistics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get search statistics"""
        if not self.storage.conn:
            return {}
        
        try:
            with self.storage.conn.cursor() as cur:
                base_query = """
                    SELECT 
                        COUNT(*) as total_searches,
                        COUNT(CASE WHEN cache_hit THEN 1 END) as cache_hits,
                        AVG(search_duration_ms) as avg_duration_ms,
                        AVG(result_count) as avg_results,
                        COUNT(CASE WHEN search_type = 'one_way' THEN 1 END) as one_way_searches,
                        COUNT(CASE WHEN search_type = 'round_trip' THEN 1 END) as round_trip_searches
                    FROM flight_searches
                """
                
                if user_id:
                    cur.execute(base_query + " WHERE user_id = %s;", (user_id,))
                else:
                    cur.execute(base_query + ";")
                
                row = cur.fetchone()
                if row:
                    return {
                        'total_searches': row[0],
                        'cache_hits': row[1],
                        'cache_hit_rate': (row[1] / row[0] * 100) if row[0] > 0 else 0,
                        'avg_duration_ms': float(row[2]) if row[2] else 0,
                        'avg_results': float(row[3]) if row[3] else 0,
                        'one_way_searches': row[4],
                        'round_trip_searches': row[5]
                    }
                return {}
                
        except Exception as e:
            print(f"Error getting search statistics: {e}")
            return {}