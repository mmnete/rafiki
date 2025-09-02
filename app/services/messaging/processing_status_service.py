# app/services/processing_status_service.py
from datetime import datetime, timedelta
from typing import Optional
from app.services.messaging.rate_limit_service import RateLimitService
from twilio.twiml.messaging_response import MessagingResponse
from app.services.redis_storage_manager import implemented_redis_storage_manager

class ProcessingStatusService:
    """
    SERVICE: Message processing status management
    Uses the same Redis storage pattern as rate limiter
    """
    
    PROCESSING_TIMEOUT_MINUTES = 10  # Auto-clear stuck processing after 10 minutes
    
    def __init__(self):
        pass
    
    def get_processing_status(self, phone_number: str) -> dict:
        """Get processing status using storage manager"""
        return implemented_redis_storage_manager.get_processing_status(phone_number)
    
    def set_processing_status(self, phone_number: str, is_processing: bool, timestamp: datetime):
        """Set processing status using storage manager"""
        implemented_redis_storage_manager.set_processing_status(
            phone_number, 
            is_processing, 
            timestamp
        )
    
    def clear_processing_status(self, phone_number: str):
        """Clear processing status using storage manager"""
        implemented_redis_storage_manager.clear_processing_status(phone_number)
    
    def handle_processing_check(self, phone_number: str, current_time: datetime, 
                              rate_limiter: RateLimitService) -> Optional[MessagingResponse]:
        """
        Check and handle processing status with rate limiting integration
        """
        user_status = self.get_processing_status(phone_number)
        
        if not user_status["is_processing"]:
            return None
        
        # Auto-clear stuck processing (safety mechanism)
        if self._is_processing_stuck(user_status, current_time):
            print(f"Auto-clearing stuck processing for {phone_number}")
            self.clear_processing_status(phone_number)
            return None
        
        # Check cooldown period using rate limiter
        if rate_limiter.is_in_cooldown(user_status["last_request_time"], current_time):
            return MessagingResponse()  # Empty response during cooldown
        
        # Update processing timestamp and return "still thinking" message
        self.set_processing_status(phone_number, True, current_time)
        response = MessagingResponse()
        response.message("Still processing your previous message...")
        return response
    
    def _is_processing_stuck(self, user_status: dict, current_time: datetime) -> bool:
        """Check if processing has been stuck for too long"""
        if not user_status["last_request_time"]:
            return True
        
        elapsed = current_time - user_status["last_request_time"]
        return elapsed > timedelta(minutes=self.PROCESSING_TIMEOUT_MINUTES)
