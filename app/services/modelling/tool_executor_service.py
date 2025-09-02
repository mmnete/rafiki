import concurrent.futures
import traceback
import json
from typing import List, Dict, Any, Callable
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
                          user_id: str) -> List[Dict[str, Any]]:
        """
        Execute multiple tool calls concurrently
        
        Args:
            tool_calls: List of parsed tool calls
            available_tools: Dict mapping tool names to executable functions
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
                    future = executor.submit(
                        self._execute_single_tool,
                        available_tools[call.name],
                        call,
                        user_id
                    )
                    future_to_tool[future] = call
                else:
                    # Tool not available
                    results.append({
                        "tool_name": call.name,
                        "success": False,
                        "error": f"Tool '{call.name}' not available",
                        "error_type": "ToolNotFound"
                    })
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_tool):
                tool_call = future_to_tool[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"Unexpected error in tool execution future: {e}")
                    traceback.print_exc()
                    results.append({
                        "tool_name": tool_call.name,
                        "success": False,
                        "error": str(e),
                        "error_type": "ExecutionError"
                    })
        
        return results
    
    def _execute_single_tool(self, tool_function: Callable, tool_call: ToolCall, user_id: str) -> Dict[str, Any]:
        """Execute a single tool call with error handling"""
        try:
            result_data = tool_function(user_id=user_id, **tool_call.args)
            return {
                "tool_name": tool_call.name,
                "success": True,
                "result": result_data
            }
        except Exception as e:
            print(f"ERROR executing tool '{tool_call.name}': {e}")
            traceback.print_exc()
            return {
                "tool_name": tool_call.name,
                "success": False,
                "error": str(e),
                "error_type": "ToolExecutionError"
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
                formatted_results.append(f'<output>{json.dumps(result_data)}</output>')
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
