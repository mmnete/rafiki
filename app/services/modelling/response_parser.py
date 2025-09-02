import re
import ast
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

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
    raw_response: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    thinking: Optional[str] = None
    errors: List[str] = field(default_factory=list)

class ResponseParser:
    """
    Parses AI model responses to extract tool calls, thinking, and final responses.
    
    Pure parsing logic with no dependencies on other services.
    """
    
    def __init__(self):
        self.patterns = {
            'tool_call': re.compile(r"<call>(\w+)\((.*?)\)</call>"),
            'response_block': re.compile(r"<response>(.*?)</response>", re.DOTALL),
            'thinking_block': re.compile(r"<thinking>(.*?)</thinking>", re.DOTALL),
        }
    
    def parse(self, response_text: str) -> ParsedResponse:
        """Parse raw model response into structured format"""
        # Extract thinking blocks
        thinking_matches = self.patterns['thinking_block'].findall(response_text)
        thinking = "\n".join(thinking_matches).strip() or None
        
        # Remove thinking blocks from response
        cleaned_response = self.patterns['thinking_block'].sub("", response_text).strip()
        
        # Parse tool calls
        tool_calls = self._parse_tool_calls(cleaned_response)
        
        if tool_calls:
            return ParsedResponse(
                response_type=ResponseType.TOOL_CALL,
                content=cleaned_response,
                tool_calls=tool_calls,
                thinking=thinking,
                raw_response=response_text
            )
        else:
            final_content = self._extract_final_response(cleaned_response)
            return ParsedResponse(
                response_type=ResponseType.FINAL_RESPONSE,
                content=final_content,
                thinking=thinking,
                raw_response=response_text
            )
    
    def _parse_tool_calls(self, text: str) -> List[ToolCall]:
        """Extract all tool calls from text"""
        calls = []
        for match in self.patterns['tool_call'].finditer(text):
            tool_name, args_str = match.groups()
            try:
                args = self._parse_arguments(args_str)
                calls.append(ToolCall(
                    name=tool_name,
                    args=args,
                    raw_call=match.group(0)
                ))
            except Exception as e:
                print(f"Warning: Could not parse args for tool '{tool_name}': {e}")
        return calls
    
    def _parse_arguments(self, args_str: str) -> Dict[str, Any]:
        """Safely parse tool call arguments"""
        if not args_str.strip():
            return {}
        
        # Try safe evaluation first
        eval_str = f"dict({args_str})"
        try:
            return ast.literal_eval(eval_str)
        except (ValueError, SyntaxError, NameError):
            # Fallback parsing for malformed arguments
            args = {}
            for part in re.finditer(r'(\w+)\s*=\s*(".*?"|\'.*?\'|[^,]+)', args_str):
                key, value = part.groups()
                try:
                    args[key] = ast.literal_eval(value)
                except (ValueError, SyntaxError):
                    args[key] = value.strip().strip('"\'')  # Remove quotes
            return args
    
    def _extract_final_response(self, text: str) -> str:
        """Extract final response content"""
        # Look for explicit response block first
        response_match = self.patterns['response_block'].search(text)
        if response_match:
            return response_match.group(1).strip()
        
        # Fallback: clean tool calls and return remaining text
        return self.patterns['tool_call'].sub("", text).strip()