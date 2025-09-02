from typing import List
from .base_schema import BaseSchema

class FlightSchema(BaseSchema):
    """Flight search caching and flight data management"""
    
    def get_table_definitions(self) -> List[str]:
        return [
            """
            CREATE TABLE IF NOT EXISTS flight_searches (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                
                -- Search Identification
                custom_search_id VARCHAR(50) UNIQUE NOT NULL,
                search_type VARCHAR(20) NOT NULL,
                
                -- Search Parameters
                search_params JSONB NOT NULL,
                
                -- Results Storage
                raw_results JSONB DEFAULT '[]',
                processed_results JSONB DEFAULT '[]',
                result_count INT DEFAULT 0,
                
                -- Search Metadata
                apis_used JSONB DEFAULT '[]',
                search_duration_ms INT,
                cache_hit BOOLEAN DEFAULT FALSE,
                
                -- Expiration Management
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '7 days'),
                accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INT DEFAULT 0,
                
                -- Constraints
                CONSTRAINT valid_search_type CHECK (search_type IN ('one_way', 'round_trip', 'multi_city'))
            );
            """,
            
            """
            CREATE TABLE IF NOT EXISTS flight_offers (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                search_id UUID NOT NULL REFERENCES flight_searches(id) ON DELETE CASCADE,
                
                -- Offer Identification
                flight_offer_id VARCHAR(100) NOT NULL,
                amadeus_offer_id VARCHAR(255),
                
                -- Pricing
                base_price DECIMAL(10,2) NOT NULL,
                taxes_and_fees DECIMAL(10,2) DEFAULT 0.00,
                total_price DECIMAL(10,2) NOT NULL,
                currency VARCHAR(3) DEFAULT 'USD',
                
                -- Offer Details
                airline_codes JSONB NOT NULL DEFAULT '[]',
                route_summary VARCHAR(200),
                total_duration_minutes INT,
                stops_count INT DEFAULT 0,
                
                -- Booking Validity
                bookable_until TIMESTAMP,
                seats_available INT,
                fare_rules JSONB DEFAULT '{}',
                
                -- Full Offer Data
                complete_offer_data JSONB NOT NULL DEFAULT '{}',
                
                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Constraints
                UNIQUE(search_id, flight_offer_id)
            );
            """,
            
            """
            CREATE TABLE IF NOT EXISTS flight_status_updates (
                id SERIAL PRIMARY KEY,
                
                -- Flight Identification
                airline_code VARCHAR(3) NOT NULL,
                flight_number VARCHAR(10) NOT NULL,
                scheduled_departure_date DATE NOT NULL,
                
                -- Status Information
                current_status VARCHAR(20) NOT NULL,
                delay_minutes INT DEFAULT 0,
                new_departure_time TIMESTAMP,
                new_arrival_time TIMESTAMP,
                gate VARCHAR(10),
                terminal VARCHAR(10),
                
                -- Update Details
                status_message TEXT,
                update_source VARCHAR(50),
                
                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Constraints
                CONSTRAINT valid_flight_status CHECK (current_status IN ('on_time', 'delayed', 'boarding', 'departed', 'arrived', 'cancelled', 'diverted')),
                UNIQUE(airline_code, flight_number, scheduled_departure_date, created_at)
            );
            """
        ]
    
    def get_indexes(self) -> List[str]:
        return [
            "CREATE INDEX IF NOT EXISTS idx_flight_searches_user ON flight_searches(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_flight_searches_custom_id ON flight_searches(custom_search_id);",
            "CREATE INDEX IF NOT EXISTS idx_flight_searches_expires ON flight_searches(expires_at);",
            "CREATE INDEX IF NOT EXISTS idx_flight_searches_type ON flight_searches(search_type);",
            
            "CREATE INDEX IF NOT EXISTS idx_flight_offers_search ON flight_offers(search_id);",
            "CREATE INDEX IF NOT EXISTS idx_flight_offers_price ON flight_offers(total_price);",
            "CREATE INDEX IF NOT EXISTS idx_flight_offers_bookable ON flight_offers(bookable_until);",
            
            "CREATE INDEX IF NOT EXISTS idx_flight_status_flight ON flight_status_updates(airline_code, flight_number, scheduled_departure_date);",
            "CREATE INDEX IF NOT EXISTS idx_flight_status_date ON flight_status_updates(scheduled_departure_date);",
        ]
