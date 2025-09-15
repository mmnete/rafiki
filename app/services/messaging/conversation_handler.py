from typing import List, Dict, Optional, Callable
import json
import time
import logging
from app.services.prompting.prompt_builder import PromptBuilder
from app.services.messaging.conversation_orchestrator import ConversationOrchestrator
from app.storage.services.conversation_storage_service import ConversationStorageService
from app.storage.services.user_storage_service import UserStorageService
from app.tools.tool_call_manager import ToolCallManager
from app.services.messaging.response_delivery_service import ResponseDeliveryService
from app.tools.tool_output_format import process_model_response


logger = logging.getLogger(__name__)

class ConversationHandler:
    """
    Handles the core conversation logic without DB coupling.

    Responsibilities:
    - Coordinate message processing flow
    - Handle image processing
    - Call AI model with tools
    - Return processed response

    NOT responsible for:
    - Direct DB operations (delegates to services)
    - Building prompts (delegates to PromptBuilder)
    - Managing conversation state (delegates to services)
    """

    def __init__(
        self,
        user_storage_service: UserStorageService,
        conversation_storage_service: ConversationStorageService,
        conversation_orchestrator: ConversationOrchestrator,
        tool_manager: ToolCallManager,
        prompt_builder: PromptBuilder,
        response_delivery_service: ResponseDeliveryService
    ):
        # Services (injected dependencies)
        self.user_storage_service = user_storage_service
        self.conversation_storage_service = conversation_storage_service
        self.conversation_orchestrator = conversation_orchestrator
        self.tool_manager = tool_manager
        self.prompt_builder = prompt_builder
        self.response_delivery_service = response_delivery_service

    # Updated conversation handler method
    def handle_message_with_cancellation(
        self,
        phone_number: str,
        message: str, # This is the user query
        media_urls: List[Dict[str, str]], # These are image inputs.
        cancellation_check: Callable[[], bool],
    ) -> Optional[str]:
        """
        Handle message processing with periodic cancellation checks
        Now sends responses via delivery service instead of returning them
        """
        start_time = time.time()

        try:
            logger.info(f"Starting message handling for {phone_number}")
            # Step 1: Get user (check cancellation)
            if cancellation_check():
                logger.info("Message processing cancelled during initial check")
                return None
            
            logger.debug("Attempting to create or retrieve user")

            user = self.user_storage_service.get_or_create_user(phone_number)
            if not user:
                raise Exception(f"Could not find user of phone number {phone_number}")

            # Step 2: Process images (check cancellation)
            if cancellation_check():
                logger.info("Message processing cancelled before image processing")
                return None

            has_media = len(media_urls) > 0
            processed_message = self._process_images_if_present(
                message, media_urls, cancellation_check
            )
            if processed_message is None:  # Cancelled during image processing
                logger.info("Message processing cancelled during image processing")
                return None

            # Step 3: Get user context (check cancellation)
            if cancellation_check():
                logger.info("Message processing cancelled before building user context")
                return None

            user_context = self._build_user_context(user)

            # Step 4: Get conversation history (check cancellation)
            if cancellation_check():
                logger.info("Message processing cancelled before retrieving conversation history")
                return None

            conversation_history = (
                self.conversation_storage_service.get_conversation_history(
                    user.id, limit=50
                )
            )

            # Step 5: Build prompt (check cancellation)
            if cancellation_check():
                logger.info("Message processing cancelled before building prompt")
                return None

            prompt = self.prompt_builder.build_conversation_prompt(
                user=user,
                user_context=user_context,
                message=processed_message,
                conversation_history=conversation_history,
            )

            # Step 6: Get available tools (check cancellation)
            if cancellation_check():
                logger.info("Message processing cancelled before retrieving tools")
                return None

            available_tools = self.tool_manager.get_available_tools_for_user(user)
            available_tool_functions = {}
            available_tool_context = {}
            for name in available_tools:
                tool_function = self.tool_manager.get_tool_function(name)
                tool_context = self.tool_manager.get_tool_context(name)
                if tool_function is not None:
                    available_tool_functions[name] = tool_function
                if tool_context is not None:
                    available_tool_context[name] = tool_context

            # Step 7: Call AI model 
            if cancellation_check():
                logger.info("Message processing cancelled before AI model call")
                return None

            # Your existing conversation processing
            ai_response, tool_results = self.conversation_orchestrator.process_conversation_turn(
                prompt, str(user.id), processed_message, available_tool_functions, available_tool_context
            )

            if cancellation_check():
                logger.info("Message processing cancelled after AI model call")
                return None

            # NEW: Send the AI response to the user
            self._send_response_to_user(phone_number, process_model_response(ai_response))

            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Extract context summaries from tool results
            context_summaries = []
            for tool_result in tool_results:
                if tool_result.get("success") and tool_result.get("context_summary"):
                    context_summaries.append(tool_result["context_summary"])
            
            # Build response to save (context + AI response)
            ai_response_to_save = ai_response
            if context_summaries:
                ai_response_to_save = "\n".join(context_summaries) + "\n\n" + ai_response
                
            logger.debug(f"AI response to save: {ai_response_to_save}")
            
            # Save the conversation with the AI response (fixed variable name)
            self.conversation_storage_service.save_conversation(
                user.id,
                processed_message,
                ai_response_to_save,  # Fixed: was "final_response" which didn't exist
                tools_used=available_tools,
                processing_time_ms=processing_time_ms,
                has_media=has_media
            )

            logger.info(f"Message handling completed successfully for {phone_number} in {processing_time_ms}ms")
            return ai_response  # Fixed: return the actual AI response

        except Exception as e:
            logger.error(f"Error in conversation handling for {phone_number}: {e}", exc_info=True)
            error_message = f"Sorry, there was an error processing your message. {e}"
            self._send_response_to_user(phone_number, error_message)
            return error_message

    def _send_response_to_user(self, phone_number: str, response: str):
        """Send response to user via delivery service"""
        if hasattr(self, 'response_delivery_service') and self.response_delivery_service:
            self.response_delivery_service.queue_response(phone_number, response)
        else:
            logger.info(f"📱 [NO DELIVERY SERVICE] Response for {phone_number}: {response}")

    def _process_images_if_present(
        self,
        message: str,
        media_urls: List[Dict[str, str]],
        cancellation_check: Callable[[], bool],
    ) -> Optional[str]:
        """Process images and prepend descriptions to message"""
        if not media_urls:
            return message

        try:
            image_descriptions = []
            for img_info in media_urls:
                # Check cancellation during image processing
                if cancellation_check():
                    return None

                parsed_response = self.conversation_orchestrator.describe_image(
                    img_info
                )
                if hasattr(parsed_response, "response_type") and hasattr(
                    parsed_response, "content"
                ):
                    image_descriptions.append(parsed_response.content)
                else:
                    logger.info(f"Warning: Failed to describe image {img_info.get('url')}")
                    image_descriptions.append("an image")

            # Prepend image descriptions to message
            descriptions_str = ", ".join(image_descriptions)
            return f"User has provided images: {descriptions_str}. {message}"

        except Exception as e:
            logger.error(f"Error processing images: {e}")
            return message  # Fallback to original message

    def _build_user_context(self, user) -> dict:
        """Build user context for prompt building with capability assessment"""
        
        # Basic user info
        context = {
            "phone_number": user.phone_number,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": getattr(user, "email", None),
            "date_of_birth": getattr(user, "date_of_birth", None),
            "location": user.location,
            "preferred_language": user.preferred_language,
            "status": getattr(user, "status", "unknown"),
            "created_at": getattr(user, "created_at", "Unknown"),
        }
        
        # Capability assessment
        missing_for_search = []
        if not user.phone_number:
            missing_for_search.append("phone_number")
        
        missing_for_booking = []
        for field, value in {
            "phone_number": user.phone_number,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": getattr(user, "email", None),
            "date_of_birth": getattr(user, "date_of_birth", None),
            "location": user.location
        }.items():
            if not value:
                missing_for_booking.append(field)
        
        # Add capability status with clear instructions
        if missing_for_search:
            context["flight_capability"] = "CANNOT_SEARCH"
            context["capability_message"] = f"User cannot search flights. Missing: {', '.join(missing_for_search)}. Do not offer flight searches."
        elif missing_for_booking:
            context["flight_capability"] = "CAN_SEARCH_ONLY"
            context["capability_message"] = f"User can search flights but cannot book. Allow searches and exploration. Only ask for missing booking details ({', '.join(missing_for_booking)}) if user explicitly wants to proceed with booking."
        else:
            context["flight_capability"] = "FULL_ACCESS"
            context["capability_message"] = "User can search and book flights"
        
        context["missing_for_search"] = missing_for_search
        context["missing_for_booking"] = missing_for_booking
        
        # Clear instruction for the model
        context["data_collection_policy"] = "IMPORTANT: Only request missing user details when user is ready to book. Let them search and explore freely with current information level."
        
        return context

