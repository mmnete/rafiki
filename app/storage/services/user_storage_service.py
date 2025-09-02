# ==============================================================================
# app/storage/services/user_storage_service.py
# ==============================================================================
from typing import Dict, Any, List, Optional
import json
import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from app.storage.db_service import StorageService

@dataclass
class User:
    id: int
    phone_number: str
    first_name: Optional[str]
    middle_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    date_of_birth: Optional[date]
    gender: Optional[str]
    location: Optional[str]
    preferred_language: str
    timezone: Optional[str]
    status: str
    onboarding_completed_at: Optional[datetime]
    is_trusted_tester: bool
    is_active: bool
    travel_preferences: Dict[str, Any]
    notification_preferences: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime]

@dataclass
class UserSession:
    id: str
    user_id: int
    session_token: str
    expires_at: datetime
    device_info: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    created_at: datetime

class UserStorageService:
    """
    Service for managing user accounts and authentication
    
    Responsibilities:
    - Create and manage user accounts with phone-based authentication
    - Handle user profile information and preferences
    - Manage user sessions and authentication tokens
    - Track onboarding status and user lifecycle
    - Support user preferences for personalization
    """
    
    def __init__(self, storage: StorageService):
        self.storage = storage
    
    def create_user(self, phone_number: str, **user_data) -> Optional[int]:
        """Create a new user account"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                # Check if user already exists
                existing_user = self.get_user_by_phone(phone_number)
                if existing_user:
                    return existing_user.id
                
                # Build insert data
                insert_data = {
                    'phone_number': phone_number,
                    'status': user_data.get('status', 'onboarding_greet'),
                    'preferred_language': user_data.get('preferred_language', 'en'),
                    'is_trusted_tester': user_data.get('is_trusted_tester', False),
                    'is_active': user_data.get('is_active', True)
                }
                
                # Add optional profile fields
                profile_fields = [
                    'first_name', 'middle_name', 'last_name', 'email', 
                    'date_of_birth', 'gender', 'location', 'timezone'
                ]
                for field in profile_fields:
                    if field in user_data:
                        insert_data[field] = user_data[field]
                
                # Handle JSON fields
                if 'travel_preferences' in user_data:
                    insert_data['travel_preferences'] = json.dumps(user_data['travel_preferences'])
                if 'notification_preferences' in user_data:
                    insert_data['notification_preferences'] = json.dumps(user_data['notification_preferences'])
                
                # Build query
                fields = list(insert_data.keys())
                placeholders = ', '.join(['%s'] * len(fields))
                field_names = ', '.join(fields)
                
                cur.execute(f"""
                    INSERT INTO users ({field_names})
                    VALUES ({placeholders})
                    RETURNING id;
                """, list(insert_data.values()))
                

                result = cur.fetchone()
                if result:
                    return result[0]
                else:
                    print("Create user returned no result")
                    return None
                
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
    
    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, phone_number, first_name, middle_name, last_name,
                           email, date_of_birth, gender, location, preferred_language,
                           timezone, status, onboarding_completed_at, is_trusted_tester,
                           is_active, travel_preferences, notification_preferences,
                           created_at, updated_at, last_login_at
                    FROM users WHERE id = %s;
                """, (user_id,))
                
                row = cur.fetchone()
                if row:
                    return User(
                        id=row[0],
                        phone_number=row[1],
                        first_name=row[2],
                        middle_name=row[3],
                        last_name=row[4],
                        email=row[5],
                        date_of_birth=row[6],
                        gender=row[7],
                        location=row[8],
                        preferred_language=row[9],
                        timezone=row[10],
                        status=row[11],
                        onboarding_completed_at=row[12],
                        is_trusted_tester=row[13],
                        is_active=row[14],
                        travel_preferences=json.loads(row[15]) if row[15] else {},
                        notification_preferences=json.loads(row[16]) if row[16] else {},
                        created_at=row[17],
                        updated_at=row[18],
                        last_login_at=row[19]
                    )
                return None
                
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    def get_or_create_user(self, phone_number: str, **user_data) -> Optional[User]:
        """
        Get an existing user by phone number, or create a new user if none exists.
        Returns a User object.
        """
        if not self.storage.conn:
            return None

        try:
            # 1️⃣ Try to get existing user
            existing_user = self.get_user_by_phone(phone_number)
            if existing_user:
                return existing_user

            # 2️⃣ Prepare insert data
            insert_data = {
                'phone_number': phone_number,
                'status': user_data.get('status', 'onboarding_greet'),
                'preferred_language': user_data.get('preferred_language', 'en'),
                'is_trusted_tester': user_data.get('is_trusted_tester', False),
                'is_active': user_data.get('is_active', True)
            }

            # Optional profile fields
            profile_fields = [
                'first_name', 'middle_name', 'last_name', 'email',
                'date_of_birth', 'gender', 'location', 'timezone'
            ]
            for field in profile_fields:
                if field in user_data:
                    insert_data[field] = user_data[field]

            # JSON fields
            if 'travel_preferences' in user_data:
                insert_data['travel_preferences'] = json.dumps(user_data['travel_preferences'])
            if 'notification_preferences' in user_data:
                insert_data['notification_preferences'] = json.dumps(user_data['notification_preferences'])

            # 3️⃣ Build and execute insert query
            fields = list(insert_data.keys())
            placeholders = ', '.join(['%s'] * len(fields))
            field_names = ', '.join(fields)

            with self.storage.conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO users ({field_names}) VALUES ({placeholders}) RETURNING *;",
                    list(insert_data.values())
                )
                row = cur.fetchone()
                if row:
                    return User(
                        id=row[0],
                        phone_number=row[1],
                        first_name=row[2],
                        middle_name=row[3],
                        last_name=row[4],
                        email=row[5],
                        date_of_birth=row[6],
                        gender=row[7],
                        location=row[8],
                        preferred_language=row[9],
                        timezone=row[10],
                        status=row[11],
                        onboarding_completed_at=row[12],
                        is_trusted_tester=row[13],
                        is_active=row[14],
                        travel_preferences=json.loads(row[15]) if row[15] else {},
                        notification_preferences=json.loads(row[16]) if row[16] else {},
                        created_at=row[17],
                        updated_at=row[18],
                        last_login_at=row[19]
                    )
                else:
                    print("Create user returned no result")
                    return None

        except Exception as e:
            print(f"Error in get_or_create_user: {e}")
            return None
    
    def get_user_by_phone(self, phone_number: str) -> Optional[User]:
        """Get user by phone number"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, phone_number, first_name, middle_name, last_name,
                           email, date_of_birth, gender, location, preferred_language,
                           timezone, status, onboarding_completed_at, is_trusted_tester,
                           is_active, travel_preferences, notification_preferences,
                           created_at, updated_at, last_login_at
                    FROM users WHERE phone_number = %s;
                """, (phone_number,))
                
                row = cur.fetchone()
                if row:
                    return User(
                        id=row[0], phone_number=row[1], first_name=row[2],
                        middle_name=row[3], last_name=row[4], email=row[5],
                        date_of_birth=row[6], gender=row[7], location=row[8],
                        preferred_language=row[9], timezone=row[10], status=row[11],
                        onboarding_completed_at=row[12], is_trusted_tester=row[13],
                        is_active=row[14],
                        travel_preferences=json.loads(row[15]) if row[15] else {},
                        notification_preferences=json.loads(row[16]) if row[16] else {},
                        created_at=row[17], updated_at=row[18], last_login_at=row[19]
                    )
                return None
                
        except Exception as e:
            print(f"Error getting user by phone: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, phone_number, first_name, middle_name, last_name,
                           email, date_of_birth, gender, location, preferred_language,
                           timezone, status, onboarding_completed_at, is_trusted_tester,
                           is_active, travel_preferences, notification_preferences,
                           created_at, updated_at, last_login_at
                    FROM users WHERE email = %s;
                """, (email,))
                
                row = cur.fetchone()
                if row:
                    return User(
                        id=row[0], phone_number=row[1], first_name=row[2],
                        middle_name=row[3], last_name=row[4], email=row[5],
                        date_of_birth=row[6], gender=row[7], location=row[8],
                        preferred_language=row[9], timezone=row[10], status=row[11],
                        onboarding_completed_at=row[12], is_trusted_tester=row[13],
                        is_active=row[14],
                        travel_preferences=json.loads(row[15]) if row[15] else {},
                        notification_preferences=json.loads(row[16]) if row[16] else {},
                        created_at=row[17], updated_at=row[18], last_login_at=row[19]
                    )
                return None
                
        except Exception as e:
            print(f"Error getting user by email: {e}")
            return None
    
    def update_user(self, user_id: int, **update_data) -> bool:
        """Update user profile information"""
        if not self.storage.conn:
            return False
        
        try:
            with self.storage.conn.cursor() as cur:
                # Build update fields dynamically
                update_fields = []
                update_values = []
                
                valid_fields = {
                    'first_name', 'middle_name', 'last_name', 'email',
                    'date_of_birth', 'gender', 'location', 'preferred_language',
                    'timezone', 'status', 'onboarding_completed_at', 'is_trusted_tester',
                    'is_active', 'travel_preferences', 'notification_preferences',
                    'last_login_at'
                }
                
                json_fields = {'travel_preferences', 'notification_preferences'}
                
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
                    UPDATE users 
                    SET {', '.join(update_fields)}
                    WHERE id = %s;
                """
                
                cur.execute(update_query, update_values + [user_id])
                return cur.rowcount > 0
                
        except Exception as e:
            print(f"Error updating user: {e}")
            return False
    
    def update_user_status(self, user_id: int, status: str) -> bool:
        """Update user status (onboarding, active, etc.)"""
        return self.update_user(user_id, status=status)
    
    def complete_onboarding(self, user_id: int) -> bool:
        """Mark user onboarding as complete"""
        return self.update_user(
            user_id, 
            status='active',
            onboarding_completed_at=datetime.now()
        )
    
    def update_last_login(self, user_id: int) -> bool:
        """Update user's last login timestamp"""
        return self.update_user(user_id, last_login_at=datetime.now())
    
    def create_session(self, user_id: int, device_info: Optional[Dict[str, Any]] = None,
                      ip_address: Optional[str] = None, expires_in_hours: int = 24) -> Optional[str]:
        """Create a new user session"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                # Generate session token
                session_token = self._generate_session_token()
                expires_at = datetime.now() + timedelta(hours=expires_in_hours)
                
                cur.execute("""
                    INSERT INTO user_sessions (user_id, session_token, expires_at, device_info, ip_address)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id;
                """, (
                    user_id, session_token, expires_at,
                    json.dumps(device_info) if device_info else None,
                    ip_address
                ))
                
                if cur.fetchone():
                    # Update last login
                    self.update_last_login(user_id)
                    return session_token
                return None
                
        except Exception as e:
            print(f"Error creating session: {e}")
            return None
    
    def get_session(self, session_token: str) -> Optional[UserSession]:
        """Get session by token"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, user_id, session_token, expires_at, device_info, ip_address, created_at
                    FROM user_sessions 
                    WHERE session_token = %s AND expires_at > CURRENT_TIMESTAMP;
                """, (session_token,))
                
                row = cur.fetchone()
                if row:
                    return UserSession(
                        id=row[0],
                        user_id=row[1],
                        session_token=row[2],
                        expires_at=row[3],
                        device_info=json.loads(row[4]) if row[4] else None,
                        ip_address=row[5],
                        created_at=row[6]
                    )
                return None
                
        except Exception as e:
            print(f"Error getting session: {e}")
            return None
    
    def validate_session(self, session_token: str) -> Optional[int]:
        """Validate session and return user_id if valid"""
        session = self.get_session(session_token)
        return session.user_id if session else None
    
    def revoke_session(self, session_token: str) -> bool:
        """Revoke/delete a session"""
        if not self.storage.conn:
            return False
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM user_sessions WHERE session_token = %s;
                """, (session_token,))
                
                return cur.rowcount > 0
                
        except Exception as e:
            print(f"Error revoking session: {e}")
            return False
    
    def revoke_all_user_sessions(self, user_id: int) -> int:
        """Revoke all sessions for a user"""
        if not self.storage.conn:
            return 0
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM user_sessions WHERE user_id = %s;
                """, (user_id,))
                
                return cur.rowcount
                
        except Exception as e:
            print(f"Error revoking user sessions: {e}")
            return 0
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        if not self.storage.conn:
            return 0
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM user_sessions WHERE expires_at < CURRENT_TIMESTAMP;
                """)
                
                return cur.rowcount
                
        except Exception as e:
            print(f"Error cleaning up sessions: {e}")
            return 0
    
    def get_user_stats(self) -> Dict[str, Any]:
        """Get user statistics"""
        if not self.storage.conn:
            return {}
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_users,
                        COUNT(CASE WHEN is_active THEN 1 END) as active_users,
                        COUNT(CASE WHEN is_trusted_tester THEN 1 END) as trusted_testers,
                        COUNT(CASE WHEN onboarding_completed_at IS NOT NULL THEN 1 END) as completed_onboarding,
                        COUNT(CASE WHEN status = 'onboarding_greet' THEN 1 END) as new_users,
                        COUNT(CASE WHEN last_login_at > CURRENT_TIMESTAMP - INTERVAL '7 days' THEN 1 END) as recent_logins
                    FROM users;
                """)
                
                row = cur.fetchone()
                if row:
                    return {
                        'total_users': row[0],
                        'active_users': row[1],
                        'trusted_testers': row[2],
                        'completed_onboarding': row[3],
                        'new_users': row[4],
                        'recent_logins': row[5],
                        'onboarding_completion_rate': (row[3] / row[0] * 100) if row[0] > 0 else 0
                    }
                return {}
                
        except Exception as e:
            print(f"Error getting user stats: {e}")
            return {}
    
    def find_users_by_name(self, query: str, limit: int = 20) -> List[User]:
        """Search users by name"""
        if not self.storage.conn:
            return []
        
        try:
            with self.storage.conn.cursor() as cur:
                search_pattern = f"%{query.lower()}%"
                cur.execute("""
                    SELECT id, phone_number, first_name, middle_name, last_name,
                           email, date_of_birth, gender, location, preferred_language,
                           timezone, status, onboarding_completed_at, is_trusted_tester,
                           is_active, travel_preferences, notification_preferences,
                           created_at, updated_at, last_login_at
                    FROM users 
                    WHERE (LOWER(first_name) LIKE %s OR LOWER(last_name) LIKE %s)
                      AND is_active = true
                    ORDER BY 
                        CASE WHEN LOWER(first_name) LIKE %s THEN 1 ELSE 2 END,
                        first_name, last_name
                    LIMIT %s;
                """, (search_pattern, search_pattern, f"{query.lower()}%", limit))
                
                return [
                    User(
                        id=row[0], phone_number=row[1], first_name=row[2],
                        middle_name=row[3], last_name=row[4], email=row[5],
                        date_of_birth=row[6], gender=row[7], location=row[8],
                        preferred_language=row[9], timezone=row[10], status=row[11],
                        onboarding_completed_at=row[12], is_trusted_tester=row[13],
                        is_active=row[14],
                        travel_preferences=json.loads(row[15]) if row[15] else {},
                        notification_preferences=json.loads(row[16]) if row[16] else {},
                        created_at=row[17], updated_at=row[18], last_login_at=row[19]
                    )
                    for row in cur.fetchall()
                ]
                
        except Exception as e:
            print(f"Error finding users by name: {e}")
            return []
    
    def _generate_session_token(self) -> str:
        """Generate a secure session token"""
        return secrets.token_urlsafe(32)
    
    def _normalize_phone_number(self, phone_number: str) -> str:
        """Normalize phone number for consistent storage"""
        # Remove spaces, dashes, parentheses
        cleaned = ''.join(filter(str.isdigit, phone_number.replace('+', '')))
        
        # Add + prefix if not present and number looks international
        if len(cleaned) > 10:
            return f"+{cleaned}"
        return phone_number.strip()

    def cleanup_eval_users(self) -> int:
        """
        Delete all users with the specific phone number '+1555000' and their sessions.
        This is used to clean up test data after an evaluation run.
        """
        if not self.storage.conn:
            return 0
        
        try:
            with self.storage.conn.cursor() as cur:
                # Find all user IDs for the specified phone number
                cur.execute("""
                    SELECT id FROM users WHERE phone_number = '+1555000';
                """)
                user_ids_to_delete = [row[0] for row in cur.fetchall()]

                if not user_ids_to_delete:
                    print("No eval users found to clean up.")
                    return 0

                # Delete sessions first to avoid foreign key issues
                cur.execute("""
                    DELETE FROM user_sessions WHERE user_id IN %s;
                """, (tuple(user_ids_to_delete),))
                sessions_deleted = cur.rowcount
                print(f"Deleted {sessions_deleted} sessions for eval users.")

                # Delete the users
                cur.execute("""
                    DELETE FROM users WHERE phone_number = '+1555000';
                """)
                users_deleted = cur.rowcount
                print(f"Deleted {users_deleted} eval users.")

                return users_deleted
        
        except Exception as e:
            print(f"Error cleaning up eval users: {e}")
            return 0
