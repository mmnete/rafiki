from typing import List
from .base_schema import BaseSchema

class BookingSchema(BaseSchema):
    """
    Booking system with support for group bookings and passenger connections
    """
    
    def get_table_definitions(self) -> List[str]:
        return [
            # 1. First create the main bookings table
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                booking_reference VARCHAR(20) UNIQUE NOT NULL,
                
                -- WHO MADE THE BOOKING (provides contact info)
                primary_user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                
                -- Group/Organization
                group_size INT DEFAULT 1,
                booking_type VARCHAR(20) DEFAULT 'individual',
                
                -- Flight Search Connection
                search_id VARCHAR(255),
                selected_flight_offers JSONB NOT NULL DEFAULT '[]',
                
                -- Trip Details
                trip_type VARCHAR(20) DEFAULT 'one_way',
                origin_airport VARCHAR(3),
                destination_airport VARCHAR(3),
                departure_date DATE,
                return_date DATE,
                
                -- Pricing
                base_price DECIMAL(10,2) DEFAULT 0.00,
                taxes_and_fees DECIMAL(10,2) DEFAULT 0.00,
                service_fee DECIMAL(10,2) DEFAULT 5.00,
                insurance_fee DECIMAL(10,2) DEFAULT 0.00,
                total_amount DECIMAL(10,2) DEFAULT 5.00,
                currency VARCHAR(3) DEFAULT 'USD',
                
                -- Status Tracking
                booking_status VARCHAR(30) DEFAULT 'draft',
                payment_status VARCHAR(30) DEFAULT 'pending',
                fulfillment_status VARCHAR(30) DEFAULT 'pending',
                
                -- External System Integration (generic)
                provider_name VARCHAR(50),                -- e.g. 'amadeus', 'sabre', 'airline_direct'
                provider_booking_id VARCHAR(255),         -- external booking identifier
                provider_pnr VARCHAR(20),                 -- PNR code if applicable
                provider_response JSONB DEFAULT '{}',     -- raw API response
                
                -- Booking-level services and requests
                travel_insurance BOOLEAN DEFAULT FALSE,
                special_requests TEXT,
                accessibility_requirements TEXT,
                
                -- Emergency contact (booking-level, not passenger-level)
                emergency_contact_name VARCHAR(255),
                emergency_contact_phone VARCHAR(50),
                emergency_contact_relationship VARCHAR(50),
                emergency_contact_email VARCHAR(255),
                
                -- Important Dates
                confirmation_deadline TIMESTAMP,
                payment_deadline TIMESTAMP,
                checkin_available_at TIMESTAMP,
                
                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                confirmed_at TIMESTAMP,
                cancelled_at TIMESTAMP,
                
                -- Constraints
                CONSTRAINT valid_booking_status CHECK (
                    booking_status IN ('draft', 'passenger_details_pending', 'payment_pending', 'confirmed', 'checked_in', 'completed', 'cancelled', 'expired')
                ),
                CONSTRAINT valid_payment_status CHECK (
                    payment_status IN ('pending', 'processing', 'completed', 'failed', 'refunded', 'partially_refunded')
                ),
                CONSTRAINT valid_trip_type CHECK (trip_type IN ('one_way', 'round_trip', 'multi_city')),
                CONSTRAINT valid_booking_type CHECK (booking_type IN ('individual', 'family', 'group', 'corporate'))
            );
            """,
            
            # 2. Then create booking_passengers table (now that bookings exists)
            """
            CREATE TABLE IF NOT EXISTS booking_passengers (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
                passenger_profile_id UUID NOT NULL REFERENCES passenger_profiles(id) ON DELETE CASCADE,
                
                -- Booking-Specific Details
                passenger_sequence INT NOT NULL,
                is_primary_passenger BOOLEAN DEFAULT FALSE,
                
                -- BOOKING-SPECIFIC SERVICES (vary per trip)
                extra_baggage_count INT DEFAULT 0,
                priority_boarding BOOLEAN DEFAULT FALSE,
                seat_upgrade_requested BOOLEAN DEFAULT FALSE,
                wheelchair_requested BOOLEAN DEFAULT FALSE,
                unaccompanied_minor BOOLEAN DEFAULT FALSE,
                
                -- Seat Assignments (populated after booking)
                assigned_seats JSONB DEFAULT '{}',
                seat_assignment_status VARCHAR(20) DEFAULT 'pending',
                
                -- Check-in Status
                checked_in_at TIMESTAMP,
                boarding_pass_issued BOOLEAN DEFAULT FALSE,
                boarding_pass_file_id UUID,
                
                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Constraints
                CONSTRAINT valid_seat_status CHECK (seat_assignment_status IN ('pending', 'assigned', 'confirmed', 'changed')),
                UNIQUE(booking_id, passenger_sequence)
            );
            """,
            
            # 3. Then create booking_flight_segments
            """
            CREATE TABLE IF NOT EXISTS booking_flight_segments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
                
                -- Flight Details
                flight_offer_id VARCHAR(100) NOT NULL,
                segment_sequence INT NOT NULL,
                segment_type VARCHAR(20) DEFAULT 'outbound',
                
                -- Airline and Flight Info
                airline_code VARCHAR(3) NOT NULL,
                airline_name VARCHAR(100),
                flight_number VARCHAR(10) NOT NULL,
                aircraft_type VARCHAR(50),
                
                -- Route Information
                departure_airport VARCHAR(3) NOT NULL,
                departure_terminal VARCHAR(10),
                departure_time TIMESTAMP NOT NULL,
                arrival_airport VARCHAR(3) NOT NULL,
                arrival_terminal VARCHAR(10),
                arrival_time TIMESTAMP NOT NULL,
                
                -- Flight Details
                duration_minutes INT,
                distance_km INT,
                flight_status VARCHAR(20) DEFAULT 'scheduled',
                
                -- Real-time Updates
                actual_departure_time TIMESTAMP,
                actual_arrival_time TIMESTAMP,
                delay_minutes INT DEFAULT 0,
                gate_info VARCHAR(20),
                
                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Constraints
                CONSTRAINT valid_segment_type CHECK (segment_type IN ('outbound', 'return', 'connecting')),
                CONSTRAINT valid_flight_status CHECK (flight_status IN ('scheduled', 'delayed', 'boarding', 'departed', 'arrived', 'cancelled')),
                UNIQUE(booking_id, segment_sequence)
            );
            """,
            
            # 4. Finally create booking_timeline
            """
            CREATE TABLE IF NOT EXISTS booking_timeline (
                id SERIAL PRIMARY KEY,
                booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
                
                -- Event Details
                event_type VARCHAR(50) NOT NULL,
                event_description TEXT,
                event_data JSONB DEFAULT '{}',
                
                -- Event Context
                triggered_by_user_id INT REFERENCES users(id) ON DELETE CASCADE,
                system_event BOOLEAN DEFAULT FALSE,
                
                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Constraints
                CONSTRAINT valid_event_type CHECK (event_type IN (
                    'booking_created', 'passenger_added', 'passenger_updated', 'payment_initiated',
                    'payment_completed', 'payment_failed', 'booking_confirmed', 'check_in_completed',
                    'flight_status_updated', 'booking_cancelled', 'refund_processed', 'documents_generated'
                ))
            );
            """
        ]
    
    def get_indexes(self) -> List[str]:
        return [
            "CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(primary_user_id);",
            "CREATE INDEX IF NOT EXISTS idx_bookings_reference ON bookings(booking_reference);",
            "CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(booking_status);",
            "CREATE INDEX IF NOT EXISTS idx_bookings_departure ON bookings(departure_date);",
            "CREATE INDEX IF NOT EXISTS idx_bookings_provider_pnr ON bookings(provider_pnr);",
            "CREATE INDEX IF NOT EXISTS idx_bookings_provider_id ON bookings(provider_booking_id);",
            
            "CREATE INDEX IF NOT EXISTS idx_booking_passengers_booking ON booking_passengers(booking_id);",
            "CREATE INDEX IF NOT EXISTS idx_booking_passengers_profile ON booking_passengers(passenger_profile_id);",
            "CREATE INDEX IF NOT EXISTS idx_booking_passengers_sequence ON booking_passengers(booking_id, passenger_sequence);",
            
            "CREATE INDEX IF NOT EXISTS idx_booking_segments_booking ON booking_flight_segments(booking_id);",
            "CREATE INDEX IF NOT EXISTS idx_booking_segments_flight ON booking_flight_segments(flight_number, departure_time);",
            "CREATE INDEX IF NOT EXISTS idx_booking_segments_route ON booking_flight_segments(departure_airport, arrival_airport);",
            
            "CREATE INDEX IF NOT EXISTS idx_booking_timeline_booking ON booking_timeline(booking_id, created_at DESC);",
            "CREATE INDEX IF NOT EXISTS idx_booking_timeline_event ON booking_timeline(event_type);",
        ]
