# ==============================================================================
# tests/storage/services/test_passenger_storage_service.py
# ==============================================================================
import pytest
import json
from unittest.mock import Mock, MagicMock
from datetime import datetime, date
from app.storage.services.passenger_storage_service import (
    PassengerStorageService, PassengerProfile, PassengerDocument, UserPassengerConnection
)

class TestPassengerStorageService:
    
    @pytest.fixture
    def mock_storage(self):
        """Mock storage service"""
        storage = Mock()
        storage.conn = MagicMock()
        return storage
    
    @pytest.fixture
    def passenger_service(self, mock_storage):
        """Create passenger service with mocked storage"""
        return PassengerStorageService(mock_storage)
    
    def test_create_passenger_success(self, passenger_service, mock_storage):
        """Test successful passenger creation"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ['passenger-uuid-123']
        
        passenger_data = {
            'middle_name': 'Michael',
            'gender': 'male',
            'email': 'john.doe@example.com',
            'seat_preference': 'window',
            'meal_preference': 'vegetarian',
            'airline_loyalties': {'AA': '123456789'},
            'created_by_user_id': 456
        }
        
        # Act
        result = passenger_service.create_passenger(
            first_name='John',
            last_name='Doe',
            date_of_birth=date(1990, 1, 15),
            **passenger_data
        )
        
        # Assert
        assert result == 'passenger-uuid-123'
        mock_cursor.execute.assert_called_once()
        
        execute_call = mock_cursor.execute.call_args[0]
        assert "INSERT INTO passenger_profiles" in execute_call[0]
        assert "RETURNING id" in execute_call[0]
    
    def test_get_passenger_success(self, passenger_service, mock_storage):
        """Test successful passenger retrieval"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        passenger_row = [
            'passenger-123', 'Jane', 'Marie', 'Smith', date(1985, 5, 20),
            'female', 'Ms.', 'jane@example.com', '+1234567890', 'passport',
            'P123456789', date(2030, 12, 31), 'USA', 'USA', 'aisle',
            'kosher', 'wheelchair assistance', None, 'no dairy',
            '{"UA": "987654321"}', 'ABC123', 'DEF456', 789,
            True, 'government_id', datetime.now(), datetime.now(), None
        ]
        mock_cursor.fetchone.return_value = passenger_row
        
        # Act
        result = passenger_service.get_passenger('passenger-123')
        
        # Assert
        assert result is not None
        assert isinstance(result, PassengerProfile)
        assert result.id == 'passenger-123'
        assert result.first_name == 'Jane'
        assert result.middle_name == 'Marie'
        assert result.seat_preference == 'aisle'
        assert result.airline_loyalties == {'UA': '987654321'}
        assert result.is_verified is True
    
    def test_update_passenger_success(self, passenger_service, mock_storage):
        """Test successful passenger update"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 1
        
        update_data = {
            'email': 'newemail@example.com',
            'seat_preference': 'window',
            'airline_loyalties': {'AA': '111222333', 'UA': '444555666'}
        }
        
        # Act
        result = passenger_service.update_passenger('passenger-123', **update_data)
        
        # Assert
        assert result is True
        mock_cursor.execute.assert_called_once()
        
        execute_call = mock_cursor.execute.call_args[0]
        assert "UPDATE passenger_profiles" in execute_call[0]
        assert "updated_at = CURRENT_TIMESTAMP" in execute_call[0]
    
    def test_find_passengers_by_details(self, passenger_service, mock_storage):
        """Test finding passengers by personal details"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        passenger_rows = [
            [
                'passenger-1', 'John', None, 'Doe', date(1990, 1, 15),
                'male', None, 'john@example.com', None, None,
                None, None, None, None, 'any',
                None, None, None, None, '{}', None, None, None,
                False, None, datetime.now(), datetime.now(), None
            ]
        ]
        mock_cursor.fetchall.return_value = passenger_rows
        
        # Act
        result = passenger_service.find_passengers_by_details(
            first_name='John',
            last_name='Doe',
            date_of_birth=date(1990, 1, 15),
            email='john@example.com'
        )
        
        # Assert
        assert len(result) == 1
        assert isinstance(result[0], PassengerProfile)
        assert result[0].first_name == 'John'
        
        # Verify query conditions
        execute_call = mock_cursor.execute.call_args[0]
        assert "LOWER(first_name) = %s" in execute_call[0]
        assert "LOWER(last_name) = %s" in execute_call[0]
        assert "date_of_birth = %s" in execute_call[0]
        assert "LOWER(email) = %s" in execute_call[0]
    
    def test_find_passengers_minimal_criteria(self, passenger_service, mock_storage):
        """Test finding passengers with minimal criteria"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        
        # Act
        result = passenger_service.find_passengers_by_details(
            first_name='Jane',
            last_name='Smith'
        )
        
        # Assert
        assert len(result) == 0
        
        # Verify only name conditions in query
        execute_call = mock_cursor.execute.call_args[0]
        assert "LOWER(first_name) = %s" in execute_call[0]
        assert "LOWER(last_name) = %s" in execute_call[0]
        assert "date_of_birth = %s" not in execute_call[0]
        assert "email = %s" not in execute_call[0]
    
    def test_add_passenger_document_success(self, passenger_service, mock_storage):
        """Test adding passenger document"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ['document-uuid-123']
        
        document_data = {
            'document_expiry': date(2030, 12, 31),
            'is_primary': True,
            'is_verified': False,
            'document_image_ids': ['image-1', 'image-2']
        }
        
        # Act
        result = passenger_service.add_passenger_document(
            passenger_id='passenger-123',
            document_type='passport',
            document_number='P987654321',
            issuing_country='USA',
            **document_data
        )
        
        # Assert
        assert result == 'document-uuid-123'
        mock_cursor.execute.assert_called_once()
        
        execute_call = mock_cursor.execute.call_args[0]
        assert "INSERT INTO passenger_documents" in execute_call[0]
    
    def test_get_passenger_documents_success(self, passenger_service, mock_storage):
        """Test getting passenger documents"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        document_rows = [
            [
                'doc-1', 'passenger-123', 'passport', 'P123456789',
                date(2030, 12, 31), 'USA', '["img-1", "img-2"]',
                True, True, datetime.now(), datetime.now()
            ],
            [
                'doc-2', 'passenger-123', 'drivers_license', 'DL987654321',
                date(2028, 6, 15), 'USA', '[]',
                False, False, datetime.now(), datetime.now()
            ]
        ]
        mock_cursor.fetchall.return_value = document_rows
        
        # Act
        result = passenger_service.get_passenger_documents('passenger-123')
        
        # Assert
        assert len(result) == 2
        assert isinstance(result[0], PassengerDocument)
        assert result[0].document_type == 'passport'
        assert result[0].is_primary is True
        assert result[0].document_image_ids == ['img-1', 'img-2']
        
        # Verify ordering (primary first, then by created_at DESC)
        execute_call = mock_cursor.execute.call_args[0]
        assert "ORDER BY is_primary DESC, created_at DESC" in execute_call[0]
    
    def test_connect_user_to_passenger_success(self, passenger_service, mock_storage):
        """Test connecting user to passenger"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = [1]
        
        connection_data = {
            'relationship': 'spouse',
            'trust_level': 'verified',
            'can_book_for_passenger': True,
            'can_modify_passenger_details': True,
            'verified_by_user': True,
            'connected_via_booking_id': 'booking-123'
        }
        
        # Act
        result = passenger_service.connect_user_to_passenger(
            user_id=456,
            passenger_id='passenger-123',
            connection_type='family',
            **connection_data
        )
        
        # Assert
        assert result == 1
        mock_cursor.execute.assert_called_once()
        
        execute_call = mock_cursor.execute.call_args[0]
        assert "INSERT INTO user_passenger_connections" in execute_call[0]
    
    def test_get_user_passengers_success(self, passenger_service, mock_storage):
        """Test getting user's connected passengers"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Mock combined passenger + connection data
        combined_rows = [
            [
                # Passenger data (28 fields)
                'passenger-1', 'John', None, 'Doe', date(1990, 1, 15),
                'male', 'Mr.', 'john@example.com', '+1234567890', 'passport',
                'P123456789', date(2030, 12, 31), 'USA', 'USA', 'window',
                'vegetarian', None, None, None, '{}', None, None, 456,
                True, 'government_id', datetime.now(), datetime.now(), None,
                # Connection data (15 fields)  
                1, 456, 'passenger-1', 'self', 'self', 'verified', None,
                datetime.now(), datetime.now(), True, True, True, True,
                datetime.now(), datetime.now()
            ]
        ]
        mock_cursor.fetchall.return_value = combined_rows
        
        # Act
        result = passenger_service.get_user_passengers(456)
        
        # Assert
        assert len(result) == 1
        passenger, connection = result[0]
        
        assert isinstance(passenger, PassengerProfile)
        assert isinstance(connection, UserPassengerConnection)
        assert passenger.first_name == 'John'
        assert connection.connection_type == 'self'
        assert connection.trust_level == 'verified'
    
    def test_get_user_passengers_with_trust_filter(self, passenger_service, mock_storage):
        """Test getting user passengers filtered by trust level"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        
        # Act
        result = passenger_service.get_user_passengers(456, trust_level='verified')
        
        # Assert
        assert len(result) == 0
        
        # Verify trust level filter in query
        execute_call = mock_cursor.execute.call_args[0]
        assert "AND upc.trust_level = %s" in execute_call[0]
        
        # Verify parameters
        params = mock_cursor.execute.call_args[0][1]
        assert '456' in params
        assert 'verified' in params
    
    def test_update_connection_permissions_success(self, passenger_service, mock_storage):
        """Test updating connection permissions"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 1
        
        permissions = {
            'trust_level': 'trusted',
            'can_book_for_passenger': True,
            'can_modify_passenger_details': False,
            'verified_by_user': True,
            'verified_at': datetime.now()
        }
        
        # Act
        result = passenger_service.update_connection_permissions(1, **permissions)
        
        # Assert
        assert result is True
        mock_cursor.execute.assert_called_once()
        
        execute_call = mock_cursor.execute.call_args[0]
        assert "UPDATE user_passenger_connections" in execute_call[0]
        assert "trust_level = %s" in execute_call[0]
        assert "updated_at = CURRENT_TIMESTAMP" in execute_call[0]
    
    def test_verify_passenger_success(self, passenger_service, mock_storage):
        """Test verifying passenger"""
        # Arrange
        passenger_service.update_passenger = Mock(return_value=True)
        
        # Act
        result = passenger_service.verify_passenger('passenger-123', 'government_id')
        
        # Assert
        assert result is True
        passenger_service.update_passenger.assert_called_once_with(
            'passenger-123',
            is_verified=True,
            verification_method='government_id'
        )
    
    def test_get_passenger_statistics_success(self, passenger_service, mock_storage):
        """Test getting passenger statistics"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        stats_row = [100, 75, 60, 45, 80, 90]  # total, verified, email, phone, docs, created_by_users
        mock_cursor.fetchone.return_value = stats_row
        
        # Act
        result = passenger_service.get_passenger_statistics()
        
        # Assert
        assert result['total_passengers'] == 100
        assert result['verified_passengers'] == 75
        assert result['verification_rate'] == 75.0  # 75/100 * 100
        assert result['with_email'] == 60
        assert result['with_phone'] == 45
        assert result['with_documents'] == 80
        assert result['created_by_users'] == 90
    
    def test_json_field_handling(self, passenger_service, mock_storage):
        """Test proper JSON field serialization"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ['passenger-123']
        
        airline_loyalties = {'AA': '123456', 'UA': '789012'}
        
        # Act
        passenger_service.create_passenger(
            first_name='Test',
            last_name='User',
            date_of_birth=date(1990, 1, 1),
            airline_loyalties=airline_loyalties
        )
        
        # Assert
        execute_call = mock_cursor.execute.call_args[0]
        execute_params = mock_cursor.execute.call_args[0][1]
        
        # Verify JSON serialization
        assert json.dumps(airline_loyalties) in execute_params
    
    def test_passenger_not_found(self, passenger_service, mock_storage):
        """Test getting non-existent passenger"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        
        # Act
        result = passenger_service.get_passenger('nonexistent-passenger')
        
        # Assert
        assert result is None
    
    def test_exception_handling(self, passenger_service, mock_storage):
        """Test exception handling in various methods"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Database error")
        
        # Act & Assert
        assert passenger_service.create_passenger('John', 'Doe', date(1990, 1, 1)) is None
        assert passenger_service.get_passenger('passenger-123') is None
        assert passenger_service.update_passenger('passenger-123', email='test@example.com') is False
        assert passenger_service.find_passengers_by_details('John', 'Doe') == []
        assert passenger_service.add_passenger_document('passenger-123', 'passport', 'P123', 'USA') is None
        assert passenger_service.get_passenger_documents('passenger-123') == []
        assert passenger_service.connect_user_to_passenger(1, 'passenger-123', 'self') is None
        assert passenger_service.get_user_passengers(1) == []
        assert passenger_service.update_connection_permissions(1, trust_level='verified') is False
        assert passenger_service.get_passenger_statistics() == {}
    
    def test_no_connection_handling(self, passenger_service):
        """Test handling when no database connection"""
        # Arrange
        passenger_service.storage.conn = None
        
        # Act & Assert
        assert passenger_service.create_passenger('John', 'Doe', date(1990, 1, 1)) is None
        assert passenger_service.get_passenger('passenger-123') is None
        assert passenger_service.update_passenger('passenger-123') is False
        assert passenger_service.find_passengers_by_details('John', 'Doe') == []
        assert passenger_service.add_passenger_document('p-123', 'passport', 'P123', 'USA') is None
        assert passenger_service.get_passenger_documents('passenger-123') == []
        assert passenger_service.connect_user_to_passenger(1, 'passenger-123', 'self') is None
        assert passenger_service.get_user_passengers(1) == []
        assert passenger_service.update_connection_permissions(1) is False
        assert passenger_service.get_passenger_statistics() == {}
    
    def test_update_passenger_no_changes(self, passenger_service, mock_storage):
        """Test updating passenger with no actual changes"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Act
        result = passenger_service.update_passenger('passenger-123')
        
        # Assert
        assert result is True  # Should return True for "nothing to update"
        mock_cursor.execute.assert_not_called()
    
    def test_update_connection_permissions_no_changes(self, passenger_service, mock_storage):
        """Test updating connection permissions with no changes"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Act
        result = passenger_service.update_connection_permissions(1)
        
        # Assert
        assert result is True  # Should return True for "nothing to update"
        mock_cursor.execute.assert_not_called()
    
    def test_zero_division_in_statistics(self, passenger_service, mock_storage):
        """Test statistics calculation with zero passengers"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        stats_row = [0, 0, 0, 0, 0, 0]  # All zeros
        mock_cursor.fetchone.return_value = stats_row
        
        # Act
        result = passenger_service.get_passenger_statistics()
        
        # Assert
        assert result['verification_rate'] == 0  # Should handle division by zero
        assert result['total_passengers'] == 0
    
    def test_dynamic_query_building_find_passengers(self, passenger_service, mock_storage):
        """Test dynamic query building in find_passengers_by_details"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        
        # Test with all criteria
        passenger_service.find_passengers_by_details(
            first_name='John',
            last_name='Doe',
            date_of_birth=date(1990, 1, 15),
            email='john@example.com'
        )
        
        # Verify all conditions are in query
        execute_call = mock_cursor.execute.call_args[0]
        query = execute_call[0]
        params = execute_call[1]
        
        assert "LOWER(first_name) = %s" in query
        assert "LOWER(last_name) = %s" in query
        assert "date_of_birth = %s" in query
        assert "LOWER(email) = %s" in query
        assert len(params) == 4  # All 4 parameters
    
    def test_document_ordering(self, passenger_service, mock_storage):
        """Test that documents are ordered by primary status then creation date"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        
        # Act
        passenger_service.get_passenger_documents('passenger-123')
        
        # Assert
        execute_call = mock_cursor.execute.call_args[0]
        assert "ORDER BY is_primary DESC, created_at DESC" in execute_call[0]
    
    def test_connection_unique_constraint_handling(self, passenger_service, mock_storage):
        """Test handling of unique constraint on user-passenger connections"""
        # This would be handled at the database level, but we can test the service behavior
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("UNIQUE constraint failed")
        
        # Act
        result = passenger_service.connect_user_to_passenger(1, 'passenger-123', 'self')
        
        # Assert
        assert result is None  # Should handle the constraint error gracefully