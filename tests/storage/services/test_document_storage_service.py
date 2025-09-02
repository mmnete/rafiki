# ==============================================================================
# tests/test_document_service.py
# ==============================================================================
import pytest
import os
import tempfile
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from app.storage.services.document_storage_service import DocumentStorageService, StoredFile

class TestDocumentStorageService:
    
    @pytest.fixture
    def mock_storage(self):
        """Mock storage service"""
        storage = Mock()
        storage.conn = MagicMock()
        return storage
    
    @pytest.fixture
    def temp_storage_path(self):
        """Create temporary directory for file storage"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def document_service(self, mock_storage, temp_storage_path):
        """Create document service with mocked storage and temp directory"""
        service = DocumentStorageService(mock_storage)
        service.base_storage_path = temp_storage_path
        return service
    
    def test_store_file_success(self, document_service, mock_storage):
        """Test successful file storage"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ['test-file-id']
        
        file_content = b"Test file content"
        
        # Act
        result = document_service.store_file(
            file_content=file_content,
            original_filename="test.pdf",
            file_category="receipt",
            owner_user_id=123,
            mime_type="application/pdf"
        )
        
        # Assert
        assert result == 'test-file-id'
        mock_cursor.execute.assert_called_once()
        assert "INSERT INTO stored_files" in mock_cursor.execute.call_args[0][0]
        
        # Verify file was written to disk
        storage_calls = mock_cursor.execute.call_args[0][1]
        storage_path = storage_calls[6]  # storage_path is the 7th parameter
        assert os.path.exists(storage_path)
        
        with open(storage_path, 'rb') as f:
            assert f.read() == file_content
    
    def test_store_file_no_connection(self, document_service):
        """Test store file when no database connection"""
        # Arrange
        document_service.storage.conn = None
        
        # Act
        result = document_service.store_file(
            file_content=b"test",
            original_filename="test.pdf",
            file_category="receipt"
        )
        
        # Assert
        assert result is None
    
    def test_get_file_success(self, document_service, mock_storage):
        """Test successful file retrieval"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = [
            'file-id', 'test.pdf', 'pdf', 'receipt', 1024,
            'application/pdf', '/path/to/file', None, 123,
            'booking-123', None, None, datetime.now()
        ]
        
        # Act
        result = document_service.get_file('file-id')
        
        # Assert
        assert result is not None
        assert isinstance(result, StoredFile)
        assert result.id == 'file-id'
        assert result.original_filename == 'test.pdf'
        assert result.file_category == 'receipt'
        assert result.owner_user_id == 123
    
    def test_get_file_not_found(self, document_service, mock_storage):
        """Test get file when file not found"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        
        # Act
        result = document_service.get_file('non-existent')
        
        # Assert
        assert result is None
    
    def test_get_file_content_success(self, document_service, mock_storage, temp_storage_path):
        """Test successful file content retrieval"""
        # Arrange
        test_content = b"Test file content"
        test_file_path = os.path.join(temp_storage_path, "test.pdf")
        
        # Create test file
        with open(test_file_path, 'wb') as f:
            f.write(test_content)
        
        # Mock get_file to return file record
        mock_file = StoredFile(
            id='file-id',
            original_filename='test.pdf',
            file_type='pdf',
            file_category='receipt',
            file_size_bytes=len(test_content),
            mime_type='application/pdf',
            storage_path=test_file_path,
            storage_url=None,
            owner_user_id=123,
            related_booking_id=None,
            related_passenger_id=None,
            expires_at=None,
            created_at=datetime.now()
        )
        
        with patch.object(document_service, 'get_file', return_value=mock_file):
            # Act
            result = document_service.get_file_content('file-id')
            
            # Assert
            assert result == test_content
    
    def test_get_file_content_file_not_found(self, document_service):
        """Test get file content when file doesn't exist"""
        # Arrange
        with patch.object(document_service, 'get_file', return_value=None):
            # Act
            result = document_service.get_file_content('non-existent')
            
            # Assert
            assert result is None
    
    def test_get_files_by_booking_success(self, document_service, mock_storage):
        """Test getting files by booking ID"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            ['file1', 'receipt.pdf', 'pdf', 'receipt', 1024, 'application/pdf', '/path1', None, 123, 'booking-123', None, None, datetime.now()],
            ['file2', 'ticket.pdf', 'pdf', 'ticket', 2048, 'application/pdf', '/path2', None, 123, 'booking-123', None, None, datetime.now()]
        ]
        
        # Act
        result = document_service.get_files_by_booking('booking-123')
        
        # Assert
        assert len(result) == 2
        assert all(isinstance(f, StoredFile) for f in result)
        assert result[0].file_category == 'receipt'
        assert result[1].file_category == 'ticket'
    
    def test_delete_file_success(self, document_service, mock_storage, temp_storage_path):
        """Test successful file deletion"""
        # Arrange
        test_file_path = os.path.join(temp_storage_path, "test.pdf")
        with open(test_file_path, 'wb') as f:
            f.write(b"test content")
        
        mock_file = StoredFile(
            id='file-id',
            original_filename='test.pdf',
            file_type='pdf',
            file_category='receipt',
            file_size_bytes=12,
            mime_type='application/pdf',
            storage_path=test_file_path,
            storage_url=None,
            owner_user_id=123,
            related_booking_id=None,
            related_passenger_id=None,
            expires_at=None,
            created_at=datetime.now()
        )
        
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 1
        
        with patch.object(document_service, 'get_file', return_value=mock_file):
            # Act
            result = document_service.delete_file('file-id')
            
            # Assert
            assert result is True
            assert not os.path.exists(test_file_path)
            mock_cursor.execute.assert_called_once()
    
    def test_delete_file_not_found(self, document_service):
        """Test delete file when file not found"""
        # Arrange
        with patch.object(document_service, 'get_file', return_value=None):
            # Act
            result = document_service.delete_file('non-existent')
            
            # Assert
            assert result is False
    
    def test_cleanup_expired_files_success(self, document_service, mock_storage, temp_storage_path):
        """Test cleanup of expired files"""
        # Arrange
        test_file_path = os.path.join(temp_storage_path, "expired.pdf")
        with open(test_file_path, 'wb') as f:
            f.write(b"expired content")
        
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [['file-id', test_file_path]]
        mock_cursor.rowcount = 1
        
        # Act
        result = document_service.cleanup_expired_files()
        
        # Assert
        assert result == 1
        assert not os.path.exists(test_file_path)
        assert mock_cursor.execute.call_count == 2  # SELECT and DELETE
    
    def test_exception_handling_in_store_file(self, document_service, mock_storage):
        """Test exception handling in store_file"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Database error")
        
        # Act
        result = document_service.store_file(
            file_content=b"test",
            original_filename="test.pdf",
            file_category="receipt"
        )
        
        # Assert
        assert result is None