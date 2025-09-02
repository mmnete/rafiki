# ==============================================================================
# tests/test_conversation_service.py
# ==============================================================================
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import json
from app.storage.services.conversation_storage_service import ConversationStorageService, Conversation

class TestConversationStorageService:
    
    @pytest.fixture
    def mock_storage(self):
        """Mock storage service"""
        storage = Mock()
        storage.conn = MagicMock()
        return storage
    
    @pytest.fixture
    def conversation_service(self, mock_storage):
        """Create conversation service with mocked storage"""
        return ConversationStorageService(mock_storage)
    
    def test_save_conversation_success(self, conversation_service, mock_storage):
        """Test successful conversation saving"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ['test-uuid']
        
        # Act
        result = conversation_service.save_conversation(
            user_id=123,
            user_message="Hello",
            ai_response="Hi there!",
            message_type="chat",
            tools_used=["search_flights"],
            processing_time_ms=1500
        )
        
        # Assert
        assert result == 'test-uuid'
        mock_cursor.execute.assert_called_once()
        assert "INSERT INTO conversations" in mock_cursor.execute.call_args[0][0]
    
    def test_save_conversation_no_connection(self, conversation_service):
        """Test save conversation when no database connection"""
        # Arrange
        conversation_service.storage.conn = None
        
        # Act
        result = conversation_service.save_conversation(
            user_id=123,
            user_message="Hello",
            ai_response="Hi there!"
        )
        
        # Assert
        assert result is None
    
    def test_get_conversation_history_success(self, conversation_service, mock_storage):
        """Test successful conversation history retrieval"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            ('conv1', 123, 'Hello', 'Hi there!', datetime.now(), 'chat', '["search_flights"]', None, 1500, 'gpt-4', False),
            ('conv2', 123, 'Thanks', 'You\'re welcome!', datetime.now(), 'chat', '[]', None, 800, 'gpt-4', False)
        ]
        
        # Act
        result = conversation_service.get_conversation_history(user_id=123, limit=10)
        
        # Assert
        assert len(result) == 2
        assert isinstance(result[0], Conversation)
        # Since the list is reversed, conv2 becomes first (chronological order)
        assert result[0].id == 'conv2'  # Changed from 'conv1' to 'conv2'
        assert result[1].id == 'conv1'  # Added this assertion
        assert result[0].request == 'Thanks'
        assert result[0].response == 'You\'re welcome!'
        assert result[0].tools_used == []
        assert result[1].tools_used == ['search_flights']
    
    def test_get_conversation_history_no_connection(self, conversation_service):
        """Test get conversation history when no database connection"""
        # Arrange
        conversation_service.storage.conn = None
        
        # Act
        result = conversation_service.get_conversation_history(user_id=123)
        
        # Assert
        assert result == []
    
    def test_update_conversation_feedback_success(self, conversation_service, mock_storage):
        """Test successful feedback update"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 1
        
        # Act
        result = conversation_service.update_conversation_feedback(
            conversation_id='test-id',
            was_helpful=True,
            satisfaction_rating=5,
            feedback_text='Great response!'
        )
        
        # Assert
        assert result is True
        mock_cursor.execute.assert_called_once()
        assert "UPDATE conversations" in mock_cursor.execute.call_args[0][0]
    
    def test_update_conversation_feedback_not_found(self, conversation_service, mock_storage):
        """Test feedback update when conversation not found"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 0
        
        # Act
        result = conversation_service.update_conversation_feedback(
            conversation_id='non-existent',
            was_helpful=True
        )
        
        # Assert
        assert result is False
    
    def test_save_media_for_conversation_success(self, conversation_service, mock_storage):
        """Test successful media saving"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ['media-uuid']
        
        # Act
        result = conversation_service.save_media_for_conversation(
            conversation_id='conv-id',
            media_type='image',
            original_url='https://example.com/image.jpg',
            ai_description='A photo of a passport'
        )
        
        # Assert
        assert result == 'media-uuid'
        mock_cursor.execute.assert_called_once()
        assert "INSERT INTO message_media" in mock_cursor.execute.call_args[0][0]
    
    def test_get_conversations_by_booking_success(self, conversation_service, mock_storage):
        """Test getting conversations by booking ID"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            ('conv1', 'I want to book a flight', 'Sure! Let me help you', datetime.now(), 'flight_search'),
            ('conv2', 'Add passenger John Doe', 'Added successfully', datetime.now(), 'passenger_collection')
        ]
        
        # Act
        result = conversation_service.get_conversations_by_booking('booking-123')
        
        # Assert
        assert len(result) == 2
        assert result[0]['user_message'] == 'I want to book a flight'
        assert result[1]['booking_stage'] == 'passenger_collection'
    
    def test_cleanup_expired_conversations_success(self, conversation_service, mock_storage):
        """Test cleanup of expired conversations"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 5  # 5 conversations deleted
        
        # Act
        result = conversation_service.cleanup_expired_conversations()
        
        # Assert
        assert result == 5
        mock_cursor.execute.assert_called_once()
        assert "DELETE FROM conversations" in mock_cursor.execute.call_args[0][0]
        assert "expires_at < CURRENT_TIMESTAMP" in mock_cursor.execute.call_args[0][0]
    
    @patch('app.storage.services.conversation_storage_service.uuid.uuid4')
    @patch('app.storage.services.conversation_storage_service.hashlib.sha256')
    def test_save_conversation_with_mocked_uuid_and_hash(self, mock_sha256, mock_uuid, conversation_service, mock_storage):
        """Test save conversation with mocked UUID and hash generation"""
        # Arrange
        mock_uuid.return_value.hex = 'mocked-uuid'
        mock_hash = MagicMock()
        mock_hash.hexdigest.return_value = 'mocked-hash'
        mock_sha256.return_value = mock_hash
        
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ['mocked-uuid']
        
        # Act
        result = conversation_service.save_conversation(
            user_id=123,
            user_message="Test message",
            ai_response="Test response"
        )
        
        # Assert
        assert result == 'mocked-uuid'
        mock_sha256.assert_called_once_with("Test message".encode())
        
    def test_exception_handling_in_save_conversation(self, conversation_service, mock_storage):
        """Test exception handling in save_conversation"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Database error")
        
        # Act
        result = conversation_service.save_conversation(
            user_id=123,
            user_message="Hello",
            ai_response="Hi there!"
        )
        
        # Assert
        assert result is None
