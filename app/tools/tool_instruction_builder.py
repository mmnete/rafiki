from app.tools.tool_access_manager import ToolAccessManager
from app.tools.tool_registry import ToolRegistry, ToolDefinition


class ToolInstructionBuilder:
    """
    Builds tool instructions for prompts based on user access
    """
    
    def __init__(self, tool_registry: ToolRegistry, tool_access_manager: ToolAccessManager):
        self.tool_registry = tool_registry
        self.tool_access_manager = tool_access_manager
    
    def build_tool_instructions_for_user(self, user) -> str:
        """Build tool instructions based on user access level"""
        available_tool_names = self.tool_access_manager.get_available_tools_for_user(user)
        
        if not available_tool_names:
            return "No tools available for this user."
        
        # Get tool definitions
        available_tools = {
            name: self.tool_registry.get_tool_definition(name) 
            for name in available_tool_names
        }
        
        # Build instructions
        instructions = f"### **Available Tools ({len(available_tools)})**\n"
        instructions += f"You have access to: {', '.join([f'`{name}`' for name in available_tools.keys()])}.\n\n"
        
        # General guidelines
        instructions += self._build_general_guidelines()
        
        # Individual tool instructions
        for tool_name, tool_def in available_tools.items():
            if tool_def:  # Make sure tool definition exists
                instructions += self._build_individual_tool_instructions(tool_def)
        
        return instructions
    
    def _build_general_guidelines(self) -> str:
        """Build general tool usage guidelines"""
        return """
        **Tool Call Guidelines:**
        - Format: `<call>tool_name(param1='value1', param2='value2')</call>`
        - You can make multiple tool calls to satisfy user queries
        - Always validate required parameters
        - Use thinking blocks for reasoning
        - Users can update their information anytime

        **Access Control:**
        - Some tools require full onboarding completion
        - Booking tools only available to active users  
        - Special tools for trusted testers

        """
    
    def _build_individual_tool_instructions(self, tool_def: ToolDefinition) -> str:
        """Build instructions for individual tool"""
        instructions = f"#### **{tool_def.name.replace('_', ' ').title()}**\n"
        instructions += f"{tool_def.description}\n"
        instructions += f"**Access:** {tool_def.access_level.value}\n\n"
        instructions += f"{tool_def.instructions}\n\n"
        
        # Parameters
        if tool_def.parameters:
            instructions += "**Parameters:**\n"
            for param in tool_def.parameters:
                req_text = "required" if param.required else "optional"
                default_text = f" (default: {param.default})" if param.default is not None else ""
                instructions += f"- `{param.name}` ({param.param_type}, {req_text}): {param.description}{default_text}\n"
            instructions += "\n"
        
        # Examples
        if tool_def.examples:
            instructions += "**Examples:**\n"
            for example in tool_def.examples:
                instructions += f"```\n{example}\n```\n"
            instructions += "\n"
        
        return instructions