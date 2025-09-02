import os
from typing import Dict, List, Optional, Protocol, Any, Union, Iterator
import openai
import google.generativeai as genai
import requests
import base64
import PIL.Image # type: ignore
import io

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
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        
        self.client = openai.OpenAI(api_key=api_key)
        
        # Define task-specific models
        self.models: Dict[str, str] = {
            "reasoning": "gpt-4o",
            "vision": "gpt-4o",
            "lightweight": "gpt-4o-mini",
            "default": "gpt-4o-mini"
        }
        self.supports_vision: bool = True

    def generate_text_content(self, text: str, task: str = "reasoning") -> str:
        """Generate text-only content"""
        try:
            model = self.models.get(task, self.models["default"])
            
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
                return "I apologize, but I couldn't generate a response."
            
            return response_content.strip()
            
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return "I encountered an error while processing your request. Please try again."

    def generate_text_content_streaming(self, text: str, task: str = "reasoning") -> Iterator[str]:
        """Generate text-only content with streaming support"""
        try:
            model = self.models.get(task, self.models["default"])
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
            print(f"OpenAI streaming error: {e}")
            yield "I encountered an error while processing your request. Please try again."

    def generate_multimodal_content(self, prompt: str, contents: List[Dict[str, Any]]) -> str:
        """Generate content with text and images"""
        if not self.supports_vision:
            raise NotImplementedError("This model does not support vision inputs.")

        try:
            model = self.models["vision"]
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
            response = self.client.chat.completions.create(
                model=model,
                messages=messages, # type: ignore
                temperature=0.7,
                max_tokens=4000
            )
            
            response_content = response.choices[0].message.content
            if not response_content:
                return "I couldn't process that content. Please try again."
            
            return response_content.strip()
            
        except Exception as e:
            print(f"OpenAI multimodal API error: {e}")
            return "I encountered an error processing your content. Please try again."

    def generate_multimodal_content_streaming(self, prompt: str, contents: List[Dict[str, Any]]) -> Iterator[str]:
        """Generate multimodal content with streaming support"""
        if not self.supports_vision:
            raise NotImplementedError("This model does not support vision inputs.")

        try:
            model = self.models["vision"]
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
            print(f"OpenAI multimodal streaming error: {e}")
            yield "I encountered an error processing your content. Please try again."

class GeminiBackend:
    """Google Gemini backend with proper error handling"""
    
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        
        genai.configure(api_key=api_key) # type: ignore
        
        self.text_model = genai.GenerativeModel("gemini-1.5-flash") # type: ignore
        self.vision_model = genai.GenerativeModel("gemini-1.5-flash") # type: ignore
        self.supports_vision: bool = True

    def generate_text_content(self, text: str, task: Optional[str] = None) -> str:
        """Generate text-only content"""
        try:
            response = self.text_model.generate_content(text)
            if not response.text:
                return "I couldn't generate a response. Please try again."
            return response.text.strip()
        except Exception as e:
            print(f"Gemini text generation error: {e}")
            return "I encountered an error while processing your request. Please try again."

    def generate_text_content_streaming(self, text: str, task: Optional[str] = None) -> Iterator[str]:
        """Generate text-only content with streaming support"""
        try:
            stream = self.text_model.generate_content(text, stream=True)
            for chunk in stream:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            print(f"Gemini streaming error: {e}")
            yield "I encountered an error while processing your request. Please try again."

    def generate_multimodal_content(self, prompt: str, contents: List[Dict[str, Any]]) -> str:
        """Generate content with text and images"""
        if not self.supports_vision:
            raise NotImplementedError("This model does not support vision inputs.")

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
                            img_response = requests.get(image_url)
                            img_response.raise_for_status()
                            img = PIL.Image.open(io.BytesIO(img_response.content))
                            gemini_contents.append(img)
                        except Exception as img_error:
                            print(f"Error fetching image: {img_error}")
                            gemini_contents.append("(Image could not be loaded)")
                elif content_type == "image_data":
                    image_data = content_item.get("data", b"")
                    if isinstance(image_data, bytes) and image_data:
                        try:
                            img = PIL.Image.open(io.BytesIO(image_data))
                            gemini_contents.append(img)
                        except Exception as img_error:
                            print(f"Error processing image data: {img_error}")
                            gemini_contents.append("(Image could not be processed)")

            response = self.vision_model.generate_content(gemini_contents)
            if not response.text:
                return "I couldn't process that content. Please try again."
            return response.text.strip()
            
        except Exception as e:
            print(f"Gemini multimodal generation error: {e}")
            return "I encountered an error processing your content. Please try again."

    def generate_multimodal_content_streaming(self, prompt: str, contents: List[Dict[str, Any]]) -> Iterator[str]:
        """Generate multimodal content with streaming support"""
        if not self.supports_vision:
            raise NotImplementedError("This model does not support vision inputs.")

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
                            img_response = requests.get(image_url)
                            img_response.raise_for_status()
                            img = PIL.Image.open(io.BytesIO(img_response.content))
                            gemini_contents.append(img)
                        except Exception as img_error:
                            print(f"Error fetching image: {img_error}")
                            gemini_contents.append("(Image could not be loaded)")
                elif content_type == "image_data":
                    image_data = content_item.get("data", b"")
                    if isinstance(image_data, bytes) and image_data:
                        try:
                            img = PIL.Image.open(io.BytesIO(image_data))
                            gemini_contents.append(img)
                        except Exception as img_error:
                            print(f"Error processing image data: {img_error}")
                            gemini_contents.append("(Image could not be processed)")
            
            stream = self.vision_model.generate_content(gemini_contents, stream=True)
            for chunk in stream:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            print(f"Gemini multimodal streaming error: {e}")
            yield "I encountered an error processing your content. Please try again."