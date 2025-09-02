# ==============================================================================
# app/storage/services/passenger_storage_service.py
# ==============================================================================
from typing import Dict, Any, List, Optional, Tuple
import json
from dataclasses import dataclass
from datetime import datetime, date
from app.storage.db_service import StorageService

@dataclass
class PassengerProfile:
    id: str
    first_name: str
    middle_name: Optional[str]
    last_name: str
    date_of_birth: date
    gender: Optional[str]
    title: Optional[str]
    email: Optional[str]
    phone_number: Optional[str]
    primary_document_type: Optional[str]
    primary_document_number: Optional[str]
    primary_document_expiry: Optional[date]
    primary_document_country: Optional[str]
    nationality: Optional[str]
    seat_preference: str
    meal_preference: Optional[str]
    special_assistance: Optional[str]
    medical_conditions: Optional[str]
    dietary_restrictions: Optional[str]
    airline_loyalties: Dict[str, Any]
    tsa_precheck_number: Optional[str]
    global_entry_number: Optional[str]
    created_by_user_id: Optional[int]
    is_verified: bool
    verification_method: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_traveled_at: Optional[datetime]

@dataclass
class PassengerDocument:
    id: str
    passenger_id: str
    document_type: str
    document_number: str
    document_expiry: Optional[date]
    issuing_country: str
    document_image_ids: List[str]
    is_primary: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

@dataclass
class UserPassengerConnection:
    id: int
    user_id: int
    passenger_id: str
    relationship: Optional[str]
    connection_type: str
    trust_level: str
    connected_via_booking_id: Optional[str]
    connection_date: datetime
    verified_at: Optional[datetime]
    verified_by_user: bool
    can_book_for_passenger: bool
    can_modify_passenger_details: bool
    can_view_passenger_history: bool
    created_at: datetime
    updated_at: datetime

class PassengerStorageService:
    """
    Service for managing passenger profiles and user connections
    
    Responsibilities:
    - Create and manage passenger profiles with travel preferences
    - Handle passenger travel documents and verification
    - Manage user-passenger connections and permissions
    - Enable passenger recognition across bookings
    - Support family/group travel scenarios
    """
    
    def __init__(self, storage: StorageService):
        self.storage = storage
    
    def create_passenger(self, first_name: str, last_name: str, 
                        date_of_birth: date, **passenger_data) -> Optional[str]:
        """Create a new passenger profile"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                # Build insert data
                insert_data = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'date_of_birth': date_of_birth,
                    'seat_preference': passenger_data.get('seat_preference', 'any'),
                    'is_verified': passenger_data.get('is_verified', False)
                }
                
                # Add optional fields
                optional_fields = [
                    'middle_name', 'gender', 'title', 'email', 'phone_number',
                    'primary_document_type', 'primary_document_number', 
                    'primary_document_expiry', 'primary_document_country', 'nationality',
                    'meal_preference', 'special_assistance', 'medical_conditions',
                    'dietary_restrictions', 'tsa_precheck_number', 'global_entry_number',
                    'created_by_user_id', 'verification_method', 'last_traveled_at'
                ]
                
                for field in optional_fields:
                    if field in passenger_data:
                        insert_data[field] = passenger_data[field]
                
                # Handle JSON fields
                if 'airline_loyalties' in passenger_data:
                    insert_data['airline_loyalties'] = json.dumps(passenger_data['airline_loyalties'])
                
                # Build query
                fields = list(insert_data.keys())
                placeholders = ', '.join(['%s'] * len(fields))
                field_names = ', '.join(fields)
                
                cur.execute(f"""
                    INSERT INTO passenger_profiles ({field_names})
                    VALUES ({placeholders})
                    RETURNING id;
                """, list(insert_data.values()))
                
                result = cur.fetchone()
                if result:
                    return result[0]
                else:
                    print("Create passenger returned no result")
                    return None
                
        except Exception as e:
            print(f"Error creating passenger: {e}")
            return None
    
    def get_passenger(self, passenger_id: str) -> Optional[PassengerProfile]:
        """Get passenger profile by ID"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, first_name, middle_name, last_name, date_of_birth,
                           gender, title, email, phone_number, primary_document_type,
                           primary_document_number, primary_document_expiry, 
                           primary_document_country, nationality, seat_preference,
                           meal_preference, special_assistance, medical_conditions,
                           dietary_restrictions, airline_loyalties, tsa_precheck_number,
                           global_entry_number, created_by_user_id, is_verified,
                           verification_method, created_at, updated_at, last_traveled_at
                    FROM passenger_profiles WHERE id = %s;
                """, (passenger_id,))
                
                row = cur.fetchone()
                if row:
                    return PassengerProfile(
                        id=row[0], first_name=row[1], middle_name=row[2],
                        last_name=row[3], date_of_birth=row[4], gender=row[5],
                        title=row[6], email=row[7], phone_number=row[8],
                        primary_document_type=row[9], primary_document_number=row[10],
                        primary_document_expiry=row[11], primary_document_country=row[12],
                        nationality=row[13], seat_preference=row[14], meal_preference=row[15],
                        special_assistance=row[16], medical_conditions=row[17],
                        dietary_restrictions=row[18],
                        airline_loyalties=json.loads(row[19]) if row[19] else {},
                        tsa_precheck_number=row[20], global_entry_number=row[21],
                        created_by_user_id=row[22], is_verified=row[23],
                        verification_method=row[24], created_at=row[25],
                        updated_at=row[26], last_traveled_at=row[27]
                    )
                return None
                
        except Exception as e:
            print(f"Error getting passenger: {e}")
            return None
    
    def update_passenger(self, passenger_id: str, **update_data) -> bool:
        """Update passenger profile information"""
        if not self.storage.conn:
            return False
        
        try:
            with self.storage.conn.cursor() as cur:
                # Build update fields dynamically
                update_fields = []
                update_values = []
                
                valid_fields = {
                    'first_name', 'middle_name', 'last_name', 'date_of_birth',
                    'gender', 'title', 'email', 'phone_number', 'primary_document_type',
                    'primary_document_number', 'primary_document_expiry', 
                    'primary_document_country', 'nationality', 'seat_preference',
                    'meal_preference', 'special_assistance', 'medical_conditions',
                    'dietary_restrictions', 'airline_loyalties', 'tsa_precheck_number',
                    'global_entry_number', 'is_verified', 'verification_method',
                    'last_traveled_at'
                }
                
                json_fields = {'airline_loyalties'}
                
                for key, value in update_data.items():
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
                
                update_query = f"""
                    UPDATE passenger_profiles 
                    SET {', '.join(update_fields)}
                    WHERE id = %s;
                """
                
                cur.execute(update_query, update_values + [passenger_id])
                return cur.rowcount > 0
                
        except Exception as e:
            print(f"Error updating passenger: {e}")
            return False
    
    def find_passengers_by_details(self, first_name: str, last_name: str,
                                 date_of_birth: Optional[date] = None,
                                 email: Optional[str] = None) -> List[PassengerProfile]:
        """Find passengers by personal details"""
        if not self.storage.conn:
            return []
        
        try:
            with self.storage.conn.cursor() as cur:
                # Build dynamic query based on available criteria
                where_conditions = ["LOWER(first_name) = %s", "LOWER(last_name) = %s"]
                query_params = [first_name.lower(), last_name.lower()]
                
                if date_of_birth:
                    where_conditions.append("date_of_birth = %s")
                    query_params.append(date_of_birth) # type: ignore
                
                if email:
                    where_conditions.append("LOWER(email) = %s")
                    query_params.append(email.lower())
                
                query = f"""
                    SELECT id, first_name, middle_name, last_name, date_of_birth,
                           gender, title, email, phone_number, primary_document_type,
                           primary_document_number, primary_document_expiry, 
                           primary_document_country, nationality, seat_preference,
                           meal_preference, special_assistance, medical_conditions,
                           dietary_restrictions, airline_loyalties, tsa_precheck_number,
                           global_entry_number, created_by_user_id, is_verified,
                           verification_method, created_at, updated_at, last_traveled_at
                    FROM passenger_profiles 
                    WHERE {' AND '.join(where_conditions)}
                    ORDER BY created_at DESC;
                """
                
                cur.execute(query, query_params)
                
                return [
                    PassengerProfile(
                        id=row[0], first_name=row[1], middle_name=row[2],
                        last_name=row[3], date_of_birth=row[4], gender=row[5],
                        title=row[6], email=row[7], phone_number=row[8],
                        primary_document_type=row[9], primary_document_number=row[10],
                        primary_document_expiry=row[11], primary_document_country=row[12],
                        nationality=row[13], seat_preference=row[14], meal_preference=row[15],
                        special_assistance=row[16], medical_conditions=row[17],
                        dietary_restrictions=row[18],
                        airline_loyalties=json.loads(row[19]) if row[19] else {},
                        tsa_precheck_number=row[20], global_entry_number=row[21],
                        created_by_user_id=row[22], is_verified=row[23],
                        verification_method=row[24], created_at=row[25],
                        updated_at=row[26], last_traveled_at=row[27]
                    )
                    for row in cur.fetchall()
                ]
                
        except Exception as e:
            print(f"Error finding passengers: {e}")
            return []
    
    def add_passenger_document(self, passenger_id: str, document_type: str,
                             document_number: str, issuing_country: str,
                             **document_data) -> Optional[str]:
        """Add a travel document to passenger profile"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                insert_data = {
                    'passenger_id': passenger_id,
                    'document_type': document_type,
                    'document_number': document_number,
                    'issuing_country': issuing_country,
                    'document_expiry': document_data.get('document_expiry'),
                    'is_primary': document_data.get('is_primary', False),
                    'is_verified': document_data.get('is_verified', False)
                }
                
                # Handle document images
                if 'document_image_ids' in document_data:
                    insert_data['document_image_ids'] = json.dumps(document_data['document_image_ids'])
                
                # Build query
                fields = list(insert_data.keys())
                placeholders = ', '.join(['%s'] * len(fields))
                field_names = ', '.join(fields)
                
                cur.execute(f"""
                    INSERT INTO passenger_documents ({field_names})
                    VALUES ({placeholders})
                    RETURNING id;
                """, list(insert_data.values()))
                
                result = cur.fetchone()
                if result:
                    return result[0]
                else:
                    print("Add passenger document returned no result")
                    return None
                
        except Exception as e:
            print(f"Error adding passenger document: {e}")
            return None
    
    def get_passenger_documents(self, passenger_id: str) -> List[PassengerDocument]:
        """Get all documents for a passenger"""
        if not self.storage.conn:
            return []
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, passenger_id, document_type, document_number,
                           document_expiry, issuing_country, document_image_ids,
                           is_primary, is_verified, created_at, updated_at
                    FROM passenger_documents 
                    WHERE passenger_id = %s 
                    ORDER BY is_primary DESC, created_at DESC;
                """, (passenger_id,))
                
                return [
                    PassengerDocument(
                        id=row[0], passenger_id=row[1], document_type=row[2],
                        document_number=row[3], document_expiry=row[4],
                        issuing_country=row[5],
                        document_image_ids=json.loads(row[6]) if row[6] else [],
                        is_primary=row[7], is_verified=row[8],
                        created_at=row[9], updated_at=row[10]
                    )
                    for row in cur.fetchall()
                ]
                
        except Exception as e:
            print(f"Error getting passenger documents: {e}")
            return []
    
    def connect_user_to_passenger(self, user_id: int, passenger_id: str,
                                 connection_type: str, **connection_data) -> Optional[int]:
        """Create a connection between user and passenger"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                insert_data = {
                    'user_id': user_id,
                    'passenger_id': passenger_id,
                    'connection_type': connection_type,
                    'trust_level': connection_data.get('trust_level', 'unverified'),
                    'can_book_for_passenger': connection_data.get('can_book_for_passenger', False),
                    'can_modify_passenger_details': connection_data.get('can_modify_passenger_details', False),
                    'can_view_passenger_history': connection_data.get('can_view_passenger_history', False),
                    'verified_by_user': connection_data.get('verified_by_user', False)
                }
                
                # Add optional fields
                optional_fields = ['relationship', 'connected_via_booking_id', 'verified_at']
                for field in optional_fields:
                    if field in connection_data:
                        insert_data[field] = connection_data[field]
                
                # Build query
                fields = list(insert_data.keys())
                placeholders = ', '.join(['%s'] * len(fields))
                field_names = ', '.join(fields)
                
                cur.execute(f"""
                    INSERT INTO user_passenger_connections ({field_names})
                    VALUES ({placeholders})
                    RETURNING id;
                """, list(insert_data.values()))
                
                result = cur.fetchone()
                if result:
                    return result[0]
                else:
                    print("Connect user to passenger returned no result")
                    return None
                
        except Exception as e:
            print(f"Error connecting user to passenger: {e}")
            return None
    
    def get_user_passengers(self, user_id: int, trust_level: Optional[str] = None) -> List[Tuple[PassengerProfile, UserPassengerConnection]]:
        """Get passengers connected to a user"""
        if not self.storage.conn:
            return []
        
        try:
            with self.storage.conn.cursor() as cur:
                base_query = """
                    SELECT pp.id, pp.first_name, pp.middle_name, pp.last_name, pp.date_of_birth,
                           pp.gender, pp.title, pp.email, pp.phone_number, pp.primary_document_type,
                           pp.primary_document_number, pp.primary_document_expiry, 
                           pp.primary_document_country, pp.nationality, pp.seat_preference,
                           pp.meal_preference, pp.special_assistance, pp.medical_conditions,
                           pp.dietary_restrictions, pp.airline_loyalties, pp.tsa_precheck_number,
                           pp.global_entry_number, pp.created_by_user_id, pp.is_verified,
                           pp.verification_method, pp.created_at, pp.updated_at, pp.last_traveled_at,
                           upc.id, upc.user_id, upc.passenger_id, upc.relationship,
                           upc.connection_type, upc.trust_level, upc.connected_via_booking_id,
                           upc.connection_date, upc.verified_at, upc.verified_by_user,
                           upc.can_book_for_passenger, upc.can_modify_passenger_details,
                           upc.can_view_passenger_history, upc.created_at, upc.updated_at
                    FROM passenger_profiles pp
                    JOIN user_passenger_connections upc ON pp.id = upc.passenger_id
                    WHERE upc.user_id = %s
                """
                
                params = [str(user_id)]
                if trust_level:
                    base_query += " AND upc.trust_level = %s"
                    params.append(trust_level)
                
                base_query += " ORDER BY upc.connection_date DESC;"
                
                cur.execute(base_query, params)
                
                results = []
                for row in cur.fetchall():
                    passenger = PassengerProfile(
                        id=row[0], first_name=row[1], middle_name=row[2],
                        last_name=row[3], date_of_birth=row[4], gender=row[5],
                        title=row[6], email=row[7], phone_number=row[8],
                        primary_document_type=row[9], primary_document_number=row[10],
                        primary_document_expiry=row[11], primary_document_country=row[12],
                        nationality=row[13], seat_preference=row[14], meal_preference=row[15],
                        special_assistance=row[16], medical_conditions=row[17],
                        dietary_restrictions=row[18],
                        airline_loyalties=json.loads(row[19]) if row[19] else {},
                        tsa_precheck_number=row[20], global_entry_number=row[21],
                        created_by_user_id=row[22], is_verified=row[23],
                        verification_method=row[24], created_at=row[25],
                        updated_at=row[26], last_traveled_at=row[27]
                    )
                    
                    connection = UserPassengerConnection(
                        id=row[28], user_id=row[29], passenger_id=row[30],
                        relationship=row[31], connection_type=row[32], trust_level=row[33],
                        connected_via_booking_id=row[34], connection_date=row[35],
                        verified_at=row[36], verified_by_user=row[37],
                        can_book_for_passenger=row[38], can_modify_passenger_details=row[39],
                        can_view_passenger_history=row[40], created_at=row[41],
                        updated_at=row[42]
                    )
                    
                    results.append((passenger, connection))
                
                return results
                
        except Exception as e:
            print(f"Error getting user passengers: {e}")
            return []
    
    def update_connection_permissions(self, connection_id: int, **permissions) -> bool:
        """Update user-passenger connection permissions"""
        if not self.storage.conn:
            return False
        
        try:
            with self.storage.conn.cursor() as cur:
                update_fields = []
                update_values = []
                
                valid_fields = {
                    'trust_level', 'can_book_for_passenger', 'can_modify_passenger_details',
                    'can_view_passenger_history', 'verified_at', 'verified_by_user'
                }
                
                for key, value in permissions.items():
                    if key in valid_fields:
                        update_fields.append(f"{key} = %s")
                        update_values.append(value)
                
                if not update_fields:
                    return True
                
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                
                update_query = f"""
                    UPDATE user_passenger_connections 
                    SET {', '.join(update_fields)}
                    WHERE id = %s;
                """
                
                cur.execute(update_query, update_values + [connection_id])
                return cur.rowcount > 0
                
        except Exception as e:
            print(f"Error updating connection permissions: {e}")
            return False
    
    def verify_passenger(self, passenger_id: str, verification_method: str) -> bool:
        """Mark passenger as verified"""
        return self.update_passenger(
            passenger_id,
            is_verified=True,
            verification_method=verification_method
        )
    
    def get_passenger_statistics(self) -> Dict[str, Any]:
        """Get passenger profile statistics"""
        if not self.storage.conn:
            return {}
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_passengers,
                        COUNT(CASE WHEN is_verified THEN 1 END) as verified_passengers,
                        COUNT(CASE WHEN email IS NOT NULL THEN 1 END) as with_email,
                        COUNT(CASE WHEN phone_number IS NOT NULL THEN 1 END) as with_phone,
                        COUNT(CASE WHEN primary_document_type IS NOT NULL THEN 1 END) as with_documents,
                        COUNT(CASE WHEN created_by_user_id IS NOT NULL THEN 1 END) as created_by_users
                    FROM passenger_profiles;
                """)
                
                row = cur.fetchone()
                if row:
                    return {
                        'total_passengers': row[0],
                        'verified_passengers': row[1],
                        'verification_rate': (row[1] / row[0] * 100) if row[0] > 0 else 0,
                        'with_email': row[2],
                        'with_phone': row[3],
                        'with_documents': row[4],
                        'created_by_users': row[5]
                    }
                return {}
                
        except Exception as e:
            print(f"Error getting passenger statistics: {e}")
            return {}
