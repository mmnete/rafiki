import concurrent.futures
import traceback
import json
from decimal import Decimal
from datetime import datetime
from dataclasses import is_dataclass, asdict
from typing import List, Dict, Any, Callable, Optional
from app.services.modelling.response_parser import ToolCall


class ToolExecutorService:
    """
    Handles tool execution with proper error handling and formatting.
    
    Responsibilities:
    - Execute tool calls concurrently
    - Handle tool execution errors
    - Format results for model consumption
    
    Does not know about specific tools - just executes callable functions.
    """
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
    
    
    def execute_tool_calls(self, tool_calls: List[ToolCall], available_tools: Dict[str, Callable], 
                        available_tool_context: Dict[str, Callable], user_id: str) -> List[Dict[str, Any]]:
        """
        Execute multiple tool calls concurrently
        
        Args:
            tool_calls: List of parsed tool calls
            available_tools: Dict mapping tool names to executable functions
            available_tool_context: Dict mapping tool names to context extraction functions (optional)
            user_id: User identifier to pass to tools
            
        Returns:
            List of execution results
        """
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tool calls
            future_to_tool = {}
            for call in tool_calls:
                if call.name in available_tools:
                    # Get context function if available, otherwise None
                    context_function = available_tool_context.get(call.name)
                    
                    future = executor.submit(
                        self._execute_single_tool,
                        available_tools[call.name],
                        call,
                        user_id,
                        context_function  # This can safely be None
                    )
                    future_to_tool[future] = call
                else:
                    # Tool not available
                    results.append({
                        "tool_name": call.name,
                        "success": False,
                        "error": f"Tool '{call.name}' not available",
                        "error_type": "ToolNotFound",
                        "context_summary": None
                    })
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_tool):
                tool_call = future_to_tool[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"Unexpected error in tool execution future for '{tool_call.name}': {e}")
                    traceback.print_exc()
                    results.append({
                        "tool_name": tool_call.name,
                        "success": False,
                        "error": f"Future execution failed: {str(e)}",
                        "error_type": "FutureExecutionError",
                        "context_summary": None
                    })
        
        return results

    def _execute_single_tool(self, tool_function: Callable, tool_call: ToolCall, user_id: str, 
                            tool_context: Optional[Callable] = None) -> Dict[str, Any]:
        """Execute a single tool call with error handling"""
        try:
            # Execute the main tool function
            result_data = tool_function(user_id=user_id, **tool_call.args)
            context_summary = None
            
            # Extract context summary if context function is provided
            if tool_context is not None:
                try:
                    context_summary = tool_context(result_data, user_id)
                    print(f"Successfully extracted context for tool '{tool_call.name}'")
                except Exception as context_error:
                    print(f"Warning: Error extracting context for tool '{tool_call.name}': {context_error}")
                    # Don't fail the entire tool execution if context extraction fails
                    context_summary = f"Context extraction failed: {str(context_error)}"
            else:
                print(f"No context extractor available for tool '{tool_call.name}'")
            
            return {
                "tool_name": tool_call.name,
                "success": True,
                "result": result_data,
                "context_summary": context_summary,
                "execution_time": None  # Could add timing if needed
            }
            
        except TypeError as type_error:
            # Handle cases where tool function signature doesn't match expected parameters
            print(f"ERROR: Type/parameter mismatch executing tool '{tool_call.name}': {type_error}")
            traceback.print_exc()
            return {
                "tool_name": tool_call.name,
                "success": False,
                "error": f"Parameter mismatch: {str(type_error)}",
                "error_type": "ParameterError",
                "context_summary": None
            }
            
        except Exception as execution_error:
            print(f"ERROR executing tool '{tool_call.name}': {execution_error}")
            traceback.print_exc()
            return {
                "tool_name": tool_call.name,
                "success": False,
                "error": str(execution_error),
                "error_type": "ToolExecutionError",
                "context_summary": None
            }

    def format_tool_results_for_model(self, tool_results: List[Dict[str, Any]]) -> str:
        """Format tool execution results for model consumption"""
        if not tool_results:
            return ""
            
        formatted_results = ["<tool_results>"]
            
        for result in tool_results:
            tool_name = result.get("tool_name", "unknown")
                    
            if result.get("success", False):
                # Successful execution
                result_data = result.get("result", {})
                formatted_results.append(f'<result tool_name="{tool_name}">')
                
                # Safe JSON serialization with dataclass support
                try:
                    json_output = json.dumps(result_data, default=self._json_serializer)
                except (TypeError, ValueError) as e:
                    # Fallback to string representation
                    json_output = json.dumps(str(result_data))
                        
                formatted_results.append(f'<output>{json_output}</output>')
                formatted_results.append('</result>')
            else:
                # Failed execution
                error_msg = result.get("error", "Unknown error")
                error_type = result.get("error_type", "Error")
                            
                formatted_results.append(f'<result tool_name="{tool_name}">')
                formatted_results.append('<error>')
                formatted_results.append(f'<type>{error_type}</type>')
                formatted_results.append(f'<message>{error_msg}</message>')
                formatted_results.append('<action_required>This tool call failed. You can retry, inform the user, or proceed if other tools provided sufficient information.</action_required>')
                formatted_results.append('</error>')
                formatted_results.append('</result>')
                
        formatted_results.append("</tool_results>")
        return "\n".join(formatted_results)

    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for complex objects"""
        # Handle dataclass objects
        if is_dataclass(obj):
            return asdict(obj) # type: ignore
        
        # Handle datetime objects
        if isinstance(obj, datetime):
            return obj.isoformat()
        
        # Handle Decimal objects
        if isinstance(obj, Decimal):
            return float(obj)
        
        # Handle other common non-serializable types
        if hasattr(obj, '__dict__'):
            # Convert object to dict, handling nested dataclasses
            result = {}
            for key, value in obj.__dict__.items():
                try:
                    # Recursively handle nested objects
                    result[key] = self._json_serializer(value) if not isinstance(value, (str, int, float, bool, type(None))) else value
                except:
                    result[key] = str(value)
            return result
        
        # Final fallback - convert to string
        return str(obj)

    
