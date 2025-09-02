from typing import List
from .base_schema import BaseSchema

class DocumentSchema(BaseSchema):
    """Simple document and file storage schema"""
    
    def get_table_definitions(self) -> List[str]:
        return [
            """
            CREATE TABLE IF NOT EXISTS stored_files (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                
                -- File Basics
                original_filename VARCHAR(500),
                file_type VARCHAR(50) NOT NULL,
                file_category VARCHAR(50) NOT NULL,
                file_size_bytes BIGINT,
                mime_type VARCHAR(100),
                
                -- Storage
                storage_path TEXT NOT NULL,
                storage_url TEXT,
                
                -- Ownership and Access
                owner_user_id INT REFERENCES users(id) ON DELETE SET NULL,
                related_booking_id UUID REFERENCES bookings(id) ON DELETE CASCADE,
                related_passenger_id UUID REFERENCES passenger_profiles(id) ON DELETE CASCADE,
                
                -- Lifecycle
                expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '5 years'),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Constraints
                CONSTRAINT valid_file_category CHECK (file_category IN (
                    'booking_confirmation', 'boarding_pass', 'receipt', 'passport_image', 
                    'id_document', 'ticket', 'invoice', 'other'
                ))
            );
            """
        ]
    
    def get_indexes(self) -> List[str]:
        return [
            "CREATE INDEX IF NOT EXISTS idx_stored_files_owner ON stored_files(owner_user_id);",
            "CREATE INDEX IF NOT EXISTS idx_stored_files_category ON stored_files(file_category);",
            "CREATE INDEX IF NOT EXISTS idx_stored_files_booking ON stored_files(related_booking_id);",
            "CREATE INDEX IF NOT EXISTS idx_stored_files_expires ON stored_files(expires_at);",
        ]
    