import logging
from typing import Any, Callable, Dict, List, Tuple
from app.services.modelling.model_service import ModelService
from app.services.modelling.response_parser import ResponseParser, ResponseType, ParsedResponse
from app.services.modelling.tool_executor_service import ToolExecutorService

logger = logging.getLogger(__name__)

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
        logger.info(f"ConversationOrchestrator initialized with max_iterations={max_iterations}")
    
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
        
        logger.info(f"Starting conversation turn for user {user_id}", extra={
            'user_id': user_id,
            'user_message_preview': user_message[:50] + '...' if len(user_message) > 50 else user_message,
            'prompt_length': len(prompt)
        })
        
        for iteration in range(self.max_iterations):
            logger.debug(f"Beginning iteration {iteration + 1}/{self.max_iterations}", extra={
                'user_id': user_id,
                'iteration': iteration + 1,
                'current_prompt_length': len(current_prompt)
            })
            
            try:
                # Generate model response
                raw_response = self.model_service.generate_text_content(current_prompt)
                logger.debug(f"Model response generated", extra={
                    'user_id': user_id,
                    'iteration': iteration + 1,
                    'response_length': len(raw_response),
                    'response_preview': raw_response[:100] + '...' if len(raw_response) > 100 else raw_response
                })
                
                # Parse response
                parsed_response = self.response_parser.parse(raw_response)
                logger.debug(f"Response parsed", extra={
                    'user_id': user_id,
                    'iteration': iteration + 1,
                    'response_type': parsed_response.response_type.value,
                    'has_tool_calls': bool(parsed_response.tool_calls),
                    'num_tool_calls': len(parsed_response.tool_calls) if parsed_response.tool_calls else 0
                })
                
                # Handle based on response type
                if parsed_response.response_type == ResponseType.FINAL_RESPONSE:
                    logger.info(f"Final response generated for user {user_id}", extra={
                        'user_id': user_id,
                        'total_iterations': iteration + 1,
                        'total_tool_results': len(all_tool_results),
                        'final_response_length': len(parsed_response.content)
                    })
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
                    logger.info(f"Executed tools for user {user_id}", extra={
                        'user_id': user_id,
                        'iteration': iteration + 1,
                        'tools_executed': tool_names,
                        'num_results': len(tool_results),
                        'total_tool_results': len(all_tool_results)
                    })
                    
                    # Format results and continue conversation
                    formatted_results = self.tool_executor.format_tool_results_for_model(tool_results)
                    current_prompt += f"""{raw_response}
                    
                    System: {formatted_results}
                    
                    Rafiki:"""
                    
                    logger.debug(f"Prompt updated for next iteration", extra={
                        'user_id': user_id,
                        'iteration': iteration + 1,
                        'new_prompt_length': len(current_prompt)
                    })
                
                else:
                    logger.warning(f"Unexpected response type or parse error", extra={
                        'user_id': user_id,
                        'iteration': iteration + 1,
                        'response_type': parsed_response.response_type.value,
                        'errors': parsed_response.errors
                    })
                    return "I'm having trouble processing that request. Could you rephrase it?", all_tool_results
                    
            except Exception as e:
                logger.error(f"Error during conversation iteration", extra={
                    'user_id': user_id,
                    'iteration': iteration + 1,
                    'error': str(e),
                    'error_type': type(e).__name__
                }, exc_info=True)
                return "I encountered an error processing your request. Please try again.", all_tool_results
        
        logger.warning(f"Max iterations reached for user {user_id}", extra={
            'user_id': user_id,
            'max_iterations': self.max_iterations,
            'total_tool_results': len(all_tool_results)
        })
        return "I'm having trouble completing your request. Please try again.", all_tool_results
    
    def describe_image(self, image_info: Dict[str, str]) -> ParsedResponse:
        """Describe an image and return structured response"""
        logger.info("Image description requested", extra={
            'image_info_keys': list(image_info.keys()) if image_info else None
        })
        
        try:
            description = self.model_service.describe_image(image_info)
            logger.info("Image description completed successfully", extra={
                'description_length': len(description)
            })
            return ParsedResponse(
                response_type=ResponseType.FINAL_RESPONSE,
                content=description,
                raw_response=description
            )
        except Exception as e:
            logger.error("Error describing image", extra={
                'error': str(e),
                'error_type': type(e).__name__
            }, exc_info=True)
            return ParsedResponse(
                response_type=ResponseType.ERROR,
                content="",
                raw_response="",
                errors=[f"Error describing image: {e}"]
            )