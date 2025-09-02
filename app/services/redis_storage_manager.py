from collections import defaultdict
from datetime import datetime, timedelta
import os
import json
from typing import Any, Optional

# Try to import Redis and its exceptions, fallback to local storage if not available
try:
    import redis
    # Import specific exceptions after the module is successfully imported
    from redis import exceptions as redis_exceptions 
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("Redis not available, using local storage for development")

class RedisStorageManager:
    """Handles both Redis and local storage for processing status"""
    
    def __init__(self):
        self.use_redis = self._should_use_redis()
        self.local_storage = defaultdict(lambda: {"is_processing": False, "last_request_time": None})
        self.redis_client = None
        
        if self.use_redis:
            self.redis_client = self._get_redis_client()
            if self.redis_client:
                print("Using Redis for processing status storage")
            else:
                self.use_redis = False  # Fallback if client connection fails
                print("Failed to connect to Redis, falling back to local storage")
        else:
            print("Using local storage for processing status")
    
    def _should_use_redis(self):
        """Determine if we should use Redis based on environment, with debugging output."""
        redis_url = os.getenv('REDIS_URL')
        local_redis_enabled = os.getenv('USE_LOCAL_REDIS', 'false').lower() == 'true'

        if not REDIS_AVAILABLE:
            print("DEBUG: Redis is NOT available (library not installed or import failed).")
            return False

        if redis_url:
            print(f"DEBUG: Found REDIS_URL environment variable. Using Redis.")
            return True

        if local_redis_enabled:
            print(f"DEBUG: USE_LOCAL_REDIS is set to '{os.getenv('USE_LOCAL_REDIS')}'. Using Redis.")
            return True

        print("DEBUG: REDIS_URL not found and USE_LOCAL_REDIS is not 'true'. Not using Redis.")
        return False
    
    def _get_redis_client(self):
        """Get Redis client for production or local development"""
        try:
            redis_url = os.getenv('REDIS_URL')
            if redis_url:
                # Production (Heroku) - use provided REDIS_URL
                return redis.from_url(redis_url, decode_responses=True, ssl_cert_reqs=None)
            else:
                # Local Redis for testing
                return redis.Redis(
                    host=os.getenv('REDIS_HOST', 'localhost'),
                    port=int(os.getenv('REDIS_PORT', 6379)),
                    db=0,
                    decode_responses=True
                )
        except redis_exceptions.ConnectionError as e: # Use the imported alias
            print(f"Failed to connect to Redis: {e}")
            print("Falling back to local storage")
            return None
    
    def set_processing_status(self, phone_number, is_processing, last_request_time=None):
        """Set processing status for a phone number"""
        if self.use_redis and self.redis_client:
            try:
                key = f"processing_status:{phone_number}"
                status = {
                    "is_processing": is_processing,
                    "last_request_time": last_request_time.isoformat() if last_request_time else None
                }
                self.redis_client.setex(key, 3600, json.dumps(status))
            except Exception as e:
                print(f"Redis error: {e}, falling back to local storage")
                self.local_storage[phone_number] = {
                    "is_processing": is_processing, 
                    "last_request_time": last_request_time
                }
        else:
            self.local_storage[phone_number] = {
                "is_processing": is_processing, 
                "last_request_time": last_request_time
            }
    
    def get_processing_status(self, phone_number):
        """Get processing status for a phone number"""
        if self.use_redis and self.redis_client:
            try:
                key = f"processing_status:{phone_number}"
                status_json = self.redis_client.get(key)
                if status_json:
                    status = json.loads(status_json) # type: ignore
                    if status["last_request_time"]:
                        status["last_request_time"] = datetime.fromisoformat(status["last_request_time"])
                    return status
                else:
                    return {"is_processing": False, "last_request_time": None}
            except Exception as e:
                print(f"Redis error: {e}, falling back to local storage")
                return self.local_storage.get(phone_number, {"is_processing": False, "last_request_time": None})
        else:
            return self.local_storage.get(phone_number, {"is_processing": False, "last_request_time": None})
    
    def clear_processing_status(self, phone_number):
        """Clear processing status for a phone number"""
        if self.use_redis and self.redis_client:
            try:
                key = f"processing_status:{phone_number}"
                self.redis_client.delete(key)
                print("deleted processing_status")
            except Exception as e:
                print(f"Redis error: {e}")
        
        if phone_number in self.local_storage:
            del self.local_storage[phone_number]
    
    def set_data(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Stores generic data with an optional Time-To-Live (TTL).
        
        Args:
            key (str): The unique key to store the data under.
            value (Any): The data to store. Must be JSON-serializable.
            ttl (Optional[int]): The time-to-live in seconds. If None, no expiration is set.
        """
        if self.use_redis and self.redis_client:
            try:
                json_value = json.dumps(value)
                if ttl:
                    self.redis_client.setex(key, ttl, json_value)
                else:
                    self.redis_client.set(key, json_value)
            except (redis_exceptions.ConnectionError, TypeError, Exception) as e:
                print(f"Redis set_data error for key '{key}': {e}, falling back to local storage.")
                self.local_storage[key] = value
        else:
            self.local_storage[key] = value

    def get_data(self, key: str) -> Optional[Any]:
        """
        Retrieves generic data by key.
        
        Args:
            key (str): The unique key for the data.
            
        Returns:
            Optional[Any]: The retrieved data, deserialized from JSON, or None if the key doesn't exist.
        """
        if self.use_redis and self.redis_client:
            try:
                json_value = self.redis_client.get(key)
                if json_value:
                    return json.loads(json_value) # type: ignore
                else:
                    return None
            except (redis_exceptions.ConnectionError, json.JSONDecodeError, Exception) as e:
                print(f"Redis get_data error for key '{key}': {e}, falling back to local storage.")
                return self.local_storage.get(key, None)
        else:
            return self.local_storage.get(key, None)

# Initialize storage manager
implemented_redis_storage_manager = RedisStorageManager()