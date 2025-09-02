from typing import List
from .base_schema import BaseSchema

class PersonalizationSchema(BaseSchema):
    """Simple AI personalization and user behavior tracking"""
    
    def get_table_definitions(self) -> List[str]:
        return [
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
                id SERIAL PRIMARY KEY,
                user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                
                -- Travel Preferences
                preferred_airlines JSONB DEFAULT '[]',
                preferred_departure_times JSONB DEFAULT '{}',
                preferred_seat_type VARCHAR(20),
                budget_range JSONB DEFAULT '{}',
                
                -- Behavioral Patterns
                typical_advance_booking_days INT,
                prefers_direct_flights BOOLEAN,
                price_sensitivity VARCHAR(20) DEFAULT 'medium',
                
                -- AI Interaction Data
                frequently_searched_routes JSONB DEFAULT '[]',
                booking_patterns JSONB DEFAULT '{}',
                
                -- Metadata
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Constraints
                CONSTRAINT valid_price_sensitivity CHECK (price_sensitivity IN ('low', 'medium', 'high')),
                CONSTRAINT valid_seat_type CHECK (preferred_seat_type IS NULL OR preferred_seat_type IN ('window', 'aisle', 'middle', 'any'))
            );
            """,
            
            """
            CREATE TABLE IF NOT EXISTS passenger_recognition_data (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                passenger_profile_id UUID NOT NULL REFERENCES passenger_profiles(id) ON DELETE CASCADE,
                
                -- Recognition Keys (hashed for privacy)
                name_hash VARCHAR(64),
                dob_hash VARCHAR(64),
                phone_hash VARCHAR(64),
                
                -- Connection History
                first_seen_with_user_id INT REFERENCES users(id),
                total_bookings_count INT DEFAULT 0,
                last_booking_date DATE,
                
                -- Recognition Settings
                auto_suggest_enabled BOOLEAN DEFAULT TRUE,
                
                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        ]
    
    def get_indexes(self) -> List[str]:
        return [
            "CREATE INDEX IF NOT EXISTS idx_user_preferences_user ON user_preferences(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_passenger_recognition_passenger ON passenger_recognition_data(passenger_profile_id);",
            "CREATE INDEX IF NOT EXISTS idx_passenger_recognition_first_user ON passenger_recognition_data(first_seen_with_user_id);",
            "CREATE INDEX IF NOT EXISTS idx_passenger_recognition_name_hash ON passenger_recognition_data(name_hash);",
        ]
