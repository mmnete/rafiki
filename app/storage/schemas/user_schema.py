from typing import List
from .base_schema import BaseSchema

class UserSchema(BaseSchema):
    """
    User accounts and profile information
    
    Design considerations:
    - One phone number = one user account
    - Users can create group bookings for multiple passengers
    - Tracks onboarding status and preferences
    - Supports user-to-passenger connections for personalization
    """
    
    def __init__(self):
        super().__init__()
        self.table_name = "users"
    
    def get_table_definitions(self) -> List[str]:
        return [
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                phone_number VARCHAR(50) UNIQUE NOT NULL,
                
                -- Profile Information (contact details for bookings)
                first_name VARCHAR(255),
                middle_name VARCHAR(255),
                last_name VARCHAR(255),
                email VARCHAR(255),
                date_of_birth DATE,
                gender VARCHAR(20),
                
                -- Location and Preferences
                location VARCHAR(255),
                preferred_language VARCHAR(10) DEFAULT 'en',
                timezone VARCHAR(50),
                
                -- Account Status
                status VARCHAR(50) DEFAULT 'onboarding_greet',
                onboarding_completed_at TIMESTAMP,
                is_trusted_tester BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                
                -- Personalization
                travel_preferences JSONB DEFAULT '{}',
                notification_preferences JSONB DEFAULT '{}',
                
                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_chat_at TIMESTAMP,
                
                -- Constraints
                CONSTRAINT valid_email CHECK (email IS NULL OR email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
                CONSTRAINT valid_phone CHECK (phone_number ~ '^[+]?[0-9\s\-()]+$'),
                CONSTRAINT valid_language CHECK (preferred_language IN ('en', 'sw', 'fr', 'es')),
                CONSTRAINT valid_user_gender CHECK (gender IN ('male', 'female', 'other', 'prefer_not_to_say'))
            );
            """,
            
            """
            CREATE TABLE IF NOT EXISTS user_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                session_token VARCHAR(255) UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                device_info JSONB,
                ip_address INET,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        ]
    
    def get_indexes(self) -> List[str]:
        return [
            "CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone_number);",
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
            "CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);",
            "CREATE INDEX IF NOT EXISTS idx_users_trusted ON users(is_trusted_tester);",
            "CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);",
            "CREATE INDEX IF NOT EXISTS idx_users_created ON users(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token);",
            "CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at);",
        ]
