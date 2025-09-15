import os
import logging
from typing import Dict, List, Optional, Protocol, Any, Union, Iterator
import openai # type: ignore
import google.generativeai as genai # type: ignore
import anthropic # type: ignore
import requests
import base64
import PIL.Image # type: ignore
import io
import time
from functools import wraps

# Configure logging
logger = logging.getLogger(__name__)

def log_api_call(func):
    """Decorator to log API calls with timing and error handling"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = time.time()
        backend_name = self.__class__.__name__
        function_name = func.__name__
        
        # Log the start of the API call
        logger.info(f"{backend_name}.{function_name} called with args: {len(args)} kwargs: {list(kwargs.keys())}")
        
        try:
            result = func(self, *args, **kwargs)
            elapsed_time = time.time() - start_time
            logger.info(f"{backend_name}.{function_name} completed successfully in {elapsed_time:.2f}s")
            return result
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"{backend_name}.{function_name} failed after {elapsed_time:.2f}s: {str(e)}", exc_info=True)
            raise
    return wrapper

def log_streaming_api_call(func):
    """Decorator to log streaming API calls"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = time.time()
        backend_name = self.__class__.__name__
        function_name = func.__name__
        
        logger.info(f"{backend_name}.{function_name} (streaming) called")
        
        try:
            generator = func(self, *args, **kwargs)
            chunk_count = 0
            for chunk in generator:
                chunk_count += 1
                if chunk_count == 1:
                    logger.debug(f"{backend_name}.{function_name} first chunk received")
                yield chunk
            
            elapsed_time = time.time() - start_time
            logger.info(f"{backend_name}.{function_name} streaming completed - {chunk_count} chunks in {elapsed_time:.2f}s")
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"{backend_name}.{function_name} streaming failed after {elapsed_time:.2f}s: {str(e)}", exc_info=True)
            yield f"I encountered an error while processing your request: {str(e)}"
    return wrapper

class BaseBackend(Protocol):
    """Abstract base backend for generative models."""
    supports_vision: bool

    def generate_text_content(self, text: str, task: Optional[str] = None) -> str:
        """Generate text-only content"""
        ...

    def generate_text_content_streaming(self, text: str, task: Optional[str] = None) -> Iterator[str]:
        """Generate text-only content with streaming support"""
        ...

    def generate_multimodal_content(self, prompt: str, contents: List[Dict[str, Any]]) -> str:
        """Generate content with text and media"""
        ...
        
    def generate_multimodal_content_streaming(self, prompt: str, contents: List[Dict[str, Any]]) -> Iterator[str]:
        """Generate multimodal content with streaming support"""
        ...

class OpenAIBackend:
    """OpenAI GPT backend with proper error handling and model selection"""
    
    def __init__(self):
        logger.info("Initializing OpenAI backend")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable not set")
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        
        logger.debug("OpenAI API key found, creating client")
        self.client = openai.OpenAI(api_key=api_key)
        
        # Define task-specific models
        self.models: Dict[str, str] = {
            "reasoning": "gpt-4o",
            "vision": "gpt-4o",
            "lightweight": "gpt-4o-mini",
            "default": "gpt-4o-mini"
        }
        self.supports_vision: bool = True
        logger.info(f"OpenAI backend initialized with models: {list(self.models.keys())}")

    @log_api_call
    def generate_text_content(self, text: str, task: str = "reasoning") -> str:
        """Generate text-only content"""
        model = self.models.get(task, self.models["default"])
        logger.debug(f"Using OpenAI model: {model} for task: {task}")
        logger.debug(f"Input text length: {len(text)} characters")
        
        try:
            messages = [
                {"role": "user", "content": text}
            ]

            response = self.client.chat.completions.create(
                model=model,
                messages=messages, # type: ignore
                temperature=0.7,
                max_tokens=4000
            )
            
            response_content = response.choices[0].message.content
            if not response_content:
                logger.warning("OpenAI returned empty response")
                return "I apologize, but I couldn't generate a response."
            
            logger.debug(f"OpenAI response length: {len(response_content)} characters")
            return response_content.strip()
            
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}", exc_info=True)
            return "I encountered an API error while processing your request. Please try again."
        except openai.RateLimitError as e: # type: ignore
            logger.error(f"OpenAI rate limit exceeded: {e}")
            return "I'm currently experiencing high demand. Please try again in a moment."
        except Exception as e:
            logger.error(f"Unexpected OpenAI error: {e}", exc_info=True)
            return "I encountered an error while processing your request. Please try again."

    @log_streaming_api_call
    def generate_text_content_streaming(self, text: str, task: str = "reasoning") -> Iterator[str]:
        """Generate text-only content with streaming support"""
        model = self.models.get(task, self.models["default"])
        logger.debug(f"Starting OpenAI streaming with model: {model}")
        
        try:
            messages = [{"role": "user", "content": text}]
            stream = self.client.chat.completions.create(
                model=model,
                messages=messages, # type: ignore
                temperature=0.7,
                stream=True
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}", exc_info=True)
            yield "I encountered an error while processing your request. Please try again."

    @log_api_call
    def generate_multimodal_content(self, prompt: str, contents: List[Dict[str, Any]]) -> str:
        """Generate content with text and images"""
        if not self.supports_vision:
            logger.error("Vision not supported but multimodal content requested")
            raise NotImplementedError("This model does not support vision inputs.")

        model = self.models["vision"]
        logger.debug(f"OpenAI multimodal request with {len(contents)} content items")

        try:
            message_content = []
            if prompt.strip():
                message_content.append({"type": "text", "text": prompt})
            
            for i, content_item in enumerate(contents):
                content_type = content_item.get("type")
                logger.debug(f"Processing content item {i}: type={content_type}")
                
                if content_type == "text":
                    message_content.append({"type": "text", "text": content_item.get("text", "")})
                elif content_type == "image_url":
                    url = content_item.get("url", "")
                    logger.debug(f"Adding image URL: {url[:50]}...")
                    message_content.append({"type": "image_url", "image_url": {"url": url}})
                elif content_type == "image_data":
                    image_data = content_item.get("data", b"")
                    mime_type = content_item.get("mime_type", "image/jpeg")
                    if isinstance(image_data, bytes):
                        logger.debug(f"Processing image data: {len(image_data)} bytes, type={mime_type}")
                        base64_image = base64.b64encode(image_data).decode('utf-8')
                        data_url = f"data:{mime_type};base64,{base64_image}"
                        message_content.append({"type": "image_url", "image_url": {"url": data_url}})

            messages = [{"role": "user", "content": message_content}]
            response = self.client.chat.completions.create(
                model=model,
                messages=messages, # type: ignore
                temperature=0.7,
                max_tokens=4000
            )
            
            response_content = response.choices[0].message.content
            if not response_content:
                logger.warning("OpenAI multimodal returned empty response")
                return "I couldn't process that content. Please try again."
            
            logger.debug(f"OpenAI multimodal response length: {len(response_content)} characters")
            return response_content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI multimodal error: {e}", exc_info=True)
            return "I encountered an error processing your content. Please try again."

    @log_streaming_api_call
    def generate_multimodal_content_streaming(self, prompt: str, contents: List[Dict[str, Any]]) -> Iterator[str]:
        """Generate multimodal content with streaming support"""
        if not self.supports_vision:
            logger.error("Vision not supported but multimodal streaming requested")
            raise NotImplementedError("This model does not support vision inputs.")

        model = self.models["vision"]
        logger.debug(f"OpenAI multimodal streaming with {len(contents)} content items")

        try:
            message_content = []
            if prompt.strip():
                message_content.append({"type": "text", "text": prompt})
            
            for content_item in contents:
                content_type = content_item.get("type")
                if content_type == "text":
                    message_content.append({"type": "text", "text": content_item.get("text", "")})
                elif content_type == "image_url":
                    message_content.append({"type": "image_url", "image_url": {"url": content_item.get("url", "")}})
                elif content_type == "image_data":
                    image_data = content_item.get("data", b"")
                    mime_type = content_item.get("mime_type", "image/jpeg")
                    if isinstance(image_data, bytes):
                        base64_image = base64.b64encode(image_data).decode('utf-8')
                        data_url = f"data:{mime_type};base64,{base64_image}"
                        message_content.append({"type": "image_url", "image_url": {"url": data_url}})

            messages = [{"role": "user", "content": message_content}]
            stream = self.client.chat.completions.create(
                model=model,
                messages=messages, # type: ignore
                temperature=0.7,
                stream=True
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"OpenAI multimodal streaming error: {e}", exc_info=True)
            yield "I encountered an error processing your content. Please try again."

class ClaudeBackend:
    """Anthropic Claude backend with proper error handling and model selection"""
    
    def __init__(self):
        logger.info("Initializing Claude backend")
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error("ANTHROPIC_API_KEY environment variable not set")
            raise ValueError("ANTHROPIC_API_KEY environment variable not set.")
        
        logger.debug("Anthropic API key found, creating client")
        self.client = anthropic.Anthropic(api_key=api_key)
        
        # Define task-specific models (optimized for cost vs performance)
        self.models: Dict[str, str] = {
            "reasoning": "claude-3-5-haiku-20241022",      # Cost-effective, excellent instruction following
            "vision": "claude-3-5-sonnet-20241022",        # Better vision capabilities 
            "lightweight": "claude-3-5-haiku-20241022",    # Most cost-effective
            "premium": "claude-sonnet-4-20250514",         # Highest quality
            "default": "claude-3-5-haiku-20241022"         # Best cost/performance balance
        }
        self.supports_vision: bool = True
        logger.info(f"Claude backend initialized with models: {list(self.models.keys())}")

    @log_api_call
    def generate_text_content(self, text: str, task: str = "reasoning") -> str:
        """Generate text-only content"""
        model = self.models.get(task, self.models["default"])
        logger.debug(f"Using Claude model: {model} for task: {task}")
        logger.debug(f"Input text length: {len(text)} characters")
        
        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=4000,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": text}
                ]
            )
            
            # Claude's response format is different - it returns TextBlock objects
            if response.content and len(response.content) > 0:
                response_text = response.content[0].text.strip() # type: ignore
                logger.debug(f"Claude response length: {len(response_text)} characters")
                return response_text
            else:
                logger.warning("Claude returned empty response")
                return "I apologize, but I couldn't generate a response."
                
        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}", exc_info=True)
            return "I encountered an API error while processing your request. Please try again."
        except anthropic.RateLimitError as e: # type: ignore
            logger.error(f"Claude rate limit exceeded: {e}")
            return "I'm currently experiencing high demand. Please try again in a moment."
        except Exception as e:
            logger.error(f"Unexpected Claude error: {e}", exc_info=True)
            return "I encountered an error while processing your request. Please try again."

    @log_streaming_api_call
    def generate_text_content_streaming(self, text: str, task: str = "reasoning") -> Iterator[str]:
        """Generate text-only content with streaming support"""
        model = self.models.get(task, self.models["default"])
        logger.debug(f"Starting Claude streaming with model: {model}")
        
        try:
            with self.client.messages.stream(
                model=model,
                max_tokens=4000,
                temperature=0.7,
                messages=[{"role": "user", "content": text}]
            ) as stream:
                for text_chunk in stream.text_stream:
                    yield text_chunk
                    
        except Exception as e:
            logger.error(f"Claude streaming error: {e}", exc_info=True)
            yield "I encountered an error while processing your request. Please try again."

    @log_api_call
    def generate_multimodal_content(self, prompt: str, contents: List[Dict[str, Any]]) -> str:
        """Generate content with text and images"""
        if not self.supports_vision:
            logger.error("Vision not supported but multimodal content requested")
            raise NotImplementedError("This model does not support vision inputs.")

        model = self.models["vision"]
        logger.debug(f"Claude multimodal request with {len(contents)} content items")

        try:
            message_content = []
            
            # Add the main prompt if provided
            if prompt.strip():
                message_content.append({"type": "text", "text": prompt})
            
            # Process each content item
            for i, content_item in enumerate(contents):
                content_type = content_item.get("type")
                logger.debug(f"Processing content item {i}: type={content_type}")
                
                if content_type == "text":
                    text_content = content_item.get("text", "")
                    if text_content:
                        message_content.append({"type": "text", "text": text_content})
                        
                elif content_type == "image_url":
                    # Claude requires images to be base64 encoded
                    image_url = content_item.get("url", "")
                    if image_url:
                        try:
                            logger.debug(f"Fetching image from URL: {image_url[:50]}...")
                            # Download and encode the image
                            img_response = requests.get(image_url, timeout=30)
                            img_response.raise_for_status()
                            
                            # Determine media type from content-type header or URL
                            content_type_header = img_response.headers.get('content-type', '')
                            if content_type_header.startswith('image/'):
                                media_type = content_type_header
                            elif image_url.lower().endswith('.png'):
                                media_type = "image/png"
                            elif image_url.lower().endswith('.gif'):
                                media_type = "image/gif"
                            elif image_url.lower().endswith('.webp'):
                                media_type = "image/webp"
                            else:
                                media_type = "image/jpeg"
                            
                            logger.debug(f"Image downloaded: {len(img_response.content)} bytes, type={media_type}")
                            base64_image = base64.b64encode(img_response.content).decode('utf-8')
                            message_content.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": base64_image
                                }
                            })
                        except Exception as img_error:
                            logger.error(f"Error fetching image from {image_url}: {img_error}")
                            message_content.append({"type": "text", "text": "(Image could not be loaded)"})
                            
                elif content_type == "image_data":
                    # Handle raw image data
                    image_data = content_item.get("data", b"")
                    mime_type = content_item.get("mime_type", "image/jpeg")
                    if isinstance(image_data, bytes) and image_data:
                        try:
                            logger.debug(f"Processing raw image data: {len(image_data)} bytes, type={mime_type}")
                            base64_image = base64.b64encode(image_data).decode('utf-8')
                            message_content.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": base64_image
                                }
                            })
                        except Exception as img_error:
                            logger.error(f"Error processing image data: {img_error}")
                            message_content.append({"type": "text", "text": "(Image could not be processed)"})

            response = self.client.messages.create(
                model=model,
                max_tokens=4000,
                temperature=0.7,
                messages=[{"role": "user", "content": message_content}]
            )
            
            if response.content and len(response.content) > 0:
                response_text = response.content[0].text.strip() # type: ignore
                logger.debug(f"Claude multimodal response length: {len(response_text)} characters")
                return response_text
            else:
                logger.warning("Claude multimodal returned empty response")
                return "I couldn't process that content. Please try again."
                
        except Exception as e:
            logger.error(f"Claude multimodal error: {e}", exc_info=True)
            return "I encountered an error processing your content. Please try again."

    @log_streaming_api_call
    def generate_multimodal_content_streaming(self, prompt: str, contents: List[Dict[str, Any]]) -> Iterator[str]:
        """Generate multimodal content with streaming support"""
        if not self.supports_vision:
            logger.error("Vision not supported but multimodal streaming requested")
            raise NotImplementedError("This model does not support vision inputs.")

        model = self.models["vision"]
        logger.debug(f"Claude multimodal streaming with {len(contents)} content items")

        try:
            message_content = []
            
            # Add the main prompt if provided
            if prompt.strip():
                message_content.append({"type": "text", "text": prompt})
            
            # Process each content item (same logic as non-streaming)
            for content_item in contents:
                content_type = content_item.get("type")
                if content_type == "text":
                    text_content = content_item.get("text", "")
                    if text_content:
                        message_content.append({"type": "text", "text": text_content})
                        
                elif content_type == "image_url":
                    image_url = content_item.get("url", "")
                    if image_url:
                        try:
                            img_response = requests.get(image_url, timeout=30)
                            img_response.raise_for_status()
                            
                            content_type_header = img_response.headers.get('content-type', '')
                            if content_type_header.startswith('image/'):
                                media_type = content_type_header
                            elif image_url.lower().endswith('.png'):
                                media_type = "image/png"
                            elif image_url.lower().endswith('.gif'):
                                media_type = "image/gif"
                            elif image_url.lower().endswith('.webp'):
                                media_type = "image/webp"
                            else:
                                media_type = "image/jpeg"
                            
                            base64_image = base64.b64encode(img_response.content).decode('utf-8')
                            message_content.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": base64_image
                                }
                            })
                        except Exception as img_error:
                            logger.error(f"Error fetching image: {img_error}")
                            message_content.append({"type": "text", "text": "(Image could not be loaded)"})
                            
                elif content_type == "image_data":
                    image_data = content_item.get("data", b"")
                    mime_type = content_item.get("mime_type", "image/jpeg")
                    if isinstance(image_data, bytes) and image_data:
                        try:
                            base64_image = base64.b64encode(image_data).decode('utf-8')
                            message_content.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": base64_image
                                }
                            })
                        except Exception as img_error:
                            logger.error(f"Error processing image data: {img_error}")
                            message_content.append({"type": "text", "text": "(Image could not be processed)"})

            with self.client.messages.stream(
                model=model,
                max_tokens=4000,
                temperature=0.7,
                messages=[{"role": "user", "content": message_content}]
            ) as stream:
                for text_chunk in stream.text_stream:
                    yield text_chunk
                    
        except Exception as e:
            logger.error(f"Claude multimodal streaming error: {e}", exc_info=True)
            yield "I encountered an error processing your content. Please try again."

class GeminiBackend:
    """Google Gemini backend with proper error handling"""
    
    def __init__(self):
        logger.info("Initializing Gemini backend")
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY environment variable not set")
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        
        logger.debug("Gemini API key found, configuring genai")
        genai.configure(api_key=api_key) # type: ignore
        
        self.text_model = genai.GenerativeModel("gemini-2.5-pro") # type: ignore
        self.vision_model = genai.GenerativeModel("gemini-2.5-pro") # type: ignore
        self.supports_vision: bool = True
        logger.info("Gemini backend initialized with gemini-2.5-pro model")

    @log_api_call
    def generate_text_content(self, text: str, task: Optional[str] = None) -> str:
        """Generate text-only content"""
        logger.debug(f"Gemini text generation, input length: {len(text)} characters")
        
        try:
            response = self.text_model.generate_content(text)
            if not response.text:
                logger.warning("Gemini returned empty response")
                return "I couldn't generate a response. Please try again."
            
            logger.debug(f"Gemini response length: {len(response.text)} characters")
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Gemini text generation error: {e}", exc_info=True)
            return "I encountered an error while processing your request. Please try again."

    @log_streaming_api_call
    def generate_text_content_streaming(self, text: str, task: Optional[str] = None) -> Iterator[str]:
        """Generate text-only content with streaming support"""
        logger.debug("Starting Gemini text streaming")
        
        try:
            stream = self.text_model.generate_content(text, stream=True)
            for chunk in stream:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error(f"Gemini streaming error: {e}", exc_info=True)
            yield "I encountered an error while processing your request. Please try again."

    @log_api_call
    def generate_multimodal_content(self, prompt: str, contents: List[Dict[str, Any]]) -> str:
        """Generate content with text and images"""
        if not self.supports_vision:
            logger.error("Vision not supported but multimodal content requested")
            raise NotImplementedError("This model does not support vision inputs.")

        logger.debug(f"Gemini multimodal request with {len(contents)} content items")

        try:
            gemini_contents = []
            if prompt.strip():
                gemini_contents.append(prompt)
            
            for i, content_item in enumerate(contents):
                content_type = content_item.get("type")
                logger.debug(f"Processing content item {i}: type={content_type}")
                
                if content_type == "text":
                    text_content = content_item.get("text", "")
                    if text_content:
                        gemini_contents.append(text_content)
                elif content_type == "image_url":
                    image_url = content_item.get("url", "")
                    if image_url:
                        try:
                            logger.debug(f"Fetching image from URL: {image_url[:50]}...")
                            img_response = requests.get(image_url, timeout=30)
                            img_response.raise_for_status()
                            logger.debug(f"Image downloaded: {len(img_response.content)} bytes")
                            img = PIL.Image.open(io.BytesIO(img_response.content))
                            gemini_contents.append(img)
                        except Exception as img_error:
                            logger.error(f"Error fetching image from {image_url}: {img_error}")
                            gemini_contents.append("(Image could not be loaded)")
                elif content_type == "image_data":
                    image_data = content_item.get("data", b"")
                    if isinstance(image_data, bytes) and image_data:
                        try:
                            logger.debug(f"Processing raw image data: {len(image_data)} bytes")
                            img = PIL.Image.open(io.BytesIO(image_data))
                            gemini_contents.append(img)
                        except Exception as img_error:
                            logger.error(f"Error processing image data: {img_error}")
                            gemini_contents.append("(Image could not be processed)")

            response = self.vision_model.generate_content(gemini_contents)
            if not response.text:
                logger.warning("Gemini multimodal returned empty response")
                return "I couldn't process that content. Please try again."
            
            logger.debug(f"Gemini multimodal response length: {len(response.text)} characters")
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Gemini multimodal generation error: {e}", exc_info=True)
            return "I encountered an error processing your content. Please try again."

    @log_streaming_api_call
    def generate_multimodal_content_streaming(self, prompt: str, contents: List[Dict[str, Any]]) -> Iterator[str]:
        """Generate multimodal content with streaming support"""
        if not self.supports_vision:
            logger.error("Vision not supported but multimodal streaming requested")
            raise NotImplementedError("This model does not support vision inputs.")

        logger.debug(f"Gemini multimodal streaming with {len(contents)} content items")

        try:
            gemini_contents = []
            if prompt.strip():
                gemini_contents.append(prompt)
            
            for content_item in contents:
                content_type = content_item.get("type")
                if content_type == "text":
                    text_content = content_item.get("text", "")
                    if text_content:
                        gemini_contents.append(text_content)
                elif content_type == "image_url":
                    image_url = content_item.get("url", "")
                    if image_url:
                        try:
                            img_response = requests.get(image_url, timeout=30)
                            img_response.raise_for_status()
                            img = PIL.Image.open(io.BytesIO(img_response.content))
                            gemini_contents.append(img)
                        except Exception as img_error:
                            logger.error(f"Error fetching image: {img_error}")
                            gemini_contents.append("(Image could not be loaded)")
                elif content_type == "image_data":
                    image_data = content_item.get("data", b"")
                    if isinstance(image_data, bytes) and image_data:
                        try:
                            img = PIL.Image.open(io.BytesIO(image_data))
                            gemini_contents.append(img)
                        except Exception as img_error:
                            logger.error(f"Error processing image data: {img_error}")
                            gemini_contents.append("(Image could not be processed)")
            
            stream = self.vision_model.generate_content(gemini_contents, stream=True)
            for chunk in stream:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Gemini multimodal streaming error: {e}", exc_info=True)
            yield "I encountered an error processing your content. Please try again."

# Factory function to create backends
def create_backend(backend_type: str) -> Union[OpenAIBackend, ClaudeBackend, GeminiBackend]:
    """Factory function to create backend instances"""
    backend_type = backend_type.lower()
    
    logger.info(f"Creating backend of type: {backend_type}")
    
    try:
        if backend_type == "openai":
            backend = OpenAIBackend()
        elif backend_type == "claude":
            backend = ClaudeBackend()
        elif backend_type == "gemini":
            backend = GeminiBackend()
        else:
            logger.error(f"Unsupported backend type: {backend_type}")
            raise ValueError(f"Unsupported backend type: {backend_type}. Supported types: openai, claude, gemini")
        
        logger.info(f"Successfully created {backend_type} backend")
        return backend
        
    except Exception as e:
        logger.error(f"Failed to create {backend_type} backend: {e}", exc_info=True)
        raise
