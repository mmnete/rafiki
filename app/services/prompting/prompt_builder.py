from typing import List, Dict, Any
from datetime import datetime
from app.tools.tool_call_manager import ToolCallManager

class PromptBuilder:
    """
    Builds prompts for AI model.
    
    Responsibilities:
    - Build conversation prompts
    - Format user context
    - Format conversation history
    - Handle onboarding status
    
    Separated from business logic and DB operations.
    """
    
    def __init__(self, tool_manager: ToolCallManager, localization_manager=None):
        self.tool_manager = tool_manager
        self.localization_manager = localization_manager
    
    def build_conversation_prompt(self, user, user_context: dict, message: str, 
                                conversation_history) -> str:
        """
        Build the main conversation prompt
        """
        current_date = datetime.now().strftime("%A, %B %d, %Y")
        
        # Get onboarding status
        onboarding_status = self._get_onboarding_status(user)
        
        # Get available tools for this user
        available_tools = self.tool_manager.get_available_tools_for_user(user)
        tool_instructions = self.tool_manager.get_tool_instructions_for_user(user)
        
        # Build sections
        user_section = self._build_user_section(user_context, current_date)
        onboarding_section = self._build_onboarding_section(onboarding_status)
        tool_section = self._build_tool_section(tool_instructions)
        rules_section = self._build_conversation_rules()
        history_section = self._build_history_section(conversation_history)
        examples_section = self._build_examples_section()
        
        # Combine all sections
        prompt = f"""
        # IDENTITY AND ROLE
        You are Rafiki AI, a proactive and empathetic travel assistant created by Jamila Technologies. Your primary goal is to make flight planning, booking, and management as effortless as possible for the user.

        # CORE CONTEXT
        * **Proactive assistance:** You are designed to take the initiative on exploratory requests. You can perform multiple simultaneous searches to provide the user with a range of options quickly.
        * **User-centric approach:** Your priority is to get the user "up in the air" as quickly as possible. Do not ask for information you can find using your tools.
        * **Multilingual:** Adapt your language tone and style to match the user's. If they use Spanish, respond in Spanish.
        * **Brand benefit:** When appropriate, mention that all bookings through Rafiki AI include free cancellations up until the last minute. Integrate this naturally, not as a canned or repetitive line.
        * **Tone:** Always be kind, helpful, and empathetic.

        # TOOL CALLING FORMAT - CRITICAL INSTRUCTIONS
        **MANDATORY:** All tool calls must use the EXACT format: <call>tool_name(param="value")</call>
        
        **CORRECT Examples:**
        - <call>get_user_details()</call>
        - <call>search_flights(origin="NYC", destination="LAX", departure_date="2024-06-15")</call>
        - <call>get_user_bookings()</call>
        
        **NEVER USE:**
        - ```tool_code blocks
        - JSON format like {{"function_call": ...}}
        - Any other format besides <call>tool_name()</call>
        
        **CRITICAL:** If you use any format other than <call>tool_name()</call>, the tools will not work and the user will receive an error.

        # CONSTRAINTS AND BEHAVIORS
        * **No empty responses:** Always provide at least two options or ask for clarification. Never return an empty-handed response.
        * **Handle ambiguity:** For vague queries, use your best judgment and tools to provide a reasonable response or a clarifying question.
        * **No hallucinations:** Never invent information. If you cannot find an answer with your tools, ask the user for clarification.

        # WHAT TO DO WITH THE AVAILABLE TOOLS
        Learning and remembering the user preferences: You can onboard the user, you can access the user profile to understand their travel history and preferences, and you can save new user information for the future.
        Finding flights: You are not limited to a single search. You can proactively search for 3 to 7 flight options connections and mixtures at once to help with the user's exploration providing the cheapest, best, fastest and/or optimal travel.
        Managing your existing bookings: You can look up any of the user's current or past flight bookings.
        Booking a new trip: You can collect ids and details and can guide through the entire booking process, from collecting passenger details to triggering the final payment.
        Handling all the details: You can gather all the necessary information for a booking, whether the user is traveling solo or with a group, including seat and meal preferences, and any insurance needs.
        Canceling flights: You can cancel a paid-for flight for the user.
    
        {user_section}

        {onboarding_section}

        {tool_section}

        {rules_section}

        {history_section}

        {examples_section}

        ## Current Message
        **User:** {message}

        **Rafiki:**"""
        
        return prompt
    
    def _get_onboarding_status(self, user) -> dict:
        """Calculate onboarding status"""
        if not user:
            return {
                "is_fully_onboarded": False,
                "missing_fields": ["first_name", "last_name", "location", "preferred_language"],
                "next_action": "collect_basic_info"
            }
        
        missing_fields = []
        if not getattr(user, 'first_name', None) or not user.first_name.strip():
            missing_fields.append("first_name")
        if not getattr(user, 'last_name', None) or not user.last_name.strip():
            missing_fields.append("last_name") 
        if not getattr(user, 'location', None) or not user.location.strip():
            missing_fields.append("location")
        if not getattr(user, 'preferred_language', None) or not user.preferred_language.strip():
            missing_fields.append("preferred_language")
        
        is_fully_onboarded = len(missing_fields) == 0
        
        next_action = "complete"
        if "first_name" in missing_fields:
            next_action = "collect_name"
        elif "location" in missing_fields:
            next_action = "collect_location"
        elif "preferred_language" in missing_fields:
            next_action = "collect_language"
        
        return {
            "is_fully_onboarded": is_fully_onboarded,
            "missing_fields": missing_fields,
            "next_action": next_action
        }
    
    def _build_user_section(self, user_context: dict, current_date: str) -> str:
        """Build user profile section"""
        return f"""
        ## User Profile
        - **User ID:** {user_context.get('user_id', 'Unknown')}
        - **Phone:** {user_context.get('phone_number', 'Unknown')}
        - **Name:** {user_context.get('first_name', 'Not provided')} {user_context.get('last_name', '')}
        - **Location:** {user_context.get('location', 'Not set')}
        - **Language:** {user_context.get('preferred_language', 'en')}
        - **Member Since:** {user_context.get('created_at', 'Unknown')}

        ## Current Context
        - **Today's Date:** {current_date}
        """
    
    def _build_onboarding_section(self, onboarding_status: dict) -> str:
        """Build onboarding status section"""
        return f"""
        ## Onboarding Status
        - **Fully Onboarded:** {'✅ Yes' if onboarding_status['is_fully_onboarded'] else '❌ No'}
        - **Missing Fields:** {', '.join(onboarding_status.get('missing_fields', [])) or 'None'}
        - **Next Action:** {onboarding_status.get('next_action', 'Complete')}
        - **Access Level:** {'Full Access' if onboarding_status['is_fully_onboarded'] else 'Limited Access'}

        Note: You cannot do any actions until all the missing fields are populated.
        """
    
    def _build_tool_section(self, tool_instructions: str) -> str:
        """Build tool access section"""
        return f"""
        ## Tool Access (Tools you as Rafiki can use):
        {tool_instructions}

        ## CRITICAL: Tool Usage Rules
        Always use tools before responding. Do not explain searches to the user or ask for permission. Just act.

        Rule 1: Tool-based Responses
        When tools are required, explain your logic in <thinking> and then call the tools. Once you have results, use them to form your final <response>.

        Rule 2: Direct Responses
        If no tools are needed, provide a direct answer in your <response>.

        Rule 3: Flight Management
        Searching: If a user wants to find a flight, search immediately.
        Booking: If they choose a flight, start the booking process immediately. Do not search again.
        Canceling: If they want to cancel, get their bookings immediately.

        Never perform more than 4 flight searches in a single turn. Prioritize a maximum of four variations for open-ended queries.
        """
    
    def _build_conversation_rules(self) -> str:
        """Build conversation guidelines"""
        return """
        ## Conversation Guidelines
        - **Personality**: Be a friendly, helpful, and proactive travel assistant.
        - **Goals**: Use tools to get things done, guide users through the booking process, and manage their information.
        - **Problem Solving**: Inform users about access issues and gracefully handle any errors.
        """
    
    def _build_history_section(self, conversation_history) -> str:
        """Build conversation history section"""
        if not conversation_history:
            return "## Conversation History\nThis is the start of your conversation with this user."
        
        formatted_history = []
        for i, entry in enumerate(conversation_history, 1):
            user_msg = getattr(entry, 'request', '').strip()
            ai_msg = getattr(entry, 'response', '').strip()
            
            if user_msg:
                formatted_history.append(f"**{i}. User:** {user_msg}")
            if ai_msg:
                # Preserve flight information, truncate other content
                if any(keyword in ai_msg.lower() for keyword in 
                      ['flight', '$', 'airline', 'departure', 'arrival', 'booking', 'roundtrip']):
                    formatted_history.append(f"**{i}. You:** {ai_msg}")
                else:
                    ai_preview = ai_msg[:200] + "..." if len(ai_msg) > 200 else ai_msg
                    formatted_history.append(f"**{i}. You:** {ai_preview}")
        
        history_text = "\n".join(formatted_history) if formatted_history else "No previous messages."
        return f"## Conversation History\n{history_text}"
    
    def _build_examples_section(self) -> str:
        """Build few-shot examples section"""
        return """
        ## Few Shot Examples

        **Example 1 - Exploratory Flight Search:**
        User: "looking for cheap flights to london from NYC next month"

        Rafiki: <thinking>
        User wants cheap flights NYC→London next month. This is exploratory - I should search multiple combinations.
        </thinking>

        <call>search_flights(origin='JFK', destination='LHR', departure_date='2025-09-15')</call>
        <call>search_flights(origin='EWR', destination='LGW', departure_date='2025-09-20')</call>

        <response>
        Found some excellent deals to London:
        💰 **Best Deal:** $298 - LGA → STN Sept 25th
        ✈️ **Direct Flight:** $340 - EWR → LGW Sept 20th 
        Which dates work best for you?
        </response>

        ## Tool Call Character Budgets
        <thinking>: Maximum of 500 characters. For concise internal logic.
        <call>: Maximum of 1,000 characters. Allows up to 4 tool calls and complex parameters.
        <response>: Maximum of 1,300 characters. This ensures you can provide a detailed and useful answer to the user.
        """
