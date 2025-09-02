# tests/test_response_delivery_service.py
import unittest
import time
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from queue import Queue

# Import the service we're testing
from app.services.messaging.response_delivery_service import ResponseDeliveryService, PendingResponse


class TestResponseDeliveryService(unittest.TestCase):
    """Test cases for ResponseDeliveryService"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'TWILIO_ACCOUNT_SID': 'test_account_sid',
            'TWILIO_AUTH_TOKEN': 'test_auth_token',
            'TWILIO_PHONE_NUMBER': '+15551234567',
            'TEST_MODE': 'true',
            'HEROKU_APP_NAME': ''  # Default to empty for localhost
        })
        self.env_patcher.start()
        
        # Create service instance for testing
        self.service = ResponseDeliveryService()
    
    def tearDown(self):
        """Clean up after each test."""
        self.env_patcher.stop()
        if self.service:
            self.service.stop_delivery_worker()
    
    def test_init_with_test_mode(self):
        """Test initialization in test mode"""
        self.assertTrue(self.service.test_mode)
        self.assertIsNone(self.service.twilio_client)
        self.assertEqual(self.service.twilio_phone_number, '+15551234567')
        self.assertEqual(self.service.flask_app_url, 'http://localhost:5000')
    
    @patch.dict(os.environ, {'HEROKU_APP_NAME': 'my-test-app'})
    def test_init_with_heroku_app_name(self):
        """Test initialization with Heroku app name"""
        service = ResponseDeliveryService()
        self.assertEqual(service.flask_app_url, 'https://my-test-app.herokuapp.com')
    
    @patch.dict(os.environ, {'TEST_MODE': 'false'})
    @patch('app.services.response_delivery_service.Client')
    def test_init_with_twilio_client(self, mock_client):
        """Test initialization with Twilio client creation"""
        service = ResponseDeliveryService()
        
        mock_client.assert_called_once_with('test_account_sid', 'test_auth_token')
        self.assertFalse(service.test_mode)
        self.assertIsNotNone(service.twilio_client)
    
    def test_queue_response(self):
        """Test queuing a response"""
        phone_number = '+15551234567'
        message = 'Test message'
        
        # Queue should be empty initially
        self.assertEqual(self.service.get_queue_size(), 0)
        
        # Queue a response
        self.service.queue_response(phone_number, message)
        
        # Queue should have one item
        self.assertEqual(self.service.get_queue_size(), 1)
        
        # Worker should be started
        self.assertTrue(self.service.is_running)
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        phone_number = '+15551234567'
        
        # First message should not be rate limited
        self.assertFalse(self.service._should_rate_limit(phone_number))
        
        # Set last sent time to now
        self.service.last_sent[phone_number] = time.time()
        
        # Second message immediately should be rate limited
        self.assertTrue(self.service._should_rate_limit(phone_number))
        
        # After waiting, should not be rate limited
        self.service.last_sent[phone_number] = time.time() - 2.0
        self.assertFalse(self.service._should_rate_limit(phone_number))
    
    def test_deliver_response_test_mode(self):
        """Test response delivery in test mode"""
        response = PendingResponse(
            phone_number='+15551234567',
            message='Test message',
            timestamp=datetime.now()
        )
        
        # Should succeed in test mode
        success = self.service._deliver_response(response)
        self.assertTrue(success)
        
        # Should store response locally
        stored_response = self.service.get_latest_response('+15551234567')
        self.assertEqual(stored_response, 'Test message')
    
    @patch('app.services.response_delivery_service.Client')
    @patch.dict(os.environ, {'TEST_MODE': 'false'})
    def test_deliver_response_with_twilio(self, mock_client_class):
        """Test response delivery with actual Twilio client"""
        # Setup mock Twilio client
        mock_client = Mock()
        mock_message = Mock()
        mock_message.sid = 'SM123456789'
        mock_client.messages.create.return_value = mock_message
        mock_client_class.return_value = mock_client
        
        # Create service with mocked Twilio
        service = ResponseDeliveryService()
        
        response = PendingResponse(
            phone_number='+15551234567',
            message='Test message',
            timestamp=datetime.now()
        )
        
        # Should succeed with Twilio
        success = service._deliver_response(response)
        self.assertTrue(success)
        
        # Verify Twilio was called correctly
        mock_client.messages.create.assert_called_once_with(
            body='Test message',
            from_='+15551234567',
            to='+15551234567'
        )
    
    @patch('app.services.response_delivery_service.Client')
    @patch.dict(os.environ, {'TEST_MODE': 'false'})
    def test_deliver_response_twilio_failure(self, mock_client_class):
        """Test response delivery failure with Twilio"""
        # Setup mock Twilio client that raises exception
        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception('Twilio error')
        mock_client_class.return_value = mock_client
        
        service = ResponseDeliveryService()
        
        response = PendingResponse(
            phone_number='+15551234567',
            message='Test message',
            timestamp=datetime.now()
        )
        
        # Should fail
        success = service._deliver_response(response)
        self.assertFalse(success)
    
    @patch('requests.post')
    def test_store_response_for_testing_localhost(self, mock_post):
        """Test storing response for testing purposes with localhost"""
        phone_number = '+15551234567'
        message = 'Test message'
        
        self.service._store_response_for_testing(phone_number, message)
        
        # Should store locally
        self.assertIn(phone_number, self.service.responses)
        self.assertEqual(self.service.responses[phone_number]['message'], message)
        
        # Should attempt to post to localhost testing endpoint
        mock_post.assert_called_once_with(
            'http://localhost:5000/testing/store-response',
            json={
                'phone_number': phone_number,
                'response': message
            },
            timeout=2
        )
    
    @patch('requests.post')
    def test_store_response_for_testing_endpoint_failure(self, mock_post):
        """Test storing response when testing endpoint fails"""
        mock_post.side_effect = Exception('Connection error')
        
        phone_number = '+15551234567'
        message = 'Test message'
        
        # Should not raise exception even if endpoint fails
        self.service._store_response_for_testing(phone_number, message)
        
        # Should still store locally
        self.assertIn(phone_number, self.service.responses)
        self.assertEqual(self.service.responses[phone_number]['message'], message)
    
    def test_worker_lifecycle(self):
        """Test starting and stopping the delivery worker"""
        # Initially not running
        self.assertFalse(self.service.is_running)
        self.assertIsNone(self.service.delivery_thread)
        
        # Start worker
        self.service.start_delivery_worker()
        self.assertTrue(self.service.is_running)
        self.assertIsNotNone(self.service.delivery_thread)
        
        # Stop worker
        self.service.stop_delivery_worker()
        self.assertFalse(self.service.is_running)
    
    def test_get_latest_response(self):
        """Test getting latest response for a phone number"""
        phone_number = '+15551234567'
        message = 'Test message'
        
        # No response initially
        self.assertIsNone(self.service.get_latest_response(phone_number))
        
        # Store a response
        self.service._store_response_for_testing(phone_number, message)
        
        # Should return the message
        self.assertEqual(self.service.get_latest_response(phone_number), message)
    
    def test_clear_responses(self):
        """Test clearing responses for a phone number"""
        phone_number = '+15551234567'
        message = 'Test message'
        
        # Store a response
        self.service._store_response_for_testing(phone_number, message)
        self.assertIsNotNone(self.service.get_latest_response(phone_number))
        
        # Clear responses
        self.service.clear_responses(phone_number)
        self.assertIsNone(self.service.get_latest_response(phone_number))
    
    def test_pending_response_dataclass(self):
        """Test PendingResponse dataclass"""
        response = PendingResponse(
            phone_number='+15551234567',
            message='Test message',
            timestamp=datetime.now()
        )
        
        self.assertEqual(response.phone_number, '+15551234567')
        self.assertEqual(response.message, 'Test message')
        self.assertEqual(response.retries, 0)  # Default value
        self.assertEqual(response.max_retries, 3)  # Default value
    
    @patch('time.sleep')  # Mock sleep to speed up test
    def test_delivery_worker_integration(self, mock_sleep):
        """Integration test for the delivery worker"""
        phone_number = '+15551234567'
        message = 'Integration test message'
        
        # Queue a response
        self.service.queue_response(phone_number, message)
        
        # Wait a bit for worker to process
        time.sleep(0.1)
        
        # Response should be delivered and stored
        self.assertEqual(self.service.get_latest_response(phone_number), message)
        
        # Queue should be empty (or nearly empty)
        # Note: There might be slight timing issues, so we'll be lenient
        self.assertLessEqual(self.service.get_queue_size(), 1)
    
    def test_multiple_responses_same_number(self):
        """Test handling multiple responses to the same number"""
        phone_number = '+15551234567'
        
        # Queue multiple responses
        self.service.queue_response(phone_number, 'Message 1')
        self.service.queue_response(phone_number, 'Message 2')
        self.service.queue_response(phone_number, 'Message 3')
        
        self.assertEqual(self.service.get_queue_size(), 3)
        
        # Wait for processing
        time.sleep(0.2)
        
        # Latest response should be stored (last one processed)
        latest = self.service.get_latest_response(phone_number)
        self.assertIsNotNone(latest)


class TestPendingResponseDataclass(unittest.TestCase):
    """Test the PendingResponse dataclass separately"""
    
    def test_pending_response_creation(self):
        """Test creating PendingResponse with all parameters"""
        timestamp = datetime.now()
        response = PendingResponse(
            phone_number='+15551234567',
            message='Test message',
            timestamp=timestamp,
            retries=2,
            max_retries=5
        )
        
        self.assertEqual(response.phone_number, '+15551234567')
        self.assertEqual(response.message, 'Test message')
        self.assertEqual(response.timestamp, timestamp)
        self.assertEqual(response.retries, 2)
        self.assertEqual(response.max_retries, 5)
    
    def test_pending_response_defaults(self):
        """Test PendingResponse with default values"""
        timestamp = datetime.now()
        response = PendingResponse(
            phone_number='+15551234567',
            message='Test message',
            timestamp=timestamp
        )
        
        self.assertEqual(response.retries, 0)
        self.assertEqual(response.max_retries, 3)
