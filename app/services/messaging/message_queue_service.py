from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import threading
import uuid
from enum import Enum

from app.services.messaging.cancellation_aware_processor import CancellationAwareProcessor

class MessageStatus(Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class QueuedMessage:
    id: str
    phone_number: str
    message: str
    media_urls: List[Dict[str, str]]
    timestamp: datetime
    status: MessageStatus = MessageStatus.QUEUED
    cancellation_event: threading.Event = field(default_factory=threading.Event)

class MessageQueueService:
    """
    SERVICE: Contains business logic for message queuing, cancellation, and retry
    
    Business Rules:
    - When new message arrives during processing, cancel current and combine
    - Maintain processing state across requests
    - Handle thread-safe queue operations
    """
    def __init__(self, conversation_handler, prompt_builder):
        self.active_messages: Dict[str, QueuedMessage] = {}
        self.message_history: Dict[str, List[QueuedMessage]] = {}
        self._lock = threading.Lock()
        
        # Dependencies - could be injected
        self.conversation_handler = conversation_handler
        self.prompt_builder = prompt_builder
    
    def queue_message(self, phone_number: str, message: str, media_urls: List[Dict[str, str]]) -> QueuedMessage:
        """
        BUSINESS LOGIC: Queue message with cancellation/combination rules
        """
        with self._lock:
            message_id = str(uuid.uuid4())
            current_time = datetime.now()
            
            # Business Rule: Check for active processing
            active_message = self.active_messages.get(phone_number)
            
            if active_message and active_message.status == MessageStatus.PROCESSING:
                # Business Rule: Cancel current and combine messages
                self._cancel_processing(phone_number)
                combined_message = self._combine_messages(active_message.message, message)
                
                new_message = QueuedMessage(
                    id=message_id,
                    phone_number=phone_number,
                    message=combined_message,
                    media_urls=media_urls,
                    timestamp=current_time
                )
            else:
                # Business Rule: No active processing, create new message
                new_message = QueuedMessage(
                    id=message_id,
                    phone_number=phone_number,
                    message=message,
                    media_urls=media_urls,
                    timestamp=current_time
                )
            
            # Update state
            self.active_messages[phone_number] = new_message
            self._add_to_history(phone_number, new_message)
            
            return new_message
    
    def start_processing_if_ready(self, phone_number: str):
        """Start processing if message is queued and ready"""
        with self._lock:
            message = self.active_messages.get(phone_number)
            if message and message.status == MessageStatus.QUEUED:
                message.status = MessageStatus.PROCESSING
                self._start_async_processing(message)
    
    def is_processing(self, phone_number: str) -> bool:
        """Check if user has message being processed"""
        message = self.active_messages.get(phone_number)
        return message is not None and message.status == MessageStatus.PROCESSING
    
    def should_cancel_processing(self, phone_number: str) -> bool:
        """Check if processing should be cancelled (called by processor)"""
        message = self.active_messages.get(phone_number)
        if message and message.status == MessageStatus.PROCESSING:
            return message.cancellation_event.is_set()
        return False
    
    def complete_processing(self, phone_number: str, success: bool = True):
        """Mark processing as completed"""
        with self._lock:
            message = self.active_messages.get(phone_number)
            if message:
                message.status = MessageStatus.COMPLETED if success else MessageStatus.FAILED
    
    def get_queue_info(self, phone_number: str) -> dict:
        """Get queue information for debugging"""
        message = self.active_messages.get(phone_number)
        if not message:
            return {"phone_number": phone_number, "status": "no_active_message"}
        
        return {
            "phone_number": phone_number,
            "message_id": message.id,
            "status": message.status.value,
            "timestamp": message.timestamp.isoformat(),
            "has_media": len(message.media_urls) > 0,
            "message_preview": message.message[:100] + "..." if len(message.message) > 100 else message.message
        }
    
    def clear_queue(self, phone_number: str):
        """Clear queue for phone number"""
        with self._lock:
            if phone_number in self.active_messages:
                self._cancel_processing(phone_number)
                del self.active_messages[phone_number]
    
    # Private methods - internal business logic
    def _cancel_processing(self, phone_number: str):
        """Business Logic: Cancel active processing"""
        message = self.active_messages.get(phone_number)
        if message and message.status == MessageStatus.PROCESSING:
            message.status = MessageStatus.CANCELLED
            message.cancellation_event.set()
    
    def _combine_messages(self, previous_message: str, new_message: str) -> str:
        """Business Logic: How to combine messages"""
        return f"{previous_message}\n\n[Additional message:]\n{new_message}"
    
    def _add_to_history(self, phone_number: str, message: QueuedMessage):
        """Maintain message history"""
        if phone_number not in self.message_history:
            self.message_history[phone_number] = []
        self.message_history[phone_number].append(message)
        
        # Business Rule: Keep only last 10 messages
        self.message_history[phone_number] = self.message_history[phone_number][-10:]
    
    def _start_async_processing(self, message: QueuedMessage):
        """Start background processing"""
        thread = threading.Thread(
            target=self._process_with_cancellation,
            args=(message,),
            daemon=True
        )
        thread.start()
    
    def _process_with_cancellation(self, message: QueuedMessage):
        """Process message with cancellation support using new processor"""
        try:
            # Create cancellation-aware processor
            processor = CancellationAwareProcessor(
                self.conversation_handler, 
                self.prompt_builder
            )
            
            # Create cancellation check function
            def check_cancellation():
                return self.should_cancel_processing(message.phone_number)
            
            # Process message
            response = processor.process_message_async(
                phone_number=message.phone_number,
                message=message.message,
                media_urls=message.media_urls,
                cancellation_check=check_cancellation
            )
            
            if response is not None:
                self.complete_processing(message.phone_number, success=True)
            else:
                print(f"Message processing was cancelled for {message.phone_number}")
                
        except Exception as e:
            self.complete_processing(message.phone_number, success=False)
            print(f"Processing error: {e}")
