import os
import re
from typing import Any, Dict, List, Optional
from flask import json
import google.generativeai as genai

class GeminiService:
    TOOL_CALL_REGEX = re.compile(r"<call>(\w+)\((.*?)\)</call>")
    
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name="gemini-1.5-flash")  # You can also try "gemini-1.5-pro"

    def _parse_tool_call(self, text: str) -> Optional[Dict[str, Any]]:
        """Parses a tool call from a Gemini text response using regex."""
        match = self.TOOL_CALL_REGEX.search(text)
        if not match:
            return None

        tool_name = match.group(1)
        args_str = match.group(2)
        
        # A simple and robust way to parse key-value pairs
        # WARNING: This simple parsing assumes arguments are simple key='value' pairs.
        # For more complex arguments, a safer method like `ast.literal_eval` might be needed.
        args = {}
        for part in args_str.split(','):
            if '=' in part:
                key, value = part.split('=', 1)
                key = key.strip()
                value = value.strip().strip("'\"")
                # Basic type conversion for numbers
                if value.isdigit():
                    value = int(value)
                args[key] = value

        return {"name": tool_name, "args": args}

    def ask_gemini(self, prompt: str, tools: Dict[str, Any]) -> str:
        """
        Communicates with Gemini, handling text-based tool calls and thinking blocks.
        
        Args:
            prompt (str): The prompt with system instructions.
            tools (Dict[str, Any]): A dictionary mapping tool names to their callable functions.
        
        Returns:
            str: The final, user-facing text response from Gemini.
        """
        current_prompt = prompt
        
        # This loop continues until Gemini responds with a final, non-tool-calling answer.
        for _ in range(5):  # Safety break after 5 turns to prevent infinite loops
            try:
                response = self.model.generate_content(current_prompt)
                response_text = response.text

                # Parse the response for a tool call
                tool_call = self._parse_tool_call(response_text)
                
                if tool_call:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]

                    print(f"DEBUG: Gemini requested tool call: {tool_name} with args: {tool_args}")
                    
                    if tool_name in tools:
                        tool_result = tools[tool_name](**tool_args)
                    else:
                        tool_result = {"error": f"Unknown tool: {tool_name}"}

                    # Prepare the next prompt by appending the tool's result to the history
                    result_str = json.dumps(tool_result)
                    
                    # Update history to simulate the tool execution
                    current_prompt += f'''"role": "tool_call", "content": f"<call>{tool_name}({tool_args})</call>"'''
                    current_prompt += f'''"role": "tool_result", "content": {result_str}'''

                else:
                    # No tool call, this is the final response.
                    # Remove any thinking blocks before returning.
                    final_response = re.sub(r"<thinking>.*?</thinking>", "", response_text, flags=re.DOTALL).strip()
                    return final_response

            except Exception as e:
                print(f"Gemini service error during tool-call loop: {e}")
                return "Samahani, kuna tatizo. Tafadhali jaribu tena baadaye."
        
        return "Samahani, Rafiki ameshindwa kukamilisha ombi lako baada ya majaribio mengi."
