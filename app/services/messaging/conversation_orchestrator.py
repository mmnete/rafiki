from typing import Any, Callable, Dict, List, Tuple
from app.services.modelling.model_service import ModelService
from app.services.modelling.response_parser import ResponseParser, ResponseType, ParsedResponse
from app.services.modelling.tool_executor_service import ToolExecutorService

class ConversationOrchestrator:
    """
    Orchestrates multi-turn conversations with tool calling support.
    
    Responsibilities:
    - Manage conversation flow
    - Coordinate between model, parser, and tool executor
    - Handle iteration limits and fallbacks
    
    This replaces your EnhancedModelService.
    """
    
    def __init__(self, model_service: ModelService, response_parser: ResponseParser, 
                 tool_executor: ToolExecutorService, max_iterations: int = 5):
        self.model_service = model_service
        self.response_parser = response_parser
        self.tool_executor = tool_executor
        self.max_iterations = max_iterations
    
    def process_conversation_turn(self, prompt: str, user_id: str, user_message: str, 
                                available_tool_functions: Dict[str, Callable], available_tool_context: Dict[str, Callable] = {}) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Process a complete conversation turn with tool calling support
        
        Args:
            prompt: The full prompt to send to the model
            user_id: User identifier
            user_message: Original user message (for logging)
            available_tool_functions: Available tool functions
            
        Returns:
            Tuple of (final_response, all_tool_results)
        """
        current_prompt = prompt
        all_tool_results = []
        
        print(f"[{user_id}] Starting conversation turn. User: '{user_message[:50]}...'")
        
        for iteration in range(self.max_iterations):
            print(f"[{user_id}] --- Iteration {iteration + 1}/{self.max_iterations} ---")
            
            print(f"--- Current Prompt: {current_prompt} ---")
            
            # Generate model response
            raw_response = self.model_service.generate_text_content(current_prompt)
            print(f"[{user_id}] Raw response: '{raw_response[:100]}...'")
            
            # Parse response
            parsed_response = self.response_parser.parse(raw_response)
            print(f"[{user_id}] Parsed type: {parsed_response.response_type.value}")
            
            # Handle based on response type
            if parsed_response.response_type == ResponseType.FINAL_RESPONSE:
                print(f"[{user_id}] Final response generated")
                return parsed_response.content, all_tool_results
            
            elif parsed_response.response_type == ResponseType.TOOL_CALL:
                # Execute tools
                tool_results = self.tool_executor.execute_tool_calls(
                    parsed_response.tool_calls, 
                    available_tool_functions, 
                    available_tool_context,
                    user_id
                )
                all_tool_results.extend(tool_results)
                
                tool_names = [call.name for call in parsed_response.tool_calls]
                print(f"[{user_id}] Executed tools: {tool_names}")
                
                # Format results and continue conversation
                formatted_results = self.tool_executor.format_tool_results_for_model(tool_results)
                current_prompt += f"\n{raw_response}\n{formatted_results}"
            
            else:
                print(f"[{user_id}] Parse error or unexpected response")
                return "I'm having trouble processing that request. Could you rephrase it?", all_tool_results
        
        print(f"[{user_id}] Max iterations reached")
        return "I'm having trouble completing your request. Please try again.", all_tool_results
    
    def describe_image(self, image_info: Dict[str, str]) -> ParsedResponse:
        """Describe an image and return structured response"""
        try:
            description = self.model_service.describe_image(image_info)
            return ParsedResponse(
                response_type=ResponseType.FINAL_RESPONSE,
                content=description,
                raw_response=description
            )
        except Exception as e:
            return ParsedResponse(
                response_type=ResponseType.ERROR,
                content="",
                raw_response="",
                errors=[f"Error describing image: {e}"]
            )
