# Enhanced version of your ModelService to support streaming/multiple responses

from typing import List, Dict, Any, Optional, Callable, Generator
from dataclasses import dataclass
from enum import Enum
import requests
import time

from app.services.modelling.model_backend import GeminiBackend, OpenAIBackend
from app.services.modelling.response_parser import ResponseParser, ParsedResponse, ResponseType
from app.services.modelling.tool_executor_service import ToolExecutorService

@dataclass
class StreamingResponse:
    """Represents a streaming response chunk"""
    type: str  # 'thinking', 'partial', 'tool_call', 'final'
    content: str
    metadata: Optional[Dict[str, Any]] = None

class ModelService:
    """
    Clean model service focused only on model communication.
    
    Now supports:
    - Traditional single responses
    - Streaming responses with multiple outputs
    - Response callbacks for real-time delivery
    """
    
    def __init__(self, use_openai: bool = False):
        self.use_openai = use_openai
        self._initialize_backend()
    
    def _initialize_backend(self):
        """Initialize the appropriate backend"""
        if self.use_openai:
            self.backend = OpenAIBackend()
        else:
            self.backend = GeminiBackend()
    
    def switch_backend(self, use_openai: bool):
        """Switch between model backends"""
        if use_openai != self.use_openai:
            self.use_openai = use_openai
            self._initialize_backend()
    
    def generate_text_content(self, prompt: str) -> str:
        """Generate text-only content (original method)"""
        try:
            response = self.backend.generate_text_content(prompt)
            return response
        except Exception as e:
            print(f"Error generating text content: {e}")
            return "I'm sorry, I encountered an error generating a response."
    
    def generate_text_content_with_streaming(
        self, 
        prompt: str,
        response_callback: Optional[Callable[[str], None]] = None,
        cancellation_check: Optional[Callable[[], bool]] = None
    ) -> str:
        """
        Generate text content with streaming support.
        
        This method will:
        1. Send a "thinking" message immediately if callback provided
        2. Generate the actual response
        3. Send the final response via callback
        4. Return the final response
        
        Args:
            prompt: The prompt to send to the AI
            response_callback: Function to call with each response chunk
            cancellation_check: Function that returns True if processing should be cancelled
        
        Returns:
            Final response string
        """
        try:
            # Send thinking message if callback provided
            if response_callback:
                thinking_messages = [
                    "Let me think about that... 🤔",
                    "Processing your request...",
                    "Looking into that for you...",
                    "Analyzing your query..."
                ]
                import random
                thinking_msg = random.choice(thinking_messages)
                response_callback(thinking_msg)
            
            # Check for cancellation
            if cancellation_check and cancellation_check():
                return "Request was cancelled."
            
            # Simulate some processing time (remove in production if backend is fast)
            time.sleep(0.5)
            
            # Generate the actual response
            if hasattr(self.backend, 'generate_text_content_streaming'):
                # If backend supports streaming, use it
                final_response = ""
                for chunk in self.backend.generate_text_content_streaming(prompt):
                    if cancellation_check and cancellation_check():
                        return "Request was cancelled."
                    
                    final_response += chunk
                    
                    # Optionally send partial updates
                    # if response_callback and len(final_response) % 50 == 0:
                    #     response_callback(f"[Partial] {final_response[:100]}...")
            else:
                # Fall back to regular generation
                final_response = self.backend.generate_text_content(prompt)
            
            # Check for cancellation before sending final response
            if cancellation_check and cancellation_check():
                return "Request was cancelled."
            
            # Send final response if callback provided
            if response_callback and final_response:
                response_callback(final_response)
            
            return final_response
            
        except Exception as e:
            error_msg = "I'm sorry, I encountered an error generating a response."
            print(f"Error generating text content: {e}")
            
            if response_callback:
                response_callback(error_msg)
            
            return error_msg
    
    def generate_multimodal_content_with_streaming(
        self, 
        prompt: str, 
        image_urls: List[Dict[str, str]],
        response_callback: Optional[Callable[[str], None]] = None,
        cancellation_check: Optional[Callable[[], bool]] = None
    ) -> str:
        """Generate multimodal content with streaming support"""
        try:
            if not self.backend.supports_vision:
                error_msg = "Image processing is not supported with the current model backend."
                if response_callback:
                    response_callback(error_msg)
                return error_msg
            
            # Send thinking message for image processing
            if response_callback:
                response_callback("Let me analyze your image(s)... 👀")
            
            # Check for cancellation
            if cancellation_check and cancellation_check():
                return "Request was cancelled."
            
            # Process images (this might take longer)
            time.sleep(1.0)  # Simulate processing time
            
            response = self.backend.generate_multimodal_content(prompt, image_urls)
            
            # Check for cancellation before sending final response
            if cancellation_check and cancellation_check():
                return "Request was cancelled."
            
            # Send final response
            if response_callback and response:
                response_callback(response)
            
            return response
            
        except Exception as e:
            error_msg = "I'm sorry, I encountered an error processing your images."
            print(f"Error generating multimodal content: {e}")
            
            if response_callback:
                response_callback(error_msg)
            
            return error_msg
    
    def describe_image(self, image_info: Dict[str, str]) -> str:
        """Describe a single image (original method)"""
        try:
            # Fetch image data
            img_response = requests.get(image_info["url"])
            img_response.raise_for_status()
            image_data = img_response.content
            
            # Prepare content for model
            contents = [
                {
                    "type": "text", 
                    "text": "Describe this image in a concise manner. If there is any text, include it completely."
                },
                {
                    "type": "image_data", 
                    "mime_type": image_info["type"], 
                    "data": image_data
                }
            ]
            
            response = self.backend.generate_multimodal_content("", contents)
            return response.strip()
            
        except requests.RequestException as e:
            print(f"Error fetching image: {e}")
            return "Could not fetch image for description"
        except Exception as e:
            print(f"Error describing image: {e}")
            return "Could not process image"
    
    def call_gemini_eval(self, prompt: str) -> str:
        """Special method for evaluation purposes (original method)"""
        try:
            # Create a dedicated Gemini backend for this call
            eval_backend = GeminiBackend()
            response = eval_backend.generate_text_content(prompt)
            return response
        except Exception as e:
            print(f"Error generating eval content with Gemini: {e}")
            return "I'm sorry, an error occurred during the Gemini evaluation call."
    
    # New helper methods for streaming support
    def supports_streaming(self) -> bool:
        """Check if current backend supports streaming"""
        return hasattr(self.backend, 'generate_text_content_streaming')
    
    def generate_with_callbacks(
        self, 
        prompt: str,
        response_callback: Callable[[str], None],
        cancellation_check: Optional[Callable[[], bool]] = None,
        include_images: bool = False,
        image_urls: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Unified method for generating responses with callbacks.
        This is the main method your conversation handler should use.
        """
        if include_images and image_urls:
            return self.generate_multimodal_content_with_streaming(
                prompt, image_urls, response_callback, cancellation_check
            )
        else:
            return self.generate_text_content_with_streaming(
                prompt, response_callback, cancellation_check
            )