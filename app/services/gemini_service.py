import os
from typing import List, Tuple
import google.generativeai as genai
import os
import google.generativeai as genai
from typing import Tuple, List
from app.tools.response_parser import ModelOrchestrator

class GeminiService:
    """
    Clean Gemini service focused only on model communication
    """
    
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name="gemini-2.5-flash")
    
    def generate_content(self, prompt: str):
        """
        Simple method to generate content from Gemini
        No parsing logic here - just raw model communication
        """
        return self.model.generate_content(prompt)

class EnhancedGeminiService:
    """
    Enhanced service that combines Gemini with the scalable parsing system
    Everything is self-contained through the ModelOrchestrator
    """
    
    def __init__(self):
        self.gemini_service = GeminiService()
        # ModelOrchestrator handles everything - tools, parsing, execution
        self.orchestrator = ModelOrchestrator(model_service=self.gemini_service)
    
    def ask_gemini(self, prompt: str) -> Tuple[str, List[str]]:
        """
        Main interface for asking Gemini with full tool support
        No need to pass tools - everything is handled by the orchestrator
        
        Args:
            prompt: The prompt to send
            
        Returns:
            Tuple[final_response, conversation_history]
        """
        return self.orchestrator.process_request(prompt)
    
    def add_parser_pattern(self, name: str, pattern: str, flags: int = 0):
        """Add a custom parsing pattern"""
        self.orchestrator.add_parser_pattern(name, pattern, flags)
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names"""
        return self.orchestrator.get_available_tools()

