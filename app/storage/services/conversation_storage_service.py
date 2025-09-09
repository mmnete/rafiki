# ==============================================================================
# app/services/conversation_service.py - Fixed version
# ==============================================================================
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import uuid
import json
import hashlib
from app.storage.db_service import StorageService

@dataclass
class Conversation:
    id: str
    user_id: int
    request: str  # user_message
    response: str  # ai_response
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    message_type: str = "chat"
    tools_used: Optional[List[str]] = None
    processing_time_ms: Optional[int] = None
    related_booking_id: Optional[str] = None
    model_used: Optional[str] = None
    has_media: bool = False
    was_helpful: Optional[bool] = None
    user_satisfaction_rating: Optional[int] = None
    feedback_provided: Optional[str] = None

@dataclass
class ConversationMedia:
    id: str
    conversation_id: str
    media_type: str
    original_url: Optional[str] = None
    ai_description: Optional[str] = None
    stored_file_id: Optional[str] = None
    created_at: Optional[datetime] = None

class ConversationStorageService:
    """
    Service for managing conversation history and context
    
    Responsibilities:
    - Save and retrieve conversation history
    - Manage conversation threading
    - Handle media attachments
    - Track AI performance metrics
    - Manage TTL and archival
    """
    
    def __init__(self, storage: StorageService):
        self.storage = storage
    
    def save_conversation(self, user_id: int, user_message: str, ai_response: str,
                         message_type: str = 'chat', tools_used: Optional[List[str]] = None,
                         processing_time_ms: Optional[int] = None, related_booking_id: Optional[str] = None,
                         model_used: Optional[str] = None, has_media: bool = False) -> Optional[str]:
        """Save a conversation entry"""
        if not self.storage.conn:
            return None
        
        try:
            conversation_id = str(uuid.uuid4())
            user_message_hash = hashlib.sha256(user_message.encode()).hexdigest()
            
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO conversations (
                        id, user_id, user_message, ai_response, user_message_hash,
                        message_type, tools_used, processing_time_ms, related_booking_id,
                        model_used, has_media
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (
                    conversation_id, user_id, user_message, ai_response, user_message_hash,
                    message_type, json.dumps(tools_used or []), processing_time_ms,
                    related_booking_id, model_used, has_media
                ))
                
                result = cur.fetchone()
                if result:
                    return result[0]
                else:
                    print("Save conversation returned no result")
                    return None
                
        except Exception as e:
            print(f"Error saving conversation: {e}")
            return None
    
    def get_conversation_history(self, user_id: int, limit: int = 10) -> List[Conversation]:
        """Get recent conversation history for user"""
        if not self.storage.conn:
            return []
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, user_id, user_message as request, ai_response as response, 
                           created_at, message_type, tools_used, related_booking_id,
                           processing_time_ms, model_used, has_media
                    FROM conversations 
                    WHERE user_id = %s AND expires_at > CURRENT_TIMESTAMP
                    ORDER BY created_at DESC 
                    LIMIT %s;
                """, (user_id, limit))
                
                conversations = []
                for row in cur.fetchall():
                    # Fix: Handle tools_used properly - it might be a JSON string or already a list
                    tools_used_list = None
                    if row[6]:
                        if isinstance(row[6], str):
                            # If it's a string, parse it as JSON
                            try:
                                tools_used_list = json.loads(row[6])
                            except json.JSONDecodeError:
                                tools_used_list = None
                        elif isinstance(row[6], list):
                            # If it's already a list, use it directly
                            tools_used_list = row[6]
                    
                    conv = Conversation(
                        id=row[0],
                        user_id=row[1],
                        request=row[2],
                        response=row[3],
                        created_at=row[4],
                        message_type=row[5],
                        tools_used=tools_used_list,
                        related_booking_id=row[7],
                        processing_time_ms=row[8],
                        model_used=row[9],
                        has_media=row[10]
                    )
                    conversations.append(conv)
                
                return list(reversed(conversations))  # Return chronological order
                
        except Exception as e:
            print(f"Error getting conversation history: {e}")
            return []
    
    def update_conversation_feedback(self, conversation_id: str, was_helpful: Optional[bool] = None,
                                   satisfaction_rating: Optional[int] = None, 
                                   feedback_text: Optional[str] = None) -> bool:
        """Update conversation with user feedback"""
        if not self.storage.conn:
            return False
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    UPDATE conversations 
                    SET was_helpful = %s, user_satisfaction_rating = %s, 
                        feedback_provided = %s
                    WHERE id = %s;
                """, (was_helpful, satisfaction_rating, feedback_text, conversation_id))
                
                return cur.rowcount > 0
                
        except Exception as e:
            print(f"Error updating conversation feedback: {e}")
            return False
    
    def save_media_for_conversation(self, conversation_id: str, media_type: str,
                                  original_url: Optional[str] = None, 
                                  ai_description: Optional[str] = None,
                                  stored_file_id: Optional[str] = None) -> Optional[str]:
        """Save media attachment for conversation"""
        if not self.storage.conn:
            return None
        
        try:
            media_id = str(uuid.uuid4())
            
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO message_media (
                        id, conversation_id, media_type, original_url, 
                        ai_description, stored_file_id
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (media_id, conversation_id, media_type, original_url, 
                     ai_description, stored_file_id))
                
                result = cur.fetchone()
                if result:
                    return result[0]
                else:
                    print("Save media conversation returned no result")
                    return None
                
        except Exception as e:
            print(f"Error saving conversation media: {e}")
            return None
    
    def get_conversations_by_booking(self, booking_id: str) -> List[Dict[str, Any]]:
        """Get all conversations related to a specific booking"""
        if not self.storage.conn:
            return []
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, user_message, ai_response, created_at, booking_stage
                    FROM conversations 
                    WHERE related_booking_id = %s
                    ORDER BY created_at;
                """, (booking_id,))
                
                return [
                    {
                        "id": row[0],
                        "user_message": row[1],
                        "ai_response": row[2],
                        "created_at": row[3],
                        "booking_stage": row[4]
                    }
                    for row in cur.fetchall()
                ]
                
        except Exception as e:
            print(f"Error getting conversations by booking: {e}")
            return []
    
    def cleanup_expired_conversations(self) -> int:
        """Clean up expired conversations (TTL management)"""
        if not self.storage.conn:
            return 0
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM conversations 
                    WHERE expires_at < CURRENT_TIMESTAMP;
                """)
                
                deleted_count = cur.rowcount
                print(f"Cleaned up {deleted_count} expired conversations")
                return deleted_count
                
        except Exception as e:
            print(f"Error cleaning up conversations: {e}")
            return 0
