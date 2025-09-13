from typing import List
from .base_schema import BaseSchema

class PassengerSchema(BaseSchema):
    """
    Passenger profiles that can be reused across bookings
    
    Design considerations:
    - Passengers exist independently of bookings
    - Only contains data that doesn't vary per booking
    - Can be linked to user accounts for personalization
    - Enables cross-booking passenger recognition and auto-fill
    """
    
    def get_table_definitions(self) -> List[str]:
        return [
            """
            CREATE TABLE IF NOT EXISTS passenger_profiles (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                
                -- Optional link to user account (if this passenger is also a user)
                user_id INT REFERENCES users(id) ON DELETE SET NULL,
                
                -- REQUIRED PERSONAL INFO (airline mandatory fields that don't change)
                first_name VARCHAR(255) NOT NULL,
                middle_name VARCHAR(255),
                last_name VARCHAR(255) NOT NULL,
                date_of_birth DATE NOT NULL,
                gender VARCHAR(20) NOT NULL,
                nationality VARCHAR(3) NOT NULL,
                
                -- TRAVEL DOCUMENTS (primary document)
                primary_document_type VARCHAR(20) DEFAULT 'passport',
                primary_document_number VARCHAR(50),
                primary_document_expiry DATE,
                primary_document_country VARCHAR(3),
                place_of_birth VARCHAR(100),
                
                -- TRAVEL PREFERENCES (passenger's default preferences)
                seat_preference VARCHAR(50) DEFAULT 'any',
                meal_preference VARCHAR(50),
                special_assistance TEXT,
                dietary_restrictions TEXT,
                preferred_class VARCHAR(20) DEFAULT 'economy',
                
                -- FREQUENT TRAVELER PROGRAMS (tied to this person)
                airline_loyalties JSONB DEFAULT '{}',
                tsa_precheck_number VARCHAR(20),
                global_entry_number VARCHAR(20),
                known_traveler_number VARCHAR(20),
                redress_number VARCHAR(20),
                
                -- MEDICAL/ACCESSIBILITY (permanent conditions)
                medical_conditions TEXT,
                mobility_assistance BOOLEAN DEFAULT FALSE,
                vision_assistance BOOLEAN DEFAULT FALSE,
                hearing_assistance BOOLEAN DEFAULT FALSE,
                service_animal BOOLEAN DEFAULT FALSE,
                oxygen_required BOOLEAN DEFAULT FALSE,
                
                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP,
                
                -- Constraints
                CONSTRAINT valid_passenger_gender CHECK (gender IN ('male', 'female', 'other')),
                CONSTRAINT valid_document_type CHECK (primary_document_type IN ('passport', 'national_id', 'drivers_license', 'birth_certificate')),
                CONSTRAINT valid_seat_pref CHECK (seat_preference IN ('window', 'aisle', 'any', 'exit_row', 'front', 'back', 'middle')),
                CONSTRAINT valid_class_pref CHECK (preferred_class IN ('economy', 'premium_economy', 'business', 'first')),
            
                -- Ensure one-to-one relationship: a user can only have one passenger profile
                UNIQUE(user_id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS user_frequent_passengers (
                id SERIAL PRIMARY KEY,
                user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                passenger_profile_id UUID NOT NULL REFERENCES passenger_profiles(id) ON DELETE CASCADE,
                
                -- Relationship info
                relationship VARCHAR(50),
                nickname VARCHAR(100),
                
                -- Usage tracking for ML/personalization
                times_booked_together INT DEFAULT 1,
                last_booked_together TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_trips_value DECIMAL(10,2) DEFAULT 0.00,
                
                -- Permissions & preferences
                can_auto_suggest BOOLEAN DEFAULT TRUE,
                can_book_on_behalf BOOLEAN DEFAULT FALSE,
                
                -- Smart suggestions context
                common_routes JSONB DEFAULT '[]',
                preferred_times JSONB DEFAULT '{}',
                
                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                CONSTRAINT valid_relationship CHECK (relationship IN ('self', 'spouse', 'partner', 'child', 'parent', 'sibling', 'friend', 'colleague', 'other')),
                UNIQUE(user_id, passenger_profile_id)
            );
            """,
            """
            -- Helper function to calculate passenger type from date of birth
            CREATE OR REPLACE FUNCTION get_passenger_type(birth_date DATE, travel_date DATE DEFAULT CURRENT_DATE) 
            RETURNS VARCHAR(20) AS $$
            BEGIN
                CASE 
                    WHEN AGE(travel_date, birth_date) < INTERVAL '2 years' THEN RETURN 'infant';
                    WHEN AGE(travel_date, birth_date) < INTERVAL '12 years' THEN RETURN 'child';
                    WHEN AGE(travel_date, birth_date) >= INTERVAL '65 years' THEN RETURN 'senior';
                    ELSE RETURN 'adult';
                END CASE;
            END;
            $$ LANGUAGE plpgsql;
            """
        ]
    
    def get_indexes(self) -> List[str]:
        return [
            "CREATE INDEX IF NOT EXISTS idx_passenger_profiles_name ON passenger_profiles(first_name, last_name);",
            "CREATE INDEX IF NOT EXISTS idx_passenger_profiles_dob ON passenger_profiles(date_of_birth);",
            "CREATE INDEX IF NOT EXISTS idx_passenger_profiles_nationality ON passenger_profiles(nationality);",
            "CREATE INDEX IF NOT EXISTS idx_passenger_profiles_document ON passenger_profiles(primary_document_number);",
            "CREATE INDEX IF NOT EXISTS idx_passenger_profiles_last_used ON passenger_profiles(last_used_at);",
            
            "CREATE INDEX IF NOT EXISTS idx_booking_passengers_booking ON booking_passengers(booking_id);",
            "CREATE INDEX IF NOT EXISTS idx_booking_passengers_profile ON booking_passengers(passenger_profile_id);",
            "CREATE INDEX IF NOT EXISTS idx_booking_passengers_sequence ON booking_passengers(booking_id, passenger_sequence);",
            
            "CREATE INDEX IF NOT EXISTS idx_user_frequent_passengers_user ON user_frequent_passengers(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_user_frequent_passengers_passenger ON user_frequent_passengers(passenger_profile_id);",
            "CREATE INDEX IF NOT EXISTS idx_user_frequent_passengers_relationship ON user_frequent_passengers(relationship);",
        ]