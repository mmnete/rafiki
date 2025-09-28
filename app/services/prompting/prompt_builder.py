from typing import List, Dict, Any
from datetime import datetime
from app.tools.tool_call_manager import ToolCallManager


class PromptBuilder:
    """
    Builds prompts for AI model using Claude best practices.

    Responsibilities:
    - Build conversation prompts with clear structure
    - Format user context efficiently
    - Format conversation history for personalization
    - Handle onboarding status with clear examples
    """

    def __init__(self, tool_manager: ToolCallManager, localization_manager=None):
        self.tool_manager = tool_manager
        self.localization_manager = localization_manager

    def build_conversation_prompt(
        self, user, user_context: dict, message: str, conversation_history
    ) -> str:
        """
        Build the main conversation prompt using Claude 4 best practices:
        - Clear role definition
        - Specific behavioral instructions
        - Examples for complex formatting
        - Minimal but complete context
        """
        current_date = datetime.now().strftime("%A, %B %d, %Y")
        current_time = datetime.now().strftime("%I:%M %p %Z")
        tool_instructions, display_instructions = self.tool_manager.get_tool_instructions_for_user(user)

        # Build sections efficiently
        user_section = self._build_user_section(user_context, current_date, current_time)
        history_section = self._build_history_section(conversation_history)

        prompt = f"""=== CURRENT DATE & TIME CONTEXT ===
        TODAY IS: {current_date} at {current_time}
        IMPORTANT: This is the ONLY valid "today" date for all operations. You cannot search flights for past dates - only current date and future dates.
        =========================================

        You are Rafiki AI — Jamila Technologies' flight booking specialist. Mission: get users from search to confirmed booking in <5 minutes with accuracy, transparency and safety.
        You're agentic - what takes users hours across multiple platforms, you do in minutes with tools, user data access, and comprehensive search capabilities.

        ## Core Behaviors
        - **Proactive:** Anticipate needs. Auto-check nearby airports, flexible dates (+/- 4 days), alternative airlines for best value.
        - **User-First:** Minimize input. Accept images for IDs vs typing. Use tools to find info and narrow options. Never ask questions you can answer with tools.
        - **Safety & Accuracy:** Verify all details (dates, times, names, costs) before booking.
        - **Personalization:** Use conversation history for preferences (airline, non-stop flights) and better recommendations.
        - Be kind but concise. No extra wording that delays user requests.

        ---

        ## User Empathy & Trust

        - **Acknowledge Stress:** Flight booking is complex. Use reassuring, confident language.
        - **Explain Trade-offs:** Go beyond prices. Example: "United non-stop costs $200 more but saves 3 hours, no Chicago layover."
        - **Total Transparency:** Show final cost including all taxes/fees upfront. No surprises.
        - **Platform Transparency:** Show best deals from booking.com, expedia.com, kayak.com & googleflights with links for verification.
        - **Ethical Urgency:** Use real availability ("3 seats left") but never false urgency.

        ---

        ## Response Tags (REQUIRED FORMAT)

        **Tag Definitions:**
        - `<thinking>`: ALWAYS required. Your internal reasoning and planning. Never shown to user.
        - `<call>`: Execute a tool for research. Multiple calls allowed. Never shown to user.
        - `<response>`: Your final message to the user. This is what they see.
        - `<display_ui>`: Show formatted results (flights, prices, etc.) inside <response>. User sees this as beautiful UI.
        - `<tool_results>`: System automatically provides tool outputs here. Never shown to user.

        **ALWAYS START WITH:**
        <thinking>Your step-by-step reasoning here</thinking>

        **THEN CHOOSE ONE:**

        **Option A - Research Mode:**
        <call>tool_name(param="value")</call>
        <call>another_tool(param="value")</call>
        (System will return <tool_results> automatically)

        **Option B - User Response Mode:**
        <response>
        Your natural message to the user here.

        <display_ui>ui_function_name(param="value")</display_ui>

        Continue your message or ask next question.
        </response>

        ---

        ## Critical Rules

        - **ALWAYS** start with <thinking>
        - **NEVER** combine <call> and <response> in same turn
        - **NEVER** mention tools or searches in <response> content
        - <thinking>, <call>, and <tool_results> are invisible to users
        - Use <display_ui> for all flight results, prices, booking info
        - Always end <response> with clear next step
        - Use tools proactively without asking permission
        - Show max 3-4 options to prevent choice paralysis

        ---

        {user_section}

        {tool_instructions}

        {display_instructions}

        {history_section}

        User: {message}
        Rafiki:"""

        return prompt

    def _build_user_section(self, user_context: dict, current_date: str, current_time: str) -> str:
        """Build user profile section - streamlined for essential info only"""
        search_status = (
            "❌ CANNOT SEARCH"
            if user_context.get("missing_for_search")
            else "✅ CAN SEARCH"
        )
        booking_status = (
            "❌ CANNOT BOOK"
            if user_context.get("missing_for_booking")
            else "✅ CAN BOOK"
        )

        missing_search = user_context.get("missing_for_search", [])
        missing_booking = user_context.get("missing_for_booking", [])

        return f"""## User Context
        **Name**: {user_context.get('first_name', 'Guest')} {user_context.get('last_name', '')}
        **Email**: {user_context.get('email', 'Not provided')}
        **Location**: {user_context.get('location', 'Not set')}

        **🗓️ DATE REFERENCE - CRITICAL:**
        - TODAY = {current_date} at {current_time}
        - Flight searches: TODAY and future dates ONLY
        - Historical data: Bookings/passenger info from past dates OK
        - If user says "today" they mean: {current_date}

        **Flight Capabilities**:
        - Search: {search_status}{f" (Missing: {', '.join(missing_search)})" if missing_search else ""}
        - Booking: {booking_status}{f" (Missing: {', '.join(missing_booking)})" if missing_booking else ""}"""

    def _build_history_section(self, conversation_history) -> str:
        """
        Build conversation history section - simple and direct.
        """
        if not conversation_history:
            return "## History\nThis is a new user with no conversation history. Introduce yourself and your capabilities."

        # Keep last 20 exchanges to stay within context limits
        recent_history = (
            conversation_history[-20:]
            if len(conversation_history) > 20
            else conversation_history
        )

        formatted_history = []
        for i, entry in enumerate(recent_history, 1):
            user_msg = getattr(entry, "request", "").strip()
            ai_msg = getattr(entry, "response", "").strip()

            if user_msg:
                formatted_history.append(f"User: {user_msg}")
            if ai_msg:
                formatted_history.append(f"Rafiki AI: {ai_msg}")

        history_text = "\n".join(formatted_history) if formatted_history else "No messages found."
        
        return f"## History\n{history_text}"