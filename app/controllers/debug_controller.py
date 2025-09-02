from app.services.messaging.rate_limit_service import RateLimitService
from app.services.messaging.processing_status_service import ProcessingStatusService

class DebugController:
    def __init__(self):
        self.rate_limit_service = RateLimitService()
        self.processing_status_service = ProcessingStatusService()
    
    def get_rate_limit_info(self, phone_number: str):
        """Get comprehensive rate limit info"""
        try:
            rate_info = self.rate_limit_service.get_rate_limit_info(phone_number)
            processing_info = self.processing_status_service.get_processing_status(phone_number)
            
            return {
                "data": {
                    "rate_limiting": rate_info,
                    "processing_status": processing_info
                }
            }, 200
        except Exception as e:
            return {"error": str(e)}, 500
    
    def reset_user_limits(self, phone_number: str):
        """Reset both rate limits and processing status"""
        try:
            self.rate_limit_service.clear_rate_limit(phone_number)
            self.processing_status_service.clear_processing_status(phone_number)
            return {"message": f"Reset all limits for {phone_number}"}, 200
        except Exception as e:
            return {"error": str(e)}, 500
