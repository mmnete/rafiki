# ==============================================================================
# tests/storage/services/test_booking_storage_service.py
# ==============================================================================
import pytest
import json
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, date
from decimal import Decimal
from app.storage.services.booking_storage_service import (
    BookingStorageService, Booking, BookingPassenger, BookingFlightSegment, BookingTimelineEvent
)

class TestBookingStorageService:
    
    @pytest.fixture
    def mock_storage(self):
        """Mock storage service"""
        storage = Mock()
        storage.conn = MagicMock()
        return storage
    
    @pytest.fixture
    def mock_flight_storage(self):
        """Mock flight storage service"""
        flight_storage = Mock()
        return flight_storage
    
    @pytest.fixture
    def booking_service(self, mock_storage, mock_flight_storage):
        """Create booking service with mocked storage services"""
        return BookingStorageService(mock_storage, mock_flight_storage)

    @pytest.fixture
    def sample_booking(self):
        return Booking(
            id='booking-1', booking_reference='ABC123', primary_user_id=456,
            group_size=1, booking_type='flight', search_id=None,
            selected_flight_offers=[], trip_type='one_way', origin_airport='NYC',
            destination_airport='LAX', departure_date=date(2025, 6, 15),
            return_date=None, base_price=Decimal('200.00'), taxes_and_fees=Decimal('50.00'),
            service_fee=Decimal('10.00'), insurance_fee=Decimal('0.00'),
            total_amount=Decimal('260.00'), currency='USD', booking_status='confirmed',
            payment_status='paid', fulfillment_status='confirmed', amadeus_booking_id=None,
            amadeus_pnr=None, amadeus_response={}, travel_insurance=False,
            special_requests=None, accessibility_requirements=None,
            confirmation_deadline=None, payment_deadline=None, checkin_available_at=None,
            created_at=datetime.now(), updated_at=datetime.now(), confirmed_at=datetime.now(),
            cancelled_at=None
        )
    
    # ====================================================================
    # CORE BOOKING CRUD OPERATIONS TESTS
    # ====================================================================
    
    def test_create_booking_success(self, booking_service, mock_storage):
        """Test successful booking creation"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ['booking-uuid-123']
        
        booking_data = {
            'primary_user_id': 123,
            'trip_type': 'round_trip',
            'origin_airport': 'NYC',
            'destination_airport': 'LAX',
            'departure_date': date(2024, 6, 15),
            'total_amount': Decimal('299.99')
        }
        
        # Act
        result = booking_service.create_booking(**booking_data)
        
        # Assert
        assert result == 'booking-uuid-123'
        assert mock_cursor.execute.call_count == 2  # INSERT booking + INSERT timeline
        
        # Verify booking insert
        first_call = mock_cursor.execute.call_args_list[0][0]
        assert "INSERT INTO bookings" in first_call[0]
        assert "RETURNING id" in first_call[0]
    
    def test_create_booking_generates_reference(self, booking_service, mock_storage):
        """Test that booking reference is generated if not provided"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ['booking-uuid-123']
        
        # Act
        result = booking_service.create_booking(primary_user_id=123)
        
        # Assert
        assert result == 'booking-uuid-123'
        # Verify that booking_reference was added to the query
        insert_call = mock_cursor.execute.call_args_list[0]
        assert 'booking_reference' in insert_call[0][0]
    
    def test_get_booking_success(self, booking_service, mock_storage):
        """Test successful booking retrieval"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Mock booking data row
        booking_row = [
            'booking-uuid-123', 'ABC123DE', 456, 2, 'family', 'search-uuid',
            '[]', 'round_trip', 'NYC', 'LAX', date(2024, 6, 15), date(2024, 6, 22),
            Decimal('250.00'), Decimal('49.99'), Decimal('5.00'), Decimal('0.00'),
            Decimal('304.99'), 'USD', 'confirmed', 'completed', 'pending',
            'amadeus-123', 'ABC123', '{}', False, None, None,
            datetime(2024, 6, 10, 10, 0), datetime(2024, 6, 12, 18, 0),
            datetime(2024, 6, 15, 6, 0), datetime(2024, 6, 1),
            datetime(2024, 6, 1), datetime(2024, 6, 10, 12, 0), None
        ]
        mock_cursor.fetchone.return_value = booking_row
        
        # Act
        result = booking_service.get_booking('booking-uuid-123')
        
        # Assert
        assert result is not None
        assert isinstance(result, Booking)
        assert result.id == 'booking-uuid-123'
        assert result.booking_reference == 'ABC123DE'
        assert result.primary_user_id == 456
        assert result.booking_status == 'confirmed'
        assert result.total_amount == Decimal('304.99')
    
    def test_get_booking_not_found(self, booking_service, mock_storage):
        """Test booking not found"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        
        # Act
        result = booking_service.get_booking('nonexistent-booking')
        
        # Assert
        assert result is None
    
    def test_get_bookings_for_user(self, booking_service, mock_storage):
        """Test getting user bookings"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Mock multiple booking rows
        booking_rows = [
            [
                'booking-1', 'ABC123DE', 456, 1, 'individual', None,
                '[]', 'one_way', 'NYC', 'LAX', date(2024, 6, 15), None,
                Decimal('199.99'), Decimal('39.99'), Decimal('5.00'), Decimal('0.00'),
                Decimal('244.98'), 'USD', 'confirmed', 'completed', 'pending',
                None, None, '{}', False, None, None,
                None, None, None, datetime(2024, 6, 1),
                datetime(2024, 6, 1), datetime(2024, 6, 10), None
            ]
        ]
        mock_cursor.fetchall.return_value = booking_rows
        
        # Act
        result = booking_service.get_bookings_for_user(456)
        
        # Assert
        assert len(result) == 1
        assert isinstance(result[0], Booking)
        assert result[0].primary_user_id == 456
        
        # Verify query parameters
        execute_call = mock_cursor.execute.call_args[0]
        assert "WHERE primary_user_id = %s" in execute_call[0]
        assert "ORDER BY created_at DESC" in execute_call[0]
    
    def test_update_booking_success(self, booking_service, mock_storage):
        """Test successful booking update with arbitrary fields"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 1  # Successful update
        
        update_data = {
            'total_amount': Decimal('350.00'),
            'booking_status': 'confirmed',
            'amadeus_pnr': 'PNR123ABC'
        }
        
        # Act
        result = booking_service.update_booking('booking-123', update_data)
        
        # Assert
        assert result is True
        
        # Verify update query
        execute_call = mock_cursor.execute.call_args[0]
        assert "UPDATE bookings" in execute_call[0]
        assert "updated_at = CURRENT_TIMESTAMP" in execute_call[0]
    
    def test_update_booking_status_success(self, booking_service, mock_storage):
        """Test successful booking status update"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 1  # Successful update
        
        # Act
        result = booking_service.update_booking_status('booking-123', 'confirmed', 456)
        
        # Assert
        assert result is True
        assert mock_cursor.execute.call_count == 2  # UPDATE + timeline INSERT
        
        # Verify update query
        update_call = mock_cursor.execute.call_args_list[0][0]
        assert "UPDATE bookings" in update_call[0]
        assert "booking_status = %s" in update_call[0]
    
    def test_get_booking_details_success(self, booking_service, mock_storage):
        """Test comprehensive booking details retrieval"""
        # Arrange - Mock the actual database calls instead of patching methods
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Mock booking row data
        booking_row = [
            'booking-123', 'ABC123', 456, 1, 'flight', None,
            '[]', 'one_way', 'NYC', 'LAX', date(2024, 6, 15), None,
            Decimal('200.00'), Decimal('50.00'), Decimal('10.00'), Decimal('0.00'),
            Decimal('260.00'), 'USD', 'confirmed', 'paid', 'confirmed',
            None, 'PNR123', '{}', False, None, None,
            None, None, None, datetime.now(), datetime.now(), None, None
        ]
        
        passenger_rows = [['passenger-1', 'booking-123', None, 1, 'adult', True,
                        'John', 'Doe', 'P123456', None, None, '{}', 'pending',
                        None, False, None, datetime.now(), datetime.now()]]
        
        segment_rows = [['segment-1', 'booking-123', 'offer-1', 1, 'outbound',
                        'AA', 'American Airlines', 'AA1234', 'Boeing 737',
                        'NYC', 'T1', datetime(2024, 6, 15, 8, 0),
                        'LAX', 'T2', datetime(2024, 6, 15, 11, 30),
                        210, 2475, 'scheduled', '{}', None, None, 0, None,
                        datetime.now(), datetime.now()]]
        
        timeline_rows = [[1, 'booking-123', 'booking_created', 'Booking created',
                        '{}', 456, False, datetime.now()]]
        
        # Set up fetchone/fetchall calls in order
        mock_cursor.fetchone.return_value = booking_row
        mock_cursor.fetchall.side_effect = [passenger_rows, segment_rows, timeline_rows]
        
        # Act
        result = booking_service.get_booking_details('booking-123')
        
        # Assert
        assert result['success'] is True
        assert result['booking_id'] == 'booking-123'
        assert result['pnr'] == 'PNR123'
        assert len(result['passengers']) == 1
        assert len(result['flight_segments']) == 1
        assert len(result['timeline']) == 1

    def test_get_user_bookings_with_filters(self, booking_service, mock_storage):
        """Test getting user bookings with filtering"""
        # Arrange - Mock the database directly instead of patching the method
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Mock booking row data
        booking_rows = [
            [
                'booking-1', 'ABC123', 456, 1, 'flight', None,
                '[]', 'one_way', 'NYC', 'LAX', date(2025, 6, 15), None,
                Decimal('200.00'), Decimal('50.00'), Decimal('10.00'), Decimal('0.00'),
                Decimal('260.00'), 'USD', 'confirmed', 'paid', 'confirmed',
                None, None, '{}', False, None, None,
                None, None, None, datetime.now(), datetime.now(), None, None
            ]
        ]
        mock_cursor.fetchall.return_value = booking_rows
        
        # Act
        result = booking_service.get_user_bookings(456, status='confirmed', include_past=True)
        
        # Assert
        assert result['success'] is True
        assert len(result['bookings']) == 1
        assert result['bookings'][0]['status'] == 'confirmed'
    
    # ====================================================================
    # PASSENGER MANAGEMENT TESTS
    # ====================================================================
    
    def test_add_passenger_to_booking_success(self, booking_service, mock_storage):
        """Test adding passenger to booking"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [
            [1],  # Next passenger sequence
            ['passenger-uuid-123']  # Inserted passenger ID
        ]
        
        passenger_data = {
            'passenger_type': 'adult',
            'is_primary_passenger': True,
            'booking_first_name': 'John',
            'booking_last_name': 'Doe'
        }
        
        # Act
        result = booking_service.add_passenger_to_booking('booking-123', **passenger_data)
        
        # Assert
        assert result == 'passenger-uuid-123'
        assert mock_cursor.execute.call_count == 3  # SELECT sequence + INSERT passenger + timeline
    
    def test_get_booking_passengers(self, booking_service, mock_storage):
        """Test getting booking passengers"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        passenger_rows = [
            [
                'passenger-1', 'booking-123', 'profile-456', 1, 'adult', True,
                'John', 'Doe', 'P123456', 'window', 'vegetarian', '{}',
                'assigned', None, False, None, datetime.now(), datetime.now()
            ]
        ]
        mock_cursor.fetchall.return_value = passenger_rows
        
        # Act
        result = booking_service.get_booking_passengers('booking-123')
        
        # Assert
        assert len(result) == 1
        assert isinstance(result[0], BookingPassenger)
        assert result[0].booking_id == 'booking-123'
        assert result[0].passenger_sequence == 1
        assert result[0].is_primary_passenger is True
        assert result[0].booking_first_name == 'John'
    
    def test_update_passenger_details_success(self, booking_service, mock_storage):
        """Test updating passenger details"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 1  # Successful update
        
        update_data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'passport_number': 'P987654'
        }
        
        # Act
        result = booking_service.update_passenger_details('booking-123', 'passenger-1', update_data)
        
        # Assert
        assert result['success'] is True
        assert result['message'] == 'Passenger updated successfully'
        
        # Verify update query uses field mapping
        execute_call = mock_cursor.execute.call_args[0]
        assert "booking_first_name = %s" in execute_call[0]
        assert "booking_last_name = %s" in execute_call[0]
        assert "booking_document_number = %s" in execute_call[0]
    
    def test_search_passenger_history_success(self, booking_service, mock_storage):
        """Test searching passenger history"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        history_rows = [
            ['John', 'Doe', 'P123456', 'adult'],
            ['John', 'Smith', 'P789012', 'adult']
        ]
        mock_cursor.fetchall.return_value = history_rows
        
        # Act
        result = booking_service.search_passenger_history(456, 'John Doe')
        
        # Assert
        assert result['success'] is True
        assert len(result['passenger_history']) == 2
        assert result['passenger_history'][0]['first_name'] == 'John'
        assert result['passenger_history'][0]['last_name'] == 'Doe'
        
        # Verify two-name search query
        execute_call = mock_cursor.execute.call_args[0]
        assert "booking_first_name ILIKE %s" in execute_call[0]
        assert "booking_last_name ILIKE %s" in execute_call[0]
    
    def test_search_passenger_history_single_name(self, booking_service, mock_storage):
        """Test searching passenger history with single name"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        
        # Act
        result = booking_service.search_passenger_history(456, 'John')
        
        # Assert
        assert result['success'] is True
        
        # Verify single-name search query - check for the pattern with flexibility for whitespace
        execute_call = mock_cursor.execute.call_args[0]
        query = execute_call[0]
        assert "bp.booking_first_name ILIKE %s OR bp.booking_last_name ILIKE %s" in query

    # ====================================================================
    # PASSENGER PROFILE INTEGRATION TESTS
    # ====================================================================

    def test_create_or_find_passenger_profile_new(self, booking_service, mock_storage):
        """Test creating new passenger profile"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [
            None,  # No existing profile found
            ['profile-uuid-456'],  # New profile created
        ]
        
        passenger_data = {
            'first_name': 'John',
            'last_name': 'Doe', 
            'date_of_birth': '1990-01-01',
            'gender': 'male',
            'email': 'john@example.com',
            'phone': '+1234567890',
            'passport_number': 'A12345678',
            'document_expiry': '2030-12-31',
            'nationality': 'US',
            'is_primary': True
        }
        
        # Act
        result = booking_service._create_or_find_passenger_profile(123, passenger_data)
        
        # Assert
        assert result == 'profile-uuid-456'
        assert mock_cursor.execute.call_count == 3  # Search + Insert profile + Insert connection

    def test_create_or_find_passenger_profile_existing(self, booking_service, mock_storage):
        """Test finding existing passenger profile"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ['existing-profile-123']
        
        passenger_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01'
        }
        
        # Act
        result = booking_service._create_or_find_passenger_profile(123, passenger_data)
        
        # Assert
        assert result == 'existing-profile-123'
        assert mock_cursor.execute.call_count == 1  # Only search query

    def test_get_complete_passenger_data_with_profiles(self, booking_service, mock_storage):
        """Test getting complete passenger data including profile information"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Corrected data to match the SQL query's SELECT order
        passenger_profile_rows = [
            [
                'passenger-1',           # bp.id (index 0)
                'John',                  # bp.booking_first_name (index 1)
                'Doe',                   # bp.booking_last_name (index 2)
                'adult',                 # bp.passenger_type (index 3)
                True,                    # bp.is_primary_passenger (index 4)
                'P123456',               # bp.booking_document_number (index 5)
                'window',                # bp.booking_seat_preference (index 6)
                'vegetarian',            # bp.booking_meal_preference (index 7)
                date(1990, 1, 1),        # pp.date_of_birth (index 8)
                'male',                  # pp.gender (index 9)
                'john@email.com',        # pp.email (index 10)
                '+1234567890',           # pp.phone_number (index 11)
                'US',                    # pp.nationality (index 12)
                'A12345678',             # pp.primary_document_number (index 13)
                date(2030, 12, 31),      # pp.primary_document_expiry (index 14)
                'passport'               # pp.primary_document_type (index 15)
            ]
        ]
        
        mock_cursor.fetchall.return_value = passenger_profile_rows
        
        # Act
        result = booking_service._get_complete_passenger_data('booking-123')
        
        # Assert
        assert len(result) == 1
        passenger = result[0]
        assert passenger['first_name'] == 'John'
        assert passenger['last_name'] == 'Doe'
        assert passenger['date_of_birth'] == date(1990, 1, 1)
        assert passenger['gender'] == 'male'
        assert passenger['email'] == 'john@email.com'
        assert passenger['nationality'] == 'US'
        assert passenger['primary_document_number'] == 'A12345678'

    def test_get_complete_passenger_data_no_profiles(self, booking_service, mock_storage):
        """Test getting passenger data when no profiles are linked"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Corrected data to match the SQL query's SELECT order
        passenger_rows = [
            [
                'passenger-1',         # bp.id (index 0)
                'John',                # bp.booking_first_name (index 1)
                'Doe',                 # bp.booking_last_name (index 2)
                'adult',               # bp.passenger_type (index 3)
                True,                  # bp.is_primary_passenger (index 4)
                'P123456',             # bp.booking_document_number (index 5)
                'window',              # bp.booking_seat_preference (index 6)
                'vegetarian',          # bp.booking_meal_preference (index 7)
                # Profile data (all None)
                None,                  # pp.date_of_birth (index 8)
                None,                  # pp.gender (index 9)
                None,                  # pp.email (index 10)
                None,                  # pp.phone_number (index 11)
                None,                  # pp.nationality (index 12)
                None,                  # pp.primary_document_number (index 13)
                None,                  # pp.primary_document_expiry (index 14)
                None                   # pp.primary_document_type (index 15)
            ]
        ]

        mock_cursor.fetchall.return_value = passenger_rows

        # Act
        result = booking_service._get_complete_passenger_data('booking-123')

        # Assert
        assert len(result) == 1
        passenger = result[0]
        assert passenger['first_name'] == 'John'
        assert passenger['document_number'] == 'P123456'  # Falls back to booking document
        assert passenger['date_of_birth'] is None
        assert passenger['primary_document_number'] is None

    def test_validate_passengers_for_amadeus_complete(self, booking_service):
        """Test passenger validation with complete data"""
        # Arrange
        passengers = [
            {
                'first_name': 'John',
                'last_name': 'Doe',
                'date_of_birth': date(1990, 1, 1),
                'nationality': 'US',
                'primary_document_number': 'A12345678'
            }
        ]
        
        # Act
        errors = booking_service._validate_passengers_for_amadeus(passengers)
        
        # Assert
        assert errors == []

    def test_validate_passengers_for_amadeus_missing_data(self, booking_service):
        """Test passenger validation with missing required data"""
        # Arrange
        passengers = [
            {
                'first_name': 'John',
                'last_name': None,  # Missing
                'date_of_birth': None,  # Missing
                'nationality': 'US',
                'primary_document_number': None,  # Missing
                'document_number': None  # Also missing
            }
        ]
        
        # Act
        errors = booking_service._validate_passengers_for_amadeus(passengers)
        
        # Assert
        assert len(errors) == 3
        assert any('Missing last name' in error for error in errors)
        assert any('Missing date of birth' in error for error in errors)
        assert any('Missing passport/document number' in error for error in errors)

    def test_validate_passengers_for_amadeus_multiple_passengers(self, booking_service):
        """Test validation with multiple passengers having different issues"""
        # Arrange
        passengers = [
            {
                'first_name': 'John',
                'last_name': 'Doe',
                'date_of_birth': date(1990, 1, 1),
                'nationality': 'US',
                'primary_document_number': 'A12345678'
            },
            {
                'first_name': None,  # Missing
                'last_name': 'Smith',
                'date_of_birth': date(1985, 5, 15),
                'nationality': None,  # Missing (recommended)
                'document_number': 'B98765432'
            }
        ]
        
        # Act
        errors = booking_service._validate_passengers_for_amadeus(passengers)
        
        # Assert
        assert len(errors) == 2
        # The validation method shows None when first_name is None
        assert 'Passenger 2 (None): Missing first name' in errors
        assert 'Passenger 2 (None): Missing nationality (recommended)' in errors

    # ====================================================================
    # UPDATED HANDLE ADD PASSENGER TESTS
    # ====================================================================

    def test_handle_add_passenger_with_profile_creation(self, booking_service, mock_storage):
        """Test adding passenger with profile creation"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [
            None,  # No existing profile
            ['profile-456'],  # New profile created
            [1],  # Next passenger sequence
            ['passenger-123']  # Inserted passenger
        ]
        
        # Act
        result = booking_service._handle_add_passenger(
            user_id=456,
            booking_id='booking-123',
            first_name='John',
            last_name='Doe',
            date_of_birth='1990-01-01',
            passport_number='A12345678',
            nationality='US',
            gender='male',
            email='john@email.com',
            phone='+1234567890'
        )
        
        # Assert
        assert result['success'] is True
        assert result['passenger_id'] == 'passenger-123'
        assert result['passenger_profile_id'] == 'profile-456'

    def test_handle_add_passenger_with_existing_profile(self, booking_service, mock_storage):
        """Test adding passenger using existing profile"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [
            ['existing-profile-789'],  # Found existing profile
            [1],  # Next passenger sequence
            ['passenger-123']  # Inserted passenger
        ]
        
        # Act
        result = booking_service._handle_add_passenger(
            user_id=456,
            booking_id='booking-123',
            first_name='Jane',
            last_name='Smith',
            date_of_birth='1985-05-15'
        )
        
        # Assert
        assert result['success'] is True
        assert result['passenger_profile_id'] == 'existing-profile-789'

    # ====================================================================
    # UPDATED FINALIZE BOOKING TESTS
    # ====================================================================

    @patch('app.services.api.flights.amadeus_scraper.AmadeusFlightScraper')
    @patch('app.storage.services.booking_storage_service.BookingStorageService.update_booking') # 1. Add this patch
    def test_handle_finalize_booking_success(self, mock_update_booking, mock_amadeus_class, booking_service, mock_storage, mock_flight_storage, sample_booking):
        """Test successful booking finalization with Amadeus integration"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Mock update_booking to return True
        mock_update_booking.return_value = True 

        # Mock booking retrieval
        booking_row = [
            'booking-123', 'ABC123', 456, 1, 'flight', 'search-456',
            json.dumps(["offer-1"]), 'one_way', 'NYC', 'LAX', date(2024, 6, 15), None,
            Decimal('200.00'), Decimal('50.00'), Decimal('10.00'), Decimal('0.00'),
            Decimal('260.00'), 'USD', 'draft', 'pending', 'pending',
            None, None, '{}', False, None, None, None, None, None,
            datetime.now(), datetime.now(), None, None
        ]

        # Mock the various database cursor calls
        mock_cursor.fetchone.side_effect = [booking_row, booking_row]
        mock_cursor.fetchall.side_effect = [[], [], []]

        # Use a single patch block for all method mocks
        with patch.object(booking_service, '_get_complete_passenger_data') as mock_passengers, \
                patch.object(booking_service, '_validate_passengers_for_amadeus') as mock_validate_passengers, \
                patch.object(booking_service, 'add_timeline_event') as mock_add_timeline_event:
            
            # Mock the return value for the passenger data method
            mock_passengers.return_value = [
                {
                    'passenger_id': 'passenger-1',
                    'first_name': 'John',
                    'last_name': 'Doe',
                    'date_of_birth': date(1990, 1, 1),
                    'gender': 'male',
                    'email': 'john@email.com',
                    'phone_number': '+1234567890',
                    'nationality': 'US',
                    'primary_document_number': 'A12345678',
                    'primary_document_expiry': date(2030, 12, 31),
                    'primary_document_type': 'passport'
                }
            ]
            
            # CRITICAL FIX: Mock the validation method to return an empty list
            mock_validate_passengers.return_value = []

            # Mock flight storage service
            mock_flight_storage.get_flight_search.return_value = Mock()
            mock_flight_storage.get_search_offers.return_value = [
                Mock(flight_offer_id='offer-1', complete_offer_data={'test': 'data'})
            ]
            
            # Mock Amadeus scraper
            mock_amadeus = mock_amadeus_class.return_value
            mock_amadeus.price_flight_offers.return_value = {
                'data': {
                    'flightOffers': [{
                        'price': {'grandTotal': '299.99', 'base': '250.00', 'currency': 'USD'}
                    }]
                }
            }
            mock_amadeus.create_flight_booking.return_value = {
                'data': {
                    'id': 'amadeus-booking-123',
                    'associatedRecords': [{'reference': 'PNR123ABC'}],
                    'flightOffers': [{
                        'price': {'grandTotal': '299.99', 'base': '250.00', 'currency': 'USD'}
                    }]
                }
            }
            
            # Act
            result = booking_service._handle_finalize_booking(user_id=456, booking_id='booking-123')
            
            print(result)
            
            # Assert
            assert result['success'] is True
            assert result['pnr'] == 'PNR123ABC'
            assert result['final_price'] == 299.99
            assert mock_add_timeline_event.called # Optional: Ensure timeline event was added
    
    def test_handle_finalize_booking_validation_errors(self, booking_service, mock_storage, mock_flight_storage):
        """Test finalize booking with passenger validation errors"""
        # Arrange - Mock the booking details properly
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        booking_row = [
            'booking-123', 'ABC123', 456, 1, 'flight', 'search-456',
            '["offer-1"]', 'one_way', 'NYC', 'LAX', date(2024, 6, 15), None,
            Decimal('200.00'), Decimal('50.00'), Decimal('10.00'), Decimal('0.00'),
            Decimal('260.00'), 'USD', 'draft', 'pending', 'pending',
            None, None, '{}', False, None, None, None, None, None,
            datetime.now(), datetime.now(), None, None
        ]
        
        mock_cursor.fetchone.return_value = booking_row
        mock_cursor.fetchall.side_effect = [[], [], []]
        
        # Mock incomplete passenger data
        with patch.object(booking_service, '_get_complete_passenger_data') as mock_passengers:
            mock_passengers.return_value = [
                {
                    'first_name': 'John',
                    'last_name': None,  # Missing required field
                    'date_of_birth': None  # Missing required field
                }
            ]
            
            # Act
            result = booking_service._handle_finalize_booking(user_id=456, booking_id='booking-123')
            
            # Assert
            assert 'error' in result
            assert 'Passenger data incomplete' in result['error']

    # ====================================================================
    # FLIGHT SEGMENT MANAGEMENT TESTS
    # ====================================================================
    
    def test_add_flight_segment_success(self, booking_service, mock_storage):
        """Test adding flight segment to booking"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [
            [1],  # Next segment sequence
            ['segment-uuid-123']  # Inserted segment ID
        ]
        
        segment_data = {
            'flight_offer_id': 'offer-123',
            'segment_type': 'outbound',
            'airline_code': 'AA',
            'flight_number': 'AA1234',
            'departure_airport': 'NYC',
            'arrival_airport': 'LAX',
            'departure_time': datetime(2024, 6, 15, 8, 0),
            'arrival_time': datetime(2024, 6, 15, 11, 30),
            'flight_status': 'scheduled'
        }
        
        # Act
        result = booking_service.add_flight_segment('booking-123', **segment_data)
        
        # Assert
        assert result == 'segment-uuid-123'
        assert mock_cursor.execute.call_count == 2  # SELECT sequence + INSERT segment
    
    def test_get_booking_flight_segments(self, booking_service, mock_storage):
        """Test getting booking flight segments"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        segment_rows = [
            [
                'segment-1', 'booking-123', 'offer-456', 1, 'outbound',
                'AA', 'American Airlines', 'AA1234', 'Boeing 737',
                'NYC', 'T1', datetime(2024, 6, 15, 8, 0),
                'LAX', 'T2', datetime(2024, 6, 15, 11, 30),
                210, 2475, 'scheduled', '{}', None, None, 0, 'A12',
                datetime.now(), datetime.now()
            ]
        ]
        mock_cursor.fetchall.return_value = segment_rows
        
        # Act
        result = booking_service.get_booking_flight_segments('booking-123')
        
        # Assert
        assert len(result) == 1
        assert isinstance(result[0], BookingFlightSegment)
        assert result[0].booking_id == 'booking-123'
        assert result[0].airline_code == 'AA'
        assert result[0].flight_number == 'AA1234'
        assert result[0].duration_minutes == 210
    
    # ====================================================================
    # TIMELINE EVENT MANAGEMENT TESTS
    # ====================================================================
    
    def test_add_timeline_event_success(self, booking_service, mock_storage):
        """Test adding timeline event"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Act
        result = booking_service.add_timeline_event(
            booking_id='booking-123',
            event_type='payment_completed',
            event_description='Payment processed successfully',
            event_data={'amount': 299.99, 'payment_method': 'credit_card'},
            triggered_by_user_id=456
        )
        
        # Assert
        assert result is True
        mock_cursor.execute.assert_called_once()
        
        execute_call = mock_cursor.execute.call_args[0]
        assert "INSERT INTO booking_timeline" in execute_call[0]
        
        # Verify parameters
        params = mock_cursor.execute.call_args[0][1]
        assert params[0] == 'booking-123'
        assert params[1] == 'payment_completed'
        assert params[4] == 456  # triggered_by_user_id
    
    def test_get_booking_timeline(self, booking_service, mock_storage):
        """Test getting booking timeline"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        timeline_rows = [
            [
                1, 'booking-123', 'booking_created', 'Booking created',
                '{"initial": true}', 456, False, datetime.now()
            ],
            [
                2, 'booking-123', 'payment_completed', 'Payment processed',
                '{"amount": 299.99}', 456, False, datetime.now()
            ]
        ]
        mock_cursor.fetchall.return_value = timeline_rows
        
        # Act
        result = booking_service.get_booking_timeline('booking-123')
        
        # Assert
        assert len(result) == 2
        assert isinstance(result[0], BookingTimelineEvent)
        assert result[0].event_type == 'booking_created'
        assert result[1].event_type == 'payment_completed'
        
        # Verify ordering (DESC by created_at)
        execute_call = mock_cursor.execute.call_args[0]
        assert "ORDER BY created_at DESC" in execute_call[0]
    
    # ====================================================================
    # TOOL OPERATION HANDLER TESTS
    # ====================================================================
    
    @patch('app.storage.services.booking_storage_service.implemented_redis_storage_manager')
    def test_handle_booking_operation_create(self, mock_redis, booking_service, mock_storage):
        """Test handle_booking_operation for create action"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ['booking-123']
        
        mock_redis.get_data.return_value = {
            'trip_type': 'one_way',
            'origin': 'NYC',
            'destination': 'LAX',
            'departure_date': '2024-06-15'
        }
        
        # Act
        result = booking_service.handle_booking_operation(
            user_id=456,
            action='create',
            search_id='search-123',
            flight_offer_ids=['offer-1'],
            passenger_count=1
        )
        
        # Assert
        assert result['success'] is True
        assert result['booking_id'] == 'booking-123'
        assert result['status'] == 'draft'
    
    def test_handle_booking_operation_add_passenger(self, booking_service, mock_storage):
        """Test handle_booking_operation for add passenger action"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [
            None,  # No existing profile
            ['profile-456'],  # New profile created
            [1], ['passenger-123']  # Passenger sequence and insertion
        ]
        
        # Act
        result = booking_service.handle_booking_operation(
            user_id=456,
            action='add',
            booking_id='booking-123',
            first_name='John',
            last_name='Doe',
            date_of_birth='1990-01-01',
            passenger_type='adult',
            is_primary=True
        )
        
        # Assert
        assert result['success'] is True
        assert result['passenger_id'] == 'passenger-123'
    
    def test_handle_booking_operation_unknown_action(self, booking_service):
        """Test handle_booking_operation with unknown action"""
        # Act
        result = booking_service.handle_booking_operation(
            user_id=456,
            action='unknown_action'
        )
        
        # Assert
        assert 'error' in result
        assert 'Unknown operation' in result['error']
    
    # ====================================================================
    # UTILITY METHODS TESTS
    # ====================================================================
    
    def test_generate_booking_reference_format(self, booking_service):
        """Test booking reference generation format"""
        # Act
        reference = booking_service._generate_booking_reference()
        
        # Assert
        assert len(reference) == 8  # 3 letters + 3 numbers + 2 letters
        assert reference[:3].isalpha()  # First 3 are letters
        assert reference[3:6].isdigit()  # Next 3 are digits
        assert reference[6:].isalpha()  # Last 2 are letters
        assert reference.isupper()  # All uppercase
    
    def test_generate_booking_reference_uniqueness(self, booking_service):
        """Test that booking references are unique"""
        # Act
        references = [booking_service._generate_booking_reference() for _ in range(100)]
        
        # Assert
        assert len(set(references)) == 100  # All should be unique
    
    # ====================================================================
    # ERROR HANDLING TESTS
    # ====================================================================
    
    def test_exception_handling(self, booking_service, mock_storage):
        """Test exception handling in various methods"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Database error")
        
        # Act & Assert
        assert booking_service.create_booking(primary_user_id=123) is None
        assert booking_service.get_booking('booking-123') is None
        assert booking_service.get_bookings_for_user(123) == []
        assert booking_service.update_booking('booking-123', {'status': 'test'}) is False
        assert booking_service.update_booking_status('booking-123', 'confirmed') is False
        assert booking_service.add_passenger_to_booking('booking-123', passenger_type='adult') is None
        assert booking_service.get_booking_passengers('booking-123') == []
        assert booking_service.add_flight_segment('booking-123', flight_offer_id='offer-123') is None
        assert booking_service.get_booking_flight_segments('booking-123') == []
        assert booking_service.add_timeline_event('booking-123', 'test_event') is False
        assert booking_service.get_booking_timeline('booking-123') == []
    
    def test_no_connection_handling(self, booking_service):
        """Test handling when no database connection"""
        # Arrange
        booking_service.storage.conn = None
        
        # Act & Assert
        assert booking_service.create_booking(primary_user_id=123) is None
        assert booking_service.get_booking('booking-123') is None
        assert booking_service.get_bookings_for_user(123) == []
        assert booking_service.update_booking('booking-123', {'status': 'test'}) is False
        assert booking_service.update_booking_status('booking-123', 'confirmed') is False
        assert booking_service.add_passenger_to_booking('booking-123') is None
        assert booking_service.get_booking_passengers('booking-123') == []
        assert booking_service.add_flight_segment('booking-123') is None
        assert booking_service.get_booking_flight_segments('booking-123') == []
        assert booking_service.add_timeline_event('booking-123', 'test') is False
        assert booking_service.get_booking_timeline('booking-123') == []
        
        # Test new methods return appropriate error responses
        assert booking_service.get_booking_details('booking-123')['error'] == 'Booking not found'
        assert booking_service.get_user_bookings(123)['success'] is True  # Should still work with empty list

        update_result = booking_service.update_passenger_details('booking-123', 'passenger-1', {})
        assert update_result['error'] == 'Database not available'
        
        search_result = booking_service.search_passenger_history(123, 'John')
        assert search_result['error'] == 'Database not available'
    
    # ====================================================================
    # JSON FIELD HANDLING TESTS
    # ====================================================================
    
    def test_json_field_handling(self, booking_service, mock_storage):
        """Test proper JSON field serialization/deserialization"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Test passenger with assigned_seats JSON field
        mock_cursor.fetchone.side_effect = [[1], ['passenger-123']]
        
        passenger_data = {
            'passenger_type': 'adult',
            'assigned_seats': {'segment_1': '12A', 'segment_2': '15C'}
        }
        
        # Act
        result = booking_service.add_passenger_to_booking('booking-123', **passenger_data)
        
        # Assert
        assert result == 'passenger-123'
        
        # Verify JSON serialization in the insert call
        insert_call = mock_cursor.execute.call_args_list[1]  # Second call is the INSERT
        insert_values = insert_call[0][1]
        
        # Find the assigned_seats value in the parameters
        for value in insert_values:
            if isinstance(value, str) and 'segment_1' in value:
                # Should be valid JSON
                parsed = json.loads(value)
                assert parsed['segment_1'] == '12A'
                break
    
    def test_json_field_handling_flight_segments(self, booking_service, mock_storage):
        """Test JSON field handling in flight segments"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [[1], ['segment-123']]
        
        segment_data = {
            'flight_offer_id': 'offer-123',
            'passenger_assignments': {'passenger_1': '12A', 'passenger_2': '12B'}
        }
        
        # Act
        result = booking_service.add_flight_segment('booking-123', **segment_data)
        
        # Assert
        assert result == 'segment-123'
        
        # Verify JSON serialization
        insert_call = mock_cursor.execute.call_args_list[1]
        insert_values = insert_call[0][1]
        
        # Find the passenger_assignments value
        for value in insert_values:
            if isinstance(value, str) and 'passenger_1' in value:
                parsed = json.loads(value)
                assert parsed['passenger_1'] == '12A'
                break
    
    def test_update_booking_json_fields(self, booking_service, mock_storage):
        """Test updating booking with JSON fields"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 1
        
        update_data = {
            'amadeus_response': {'pnr': 'ABC123', 'status': 'confirmed'},
            'selected_flight_offers': [{'id': 'offer-1', 'price': 299.99}],
            'booking_status': 'confirmed'
        }
        
        # Act
        result = booking_service.update_booking('booking-123', update_data)
        
        # Assert
        assert result is True
        
        # Verify JSON serialization in update
        execute_call = mock_cursor.execute.call_args[0]
        params = execute_call[1]
        
        # Check that JSON fields were serialized
        json_found = False
        for param in params:
            if isinstance(param, str) and 'pnr' in param:
                parsed = json.loads(param)
                assert parsed['pnr'] == 'ABC123'
                json_found = True
                break
        assert json_found
    
    # ====================================================================
    # SEQUENCE AUTO-INCREMENT TESTS
    # ====================================================================
    
    def test_passenger_sequence_auto_increment(self, booking_service, mock_storage):
        """Test passenger sequence auto-increments correctly"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [
            [3],  # Next sequence should be 3 (meaning 2 passengers already exist)
            ['passenger-123']
        ]
        
        # Act
        result = booking_service.add_passenger_to_booking(
            'booking-123', 
            passenger_type='adult'
        )
        
        # Assert
        assert result == 'passenger-123'
        
        # Verify the sequence query
        sequence_call = mock_cursor.execute.call_args_list[0]
        assert "MAX(passenger_sequence)" in sequence_call[0][0]
        assert "+ 1" in sequence_call[0][0]
    
    def test_flight_segment_sequence_auto_increment(self, booking_service, mock_storage):
        """Test flight segment sequence auto-increments correctly"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [
            [2],  # Next sequence should be 2
            ['segment-123']
        ]
        
        # Act
        result = booking_service.add_flight_segment(
            'booking-123',
            flight_offer_id='offer-456',
            airline_code='AA',
            flight_number='AA1234',
            departure_airport='NYC',
            arrival_airport='LAX',
            departure_time=datetime(2024, 6, 15, 8, 0),
            arrival_time=datetime(2024, 6, 15, 11, 30)
        )
        
        # Assert
        assert result == 'segment-123'
        
        # Verify the sequence query
        sequence_call = mock_cursor.execute.call_args_list[0]
        assert "MAX(segment_sequence)" in sequence_call[0][0]
        assert "booking_flight_segments" in sequence_call[0][0]
    
    # ====================================================================
    # INTEGRATION TESTS FOR NEW STRUCTURE
    # ====================================================================
    
    def test_booking_workflow_integration(self, booking_service, mock_storage):
        """Test complete booking workflow using the reorganized methods"""
        # This test verifies that all the reorganized sections work together
        
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Mock responses for the workflow
        mock_cursor.fetchone.side_effect = [
            ['booking-123'],  # create_booking
            [1], ['passenger-456'],  # add_passenger_to_booking
            [1], ['segment-789'],  # add_flight_segment  
        ]
        
        # Act - Step 1: Create booking (Core CRUD section)
        booking_id = booking_service.create_booking(
            primary_user_id=123,
            trip_type='one_way',
            total_amount=Decimal('299.99')
        )
        
        # Act - Step 2: Add passenger (Passenger Management section)
        passenger_id = booking_service.add_passenger_to_booking(
            booking_id,
            passenger_type='adult',
            booking_first_name='John',
            booking_last_name='Doe'
        )
        
        # Act - Step 3: Add flight segment (Flight Segment Management section) 
        segment_id = booking_service.add_flight_segment(
            booking_id,
            flight_offer_id='offer-123',
            airline_code='AA',
            flight_number='AA1234'
        )
        
        # Act - Step 4: Add timeline event (Timeline Management section)
        timeline_success = booking_service.add_timeline_event(
            booking_id,
            event_type='booking_completed',
            event_description='Booking workflow completed'
        )
        
        # Assert
        assert booking_id == 'booking-123'
        assert passenger_id == 'passenger-456' 
        assert segment_id == 'segment-789'
        assert timeline_success is True
        
        # Verify all sections were called - updated count includes automatic timeline events
        assert mock_cursor.execute.call_count == 8  # create(2) + add_passenger(3) + add_segment(2) + timeline(1)
    
    def test_error_propagation_across_sections(self, booking_service, mock_storage):
        """Test that errors propagate correctly across the reorganized sections"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Simulate database error
        mock_cursor.execute.side_effect = Exception("Connection lost")
        
        # Act & Assert - Test each section handles errors properly
        
        # Core CRUD operations
        assert booking_service.create_booking(primary_user_id=123) is None
        assert booking_service.get_booking('booking-123') is None
        assert booking_service.update_booking('booking-123', {'status': 'test'}) is False
        
        # Passenger Management
        assert booking_service.add_passenger_to_booking('booking-123') is None
        assert booking_service.get_booking_passengers('booking-123') == []
        
        # Flight Segment Management  
        assert booking_service.add_flight_segment('booking-123') is None
        assert booking_service.get_booking_flight_segments('booking-123') == []
        
        # Timeline Management
        assert booking_service.add_timeline_event('booking-123', 'test') is False
        assert booking_service.get_booking_timeline('booking-123') == []