# ==============================================================================
# app/services/personalization_service.py
# ==============================================================================
from typing import Dict, Any, List, Optional
import json
import hashlib
from dataclasses import dataclass
from app.storage.db_service import StorageService

@dataclass
class UserPreferences:
    user_id: int
    preferred_airlines: List[str]
    preferred_departure_times: Dict[str, Any]
    preferred_seat_type: Optional[str]
    budget_range: Dict[str, Any]
    typical_advance_booking_days: Optional[int]
    prefers_direct_flights: Optional[bool]
    price_sensitivity: str
    frequently_searched_routes: List[Dict[str, Any]]
    booking_patterns: Dict[str, Any]
    updated_at: Optional[Any]
    created_at: Optional[Any]

@dataclass
class PassengerRecognition:
    id: str
    passenger_profile_id: str
    name_hash: str
    dob_hash: str
    phone_hash: Optional[str]
    first_seen_with_user_id: Optional[int]
    total_bookings_count: int
    last_booking_date: Optional[Any]
    auto_suggest_enabled: bool
    created_at: Optional[Any]
    updated_at: Optional[Any]

class PersonalizationStorageService:
    """
    Service for managing user personalization and passenger recognition
    
    Responsibilities:
    - Manage user travel preferences and patterns
    - Handle passenger recognition for cross-booking suggestions
    - Track user behavior for AI personalization
    - Maintain privacy through hashing of sensitive data
    """
    
    def __init__(self, storage: StorageService):
        self.storage = storage
    
    def get_user_preferences(self, user_id: int) -> Optional[UserPreferences]:
        """Get user travel preferences"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT user_id, preferred_airlines, preferred_departure_times, 
                           preferred_seat_type, budget_range, typical_advance_booking_days,
                           prefers_direct_flights, price_sensitivity, frequently_searched_routes, 
                           booking_patterns, updated_at, created_at
                    FROM user_preferences WHERE user_id = %s;
                """, (user_id,))
                
                row = cur.fetchone()
                if row:
                    return UserPreferences(
                        user_id=row[0],
                        preferred_airlines=json.loads(row[1]) if row[1] else [],
                        preferred_departure_times=json.loads(row[2]) if row[2] else {},
                        preferred_seat_type=row[3],
                        budget_range=json.loads(row[4]) if row[4] else {},
                        typical_advance_booking_days=row[5],
                        prefers_direct_flights=row[6],
                        price_sensitivity=row[7] or 'medium',
                        frequently_searched_routes=json.loads(row[8]) if row[8] else [],
                        booking_patterns=json.loads(row[9]) if row[9] else {},
                        updated_at=row[10],
                        created_at=row[11]
                    )
                return None
                
        except Exception as e:
            print(f"Error getting user preferences: {e}")
            return None
    
    def update_user_preferences(self, user_id: int, **preferences) -> bool:
        """Update user travel preferences"""
        if not self.storage.conn:
            return False
        
        try:
            # Build update fields dynamically
            update_fields = []
            update_values = []
            
            valid_fields = {
                'preferred_airlines', 'preferred_departure_times', 'preferred_seat_type',
                'budget_range', 'typical_advance_booking_days', 'prefers_direct_flights',
                'price_sensitivity', 'frequently_searched_routes', 'booking_patterns'
            }
            
            json_fields = {
                'preferred_airlines', 'preferred_departure_times', 'budget_range',
                'frequently_searched_routes', 'booking_patterns'
            }
            
            for key, value in preferences.items():
                if key in valid_fields:
                    if key in json_fields:
                        update_fields.append(f"{key} = %s")
                        update_values.append(json.dumps(value))
                    else:
                        update_fields.append(f"{key} = %s")
                        update_values.append(value)
            
            if not update_fields:
                return True  # Nothing to update
            
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            
            with self.storage.conn.cursor() as cur:
                # Try to update existing record
                update_query = f"""
                    UPDATE user_preferences 
                    SET {', '.join(update_fields)}
                    WHERE user_id = %s;
                """
                cur.execute(update_query, update_values + [user_id])
                
                if cur.rowcount == 0:
                    # Insert new record if user doesn't exist
                    cur.execute("""
                        INSERT INTO user_preferences (user_id) VALUES (%s);
                    """, (user_id,))
                    
                    # Now update with the preferences
                    cur.execute(update_query, update_values + [user_id])
                
                return True
                
        except Exception as e:
            print(f"Error updating user preferences: {e}")
            return False
    
    def find_similar_passengers(self, first_name: str, last_name: str, 
                              date_of_birth: str, phone_number: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find passengers with similar details for recognition"""
        if not self.storage.conn:
            return []
        
        try:
            # Create hashes for matching
            name_hash = self._hash_name(first_name, last_name)
            dob_hash = self._hash_dob(date_of_birth)
            phone_hash = self._hash_phone(phone_number) if phone_number else None
            
            with self.storage.conn.cursor() as cur:
                # Build query based on available data
                if phone_hash:
                    cur.execute("""
                        SELECT prd.passenger_profile_id, prd.first_seen_with_user_id,
                               prd.total_bookings_count, pp.first_name, pp.last_name,
                               pp.date_of_birth
                        FROM passenger_recognition_data prd
                        JOIN passenger_profiles pp ON prd.passenger_profile_id = pp.id
                        WHERE (prd.name_hash = %s AND prd.dob_hash = %s) 
                           OR prd.phone_hash = %s;
                    """, (name_hash, dob_hash, phone_hash))
                else:
                    cur.execute("""
                        SELECT prd.passenger_profile_id, prd.first_seen_with_user_id,
                               prd.total_bookings_count, pp.first_name, pp.last_name,
                               pp.date_of_birth
                        FROM passenger_recognition_data prd
                        JOIN passenger_profiles pp ON prd.passenger_profile_id = pp.id
                        WHERE prd.name_hash = %s AND prd.dob_hash = %s;
                    """, (name_hash, dob_hash))
                
                return [
                    {
                        "passenger_id": row[0],
                        "first_seen_with_user": row[1],
                        "booking_count": row[2],
                        "first_name": row[3],
                        "last_name": row[4],
                        "date_of_birth": row[5]
                    }
                    for row in cur.fetchall()
                ]
                
        except Exception as e:
            print(f"Error finding similar passengers: {e}")
            return []
    
    def record_passenger_recognition(self, passenger_id: str, first_seen_user_id: int,
                                   first_name: str, last_name: str, date_of_birth: str,
                                   phone_number: Optional[str] = None) -> bool:
        """Record passenger for future recognition"""
        if not self.storage.conn:
            return False
        
        try:
            name_hash = self._hash_name(first_name, last_name)
            dob_hash = self._hash_dob(date_of_birth)
            phone_hash = self._hash_phone(phone_number) if phone_number else None
            
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO passenger_recognition_data (
                        passenger_profile_id, name_hash, dob_hash, phone_hash, first_seen_with_user_id
                    ) VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (passenger_profile_id) DO UPDATE SET
                        total_bookings_count = passenger_recognition_data.total_bookings_count + 1,
                        last_booking_date = CURRENT_DATE,
                        updated_at = CURRENT_TIMESTAMP;
                """, (passenger_id, name_hash, dob_hash, phone_hash, first_seen_user_id))
                
                return True
                
        except Exception as e:
            print(f"Error recording passenger recognition: {e}")
            return False
    
    def suggest_passengers_for_user(self, user_id: int, search_query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get passenger suggestions for a user based on their history"""
        if not self.storage.conn:
            return []
        
        try:
            with self.storage.conn.cursor() as cur:
                if search_query:
                    # Simple name-based search
                    search_pattern = f"%{search_query.lower()}%"
                    cur.execute("""
                        SELECT pp.id, pp.first_name, pp.last_name, pp.date_of_birth,
                               prd.total_bookings_count, prd.last_booking_date
                        FROM passenger_profiles pp
                        JOIN passenger_recognition_data prd ON pp.id = prd.passenger_profile_id
                        WHERE prd.first_seen_with_user_id = %s 
                          AND prd.auto_suggest_enabled = true
                          AND (LOWER(pp.first_name) LIKE %s OR LOWER(pp.last_name) LIKE %s)
                        ORDER BY prd.total_bookings_count DESC, prd.last_booking_date DESC;
                    """, (user_id, search_pattern, search_pattern))
                else:
                    # Get frequently used passengers
                    cur.execute("""
                        SELECT pp.id, pp.first_name, pp.last_name, pp.date_of_birth,
                               prd.total_bookings_count, prd.last_booking_date
                        FROM passenger_profiles pp
                        JOIN passenger_recognition_data prd ON pp.id = prd.passenger_profile_id
                        WHERE prd.first_seen_with_user_id = %s 
                          AND prd.auto_suggest_enabled = true
                        ORDER BY prd.total_bookings_count DESC, prd.last_booking_date DESC
                        LIMIT 10;
                    """, (user_id,))
                
                return [
                    {
                        "passenger_id": row[0],
                        "first_name": row[1],
                        "last_name": row[2],
                        "date_of_birth": row[3],
                        "booking_count": row[4],
                        "last_booking_date": row[5]
                    }
                    for row in cur.fetchall()
                ]
                
        except Exception as e:
            print(f"Error getting passenger suggestions: {e}")
            return []
    
    def update_search_patterns(self, user_id: int, origin: str, destination: str, 
                              departure_date: str, search_count: int = 1) -> bool:
        """Update user's frequently searched routes"""
        preferences = self.get_user_preferences(user_id)
        
        if not preferences:
            # Create new preferences
            frequently_searched = [{"origin": origin, "destination": destination, "count": search_count}]
        else:
            frequently_searched = preferences.frequently_searched_routes.copy()
            
            # Update existing route or add new one
            route_found = False
            for route in frequently_searched:
                if route.get("origin") == origin and route.get("destination") == destination:
                    route["count"] = route.get("count", 0) + search_count
                    route_found = True
                    break
            
            if not route_found:
                frequently_searched.append({
                    "origin": origin, 
                    "destination": destination, 
                    "count": search_count
                })
            
            # Keep only top 20 routes
            frequently_searched.sort(key=lambda x: x.get("count", 0), reverse=True)
            frequently_searched = frequently_searched[:20]
        
        return self.update_user_preferences(
            user_id=user_id,
            frequently_searched_routes=frequently_searched
        )
    
    def _hash_name(self, first_name: str, last_name: str) -> str:
        """Create hash for name matching"""
        combined_name = f"{first_name.lower().strip()}_{last_name.lower().strip()}"
        return hashlib.sha256(combined_name.encode()).hexdigest()
    
    def _hash_dob(self, date_of_birth: str) -> str:
        """Create hash for date of birth"""
        return hashlib.sha256(date_of_birth.encode()).hexdigest()
    
    def _hash_phone(self, phone_number: str) -> str:
        """Create hash for phone number"""
        # Clean phone number (remove spaces, dashes, etc.)
        cleaned_phone = ''.join(filter(str.isdigit, phone_number))
        return hashlib.sha256(cleaned_phone.encode()).hexdigest()