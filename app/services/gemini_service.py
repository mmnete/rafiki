import os
import re
from typing import Any, Dict, List, Optional, Tuple
from flask import json
import google.generativeai as genai
import ast


class GeminiService:
    # Regex to find tool calls like <call>tool_name(arg1='val', ...)</call>
    TOOL_CALL_REGEX = re.compile(r"<call>(\w+)\((.*?)\)</call>")
    # Regex to extract the final response from <response>...</response>
    RESPONSE_REGEX = re.compile(r"<response>(.*?)</response>", re.DOTALL)
    # Regex to remove thinking blocks
    THINKING_REGEX = re.compile(r"<thinking>.*?</thinking>", re.DOTALL)
    
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name="gemini-1.5-flash")  # You can also try "gemini-1.5-pro"

    def _parse_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        """Parses all tool calls from a Gemini text response."""
        matches = self.TOOL_CALL_REGEX.findall(text)
        calls = []

        for tool_name, args_str in matches:
            try:
                # Use a more robust parsing method without relying on a dictionary literal
                args = {}
                for arg_part in args_str.split(','):
                    key_value = arg_part.strip().split('=', 1)
                    if len(key_value) == 2:
                        key = key_value[0].strip()
                        value_str = key_value[1].strip()
                        # Use ast.literal_eval for type-safe parsing of the value
                        args[key] = ast.literal_eval(value_str)
                
                if args:
                    calls.append({"name": tool_name, "args": args})

            except (ValueError, SyntaxError) as e:
                print(f"Error parsing tool call arguments: {e}")
                continue

        return calls


    def ask_gemini(self, prompt: str, tools: Dict[str, Any]) -> Tuple[str, List[str]]:
        """
        Communicates with Gemini, handling text-based tool calls and thinking blocks.
        
        Args:
            prompt (str): The prompt with system instructions.
            tools (Dict[str, Any]): A dictionary mapping tool names to their callable functions.
        
        Returns:
            str: The final, user-facing text response from Gemini.
        """
        current_prompt = prompt
        model_responses = []
        
        for _ in range(3):
            try:
                response = self.model.generate_content(current_prompt)
                response_text = response.text
                
                model_responses += [response_text]
                tool_calls = self._parse_tool_calls(response_text)
                if tool_calls:
                    for tool_call in tool_calls:
                        tool_name = tool_call["name"]
                        tool_args = tool_call["args"]

                        print(f"DEBUG: Gemini requested tool call: {tool_name} with args: {tool_args}")
                        
                        if tool_name in tools:
                            tool_result = tools[tool_name](**tool_args)
                        else:
                            tool_result = {"error": f"Unknown tool: {tool_name}"}

                        result_str = json.dumps(tool_result)
                        print(f"DEBUG tool_result: {result_str}")
                        current_prompt += f"rafiki: tool_code\n{result_str}\n\nrafiki: "

                else:
                    # No tool call, this should be the final response.
                    # Check for a final response block and extract it.
                    response_match = self.RESPONSE_REGEX.search(response_text)
                    final_response = ""
                    # Remove <thinking> block from the entire response text first
                    cleaned_response = self.THINKING_REGEX.sub("", response_text).strip()

                    # Then extract final <response> content if it exists
                    response_match = self.RESPONSE_REGEX.search(cleaned_response)
                    if response_match:
                        final_response = response_match.group(1).strip()
                    else:
                        final_response = cleaned_response

                    model_responses += [response_text]
                    return final_response, model_responses

            except Exception as e:
                model_responses += ["error happened!"]
                print(f"Gemini service error during tool-call loop: {e}")
                return "Samahani, kumetokea hitilafu.", model_responses
        
        return "Samahani, Rafiki ameshindwa kukamilisha ombi lako baada ya majaribio mengi.", model_responses
        
