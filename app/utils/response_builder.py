from twilio.twiml.messaging_response import MessagingResponse
from flask import jsonify
from typing import Optional

class MessageResponseBuilder:
    """
    Build responses for different messaging providers
    Handles provider-specific response formats
    """
    
    def build_twilio_response(self, message: str) -> str:
        """
        Build Twilio TwiML response
        
        Args:
            message: Message text to send
            
        Returns:
            TwiML response as string
        """
        response = MessagingResponse()
        response.message(message)
        return str(response)
    
    def build_empty_response(self, provider: str = "twilio") -> str:
        """
        Build empty response (for cooldown scenarios)
        
        Args:
            provider: Message provider
            
        Returns:
            Empty response in provider format
        """
        if provider == "twilio":
            return str(MessagingResponse())
        else:
            return ""
    
    def build_rate_limit_response(self, provider: str = "twilio", 
                                custom_message: Optional[str] = None) -> str:
        """
        Build rate limit response
        
        Args:
            provider: Message provider
            custom_message: Custom rate limit message
            
        Returns:
            Rate limit response in provider format
        """
        message = custom_message or "Please slow down! You're sending messages too quickly."
        
        if provider == "twilio":
            response = MessagingResponse()
            response.message(message)
            return str(response)
        else:
            return message
    
    def build_error_response(self, error_message: Optional[str] = None, 
                           provider: str = "twilio") -> str:
        """
        Build error response
        
        Args:
            error_message: Custom error message
            provider: Message provider
            
        Returns:
            Error response in provider format
        """
        message = error_message or "Sorry, there was an error processing your message."
        
        if provider == "twilio":
            response = MessagingResponse()
            response.message(message)
            return str(response)
        else:
            return message
    
    def build_processing_response(self, message: str, provider: str = "twilio") -> str:
        """
        Build "still processing" response
        
        Args:
            message: Processing message text
            provider: Message provider
            
        Returns:
            Processing response in provider format
        """
        if provider == "twilio":
            response = MessagingResponse()
            response.message(message)
            return str(response)
        else:
            return message
    
    def build_json_response(self, data: dict, status_code: int = 200) -> tuple:
        """
        Build JSON response for API endpoints
        
        Args:
            data: Data to include in response
            status_code: HTTP status code
            
        Returns:
            Tuple of (json_response, status_code)
        """
        return jsonify(data), status_code
    
    def build_success_json(self, message: str, data: Optional[dict] = None) -> tuple:
        """
        Build successful JSON response
        
        Args:
            message: Success message
            data: Optional additional data
            
        Returns:
            Tuple of (json_response, 200)
        """
        response_data = {"message": message}
        if data:
            response_data.update(data)
        return self.build_json_response(response_data, 200)
    
    def build_error_json(self, error: str, status_code: int = 500) -> tuple:
        """
        Build error JSON response
        
        Args:
            error: Error message
            status_code: HTTP status code
            
        Returns:
            Tuple of (json_response, status_code)
        """
        return self.build_json_response({"error": error}, status_code)
