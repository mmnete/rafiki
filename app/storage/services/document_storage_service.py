# ==============================================================================
# app/services/document_service.py
# ==============================================================================
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import uuid
import os
from app.storage.db_service import StorageService

@dataclass
class StoredFile:
    id: str
    original_filename: Optional[str]
    file_type: str
    file_category: str
    file_size_bytes: Optional[int]
    mime_type: Optional[str]
    storage_path: str
    storage_url: Optional[str]
    owner_user_id: Optional[int]
    related_booking_id: Optional[str]
    related_passenger_id: Optional[str]
    expires_at: Optional[datetime]
    created_at: Optional[datetime]

class DocumentStorageService:
    """
    Service for managing file storage and document operations
    
    Responsibilities:
    - Store and retrieve files
    - Link files to users, bookings, and passengers
    - Manage file lifecycle and expiration
    - Generate storage paths and URLs
    """
    
    def __init__(self, storage: StorageService):
        self.storage = storage
        self.base_storage_path = os.getenv('FILE_STORAGE_PATH', '/app/storage/files')
    
    def store_file(self, file_content: bytes, original_filename: str, file_category: str,
                   owner_user_id: Optional[int] = None, related_booking_id: Optional[str] = None,
                   related_passenger_id: Optional[str] = None, mime_type: Optional[str] = None) -> Optional[str]:
        """Store a file and create database record"""
        if not self.storage.conn:
            return None
        
        try:
            file_id = str(uuid.uuid4())
            file_extension = os.path.splitext(original_filename)[1]
            storage_filename = f"{file_id}{file_extension}"
            storage_path = os.path.join(self.base_storage_path, file_category, storage_filename)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(storage_path), exist_ok=True)
            
            # Write file to disk
            with open(storage_path, 'wb') as f:
                f.write(file_content)
            
            # Store in database
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO stored_files (
                        id, original_filename, file_type, file_category, file_size_bytes,
                        mime_type, storage_path, owner_user_id, related_booking_id, 
                        related_passenger_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (
                    file_id, original_filename, file_extension.lstrip('.'), file_category,
                    len(file_content), mime_type, storage_path, owner_user_id,
                    related_booking_id, related_passenger_id
                ))
                
                result = cur.fetchone()
                if result:
                    return result[0]
                else:
                    print("Store file returned no result")
                    return None
                
        except Exception as e:
            print(f"Error storing file: {e}")
            return None
    
    def get_file(self, file_id: str) -> Optional[StoredFile]:
        """Get file metadata by ID"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, original_filename, file_type, file_category, file_size_bytes,
                           mime_type, storage_path, storage_url, owner_user_id,
                           related_booking_id, related_passenger_id, expires_at, created_at
                    FROM stored_files
                    WHERE id = %s AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP);
                """, (file_id,))
                
                row = cur.fetchone()
                if row:
                    return StoredFile(
                        id=row[0],
                        original_filename=row[1],
                        file_type=row[2],
                        file_category=row[3],
                        file_size_bytes=row[4],
                        mime_type=row[5],
                        storage_path=row[6],
                        storage_url=row[7],
                        owner_user_id=row[8],
                        related_booking_id=row[9],
                        related_passenger_id=row[10],
                        expires_at=row[11],
                        created_at=row[12]
                    )
                return None
                
        except Exception as e:
            print(f"Error getting file: {e}")
            return None
    
    def get_file_content(self, file_id: str) -> Optional[bytes]:
        """Get file content from disk"""
        file_record = self.get_file(file_id)
        if not file_record:
            return None
        
        try:
            with open(file_record.storage_path, 'rb') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file content: {e}")
            return None
    
    def get_files_by_booking(self, booking_id: str) -> List[StoredFile]:
        """Get all files related to a booking"""
        if not self.storage.conn:
            return []
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, original_filename, file_type, file_category, file_size_bytes,
                           mime_type, storage_path, storage_url, owner_user_id,
                           related_booking_id, related_passenger_id, expires_at, created_at
                    FROM stored_files
                    WHERE related_booking_id = %s 
                    AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                    ORDER BY created_at DESC;
                """, (booking_id,))
                
                files = []
                for row in cur.fetchall():
                    files.append(StoredFile(
                        id=row[0],
                        original_filename=row[1],
                        file_type=row[2],
                        file_category=row[3],
                        file_size_bytes=row[4],
                        mime_type=row[5],
                        storage_path=row[6],
                        storage_url=row[7],
                        owner_user_id=row[8],
                        related_booking_id=row[9],
                        related_passenger_id=row[10],
                        expires_at=row[11],
                        created_at=row[12]
                    ))
                return files
                
        except Exception as e:
            print(f"Error getting files by booking: {e}")
            return []
    
    def delete_file(self, file_id: str) -> bool:
        """Delete file from both database and disk"""
        file_record = self.get_file(file_id)
        if not file_record:
            return False
        
        try:
            if not self.storage.conn:
                raise Exception("No database connection")
            
            # Delete from database
            with self.storage.conn.cursor() as cur:
                cur.execute("DELETE FROM stored_files WHERE id = %s;", (file_id,))
                deleted = cur.rowcount > 0
            
            # Delete from disk if database deletion was successful
            if deleted and os.path.exists(file_record.storage_path):
                os.remove(file_record.storage_path)
            
            return deleted
            
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False
    
    def cleanup_expired_files(self) -> int:
        """Clean up expired files from database and disk"""
        if not self.storage.conn:
            return 0
        
        try:
            # Get expired files first to delete from disk
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, storage_path FROM stored_files 
                    WHERE expires_at < CURRENT_TIMESTAMP;
                """)
                
                expired_files = cur.fetchall()
                
                # Delete from database
                cur.execute("""
                    DELETE FROM stored_files 
                    WHERE expires_at < CURRENT_TIMESTAMP;
                """)
                
                deleted_count = cur.rowcount
                
                # Delete files from disk
                for file_id, storage_path in expired_files:
                    try:
                        if os.path.exists(storage_path):
                            os.remove(storage_path)
                    except Exception as e:
                        print(f"Error deleting expired file {file_id}: {e}")
                
                print(f"Cleaned up {deleted_count} expired files")
                return deleted_count
                
        except Exception as e:
            print(f"Error cleaning up expired files: {e}")
            return 0