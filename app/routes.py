from flask import Blueprint, request, jsonify
from app.controllers.conversation_manager import ConversationManager
from twilio.twiml.messaging_response import MessagingResponse
from flask import Blueprint, request, jsonify
from app.controllers.conversation_manager import ConversationManager
from app.services.message_processor import MessageProcessor, get_processing_status, set_processing_status, clear_processing_status, redis_storage_manager
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta
import requests
import os

main = Blueprint("main", __name__)
test_mode = os.getenv("TEST_MODE", "false").lower() == "true"
conv_manager = ConversationManager(test_mode=test_mode)
message_processor = MessageProcessor(conv_manager)

@main.route("/message", methods=["POST"])
def message():
    # Twilio sends form-encoded data
    phone_number = request.form.get("From")
    user_message = request.form.get("Body")
    
    if not phone_number or not user_message:
        return "Missing phone number or message", 400
    
    if phone_number.startswith("whatsapp:"):
        phone_number = phone_number[len("whatsapp:"):]
    
    current_time = datetime.now()
    user_status = get_processing_status(phone_number)
    
    # Check if user is currently being processed
    if user_status["is_processing"]:
        print(f"found status: {user_status}")
        # Check if this is a duplicate/spam message within a short time window
        if (user_status["last_request_time"] and 
            current_time - user_status["last_request_time"] < timedelta(seconds=5)):
            
            # Don't respond to rapid duplicate messages
            response = MessagingResponse()
            return str(response)  # Empty response
        
        # Update last request time
        set_processing_status(phone_number, True, current_time)
        
        # Send personalized "still thinking" message
        still_thinking_message = conv_manager.get_still_thinking_message(phone_number)
        response = MessagingResponse()
        response.message(still_thinking_message)
        return str(response)
    
    # Check if this is a quick message that doesn't need AI processing
    quick_response = conv_manager.get_quick_response(phone_number, user_message)
    if quick_response:
        print(f"generating quick response: {quick_response}")
        response = MessagingResponse()
        response.message(quick_response)
        return str(response)
    
    # For messages that need AI processing
    set_processing_status(phone_number, True, current_time)
    
    # Send immediate "thinking" response
    immediate_response = conv_manager.get_thinking_message()
    
    # Start background processing
    thread = threading.Thread(
        target=message_processor.process_message_async,
        args=(phone_number, user_message)
    )
    thread.daemon = True
    thread.start()
    
    # Return immediate response
    response = MessagingResponse()
    response.message(immediate_response)
    return str(response)

# Testing endpoints for Postman
@main.route("/test/responses/<phone_number>", methods=["GET"])
def get_test_responses(phone_number):
    """Get all stored test responses for a phone number"""
    if not conv_manager.test_mode:
        return jsonify({"error": "Not in test mode"}), 400
    
    # Filter responses for this phone number
    user_responses = [
        resp for resp in conv_manager.test_responses 
        if resp["phone_number"] == phone_number
    ]
    
    return jsonify({
        "phone_number": phone_number,
        "responses": user_responses,
        "total_count": len(user_responses)
    })

@main.route("/test/responses/clear", methods=["POST"])
def clear_test_responses():
    """Clear all test responses"""
    if not conv_manager.test_mode:
        return jsonify({"error": "Not in test mode"}), 400
    
    conv_manager.test_responses.clear()
    return jsonify({"message": "Test responses cleared"})

@main.route("/test/status/<phone_number>", methods=["GET"])
def get_processing_status_endpoint(phone_number):
    """Get current processing status for a phone number"""
    status = get_processing_status(phone_number)
    return jsonify({
        "phone_number": phone_number,
        "is_processing": status["is_processing"],
        "last_request_time": status["last_request_time"].isoformat() if status["last_request_time"] else None
    })

@main.route("/test/storage-info", methods=["GET"])
def get_storage_info():
    """Get information about what storage system is being used"""
    
    storage_type = "Redis" if redis_storage_manager.use_redis else "Local Memory"
    redis_connected = False
    
    if redis_storage_manager.use_redis and hasattr(redis_storage_manager, 'redis_client') and redis_storage_manager.redis_client:
        try:
            redis_storage_manager.redis_client.ping()
            redis_connected = True
        except:
            redis_connected = False
    
    return jsonify({
        "storage_type": storage_type,
        "redis_available": redis_storage_manager.use_redis,
        "redis_connected": redis_connected,
        "redis_url": "Present" if os.getenv('REDIS_URL') else "Not set",
        "use_local_redis": os.getenv('USE_LOCAL_REDIS', 'false')
    })

@main.route("/debug/reset-processing/<phone_number>", methods=["GET"])
def reset_processing_status(phone_number):
    """Manually clear processing status for debugging"""
    clear_processing_status(phone_number)
    return jsonify({"message": f"Cleared processing status for {phone_number}"})

@main.route("/delete_all_users", methods=["POST"])
def delete_all_users():
    conv_manager.delete_all_users()
    return str("done")