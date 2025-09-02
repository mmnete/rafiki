from typing import List, Dict, Optional, Callable
from datetime import datetime
import json

from app.services.prompting.prompt_builder import PromptBuilder
from app.services.messaging.conversation_handler import ConversationHandler

class CancellationAwareProcessor:
    """
    Processes messages with cancellation support.
    
    Responsibilities:
    - Check for cancellation signals during processing
    - Delegate to conversation handler for actual processing
    - Handle cancellation cleanup
    """
    
    def __init__(self, conversation_handler: ConversationHandler, 
                 prompt_builder: PromptBuilder):
        self.conversation_handler = conversation_handler
        self.prompt_builder = prompt_builder
    
    def process_message_async(self, phone_number: str, message: str, 
                            media_urls: List[Dict[str, str]], 
                            cancellation_check: Callable[[], bool]):
        """
        Process message with cancellation support
        
        Args:
            phone_number: User's phone number
            message: User message text
            media_urls: List of media URLs
            cancellation_check: Function that returns True if processing should be cancelled
        
        Returns:
            str: AI response or None if cancelled
        """
        try:
            # Check cancellation before starting
            if cancellation_check():
                print(f"Message processing cancelled before start for {phone_number}")
                return None
            
            # Delegate to conversation handler with cancellation check
            response = self.conversation_handler.handle_message_with_cancellation(
                phone_number=phone_number,
                message=message,
                media_urls=media_urls,
                cancellation_check=cancellation_check
            )
            
            # Check cancellation after processing
            if cancellation_check():
                print(f"Message processing cancelled after completion for {phone_number}")
                # Could implement cleanup here if needed
                return None
            
            return response
            
        except Exception as e:
            print(f"Error in cancellation-aware processing for {phone_number}: {e}")
            return "Sorry, there was an error processing your message."
    