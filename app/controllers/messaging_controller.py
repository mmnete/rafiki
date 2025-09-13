import re
from flask import request
from app.services.messaging.message_queue_service import MessageQueueService
from app.services.messaging.rate_limit_service import RateLimitService
from app.utils.request_validators import validate_messaging_request
from app.utils.response_builder import MessageResponseBuilder
from app.services.messaging.conversation_handler import ConversationHandler
from app.services.prompting.prompt_builder import PromptBuilder
from app.services.messaging.response_delivery_service import ResponseDeliveryService

# Import your existing services
from app.services.service_factory import ServiceFactory
from app.tools.tool_call_manager import ToolCallManager


class MessagingController:
    """
    Controller: Handles HTTP requests and orchestrates services
    Thin layer - delegates business logic to services
    """
    
    def __init__(self):
        # Initialize core dependencies (your existing pattern)
        self.services = ServiceFactory.create_services(
            use_real_payments=False
        )
        
        # Initialize managers and services
        self.tool_manager = ToolCallManager(self.services)
        self.prompt_builder = PromptBuilder(self.tool_manager, self.services["localization_manager"])
        # We are using .env variables here
        self.response_delivery_service = ResponseDeliveryService(twilio_client=None)

        
        self.conversation_handler = ConversationHandler(
            user_storage_service=self.services["user_storage_service"],
            conversation_storage_service=self.services["conversation_storage_service"],
            conversation_orchestrator=self.services["conversation_orchestrator"],
            tool_manager=self.tool_manager,
            prompt_builder=self.prompt_builder,
            response_delivery_service=self.response_delivery_service
        ) # type: ignore
        
        # Initialize messaging services
        self.message_queue_service = MessageQueueService(
            conversation_handler=self.conversation_handler,
            prompt_builder=self.prompt_builder
        )
        self.rate_limit_service = RateLimitService()
        self.response_builder = MessageResponseBuilder()
    
    def handle_twilio_message(self, form_data):
        """Handle incoming Twilio webhook - orchestrates the flow"""
        
        # 1. Input validation (controller responsibility)
        validation_result = validate_messaging_request(form_data, provider="twilio")
        if not validation_result.is_valid:
            print("Invalid message found")
            return self.response_builder.build_error_response("Invalid request"), 400
        
        if not self.is_valid_supported_number(validation_result.require_phone()):
            return self.response_builder.build_twilio_response("Thank you for trying to use Rafiki AI ✨. We are on active roll out but currently dont support your phone number. Please stay tuned on our socials as we continue to expand 😊"), 200
        
        # 2. Rate limiting check (delegate to service)
        if self.rate_limit_service.is_rate_limited(validation_result.require_phone()):
            return self.response_builder.build_rate_limit_response(), 429
        
        print("queueing message now!")
        
        # 3. Message queuing (delegate to service)
        queued_message = self.message_queue_service.queue_message(
            phone_number=validation_result.require_phone(),
            message=validation_result.require_message(),
            media_urls=validation_result.require_media_urls()
        )
        
        # 4. Start processing if needed (delegate to service)
        self.message_queue_service.start_processing_if_ready(validation_result.require_phone())
        
        # 5. Build response (controller responsibility)
        immediate_response = self._get_thinking_message()
        return self.response_builder.build_twilio_response(immediate_response), 200
    
    def _get_thinking_message(self):
        """Get immediate thinking message - could delegate to another service"""
        return "Thinking ..."
    
    def is_valid_supported_number(self, phone_number: str) -> bool:
        """Validate phone number formats for supported regions"""
        tz_pattern = r"^(?:\+255|0)(6|7)\d{8}$"
        us_pattern = r"^\+1\d{10}$"
        ke_pattern = r"^(?:\+254|0)(7|1)\d{8}$"  # Added Kenya support
        return any([
            re.match(tz_pattern, phone_number),
            re.match(us_pattern, phone_number),
            re.match(ke_pattern, phone_number)
        ])

