# app/services/response_delivery_service.py
import requests
import time
import os
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading
from queue import Queue, Empty

# Add Twilio import
from twilio.rest import Client

@dataclass
class PendingResponse:
    phone_number: str
    message: str
    timestamp: datetime
    retries: int = 0
    max_retries: int = 3

class ResponseDeliveryService:
    """
    Handles delivery of AI responses back to users via Twilio
    
    This service manages:
    1. Queueing responses for delivery
    2. Retry logic for failed deliveries  
    3. Rate limiting outbound messages
    4. Multiple response handling (thinking -> final response)
    5. Testing integration for evaluation scripts
    """
    
    def __init__(self, twilio_client=None):
        heroku_app_name = os.getenv("HEROKU_APP_NAME")
        if heroku_app_name:
            self.flask_app_url = f"https://{heroku_app_name}.herokuapp.com"
        else:
            self.flask_app_url = "http://localhost:5000"
            
        # Initialize Twilio client from environment variables if not provided
        if twilio_client is None and not os.getenv('TEST_MODE', '').lower() == 'true':
            account_sid = os.getenv('TWILIO_ACCOUNT_SID')
            auth_token = os.getenv('TWILIO_AUTH_TOKEN')
            
            if account_sid and auth_token:
                self.twilio_client = Client(account_sid, auth_token)
                print("✅ Twilio client initialized from environment variables")
            else:
                self.twilio_client = None
                print("⚠️  Twilio credentials not found in environment")
        else:
            self.twilio_client = twilio_client
            
        # Get Twilio phone number from environment
        self.twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER', '+14155238886')

        self.delivery_queue = Queue()
        self.delivery_thread = None
        self.is_running = False
        self._lock = threading.Lock()
        
        # Rate limiting: max 1 message per second per number
        self.last_sent = {}  # phone_number -> timestamp
        self.min_interval = 1.0  # seconds between messages
        
        # For testing: store responses locally too
        self.responses = {}  # phone_number -> response_data
        
        # Check if we're in test mode
        self.test_mode = os.getenv('TEST_MODE', '').lower() == 'true'
        
    def start_delivery_worker(self):
        """Start the background delivery worker"""
        with self._lock:
            if not self.is_running:
                self.is_running = True
                self.delivery_thread = threading.Thread(
                    target=self._delivery_worker,
                    daemon=True
                )
                self.delivery_thread.start()
                print("📤 Response delivery worker started")
    
    def stop_delivery_worker(self):
        """Stop the background delivery worker"""
        with self._lock:
            self.is_running = False
            if self.delivery_thread:
                self.delivery_thread.join(timeout=5)
                print("📤 Response delivery worker stopped")
    
    def queue_response(self, phone_number: str, message: str):
        """Queue a response for delivery to the user"""
        response = PendingResponse(
            phone_number=phone_number,
            message=message,
            timestamp=datetime.now()
        )
        self.delivery_queue.put(response)
        
        # Ensure delivery worker is running
        self.start_delivery_worker()
        
        print(f"📨 Queued response for {phone_number}: {message[:50]}...")
    
    def _delivery_worker(self):
        """Background worker that delivers queued responses"""
        print("🚀 Delivery worker started")
        
        while self.is_running:
            try:
                # Get next response to deliver (timeout prevents blocking forever)
                response = self.delivery_queue.get(timeout=1.0)
                
                if self._should_rate_limit(response.phone_number):
                    # Put it back in queue and wait
                    self.delivery_queue.put(response)
                    time.sleep(0.1)
                    continue
                
                success = self._deliver_response(response)
                
                if not success and response.retries < response.max_retries:
                    # Retry failed delivery
                    response.retries += 1
                    response.timestamp = datetime.now() + timedelta(seconds=5)  # Delay retry
                    self.delivery_queue.put(response)
                    print(f"🔄 Retrying delivery to {response.phone_number} (attempt {response.retries})")
                elif not success:
                    print(f"❌ Failed to deliver to {response.phone_number} after {response.max_retries} attempts")
                
                self.delivery_queue.task_done()
                
            except Empty:
                # Timeout - continue loop
                continue
            except Exception as e:
                print(f"❌ Delivery worker error: {e}")
                time.sleep(1)
        
        print("🛑 Delivery worker stopped")
    
    def _should_rate_limit(self, phone_number: str) -> bool:
        """Check if we should rate limit this phone number"""
        now = time.time()
        last_sent = self.last_sent.get(phone_number, 0)
        
        if now - last_sent < self.min_interval:
            return True
        
        return False
    
    def _deliver_response(self, response: PendingResponse) -> bool:
        """Deliver a single response via Twilio and store for testing"""
        try:
            # Store response for testing purposes
            self._store_response_for_testing(response.phone_number, response.message)
            
            if self.test_mode or not self.twilio_client:
                # For testing/development - just log the message
                print(f"📱 [MOCK DELIVERY] To {response.phone_number}: {response.message}")
                self.last_sent[response.phone_number] = time.time()
                return True
            
            # Send via Twilio
            message = self.twilio_client.messages.create(
                body=response.message,
                from_=self.twilio_phone_number,
                to=response.phone_number
            )
            
            self.last_sent[response.phone_number] = time.time()
            print(f"✅ Delivered to {response.phone_number}: {message.sid}")
            return True
            
        except Exception as e:
            print(f"❌ Delivery failed to {response.phone_number}: {e}")
            return False
    
    def _store_response_for_testing(self, phone_number: str, message: str):
        """Store response for testing/evaluation purposes"""
        # Store locally
        self.responses[phone_number] = {
            'message': message,
            'timestamp': time.time()
        }
        
        # Also try to store in testing endpoint for eval script
        try:
            requests.post(f"{self.flask_app_url}/testing/store-response", json={
                'phone_number': phone_number,
                'response': message
            }, timeout=2)
        except Exception as e:
            # Don't fail delivery if testing endpoint is down
            print(f"⚠️  Could not store response for testing: {e}")
    
    def get_queue_size(self) -> int:
        """Get current queue size for monitoring"""
        return self.delivery_queue.qsize()
    
    def is_delivery_pending(self, phone_number: str) -> bool:
        """Check if there are pending deliveries for a phone number"""
        return self.delivery_queue.qsize() > 0
    
    def get_latest_response(self, phone_number: str) -> Optional[str]:
        """Get latest response for testing purposes"""
        response_data = self.responses.get(phone_number)
        return response_data['message'] if response_data else None
    
    def clear_responses(self, phone_number: str):
        """Clear stored responses for testing"""
        if phone_number in self.responses:
            del self.responses[phone_number]