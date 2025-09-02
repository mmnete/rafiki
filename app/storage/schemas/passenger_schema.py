from typing import List
from .base_schema import BaseSchema

class PassengerSchema(BaseSchema):
    """
    Passenger profiles that can be reused across bookings
    
    Design considerations:
    - Passengers exist independently of bookings
    - Can be linked to user accounts for personalization
    - Stores travel documents, preferences, and history
    - Enables cross-booking passenger recognition
    """
    
    def get_table_definitions(self) -> List[str]:
        return [
            """
            CREATE TABLE IF NOT EXISTS passenger_profiles (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                
                -- Personal Information
                first_name VARCHAR(255) NOT NULL,
                middle_name VARCHAR(255),
                last_name VARCHAR(255) NOT NULL,
                date_of_birth DATE NOT NULL,
                gender VARCHAR(20),
                title VARCHAR(10),
                
                -- Contact Information
                email VARCHAR(255),
                phone_number VARCHAR(50),
                
                -- Travel Documents (can have multiple)
                primary_document_type VARCHAR(20),
                primary_document_number VARCHAR(50),
                primary_document_expiry DATE,
                primary_document_country VARCHAR(3),
                nationality VARCHAR(3),
                
                -- Travel Preferences
                seat_preference VARCHAR(20) DEFAULT 'any',
                meal_preference VARCHAR(50),
                special_assistance TEXT,
                medical_conditions TEXT,
                dietary_restrictions TEXT,
                
                -- Frequent Traveler Information
                airline_loyalties JSONB DEFAULT '{}',
                tsa_precheck_number VARCHAR(20),
                global_entry_number VARCHAR(20),
                
                -- System Fields
                created_by_user_id INT REFERENCES users(id),
                is_verified BOOLEAN DEFAULT FALSE,
                verification_method VARCHAR(50),
                
                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_traveled_at TIMESTAMP,
                
                -- Constraints
                CONSTRAINT valid_passenger_email CHECK (email IS NULL OR email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
                CONSTRAINT valid_passenger_phone CHECK (phone_number IS NULL OR phone_number ~ '^[+]?[0-9\s\-()]+$'),
                CONSTRAINT valid_gender CHECK (gender IS NULL OR gender IN ('male', 'female', 'other', 'prefer_not_to_say'))
            );
            """,
            
            """
            CREATE TABLE IF NOT EXISTS passenger_documents (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                passenger_id UUID NOT NULL REFERENCES passenger_profiles(id) ON DELETE CASCADE,
                
                -- Document Details
                document_type VARCHAR(20) NOT NULL,
                document_number VARCHAR(50) NOT NULL,
                document_expiry DATE,
                issuing_country VARCHAR(3) NOT NULL,
                
                -- Document Images/Files
                document_image_ids JSONB DEFAULT '[]',
                is_primary BOOLEAN DEFAULT FALSE,
                is_verified BOOLEAN DEFAULT FALSE,
                
                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Constraints
                CONSTRAINT valid_document_type CHECK (document_type IN ('passport', 'national_id', 'drivers_license', 'birth_certificate')),
                UNIQUE(passenger_id, document_type, document_number)
            );
            """,
            
            """
            CREATE TABLE IF NOT EXISTS user_passenger_connections (
                id SERIAL PRIMARY KEY,
                user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                passenger_id UUID NOT NULL REFERENCES passenger_profiles(id) ON DELETE CASCADE,
                
                -- Connection Details
                relationship VARCHAR(50),
                connection_type VARCHAR(30) NOT NULL,
                trust_level VARCHAR(20) DEFAULT 'unverified',
                
                -- When/How Connection Was Made
                connected_via_booking_id UUID,
                connection_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_at TIMESTAMP,
                verified_by_user BOOLEAN DEFAULT FALSE,
                
                -- Permissions
                can_book_for_passenger BOOLEAN DEFAULT FALSE,
                can_modify_passenger_details BOOLEAN DEFAULT FALSE,
                can_view_passenger_history BOOLEAN DEFAULT FALSE,
                
                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Constraints
                CONSTRAINT valid_connection_type CHECK (connection_type IN ('self', 'family', 'friend', 'colleague', 'auto_detected')),
                CONSTRAINT valid_relationship CHECK (relationship IN ('self', 'spouse', 'child', 'parent', 'sibling', 'friend', 'colleague', 'other')),
                CONSTRAINT valid_trust_level CHECK (trust_level IN ('unverified', 'pending', 'verified', 'trusted')),
                UNIQUE(user_id, passenger_id)
            );
            """
        ]
    
    def get_indexes(self) -> List[str]:
        return [
            "CREATE INDEX IF NOT EXISTS idx_passenger_profiles_name ON passenger_profiles(first_name, last_name);",
            "CREATE INDEX IF NOT EXISTS idx_passenger_profiles_dob ON passenger_profiles(date_of_birth);",
            "CREATE INDEX IF NOT EXISTS idx_passenger_profiles_created_by ON passenger_profiles(created_by_user_id);",
            "CREATE INDEX IF NOT EXISTS idx_passenger_profiles_email ON passenger_profiles(email);",
            "CREATE INDEX IF NOT EXISTS idx_passenger_profiles_phone ON passenger_profiles(phone_number);",
            
            "CREATE INDEX IF NOT EXISTS idx_passenger_documents_passenger ON passenger_documents(passenger_id);",
            "CREATE INDEX IF NOT EXISTS idx_passenger_documents_type ON passenger_documents(document_type);",
            "CREATE INDEX IF NOT EXISTS idx_passenger_documents_primary ON passenger_documents(is_primary);",
            
            "CREATE INDEX IF NOT EXISTS idx_user_passenger_connections_user ON user_passenger_connections(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_user_passenger_connections_passenger ON user_passenger_connections(passenger_id);",
            "CREATE INDEX IF NOT EXISTS idx_user_passenger_connections_type ON user_passenger_connections(connection_type);",
            "CREATE INDEX IF NOT EXISTS idx_user_passenger_connections_trust ON user_passenger_connections(trust_level);",
        ]
