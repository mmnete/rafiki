# Updated response_parser.py with formatting support
import re
import ast
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from .toolcall_config import get_tool_manager

class ResponseType(Enum):
    TOOL_CALL = "tool_call"
    FINAL_RESPONSE = "final_response"
    ERROR = "error"

@dataclass
class ToolCall:
    name: str
    args: Dict[str, Any]
    raw_call: str

@dataclass
class ParsedResponse:
    response_type: ResponseType
    content: str
    tool_calls: List[ToolCall] = None
    thinking: str = None
    raw_response: str = None
    errors: List[str] = None

class ResponseParser:
    """
    Enhanced parser for AI model responses that handles:
    - Thinking blocks
    - Tool calls
    - Final responses with formatting
    - Error handling
    """
    
    def __init__(self):
        # Configurable regex patterns
        self.patterns = {
            'tool_call': re.compile(r"<call>(\w+)\((.*?)\)</call>"),
            'response_block': re.compile(r"<response>(.*?)</response>", re.DOTALL),
            'thinking_block': re.compile(r"<thinking>(.*?)</thinking>", re.DOTALL),
            'action_block': re.compile(r"<action>(.*?)</action>", re.DOTALL),
            # Add more patterns as needed
        }
    
    def parse_response(self, response_text: str) -> ParsedResponse:
        """
        Parse a model response and return structured data
        
        Args:
            response_text: Raw response from the AI model
            
        Returns:
            ParsedResponse: Structured response data
        """
        errors = []
        
        # Extract thinking blocks
        thinking_matches = self.patterns['thinking_block'].findall(response_text)
        thinking = "\n".join(thinking_matches).strip() if thinking_matches else None
        
        # Remove thinking blocks for further processing
        cleaned_response = self.patterns['thinking_block'].sub("", response_text).strip()
        
        # Parse tool calls
        tool_calls = self._parse_tool_calls(cleaned_response)
        
        # Determine response type and extract content
        if tool_calls:
            return ParsedResponse(
                response_type=ResponseType.TOOL_CALL,
                content=cleaned_response,
                tool_calls=tool_calls,
                thinking=thinking,
                raw_response=response_text
            )
        else:
            # Extract final response
            final_content = self._extract_final_response(cleaned_response)
            return ParsedResponse(
                response_type=ResponseType.FINAL_RESPONSE,
                content=final_content,
                thinking=thinking,
                raw_response=response_text,
                errors=errors if errors else None
            )
    
    def _parse_tool_calls(self, text: str) -> List[ToolCall]:
        """Parse tool calls from text"""
        tool_calls = []
        matches = self.patterns['tool_call'].findall(text)
        
        for tool_name, args_str in matches:
            try:
                args = self._parse_tool_arguments(args_str)
                tool_calls.append(ToolCall(
                    name=tool_name,
                    args=args,
                    raw_call=f"<call>{tool_name}({args_str})</call>"
                ))
            except Exception as e:
                print(f"Error parsing tool call {tool_name}: {e}")
                continue
        
        return tool_calls
    
    def _parse_tool_arguments(self, args_str: str) -> Dict[str, Any]:
        """Parse tool arguments from string format"""
        args = {}
        
        # Handle empty arguments
        if not args_str.strip():
            return args
        
        # Split by comma, but be careful with nested structures
        arg_parts = self._split_arguments(args_str)
        
        for arg_part in arg_parts:
            key_value = arg_part.strip().split('=', 1)
            if len(key_value) == 2:
                key = key_value[0].strip()
                value_str = key_value[1].strip()
                
                try:
                    # Use ast.literal_eval for safe parsing
                    args[key] = ast.literal_eval(value_str)
                except (ValueError, SyntaxError):
                    # Fallback to string if literal_eval fails
                    # Remove quotes if present
                    if (value_str.startswith('"') and value_str.endswith('"')) or \
                       (value_str.startswith("'") and value_str.endswith("'")):
                        args[key] = value_str[1:-1]
                    else:
                        args[key] = value_str
        
        return args
    
    def _split_arguments(self, args_str: str) -> List[str]:
        """Smart argument splitting that handles nested structures"""
        parts = []
        current_part = ""
        paren_count = 0
        bracket_count = 0
        in_quotes = False
        quote_char = None
        
        for char in args_str:
            if char in ['"', "'"] and not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
            elif not in_quotes:
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                elif char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                elif char == ',' and paren_count == 0 and bracket_count == 0:
                    parts.append(current_part)
                    current_part = ""
                    continue
            
            current_part += char
        
        if current_part:
            parts.append(current_part)
        
        return parts
    
    def _extract_final_response(self, text: str) -> str:
        """Extract final response from text"""
        # First try to find response block
        response_match = self.patterns['response_block'].search(text)
        if response_match:
            return response_match.group(1).strip()
        
        # If no response block, return cleaned text
        # Remove any remaining tool call patterns
        cleaned = self.patterns['tool_call'].sub("", text).strip()
        
        prefix = "Rafiki:"
        if cleaned.lower().startswith(prefix.lower()):
            cleaned = cleaned[len(prefix):].lstrip()
        
        return cleaned
    
    def add_pattern(self, name: str, pattern: str, flags: int = 0):
        """Add a new regex pattern for parsing"""
        self.patterns[name] = re.compile(pattern, flags)
    
    def remove_pattern(self, name: str):
        """Remove a regex pattern"""
        if name in self.patterns:
            del self.patterns[name]

class ToolExecutor:
    """
    Handles tool execution separately from parsing
    """
    
    def __init__(self, available_tools: Dict[str, callable]):
        self.available_tools = available_tools
    
    def execute_tool_calls(self, tool_calls: List[ToolCall]) -> List[Dict[str, Any]]:
        """Execute a list of tool calls and return results"""
        results = []
        
        for tool_call in tool_calls:
            try:
                if tool_call.name in self.available_tools:
                    tool_function = self.available_tools[tool_call.name]
                    result = tool_function(**tool_call.args)
                    results.append({
                        "tool_name": tool_call.name,
                        "success": True,
                        "result": result
                    })
                else:
                    results.append({
                        "tool_name": tool_call.name,
                        "success": False,
                        "error": f"Unknown tool: {tool_call.name}"
                    })
            except Exception as e:
                results.append({
                    "tool_name": tool_call.name,
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    def add_tool(self, name: str, function: callable):
        """Add a new tool"""
        self.available_tools[name] = function
    
    def remove_tool(self, name: str):
        """Remove a tool"""
        if name in self.available_tools:
            del self.available_tools[name]

class ModelOrchestrator:
    """
    Enhanced orchestrator with formatting support
    Orchestrates the entire flow: model calls -> parsing -> tool execution -> formatted response
    """
    
    def __init__(self, model_service):
        self.model_service = model_service
        self.parser = ResponseParser()
        self.tool_manager = get_tool_manager()
        self.max_iterations = 3
    
    def process_request(self, prompt: str) -> Tuple[str, List[str]]:
        """
        Process a request through the complete pipeline with formatting support
        
        Returns:
            Tuple[final_response, conversation_history]
        """
        # Add formatting instructions to the prompt
        enhanced_prompt = self._enhance_prompt_with_formatting_instructions(prompt)
        
        current_prompt = enhanced_prompt
        conversation_history = []
        
        for iteration in range(self.max_iterations):
            try:
                # Get response from model
                raw_response = self.model_service.generate_content(current_prompt)
                response_text = raw_response.text if hasattr(raw_response, 'text') else str(raw_response)
                conversation_history.append(response_text)
                
                # Parse the response
                parsed = self.parser.parse_response(response_text)
                
                if parsed.response_type == ResponseType.TOOL_CALL:
                    # Execute tool calls using tool manager
                    tool_results = self._execute_tool_calls(parsed.tool_calls)
                    
                    # Format tool results for next iteration
                    formatted_tool_output = self._format_tool_results_for_model(tool_results)
                    current_prompt += f"\n\n{formatted_tool_output}\n\nrafiki: "
                    
                elif parsed.response_type == ResponseType.FINAL_RESPONSE:
                    # Return final response (should already be formatted)
                    return parsed.content, conversation_history
                    
            except Exception as e:
                print(f"Error in iteration {iteration}: {e}")
                conversation_history.append(f"Error: {str(e)}")
                break
        
        # If we reach here, we've exhausted iterations
        return "Samahani, Rafiki ameshindwa kukamilisha ombi lako baada ya majaribio mengi.", conversation_history
    
    def _enhance_prompt_with_formatting_instructions(self, prompt: str) -> str:
        """Add formatting instructions to the prompt"""
        formatting_instructions = """
        
        **CRITICAL FORMATTING REQUIREMENTS:**
        - When you receive tool results, ALWAYS use the 'formatted_response' field in your final answer
        - The formatted_response contains properly structured flight information with emojis and Swahili text
        - ALWAYS include the corroboration links from search_links so users can verify and book flights
        - If no formatted_response is provided, format the flight data according to the standard format shown in examples
        - Present information in a user-friendly manner with clear pricing, airline names, times, and booking links
        """
        
        return prompt + formatting_instructions
    
    def _execute_tool_calls(self, tool_calls: List[ToolCall]) -> List[Dict[str, Any]]:
        """Execute tool calls using the tool manager"""
        results = []
        
        for tool_call in tool_calls:
            try:
                tool_function = self.tool_manager.get_tool_function(tool_call.name)
                if tool_function:
                    result = tool_function(**tool_call.args)
                    results.append({
                        "tool_name": tool_call.name,
                        "success": True,
                        "result": result
                    })
                else:
                    results.append({
                        "tool_name": tool_call.name,
                        "success": False,
                        "error": f"Unknown tool: {tool_call.name}"
                    })
            except Exception as e:
                results.append({
                    "tool_name": tool_call.name,
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    def _format_tool_results_for_model(self, tool_results: List[Dict[str, Any]]) -> str:
        """Format tool results to send back to the model with emphasis on using formatted_response"""
        formatted_output = "Tool Results:\n"
        
        for result in tool_results:
            if result["success"]:
                tool_data = result["result"]
                formatted_output += f"\n{result['tool_name']} output:\n"
                
                # Prioritize formatted_response if available
                if isinstance(tool_data, dict) and 'formatted_response' in tool_data:
                    formatted_output += f"FORMATTED_RESPONSE (USE THIS): {tool_data['formatted_response']}\n"
                    if 'search_links' in tool_data:
                        formatted_output += f"SEARCH_LINKS (INCLUDE THESE): {tool_data['search_links']}\n"
                    if 'flight_count' in tool_data:
                        formatted_output += f"Flight count: {tool_data['flight_count']}\n"
                else:
                    formatted_output += f"{json.dumps(tool_data)}\n"
            else:
                formatted_output += f"\n{result['tool_name']} error: {result['error']}\n"
        
        formatted_output += "\nIMPORTANT: Use the FORMATTED_RESPONSE exactly as provided and include all SEARCH_LINKS in your response to the user.\n"
        
        return formatted_output
    
    def add_parser_pattern(self, name: str, pattern: str, flags: int = 0):
        """Add a new parsing pattern"""
        self.parser.add_pattern(name, pattern, flags)
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tools from tool manager"""
        return list(self.tool_manager.tools.keys())