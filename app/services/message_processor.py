from app.controllers.conversation_manager import ConversationManager
from twilio.twiml.messaging_response import MessagingResponse
import threading
import time
from collections import defaultdict
import os
import json
from datetime import datetime, timedelta

# Try to import Redis, fallback to local storage if not available
try:
    import redis
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
            print("Using Redis for processing status storage")
        else:
            self.local_storage = defaultdict(lambda: {"is_processing": False, "last_request_time": None})
            print("Using local storage for processing status")
    
    def _should_use_redis(self):
        """Determine if we should use Redis based on environment, with debugging output."""
        
        # Use Redis if:
        # 1. Redis is available (installed)
        # 2. We're in production (REDIS_URL exists) OR explicitly enabled for local testing

        redis_url = os.getenv('REDIS_URL')
        local_redis_enabled = os.getenv('USE_LOCAL_REDIS', 'false').lower() == 'true'

        # Debugging checks
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
        except Exception as e:
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
                # Set with expiration of 1 hour as safety net
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
                    status = json.loads(status_json)
                    # Parse datetime if it exists
                    if status["last_request_time"]:
                        status["last_request_time"] = datetime.fromisoformat(status["last_request_time"])
                    return status
                else:
                    return {"is_processing": False, "last_request_time": None}
            except Exception as e:
                print(f"Redis error: {e}, falling back to local storage")
                # Fixed: Handle case where phone_number doesn't exist in local storage
                return self.local_storage.get(phone_number, {"is_processing": False, "last_request_time": None})
        else:
            # Fixed: Handle case where phone_number doesn't exist in local storage
            return self.local_storage.get(phone_number, {"is_processing": False, "last_request_time": None})
    
    def clear_processing_status(self, phone_number):
        """Clear processing status for a phone number"""
        if self.use_redis and self.redis_client:
            try:
                key = f"processing_status:{phone_number}"
                self.redis_client.delete(key)
                key = f"processing_status:{phone_number}"
                print("deleted processing_status")
            except Exception as e:
                print(f"Redis error: {e}")
        
        # Always clear from local storage as fallback
        if phone_number in self.local_storage:
            del self.local_storage[phone_number]

# Initialize storage manager
redis_storage_manager = RedisStorageManager()

class MessageProcessor:
    def __init__(self, conversation_manager: ConversationManager):
        self.conv_manager = conversation_manager
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_number = os.getenv("TWILIO_PHONE_NUMBER")
    
    def send_delayed_response(self, phone_number, message):
        """Send a response back to the user via Twilio API or store for testing"""
        if self.conv_manager.test_mode:
            # In test mode, store the response instead of sending
            self.conv_manager.test_responses.append({
                "phone_number": phone_number,
                "message": message,
                "timestamp": datetime.now().isoformat()
            })
            print(f"TEST MODE - Would send to {phone_number}: {message}")
            return
            
        try:
            from twilio.rest import Client
            client = Client(self.account_sid, self.auth_token)
            
            client.messages.create(
                body=message,
                from_=f"whatsapp:{self.twilio_number}",
                to=f"whatsapp:{phone_number}"
            )
            print(f"Sent delayed response to {phone_number}")
        except Exception as e:
            print(f"Error sending delayed response: {e}")
    
    def send_progress_updates(self, phone_number, user_message):
        """Send encouraging progress updates during long processing"""
        try:
            # Get user for personalization
            user, _ = self.conv_manager.user_service.get_or_create_user(phone_number)
            first_name = user.first_name if user and user.first_name else ""
            
            # Wait a bit before first update
            if not self.conv_manager.test_mode:
                time.sleep(8)
            else:
                time.sleep(2)  # Faster for testing
            
            # Check if still processing
            status = redis_storage_manager.get_processing_status(phone_number)
            if status["is_processing"]:
                if first_name:
                    update_message = f"Usijali {first_name}... subiri kidogo nipo nakusaidia hapa! 😊💪"
                else:
                    update_message = "Ninashughulika na maombi yako... Subiri kidogo! 🔄✨"
                
                self.send_delayed_response(phone_number, update_message)
            
            # Wait more and send another update if still processing
            if not self.conv_manager.test_mode:
                time.sleep(12)
            else:
                time.sleep(3)  # Faster for testing
            
            status = redis_storage_manager.get_processing_status(phone_number)
            if status["is_processing"]:
                if first_name:
                    update_message = f"Karibu {first_name}! Bado ninafanya kazi... Majibu mazuri yanakuja! 🚀"
                else:
                    update_message = "Bado ninakusanyisha majibu yako bora... Hivi karibuni! 📊⏳"
                
                self.send_delayed_response(phone_number, update_message)
                
        except Exception as e:
            print(f"Error sending progress updates: {e}")
    
    def process_message_async(self, phone_number, user_message):
        """Process message in background thread"""
        try:
            # Mark as processing
            redis_storage_manager.set_processing_status(phone_number, True, datetime.now())
            
            # Start progress updates in a separate thread
            progress_thread = threading.Thread(
                target=self.send_progress_updates,
                args=(phone_number, user_message)
            )
            progress_thread.daemon = True
            progress_thread.start()
            
            # Process the message (this is where the long-running model call happens)
            reply = self.conv_manager.handle_message(phone_number, user_message)
            
            # Send the final response back to user
            self.send_delayed_response(phone_number, reply)
            
        except Exception as e:
            error_message = "Samahani, kuna tatizo. Tafadhali jaribu tena baadaye."
            self.send_delayed_response(phone_number, error_message)
            print(f"Error processing message: {e}")
        
        finally:
            # Clear processing status
            redis_storage_manager.clear_processing_status(phone_number)

# Helper functions for the main Flask route
def get_processing_status(phone_number):
    """Get processing status for a phone number"""
    return redis_storage_manager.get_processing_status(phone_number)

def set_processing_status(phone_number, is_processing, last_request_time=None):
    """Set processing status for a phone number"""
    redis_storage_manager.set_processing_status(phone_number, is_processing, last_request_time)

def clear_processing_status(phone_number):
    """Clear processing status for a phone number"""
    redis_storage_manager.clear_processing_status(phone_number)