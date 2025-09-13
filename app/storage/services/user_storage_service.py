# ==============================================================================
# app/storage/services/user_storage_service.py
# ==============================================================================
from typing import Dict, Any, List, Optional
import json
import secrets
import logging
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
    last_chat_at: Optional[datetime]

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
    - Link users to their passenger profiles
    """
    
    def __init__(self, storage: StorageService):
        self.storage = storage
    
    def create_user(self, phone_number: str, **user_data) -> Optional[int]:
        """Create a new user account"""
        if not self.storage.conn:
            logging.warning("No database connection available.")
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                logging.info(f"Checking if user already exists with phone_number={phone_number}")
                existing_user = self.get_user_by_phone(phone_number)
                if existing_user:
                    logging.warning(f"User already exists: {existing_user}")
                    return existing_user.id
                
                # Build insert data
                insert_data = {
                    'phone_number': phone_number,
                    'status': user_data.get('status', 'onboarding_greet'),
                    'preferred_language': user_data.get('preferred_language', 'en'),
                    'is_trusted_tester': user_data.get('is_trusted_tester', False),
                    'is_active': user_data.get('is_active', True)
                }
                logging.info(f"Initial insert_data: {insert_data}")
                
                # Add optional profile fields
                profile_fields = [
                    'first_name', 'middle_name', 'last_name', 'email', 
                    'date_of_birth', 'gender', 'location', 'timezone',
                ]
                for field in profile_fields:
                    if field in user_data:
                        insert_data[field] = user_data[field]
                        logging.info(f"Added field {field}={user_data[field]}")
                
                # Handle JSON fields
                if 'travel_preferences' in user_data:
                    try:
                        insert_data['travel_preferences'] = json.dumps(user_data['travel_preferences'])
                        logging.info(f"Encoded travel_preferences: {insert_data['travel_preferences']}")
                    except Exception as je:
                        logging.error(f"Failed to encode travel_preferences: {je}")
                if 'notification_preferences' in user_data:
                    try:
                        insert_data['notification_preferences'] = json.dumps(user_data['notification_preferences'])
                        logging.info(f"Encoded notification_preferences: {insert_data['notification_preferences']}")
                    except Exception as je:
                        logging.error(f"Failed to encode notification_preferences: {je}")
                
                # Build query
                fields = list(insert_data.keys())
                placeholders = ', '.join(['%s'] * len(fields))
                field_names = ', '.join(fields)
                
                query = f"""
                    INSERT INTO users ({field_names})
                    VALUES ({placeholders})
                    RETURNING id;
                """
                values = list(insert_data.values())
                
                logging.info(f"Final query: {query}")
                logging.info(f"Values: {values}")
                
                cur.execute(query, values)
                
                result = cur.fetchone()
                if result:
                    logging.info(f"User created with id={result[0]}")
                    return result[0]
                else:
                    logging.warning("Create user returned no result")
                    return None
        
        except Exception as e:
            logging.exception(f"Error creating user: {e}")
            return None

    
    
    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, phone_number, first_name, middle_name, last_name,
                           email, date_of_birth, gender,
                           location, preferred_language, timezone, status, 
                           onboarding_completed_at, is_trusted_tester, is_active, 
                           travel_preferences, notification_preferences,
                           created_at, updated_at, last_chat_at
                    FROM users WHERE id = %s;
                """, (user_id,))
                
                row = cur.fetchone()
                if row:
                    return self._row_to_user(row)
                return None
                
        except Exception as e:
            logging.error(f"Error getting user: {e}")
            return None
    
    def get_user_by_phone(self, phone_number: str) -> Optional[User]:
        """Get user by phone number"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, phone_number, first_name, middle_name, last_name,
                           email, date_of_birth, gender,
                           location, preferred_language, timezone, status, 
                           onboarding_completed_at, is_trusted_tester, is_active, 
                           travel_preferences, notification_preferences,
                           created_at, updated_at, last_chat_at
                    FROM users WHERE phone_number = %s;
                """, (phone_number,))
                
                row = cur.fetchone()
                if row:
                    return self._row_to_user(row)
                return None
                
        except Exception as e:
            logging.error(f"Error getting user by phone: {e}")
            return None
    
    def get_or_create_user(self, phone_number: str, **user_data) -> Optional[User]:
        """Get an existing user by phone number, or create a new user if none exists"""
        if not self.storage.conn:
            logging.warning("no database connection found")
            return None
        
        logging.info("checking for a user now")

        try:
            # Try to get existing user
            existing_user = self.get_user_by_phone(phone_number)
            if existing_user:
                return existing_user
            
            logging.info(f"trying to create user now {phone_number}")

            # Create new user
            user_id = self.create_user(phone_number, **user_data)
            if user_id:
                return self.get_user(user_id)
            return None

        except Exception as e:
            logging.error(f"Error in get_or_create_user: {e}")
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
                    'date_of_birth', 'gender',
                    'location', 'preferred_language', 'timezone', 'status', 
                    'onboarding_completed_at', 'is_trusted_tester', 'is_active', 
                    'travel_preferences', 'notification_preferences', 'last_chat_at'
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
            logging.error(f"Error updating user: {e}")
            return False
    
    def complete_onboarding(self, user_id: int) -> bool:
        """Mark user onboarding as complete"""
        return self.update_user(
            user_id, 
            status='active',
            onboarding_completed_at=datetime.now()
        )
    
    def update_last_chat(self, user_id: int) -> bool:
        """Update user's last login timestamp"""
        return self.update_user(user_id, last_chat_at=datetime.now())
    
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
                    self.update_last_chat(user_id)
                    return session_token
                return None
                
        except Exception as e:
            logging.error(f"Error creating session: {e}")
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
            logging.error(f"Error getting session: {e}")
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
                cur.execute("DELETE FROM user_sessions WHERE session_token = %s;", (session_token,))
                return cur.rowcount > 0
                
        except Exception as e:
            logging.error(f"Error revoking session: {e}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        if not self.storage.conn:
            return 0
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("DELETE FROM user_sessions WHERE expires_at < CURRENT_TIMESTAMP;")
                return cur.rowcount
                
        except Exception as e:
            logging.error(f"Error cleaning up sessions: {e}")
            return 0
    
    def _row_to_user(self, row) -> User:
        """Convert database row to User object"""
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
            last_chat_at=row[19]
        )
    
    def _generate_session_token(self) -> str:
        """Generate a secure session token"""
        return secrets.token_urlsafe(32)
    
    def build_user_context(self, user: User) -> dict:
        """
        Build a public user context for the chat agent's prompt.
        Includes key personalization details without exposing sensitive PII.
        Handles optional fields gracefully.
        """
        context = {
            "phone_number": getattr(user, "phone_number", None),
            "first_name": getattr(user, "first_name", None),
            "last_name": getattr(user, "last_name", None),
            "status": getattr(user, "status", "unknown"),
            "preferred_language": getattr(user, "preferred_language", "en"),
            "is_trusted_tester": getattr(user, "is_trusted_tester", False),
            "travel_preferences": getattr(user, "travel_preferences", {}),
            "is_student_or_recent_grad": getattr(user, "is_student_or_recent_grad", None),
            "completed_bookings_count": getattr(user, "completed_bookings_count", 0),
        }

        # Known travelers list
        known_travelers = context["travel_preferences"].get("known_travelers") if context["travel_preferences"] else []
        context["known_travelers"] = known_travelers if known_travelers else []

        return context
