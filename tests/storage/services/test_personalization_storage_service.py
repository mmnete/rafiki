# ==============================================================================
# tests/test_personalization_service.py
# ==============================================================================
import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, date
from app.storage.services.personalization_storage_service import PersonalizationStorageService, UserPreferences

class TestPersonalizationStorageService:
    
    @pytest.fixture
    def mock_storage(self):
        """Mock storage service"""
        storage = Mock()
        storage.conn = MagicMock()
        return storage
    
    @pytest.fixture
    def personalization_service(self, mock_storage):
        """Create personalization service with mocked storage"""
        return PersonalizationStorageService(mock_storage)
    
    def test_get_user_preferences_success(self, personalization_service, mock_storage):
        """Test successful user preferences retrieval"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = [
            123, '["AA", "UA"]', '{"morning": true}', 'window', '{"min": 200, "max": 800}',
            14, True, 'medium', '[{"origin": "NYC", "destination": "LAX", "count": 3}]',
            '{"prefers_weekend": false}', datetime.now(), datetime.now()
        ]
        
        # Act
        result = personalization_service.get_user_preferences(123)
        
        # Assert
        assert result is not None
        assert isinstance(result, UserPreferences)
        assert result.user_id == 123
        assert result.preferred_airlines == ["AA", "UA"]
        assert result.preferred_departure_times == {"morning": True}
        assert result.preferred_seat_type == 'window'
        assert result.prefers_direct_flights is True
        assert len(result.frequently_searched_routes) == 1
    
    def test_get_user_preferences_not_found(self, personalization_service, mock_storage):
        """Test get preferences when user not found"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        
        # Act
        result = personalization_service.get_user_preferences(999)
        
        # Assert
        assert result is None
    
    def test_update_user_preferences_existing_user(self, personalization_service, mock_storage):
        """Test updating preferences for existing user"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 1  # Simulate successful update
        
        # Act
        result = personalization_service.update_user_preferences(
            user_id=123,
            preferred_airlines=["AA", "UA"],
            price_sensitivity="high",
            prefers_direct_flights=True
        )
        
        # Assert
        assert result is True
        mock_cursor.execute.assert_called()
        execute_call = mock_cursor.execute.call_args[0]
        assert "UPDATE user_preferences" in execute_call[0]
    
    def test_update_user_preferences_new_user(self, personalization_service, mock_storage):
        """Test updating preferences for new user"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Mock the rowcount to return 0 for first UPDATE, then allow subsequent calls
        mock_cursor.rowcount = 0
        
        # Act
        result = personalization_service.update_user_preferences(
            user_id=456,
            preferred_seat_type="aisle"
        )
        
        # Assert
        assert result is True
        # The method calls: 1) UPDATE (fails), 2) INSERT new record, 3) UPDATE again
        assert mock_cursor.execute.call_count == 3  # UPDATE, INSERT, UPDATE
    
    def test_find_similar_passengers_with_phone(self, personalization_service, mock_storage):
        """Test finding similar passengers with phone number"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            ['passenger-123', 456, 2, 'John', 'Doe', date(1990, 1, 15)]
        ]
        
        # Act
        result = personalization_service.find_similar_passengers(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-15",
            phone_number="+1-555-123-4567"
        )
        
        # Assert
        assert len(result) == 1
        assert result[0]["passenger_id"] == 'passenger-123'
        assert result[0]["first_name"] == 'John'
        assert result[0]["booking_count"] == 2
    
    def test_find_similar_passengers_without_phone(self, personalization_service, mock_storage):
        """Test finding similar passengers without phone number"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        
        # Act
        result = personalization_service.find_similar_passengers(
            first_name="Jane",
            last_name="Smith",
            date_of_birth="1985-05-20"
        )
        
        # Assert
        assert len(result) == 0
        # Verify query used name_hash and dob_hash only
        execute_call = mock_cursor.execute.call_args[0]
        # Fix: Check for the actual SQL pattern with proper whitespace handling
        assert "prd.name_hash = %s AND prd.dob_hash = %s" in execute_call[0]
    
    def test_record_passenger_recognition_success(self, personalization_service, mock_storage):
        """Test successful passenger recognition recording"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Act
        result = personalization_service.record_passenger_recognition(
            passenger_id="passenger-123",
            first_seen_user_id=456,
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-15",
            phone_number="+1-555-123-4567"
        )
        
        # Assert
        assert result is True
        mock_cursor.execute.assert_called_once()
        execute_call = mock_cursor.execute.call_args[0]
        assert "INSERT INTO passenger_recognition_data" in execute_call[0]
        assert "ON CONFLICT" in execute_call[0]
    
    def test_suggest_passengers_for_user_with_search(self, personalization_service, mock_storage):
        """Test passenger suggestions with search query"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            ['passenger-123', 'John', 'Doe', date(1990, 1, 15), 3, date(2024, 1, 1)]
        ]
        
        # Act
        result = personalization_service.suggest_passengers_for_user(
            user_id=456,
            search_query="John"
        )
        
        # Assert
        assert len(result) == 1
        assert result[0]["first_name"] == 'John'
        assert result[0]["booking_count"] == 3
        # Verify search query was used
        execute_call = mock_cursor.execute.call_args[0]
        assert "LIKE %s" in execute_call[0]
    
    def test_suggest_passengers_for_user_without_search(self, personalization_service, mock_storage):
        """Test passenger suggestions without search query"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        
        # Act
        result = personalization_service.suggest_passengers_for_user(user_id=456)
        
        # Assert
        assert len(result) == 0
        # Verify LIMIT was used
        execute_call = mock_cursor.execute.call_args[0]
        assert "LIMIT 10" in execute_call[0]
    
    def test_update_search_patterns_new_route(self, personalization_service, mock_storage):
        """Test updating search patterns with new route"""
        # Arrange
        with patch.object(personalization_service, 'get_user_preferences', return_value=None):
            with patch.object(personalization_service, 'update_user_preferences', return_value=True) as mock_update:
                
                # Act
                result = personalization_service.update_search_patterns(
                    user_id=123,
                    origin="NYC",
                    destination="LAX",
                    departure_date="2024-06-15"
                )
                
                # Assert
                assert result is True
                mock_update.assert_called_once()
                call_args = mock_update.call_args[1]
                assert call_args["user_id"] == 123
                assert len(call_args["frequently_searched_routes"]) == 1
                assert call_args["frequently_searched_routes"][0]["origin"] == "NYC"
    
    def test_hash_name_consistency(self, personalization_service):
        """Test that name hashing is consistent"""
        # Act
        hash1 = personalization_service._hash_name("John", "Doe")
        hash2 = personalization_service._hash_name("john", "doe")
        hash3 = personalization_service._hash_name(" John ", " Doe ")
        
        # Assert
        assert hash1 == hash2 == hash3  # Should be case and whitespace insensitive
        assert len(hash1) == 64  # SHA256 hex digest length
    
    def test_hash_phone_cleaning(self, personalization_service):
        """Test that phone number hashing cleans the input"""
        # Act
        hash1 = personalization_service._hash_phone("+1-555-123-4567")
        hash2 = personalization_service._hash_phone("15551234567")
        hash3 = personalization_service._hash_phone("(555) 123-4567")
        
        # Assert
        assert hash1 == hash2  # Should clean formatting
        # hash3 won't match because it's missing country code
        assert len(hash1) == 64  # SHA256 hex digest length
    
    def test_exception_handling(self, personalization_service, mock_storage):
        """Test exception handling in various methods"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Database error")
        
        # Act & Assert
        assert personalization_service.get_user_preferences(123) is None
        assert personalization_service.update_user_preferences(123, price_sensitivity="high") is False
        assert personalization_service.find_similar_passengers("John", "Doe", "1990-01-15") == []
        assert personalization_service.record_passenger_recognition("p123", 456, "John", "Doe", "1990-01-15") is False
    
    def test_no_connection_handling(self, personalization_service):
        """Test handling when no database connection"""
        # Arrange
        personalization_service.storage.conn = None
        
        # Act & Assert
        assert personalization_service.get_user_preferences(123) is None
        assert personalization_service.update_user_preferences(123) is False
        assert personalization_service.find_similar_passengers("John", "Doe", "1990-01-15") == []
        assert personalization_service.record_passenger_recognition("p123", 456, "John", "Doe", "1990-01-15") is False
