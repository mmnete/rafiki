# ==============================================================================
# tests/storage/services/test_user_storage_service.py
# ==============================================================================
import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, date, timedelta
from app.storage.services.user_storage_service import (
    UserStorageService, User, UserSession
)

class TestUserStorageService:
    
    @pytest.fixture
    def mock_storage(self):
        """Mock storage service"""
        storage = Mock()
        storage.conn = MagicMock()
        return storage
    
    @pytest.fixture
    def user_service(self, mock_storage):
        """Create user service with mocked storage"""
        return UserStorageService(mock_storage)
    
    def test_create_user_success(self, user_service, mock_storage):
        """Test successful user creation"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = [123]
        
        # Mock get_user_by_phone to return None (no existing user)
        user_service.get_user_by_phone = Mock(return_value=None)
        
        user_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'preferred_language': 'en',
            'travel_preferences': {'seat_type': 'window'}
        }
        
        # Act
        result = user_service.create_user('+1234567890', **user_data)
        
        # Assert
        assert result == 123
        mock_cursor.execute.assert_called_once()
        
        execute_call = mock_cursor.execute.call_args[0]
        assert "INSERT INTO users" in execute_call[0]
        assert "RETURNING id" in execute_call[0]
    
    def test_create_user_existing_phone(self, user_service, mock_storage):
        """Test creating user with existing phone returns existing user ID"""
        # Arrange
        existing_user = User(
            id=456, phone_number='+1234567890', first_name='Jane',
            middle_name=None, last_name='Smith', email=None,
            date_of_birth=None, gender=None, location=None,
            preferred_language='en', timezone=None, status='active',
            onboarding_completed_at=datetime.now(), is_trusted_tester=False,
            is_active=True, travel_preferences={}, notification_preferences={},
            created_at=datetime.now(), updated_at=datetime.now(), last_login_at=None
        )
        
        user_service.get_user_by_phone = Mock(return_value=existing_user)
        
        # Act
        result = user_service.create_user('+1234567890', first_name='John')
        
        # Assert
        assert result == 456  # Returns existing user ID
    
    def test_get_user_success(self, user_service, mock_storage):
        """Test successful user retrieval"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        user_row = [
            123, '+1234567890', 'John', 'Michael', 'Doe',
            'john.doe@example.com', date(1990, 1, 15), 'male',
            'New York', 'en', 'America/New_York', 'active',
            datetime.now(), False, True,
            '{"seat_type": "window"}', '{"email": true}',
            datetime.now(), datetime.now(), datetime.now()
        ]
        mock_cursor.fetchone.return_value = user_row
        
        # Act
        result = user_service.get_user(123)
        
        # Assert
        assert result is not None
        assert isinstance(result, User)
        assert result.id == 123
        assert result.first_name == 'John'
        assert result.middle_name == 'Michael'
        assert result.email == 'john.doe@example.com'
        assert result.travel_preferences == {'seat_type': 'window'}
    
    def test_get_user_by_phone_success(self, user_service, mock_storage):
        """Test getting user by phone number"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        user_row = [
            789, '+9876543210', 'Alice', None, 'Johnson',
            None, None, None, None, 'sw', None, 'onboarding_greet',
            None, True, True, '{}', '{}',
            datetime.now(), datetime.now(), None
        ]
        mock_cursor.fetchone.return_value = user_row
        
        # Act
        result = user_service.get_user_by_phone('+9876543210')
        
        # Assert
        assert result is not None
        assert result.phone_number == '+9876543210'
        assert result.first_name == 'Alice'
        assert result.preferred_language == 'sw'
        assert result.is_trusted_tester is True
    
    def test_get_user_by_email_success(self, user_service, mock_storage):
        """Test getting user by email"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        user_row = [
            456, '+5555555555', 'Bob', None, 'Wilson',
            'bob@example.com', None, None, None, 'en', None, 'active',
            datetime.now(), False, True, '{}', '{}',
            datetime.now(), datetime.now(), datetime.now()
        ]
        mock_cursor.fetchone.return_value = user_row
        
        # Act
        result = user_service.get_user_by_email('bob@example.com')
        
        # Assert
        assert result is not None
        assert result.email == 'bob@example.com'
        assert result.first_name == 'Bob'
    
    def test_update_user_success(self, user_service, mock_storage):
        """Test successful user update"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 1
        
        update_data = {
            'first_name': 'Johnny',
            'email': 'johnny.doe@example.com',
            'travel_preferences': {'seat_type': 'aisle', 'meal': 'vegetarian'}
        }
        
        # Act
        result = user_service.update_user(123, **update_data)
        
        # Assert
        assert result is True
        mock_cursor.execute.assert_called_once()
        
        execute_call = mock_cursor.execute.call_args[0]
        assert "UPDATE users" in execute_call[0]
        assert "updated_at = CURRENT_TIMESTAMP" in execute_call[0]
        assert "WHERE id = %s" in execute_call[0]
    
    def test_update_user_status(self, user_service, mock_storage):
        """Test updating user status"""
        # Arrange
        user_service.update_user = Mock(return_value=True)
        
        # Act
        result = user_service.update_user_status(123, 'active')
        
        # Assert
        assert result is True
        user_service.update_user.assert_called_once_with(123, status='active')
    
    def test_complete_onboarding(self, user_service, mock_storage):
        """Test completing user onboarding"""
        # Arrange
        user_service.update_user = Mock(return_value=True)
        
        # Act
        result = user_service.complete_onboarding(123)
        
        # Assert
        assert result is True
        call_args = user_service.update_user.call_args[1]
        assert call_args['status'] == 'active'
        assert 'onboarding_completed_at' in call_args
    
    def test_create_session_success(self, user_service, mock_storage):
        """Test successful session creation"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ['session-uuid-123']
        
        user_service.update_last_login = Mock(return_value=True)
        
        device_info = {'platform': 'iOS', 'version': '14.0'}
        
        # Act
        result = user_service.create_session(
            user_id=123,
            device_info=device_info,
            ip_address='192.168.1.1',
            expires_in_hours=48
        )
        
        # Assert
        assert result is not None
        assert len(result) == 43  # URL-safe base64 token length for 32 bytes
        
        mock_cursor.execute.assert_called_once()
        execute_call = mock_cursor.execute.call_args[0]
        assert "INSERT INTO user_sessions" in execute_call[0]
        
        user_service.update_last_login.assert_called_once_with(123)
    
    def test_get_session_success(self, user_service, mock_storage):
        """Test successful session retrieval"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        session_row = [
            'session-uuid-123', 456, 'abc123token', 
            datetime.now() + timedelta(hours=24),
            '{"platform": "Android"}', '10.0.0.1', datetime.now()
        ]
        mock_cursor.fetchone.return_value = session_row
        
        # Act
        result = user_service.get_session('abc123token')
        
        # Assert
        assert result is not None
        assert isinstance(result, UserSession)
        assert result.user_id == 456
        assert result.session_token == 'abc123token'
        assert result.device_info == {'platform': 'Android'}
        
        # Verify expiration check in query
        execute_call = mock_cursor.execute.call_args[0]
        assert "expires_at > CURRENT_TIMESTAMP" in execute_call[0]
    
    def test_validate_session_success(self, user_service, mock_storage):
        """Test session validation"""
        # Arrange
        mock_session = UserSession(
            id='session-123', user_id=789, session_token='valid_token',
            expires_at=datetime.now() + timedelta(hours=12),
            device_info=None, ip_address=None, created_at=datetime.now()
        )
        user_service.get_session