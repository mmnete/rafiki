from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
from collections import defaultdict

from app.services.redis_storage_manager import implemented_redis_storage_manager

class RateLimitService:
    """
    SERVICE: Rate limiting with Redis/local storage fallback
    
    Rate limiting strategies:
    1. Requests per minute limit
    2. Cooldown period between requests  
    3. Burst protection
    """
    
    # Configuration
    MAX_REQUESTS_PER_MINUTE = 10
    COOLDOWN_SECONDS = 5
    BURST_THRESHOLD = 3  # Max requests in burst window
    BURST_WINDOW_SECONDS = 10
    
    def __init__(self):
        # Fallback local storage (only used if Redis fails)
        self.local_request_history = defaultdict(list)
        self.local_last_request = {}
    
    def is_rate_limited(self, phone_number: str) -> bool:
        """
        Check if phone number is rate limited
        
        Returns True if user should be rate limited
        """
        current_time = datetime.now()
        
        # Check cooldown period
        if self._is_in_cooldown(phone_number, current_time):
            return True
        
        # Check requests per minute
        if self._exceeds_per_minute_limit(phone_number, current_time):
            return True
        
        # Check burst protection
        if self._exceeds_burst_limit(phone_number, current_time):
            return True
        
        # Update request history
        self._record_request(phone_number, current_time)
        
        return False
    
    def is_in_cooldown(self, last_request_time: Optional[datetime], current_time: datetime) -> bool:
        """
        Check if user is in cooldown period (for message processing logic)
        This is separate from rate limiting - used by message queue
        """
        if not last_request_time:
            return False
        return (current_time - last_request_time).total_seconds() < self.COOLDOWN_SECONDS
    
    def get_rate_limit_info(self, phone_number: str) -> dict:
        """Get rate limiting information for debugging"""
        current_time = datetime.now()
        
        # Get request history
        request_history = self._get_request_history(phone_number)
        recent_requests = self._filter_recent_requests(request_history, current_time, minutes=1)
        
        # Get last request time
        last_request = self._get_last_request_time(phone_number)
        
        # Calculate remaining limits
        requests_remaining = max(0, self.MAX_REQUESTS_PER_MINUTE - len(recent_requests))
        
        # Calculate cooldown remaining
        cooldown_remaining = 0
        if last_request:
            cooldown_elapsed = (current_time - last_request).total_seconds()
            cooldown_remaining = max(0, self.COOLDOWN_SECONDS - cooldown_elapsed)
        
        return {
            "phone_number": phone_number,
            "requests_in_last_minute": len(recent_requests),
            "requests_remaining": requests_remaining,
            "cooldown_remaining_seconds": round(cooldown_remaining, 2),
            "is_rate_limited": self.is_rate_limited(phone_number),
            "last_request_time": last_request.isoformat() if last_request else None
        }
    
    def clear_rate_limit(self, phone_number: str):
        """Clear rate limiting data for phone number (debugging)"""
        # Clear from Redis/storage
        history_key = f"rate_limit_history:{phone_number}"
        last_request_key = f"rate_limit_last:{phone_number}"
        
        implemented_redis_storage_manager.set_data(history_key, [])
        implemented_redis_storage_manager.set_data(last_request_key, None)
        
        # Clear from local fallback
        if phone_number in self.local_request_history:
            del self.local_request_history[phone_number]
        if phone_number in self.local_last_request:
            del self.local_last_request[phone_number]
    
    def reset_all_rate_limits(self):
        """Clear all rate limiting data (debugging/admin)"""
        # Note: This only clears local fallback
        # For Redis, you'd need to scan and delete keys or use a different approach
        self.local_request_history.clear()
        self.local_last_request.clear()
    
    # Private methods
    def _is_in_cooldown(self, phone_number: str, current_time: datetime) -> bool:
        """Check if user is in cooldown period"""
        last_request = self._get_last_request_time(phone_number)
        if not last_request:
            return False
        
        elapsed = (current_time - last_request).total_seconds()
        return elapsed < self.COOLDOWN_SECONDS
    
    def _exceeds_per_minute_limit(self, phone_number: str, current_time: datetime) -> bool:
        """Check if user exceeds requests per minute limit"""
        request_history = self._get_request_history(phone_number)
        recent_requests = self._filter_recent_requests(request_history, current_time, minutes=1)
        
        return len(recent_requests) >= self.MAX_REQUESTS_PER_MINUTE
    
    def _exceeds_burst_limit(self, phone_number: str, current_time: datetime) -> bool:
        """Check if user exceeds burst limit"""
        request_history = self._get_request_history(phone_number)
        burst_requests = self._filter_recent_requests(
            request_history, 
            current_time, 
            seconds=self.BURST_WINDOW_SECONDS
        )
        
        return len(burst_requests) >= self.BURST_THRESHOLD
    
    def _record_request(self, phone_number: str, request_time: datetime):
        """Record a new request"""
        # Update request history
        history_key = f"rate_limit_history:{phone_number}"
        request_history = self._get_request_history(phone_number)
        
        # Add new request
        request_history.append(request_time.isoformat())
        
        # Keep only recent requests (last 5 minutes for cleanup)
        cutoff_time = request_time - timedelta(minutes=5)
        request_history = [
            req_time for req_time in request_history 
            if datetime.fromisoformat(req_time) > cutoff_time
        ]
        
        # Store updated history with TTL of 1 hour
        implemented_redis_storage_manager.set_data(history_key, request_history, ttl=3600)
        
        # Update last request time
        last_request_key = f"rate_limit_last:{phone_number}"
        implemented_redis_storage_manager.set_data(
            last_request_key, 
            request_time.isoformat(), 
            ttl=3600
        )
    
    def _get_request_history(self, phone_number: str) -> List[str]:
        """Get request history for phone number"""
        history_key = f"rate_limit_history:{phone_number}"
        
        # Try to get from storage
        history = implemented_redis_storage_manager.get_data(history_key)
        if history is not None:
            return history
        
        # Fallback to local storage
        return self.local_request_history.get(phone_number, [])
    
    def _get_last_request_time(self, phone_number: str) -> Optional[datetime]:
        """Get last request time for phone number"""
        last_request_key = f"rate_limit_last:{phone_number}"
        
        # Try to get from storage  
        last_request_str = implemented_redis_storage_manager.get_data(last_request_key)
        if last_request_str:
            return datetime.fromisoformat(last_request_str)
        
        # Fallback to local storage
        return self.local_last_request.get(phone_number)
    
    def _filter_recent_requests(self, request_history: List[str], current_time: datetime, 
                               minutes: int = 0, seconds: int = 0) -> List[str]:
        """Filter request history to only recent requests"""
        if not request_history:
            return []
        
        cutoff_time = current_time - timedelta(minutes=minutes, seconds=seconds)
        
        recent_requests = []
        for req_time_str in request_history:
            try:
                req_time = datetime.fromisoformat(req_time_str)
                if req_time > cutoff_time:
                    recent_requests.append(req_time_str)
            except (ValueError, TypeError):
                # Skip invalid datetime strings
                continue
        
        return recent_requests