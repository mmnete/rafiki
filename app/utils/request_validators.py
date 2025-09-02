from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class ValidationResult:
    is_valid: bool
    phone_number: Optional[str] = None
    message: Optional[str] = None
    media_urls: Optional[List[Dict[str, str]]] = field(default_factory=list)  # Fixed this line
    error_response: Optional[str] = None
    
    def require_phone(self) -> str:
        if not self.phone_number:
            raise ValueError("Phone number is missing")
        return self.phone_number
    
    def require_message(self) -> str:
        if not self.message:
            raise ValueError("Message is missing")
        return self.message
    
    def require_media_urls(self) -> List[Dict[str, str]]:
        return self.media_urls or []  # Handle None case
    

def validate_messaging_request(form_data, provider="twilio") -> ValidationResult:
    """
    Validate incoming messaging request based on provider
    
    Args:
        form_data: Flask request.form data
        provider: Message provider ("twilio", "whatsapp", etc.)
    
    Returns:
        ValidationResult with validation status and extracted data
    """
    if provider == "twilio":
        return _validate_twilio_request(form_data)
    elif provider == "whatsapp":
        return _validate_whatsapp_request(form_data)
    else:
        return ValidationResult(is_valid=False, error_response="Unsupported provider")

def _validate_twilio_request(form_data) -> ValidationResult:
    """Validate Twilio-specific request format"""
    # Extract phone number
    raw_phone = form_data.get("From")
    if not raw_phone:
        return ValidationResult(is_valid=False, error_response="Missing phone number")
    
    # Clean phone number (your existing logic)
    phone_number = raw_phone
    if phone_number.startswith("whatsapp:"):
        phone_number = phone_number[len("whatsapp:"):]
    
    # Extract message
    user_message = form_data.get("Body", "")
    
    # Extract media URLs (your existing logic)
    media_urls = _extract_twilio_media(form_data)
    
    # Basic validation - at least message or media should be present
    if not user_message and not media_urls:
        return ValidationResult(is_valid=False, error_response="Empty message")
    
    return ValidationResult(
        is_valid=True,
        phone_number=phone_number,
        message=user_message,
        media_urls=media_urls
    )

def _validate_whatsapp_request(form_data) -> ValidationResult:
    """Validate WhatsApp-specific request format (for future use)"""
    # Placeholder for WhatsApp Business API format
    # This would have different field names than Twilio
    return ValidationResult(is_valid=False, error_response="WhatsApp validation not implemented yet")

def _extract_twilio_media(form_data) -> List[Dict[str, str]]:
    """Extract media URLs from Twilio request (your existing logic)"""
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    media_urls = []
    num_media = int(form_data.get("NumMedia", 0))
    
    for i in range(num_media):
        media_url = form_data.get(f"MediaUrl{i}")
        media_type = form_data.get(f"MediaContentType{i}")
        
        if media_url and media_type in allowed_types:
            media_urls.append({"url": media_url, "type": media_type})
    
    return media_urls