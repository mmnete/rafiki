# tests/test_user_storage_service.py
import pytest
import json
from datetime import datetime, date, timedelta
from unittest.mock import Mock, MagicMock
from app.storage.services.user_storage_service import UserStorageService, User, UserSession
from app.storage.db_service import StorageService

class TestUserStorageService:
    
    @pytest.fixture
    def mock_storage(self):
        """Create mock storage service"""
        storage = Mock(spec=StorageService)
        storage.conn = Mock()
        return storage
    
    @pytest.fixture
    def user_service(self, mock_storage):
        """Create user service with mock storage"""
        return UserStorageService(mock_storage)
    
    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing"""
        return {
            'phone_number': '+1234567890',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'date_of_birth': date(1990, 1, 1),
            'gender': 'male',
            'location': 'San Francisco',
            'preferred_language': 'en',
            'timezone': 'America/Los_Angeles',
            'travel_preferences': {'seat': 'window', 'meal': 'vegetarian'},
            'notification_preferences': {'email': True, 'sms': False}
        }
    
    def test_create_user_success(self, user_service, mock_storage, sample_user_data):
        """Test successful user creation"""
        # Setup
        mock_cursor = Mock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [None, (123,)]  # First None (no existing), then new ID
        
        # Execute
        user_id = user_service.create_user(**sample_user_data)
        
        # Verify
        assert user_id == 123
        assert mock_cursor.execute.call_count == 2  # Check existing + insert
        
        # Verify insert call
        insert_call_args = mock_cursor.execute.call_args_list[1]
        assert 'INSERT INTO users' in insert_call_args[0][0]
        assert 'phone_number' in insert_call_args[0][0]
        assert 'first_name' in insert_call_args[0][0]
        assert 'self_passenger_profile_id' not in insert_call_args[0][0]  # Not provided
    
    def test_create_user_with_passenger_profile_id(self, user_service, mock_storage, sample_user_data):
        """Test user creation with passenger profile link"""
        # Setup
        sample_user_data['self_passenger_profile_id'] = 'uuid-123-456'
        mock_cursor = Mock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [None, (123,)]
        
        # Execute
        user_id = user_service.create_user(**sample_user_data)
        
        # Verify
        assert user_id == 123
        insert_call_args = mock_cursor.execute.call_args_list[1]
        assert 'self_passenger_profile_id' in insert_call_args[0][0]
    
    def test_create_user_already_exists(self, user_service, mock_storage, sample_user_data):
        """Test creating user that already exists returns existing ID"""
        # Setup
        existing_user = User(
            id=456, phone_number=sample_user_data['phone_number'],
            first_name='Jane', middle_name=None, last_name='Smith',
            email='jane@example.com', date_of_birth=None, gender=None,
            self_passenger_profile_id=None, location=None, preferred_language='en',
            timezone=None, status='active', onboarding_completed_at=None,
            is_trusted_tester=False, is_active=True, travel_preferences={},
            notification_preferences={}, created_at=datetime.now(),
            updated_at=datetime.now(), last_chat_at=None
        )
        
        mock_cursor = Mock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (
            456, sample_user_data['phone_number'], 'Jane', None, 'Smith',
            'jane@example.com', None, None, None, None, 'en', None, 'active',
            None, False, True, '{}', '{}', datetime.now(), datetime.now(), None
        )
        
        # Execute
        user_id = user_service.create_user(**sample_user_data)
        
        # Verify
        assert user_id == 456
        assert mock_cursor.execute.call_count == 1  # Only check existing user query
    
    def test_get_user_success(self, user_service, mock_storage):
        """Test successful user retrieval"""
        # Setup
        mock_cursor = Mock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (
            123, '+1234567890', 'John', 'M', 'Doe', 'john@example.com',
            date(1990, 1, 1), 'male', 'uuid-passenger-123', 'SF', 'en', 'PST',
            'active', datetime(2024, 1, 1), False, True,
            '{"seat": "window"}', '{"email": true}',
            datetime(2024, 1, 1), datetime(2024, 1, 2), datetime(2024, 1, 3)
        )
        
        # Execute
        user = user_service.get_user(123)
        
        # Verify
        assert user is not None
        assert user.id == 123
        assert user.phone_number == '+1234567890'
        assert user.first_name == 'John'
        assert user.middle_name == 'M'
        assert user.last_name == 'Doe'
        assert user.email == 'john@example.com'
        assert user.date_of_birth == date(1990, 1, 1)
        assert user.gender == 'male'
        assert user.self_passenger_profile_id == 'uuid-passenger-123'
        assert user.location == 'SF'
        assert user.preferred_language == 'en'
        assert user.timezone == 'PST'
        assert user.status == 'active'
        assert user.is_trusted_tester is False
        assert user.is_active is True
        assert user.travel_preferences == {"seat": "window"}
        assert user.notification_preferences == {"email": True}
        
        # Verify query
        query_call = mock_cursor.execute.call_args[0][0]
        assert 'SELECT' in query_call
        assert 'self_passenger_profile_id' in query_call
        assert 'WHERE id = %s' in query_call
    
    def test_get_user_not_found(self, user_service, mock_storage):
        """Test user not found returns None"""
        # Setup
        mock_cursor = Mock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        
        # Execute
        user = user_service.get_user(999)
        
        # Verify
        assert user is None
    
    def test_get_user_by_phone_success(self, user_service, mock_storage):
        """Test successful user retrieval by phone"""
        # Setup
        mock_cursor = Mock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (
            123, '+1234567890', 'John', None, 'Doe', None, None, None, None,
            None, 'en', None, 'active', None, False, True, '{}', '{}',
            datetime.now(), datetime.now(), None
        )
        
        # Execute
        user = user_service.get_user_by_phone('+1234567890')
        
        # Verify
        assert user is not None
        assert user.id == 123
        assert user.phone_number == '+1234567890'
        
        # Verify query
        query_call = mock_cursor.execute.call_args[0]
        assert 'WHERE phone_number = %s' in query_call[0]
        assert query_call[1] == ('+1234567890',)
    
    def test_get_or_create_user_existing(self, user_service, mock_storage):
        """Test get_or_create returns existing user"""
        # Setup
        mock_cursor = Mock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (
            123, '+1234567890', 'John', None, 'Doe', None, None, None, None,
            None, 'en', None, 'active', None, False, True, '{}', '{}',
            datetime.now(), datetime.now(), None
        )
        
        # Execute
        user = user_service.get_or_create_user('+1234567890', first_name='Jane')
        
        # Verify
        assert user is not None
        assert user.id == 123
        assert user.first_name == 'John'  # Existing user data, not new data
    
    def test_get_or_create_user_new(self, user_service, mock_storage):
        """Test get_or_create creates new user"""
        # Setup
        mock_cursor = Mock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        # First call returns None (no existing), second returns new user ID, third returns full user
        mock_cursor.fetchone.side_effect = [
            None,  # No existing user
            (123,),  # New user ID from create
            (123, '+1234567890', 'Jane', None, 'Doe', None, None, None, None,
             None, 'en', None, 'onboarding_greet', None, False, True, '{}', '{}',
             datetime.now(), datetime.now(), None)  # Full user data
        ]
        
        # Execute
        user = user_service.get_or_create_user('+1234567890', first_name='Jane')
        
        # Verify
        assert user is not None
        assert user.id == 123
        assert user.first_name == 'Jane'
    
    def test_update_user_success(self, user_service, mock_storage):
        """Test successful user update"""
        # Setup
        mock_cursor = Mock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 1
        
        # Execute
        result = user_service.update_user(
            123,
            first_name='Jane',
            self_passenger_profile_id='new-uuid-456',
            travel_preferences={'seat': 'aisle'}
        )
        
        # Verify
        assert result is True
        
        # Verify update query
        query_call = mock_cursor.execute.call_args[0]
        assert 'UPDATE users' in query_call[0]
        assert 'first_name = %s' in query_call[0]
        assert 'self_passenger_profile_id = %s' in query_call[0]
        assert 'travel_preferences = %s' in query_call[0]
        assert 'updated_at = CURRENT_TIMESTAMP' in query_call[0]
        assert 'WHERE id = %s' in query_call[0]
        
        # Verify parameters
        params = query_call[1]
        assert 'Jane' in params
        assert 'new-uuid-456' in params
        assert '{"seat": "aisle"}' in params
        assert 123 in params
    
    def test_update_user_no_fields(self, user_service, mock_storage):
        """Test update with no valid fields returns True"""
        # Execute
        result = user_service.update_user(123, invalid_field='value')
        
        # Verify
        assert result is True
    
    def test_link_passenger_profile(self, user_service, mock_storage):
        """Test linking user to passenger profile"""
        # Setup
        mock_cursor = Mock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 1
        
        # Execute
        result = user_service.link_passenger_profile(123, 'uuid-passenger-456')
        
        # Verify
        assert result is True
        
        # Verify update query includes passenger profile ID
        query_call = mock_cursor.execute.call_args[0]
        assert 'self_passenger_profile_id = %s' in query_call[0]
        assert 'uuid-passenger-456' in query_call[1]
    
    def test_unlink_passenger_profile(self, user_service, mock_storage):
        """Test unlinking user from passenger profile"""
        # Setup
        mock_cursor = Mock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 1
        
        # Execute
        result = user_service.unlink_passenger_profile(123)
        
        # Verify
        assert result is True
        
        # Verify update query sets passenger profile ID to NULL
        query_call = mock_cursor.execute.call_args[0]
        assert 'self_passenger_profile_id = %s' in query_call[0]
        assert None in query_call[1]
    
    def test_complete_onboarding(self, user_service, mock_storage):
        """Test completing user onboarding"""
        # Setup
        mock_cursor = Mock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 1
        
        # Execute
        result = user_service.complete_onboarding(123)
        
        # Verify
        assert result is True
        
        # Verify update includes status and onboarding timestamp
        query_call = mock_cursor.execute.call_args[0]
        assert 'status = %s' in query_call[0]
        assert 'onboarding_completed_at = %s' in query_call[0]
        assert 'active' in query_call[1]
    
    def test_create_session_success(self, user_service, mock_storage):
        """Test successful session creation"""
        # Setup
        mock_cursor = Mock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [('session_id',), 1]  # Session created, user updated
        mock_cursor.rowcount = 1
        
        device_info = {'device': 'iPhone', 'os': 'iOS 15'}
        
        # Execute
        session_token = user_service.create_session(
            123, 
            device_info=device_info, 
            ip_address='192.168.1.1'
        )
        
        # Verify
        assert session_token is not None
        assert len(session_token) > 20  # Should be URL-safe token
        
        # Verify session insert
        session_call = mock_cursor.execute.call_args_list[0][0]
        assert 'INSERT INTO user_sessions' in session_call[0]
        assert 'user_id' in session_call[0]
        assert 'session_token' in session_call[0]
        assert 'expires_at' in session_call[0]
        assert 'device_info' in session_call[0]
        assert 'ip_address' in session_call[0]
        
        # Verify parameters
        params = session_call[1]
        assert 123 in params  # user_id
        assert '192.168.1.1' in params  # ip_address
        assert '{"device": "iPhone", "os": "iOS 15"}' in [p for p in params if isinstance(p, str) and 'iPhone' in p][0]
    
    def test_get_session_success(self, user_service, mock_storage):
        """Test successful session retrieval"""
        # Setup
        mock_cursor = Mock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (
            'session_uuid', 123, 'token123', 
            datetime.now() + timedelta(hours=1),  # expires_at
            '{"device": "iPhone"}', '192.168.1.1', datetime.now()
        )
        
        # Execute
        session = user_service.get_session('token123')
        
        # Verify
        assert session is not None
        assert session.id == 'session_uuid'
        assert session.user_id == 123
        assert session.session_token == 'token123'
        assert session.device_info == {"device": "iPhone"}
        assert session.ip_address == '192.168.1.1'
        
        # Verify query includes expiration check
        query_call = mock_cursor.execute.call_args[0]
        assert 'WHERE session_token = %s AND expires_at > CURRENT_TIMESTAMP' in query_call[0]
    
    def test_get_session_expired(self, user_service, mock_storage):
        """Test expired session returns None"""
        # Setup
        mock_cursor = Mock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None  # No results for expired session
        
        # Execute
        session = user_service.get_session('expired_token')
        
        # Verify
        assert session is None
    
    def test_validate_session_valid(self, user_service, mock_storage):
        """Test session validation with valid token"""
        # Setup
        mock_cursor = Mock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (
            'session_uuid', 123, 'valid_token',
            datetime.now() + timedelta(hours=1),
            None, None, datetime.now()
        )
        
        # Execute
        user_id = user_service.validate_session('valid_token')
        
        # Verify
        assert user_id == 123
    
    def test_validate_session_invalid(self, user_service, mock_storage):
        """Test session validation with invalid token"""
        # Setup
        mock_cursor = Mock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        
        # Execute
        user_id = user_service.validate_session('invalid_token')
        
        # Verify
        assert user_id is None
    
    def test_revoke_session_success(self, user_service, mock_storage):
        """Test successful session revocation"""
        # Setup
        mock_cursor = Mock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 1
        
        # Execute
        result = user_service.revoke_session('token_to_revoke')
        
        # Verify
        assert result is True
        
        # Verify delete query
        query_call = mock_cursor.execute.call_args[0]
        assert 'DELETE FROM user_sessions WHERE session_token = %s' in query_call[0]
        assert query_call[1] == ('token_to_revoke',)
    
    def test_revoke_session_not_found(self, user_service, mock_storage):
        """Test revoking non-existent session"""
        # Setup
        mock_cursor = Mock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 0
        
        # Execute
        result = user_service.revoke_session('nonexistent_token')
        
        # Verify
        assert result is False
    
    def test_cleanup_expired_sessions(self, user_service, mock_storage):
        """Test cleaning up expired sessions"""
        # Setup
        mock_cursor = Mock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 5  # 5 expired sessions cleaned
        
        # Execute
        count = user_service.cleanup_expired_sessions()
        
        # Verify
        assert count == 5
        
        # Verify delete query
        query_call = mock_cursor.execute.call_args[0]
        assert 'DELETE FROM user_sessions WHERE expires_at < CURRENT_TIMESTAMP' in query_call[0]
    
    def test_database_connection_error(self, user_service):
        """Test handling when database connection is None"""
        # Setup - no connection
        user_service.storage.conn = None
        
        # Execute various methods
        assert user_service.create_user('+1234567890') is None
        assert user_service.get_user(123) is None
        assert user_service.get_user_by_phone('+1234567890') is None
        assert user_service.get_or_create_user('+1234567890') is None
        assert user_service.update_user(123, first_name='John') is False
        assert user_service.create_session(123) is None
        assert user_service.get_session('token') is None
        assert user_service.revoke_session('token') is False
        assert user_service.cleanup_expired_sessions() == 0
    
    def test_database_exception_handling(self, user_service, mock_storage):
        """Test handling of database exceptions"""
        # Setup - cursor raises exception
        mock_storage.conn.cursor.side_effect = Exception("Database error")
        
        # Execute and verify exceptions are caught
        assert user_service.create_user('+1234567890') is None
        assert user_service.get_user(123) is None
        assert user_service.update_user(123, first_name='John') is False
        assert user_service.create_session(123) is None
    
    def test_json_field_handling(self, user_service, mock_storage):
        """Test proper JSON encoding/decoding of preference fields"""
        # Setup
        mock_cursor = Mock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [None, (123,)]  # No existing, then new ID
        
        preferences = {
            'travel_preferences': {'seat': 'window', 'meal': 'vegetarian'},
            'notification_preferences': {'email': True, 'sms': False}
        }
        
        # Execute
        user_service.create_user('+1234567890', **preferences)
        
        # Verify JSON encoding in insert
        insert_call = mock_cursor.execute.call_args_list[1][0]
        params = insert_call[1]
        
        # Should contain JSON strings, not dict objects
        json_params = [p for p in params if isinstance(p, str) and ('{' in p or 'true' in p or 'false' in p)]
        assert len(json_params) >= 2  # Should have both JSON preference fields
        
        # Verify one is properly formatted JSON
        travel_json = '{"seat": "window", "meal": "vegetarian"}'
        notification_json = '{"email": true, "sms": false}'
        assert travel_json in params or notification_json in params
    
    def test_row_to_user_conversion(self, user_service):
        """Test internal _row_to_user method"""
        # Setup sample row data
        row = (
            123, '+1234567890', 'John', 'M', 'Doe', 'john@example.com',
            date(1990, 1, 1), 'male', 'uuid-passenger-123', 'SF', 'en', 'PST',
            'active', datetime(2024, 1, 1), False, True,
            '{"seat": "window"}', '{"email": true}',
            datetime(2024, 1, 1), datetime(2024, 1, 2), datetime(2024, 1, 3)
        )
        
        # Execute
        user = user_service._row_to_user(row)
        
        # Verify all fields mapped correctly
        assert user.id == 123
        assert user.phone_number == '+1234567890'
        assert user.first_name == 'John'
        assert user.middle_name == 'M'
        assert user.last_name == 'Doe'
        assert user.email == 'john@example.com'
        assert user.date_of_birth == date(1990, 1, 1)
        assert user.gender == 'male'
        assert user.self_passenger_profile_id == 'uuid-passenger-123'
        assert user.location == 'SF'
        assert user.preferred_language == 'en'
        assert user.timezone == 'PST'
        assert user.status == 'active'
        assert user.onboarding_completed_at == datetime(2024, 1, 1)
        assert user.is_trusted_tester is False
        assert user.is_active is True
        assert user.travel_preferences == {"seat": "window"}
        assert user.notification_preferences == {"email": True}
        assert user.created_at == datetime(2024, 1, 1)
        assert user.updated_at == datetime(2024, 1, 2)
        assert user.last_chat_at == datetime(2024, 1, 3)
    
    def test_generate_session_token(self, user_service):
        """Test session token generation"""
        # Execute
        token1 = user_service._generate_session_token()
        token2 = user_service._generate_session_token()
        
        # Verify
        assert token1 != token2  # Should be unique
        assert len(token1) > 20    # Should be reasonable length
        assert len(token2) > 20
        assert token1.replace('-', '').replace('_', '').isalnum()  # URL-safe characters

# Integration tests that would require a real database
class TestUserStorageServiceIntegration:
    """
    Integration tests - these would run against a real test database
    Run with: pytest tests/test_user_storage_service.py::TestUserStorageServiceIntegration -v
    """
    
    @pytest.mark.integration
    def test_full_user_lifecycle(self):
        """Test complete user lifecycle with real database"""
        # This would test:
        # 1. Create user
        # 2. Get user
        # 3. Update user with passenger profile link
        # 4. Create session
        # 5. Validate session
        # 6. Complete onboarding
        # 7. Cleanup
        pass
    
    @pytest.mark.integration  
    def test_concurrent_session_management(self):
        """Test multiple sessions for same user"""
        # This would test:
        # 1. Create multiple sessions for one user
        # 2. Validate all sessions work
        # 3. Revoke one session
        # 4. Verify others still work
        # 5. Cleanup expired sessions
        pass
    
    @pytest.mark.integration
    def test_database_constraints(self):
        """Test database constraints are enforced"""
        # This would test:
        # 1. Unique phone number constraint
        # 2. Valid email format constraint
        # 3. Foreign key constraint for passenger profile
        # 4. JSON field validation
        pass
