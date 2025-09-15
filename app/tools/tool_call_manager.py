# unified_toolcall_manager.py - Clean Tool Configuration with Display UI Support
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from app.services.api.flights.response_models import SimplifiedSearchResponse


@dataclass
class ToolParameter:
    name: str
    param_type: str
    required: bool
    description: str
    default: Any = None


class ToolRunningStyle(Enum):
    FORCED_ALWAYS = 1
    REQUESTED_BY_MODEL = 2


class ToolType(Enum):
    TOOL = "tool"           # Background research tools - use <call>
    DISPLAY_UI = "display"  # UI display functions - use <display_ui>


@dataclass
class ToolConfig:
    name: str
    description: str
    parameters: List[ToolParameter]
    instructions: str
    examples: List[str]
    execute_function: Callable
    tool_type: ToolType = ToolType.TOOL
    running_style: ToolRunningStyle = ToolRunningStyle.REQUESTED_BY_MODEL
    access_level: str = "all"
    extract_context: Optional[Callable[[Any, str], str]] = None


class ToolCallManager:
    """
    Tool configuration manager - handles tool definitions, display UI functions, and access control.
    Service implementations are delegated to respective service classes.
    """

    def __init__(self, services: Dict[str, Any]):
        self.services = services
        self.tools = {}
        self._validate_required_services()
        self._register_all_tools()

    def _validate_required_services(self):
        """Validate all required services are provided"""
        required_services = [
            "user_storage_service",
            "flight_service", 
            "flight_details_service",
            "booking_storage_service",
            "shared_storage_service",
        ]

        for service_name in required_services:
            if service_name not in self.services or self.services[service_name] is None:
                raise ValueError(f"Required service not provided: {service_name}")

    def _register_all_tools(self):
        """Register tools and display functions in logical order"""
        # Phase 1: User Management
        self.register_tool(self._update_user_profile_config())

        # Phase 2: Flight Search Tools
        self.register_tool(self._search_flights_config())

        # Phase 3: Flight Display UI Functions
        self.register_tool(self._display_main_flight_config())
        self.register_tool(self._display_nearby_flight_config()) 
        self.register_tool(self._display_comparison_sites_config())

        # Phase 4: Booking Tools
        self.register_tool(self._create_flight_booking_config())
        self.register_tool(self._manage_booking_passengers_config())
        self.register_tool(self._finalize_booking_config())

        # Phase 5: Booking Display UI Functions
        self.register_tool(self._display_booking_summary_config())
        self.register_tool(self._display_payment_link_config())

        # Phase 6: Booking Operations
        self.register_tool(self._get_booking_details_config())
        self.register_tool(self._cancel_booking_config())

    def register_tool(self, tool_config: ToolConfig):
        """Register a tool configuration"""
        self.tools[tool_config.name] = tool_config

    def get_available_tools_for_user(self, user) -> List[str]:
        """Get research tools available based on user onboarding status"""
        available_tools = []

        for tool_name, tool_config in self.tools.items():
            # Skip display UI functions and forced tools
            if (tool_config.tool_type == ToolType.DISPLAY_UI or 
                tool_config.running_style == ToolRunningStyle.FORCED_ALWAYS):
                continue

            if tool_config.access_level == "all":
                available_tools.append(tool_name)
            elif tool_config.access_level == "onboarded" and self._is_user_onboarded(user):
                available_tools.append(tool_name)
            elif tool_config.access_level == "active" and self._is_user_active(user):
                available_tools.append(tool_name)

        return available_tools

    def get_display_functions_for_user(self, user) -> List[str]:
        """Get display UI functions available to user"""
        display_functions = []
        
        for tool_name, tool_config in self.tools.items():
            if tool_config.tool_type == ToolType.DISPLAY_UI:
                if tool_config.access_level == "all":
                    display_functions.append(tool_name)
                elif tool_config.access_level == "onboarded" and self._is_user_onboarded(user):
                    display_functions.append(tool_name)
                elif tool_config.access_level == "active" and self._is_user_active(user):
                    display_functions.append(tool_name)
                    
        return display_functions

    def get_forced_tools(self) -> List[str]:
        """Get tools that run automatically"""
        return [tool_name for tool_name, tool_config in self.tools.items() 
                if tool_config.running_style == ToolRunningStyle.FORCED_ALWAYS]

    def _is_user_onboarded(self, user) -> bool:
        """Check if user has completed required onboarding fields"""
        if not user:
            return False
        required_fields = ["first_name", "last_name", "location", "preferred_language"]
        return all(getattr(user, field, None) for field in required_fields)

    def _is_user_active(self, user) -> bool:
        """Check if user can perform booking operations"""
        return self._is_user_onboarded(user) and user is not None

    def get_tool_instructions_for_user(self, user) -> tuple[str, str]:
        """Generate separate instructions for tools and display functions"""
        available_tools = self.get_available_tools_for_user(user)
        display_functions = self.get_display_functions_for_user(user)
        
        # Build tool instructions
        tool_instructions = self._build_tool_instructions(available_tools)
        
        # Build display function instructions  
        display_instructions = self._build_display_instructions(display_functions)
        
        return tool_instructions, display_instructions

    def _build_tool_instructions(self, available_tools: List[str]) -> str:
        """Build instructions for research tools"""
        if not available_tools:
            return "## Available Tools\nNo tools available. Complete user onboarding first."

        instructions = "## Available Tools (Research Only)\n"
        instructions += f"Tools: {', '.join([f'`{name}`' for name in available_tools])}\n\n"

        for tool_name in available_tools:
            tool_config = self.tools[tool_name]
            instructions += f"**{tool_name}**: {tool_config.description}\n"
            instructions += f"{tool_config.instructions}\n\n"

        return instructions

    def _build_display_instructions(self, display_functions: List[str]) -> str:
        """Build instructions for display UI functions with usage policies"""
        if not display_functions:
            return "## Display Functions\nNo display functions available."

        instructions = "## Display Functions (UI Elements)\n"
        instructions += f"Functions: {', '.join([f'`{name}`' for name in display_functions])}\n\n"
        instructions += "**Usage**: Always use <display_ui> tags to show results to users inside the <response> tag. Raw strings or words can be used to answer the user or ask or point to a <display_ui> tag.\n"
        instructions += "**Never**: Show raw data or manually format information.\n\n"

        # Add display policy rules
        instructions += "## Display Policy Rules\n\n"
        instructions += "**Flight Search Results Policy (CRITICAL):**\n"
        instructions += "Always display flight results in this exact order:\n"
        instructions += "1. **Exact Route Results**: Show 3-4 optimal flights for requested route using display_main_flight\n"
        instructions += "2. **Nearby Airport Alternatives**: Show 3-4 results from alternative airports using display_nearby_flight (if beneficial savings/options exist)\n"
        instructions += "3. **Platform Comparison**: ALWAYS show display_comparison_sites for the same routes - this is ESSENTIAL for user trust so they can verify Rafiki offers competitive pricing against other platforms\n"
        instructions += "Users need to see what other platforms are charging for identical routes to trust that Rafiki is providing fair value.\n\n"

        instructions += "**Booking Summary Policy:**\n"
        instructions += "- Use display_booking_summary ONLY at the very end of booking process or when user explicitly asks\n"
        instructions += "- Booking process = collecting user details, NOT displaying summaries\n"
        instructions += "- Reserve summary display for final confirmation before payment\n\n"

        instructions += "**Payment Display Policy:**\n"
        instructions += "- Use display_payment_link only after user confirms final booking summary\n"
        instructions += "- Always show total amount and expiration clearly\n\n"

        for func_name in display_functions:
            func_config = self.tools[func_name]
            instructions += f"**{func_name}**: {func_config.description}\n"
            
            if func_config.parameters:
                param_list = ", ".join([f"{p.name}='{p.description}'" for p in func_config.parameters])
                instructions += f"Usage: `<display_ui>{func_name}({param_list})</display_ui>`\n\n"

        return instructions

    def _get_user_phase(self, user) -> str:
        """Determine user's current phase"""
        if not self._is_user_onboarded(user):
            return "Onboarding"
        elif self._is_user_onboarded(user):
            return "Flight Search"
        else:
            return "Active User"

    def can_user_access_tool(self, user, tool_name: str) -> bool:
        """Check if user has access to specific tool"""
        return tool_name in self.get_available_tools_for_user(user)

    def get_tool_context(self, tool_name: str) -> Optional[Callable]:
        """Get context extraction function for a tool"""
        if tool_name not in self.tools:
            return None
        return getattr(self.tools[tool_name], "extract_context", None)

    def get_tool_function(self, tool_name: str) -> Optional[Callable]:
        """Get executable function for a tool"""
        if tool_name not in self.tools:
            return None
        return self.tools[tool_name].execute_function

    def execute_tool_for_user(self, user, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute tool with access validation"""
        if not self.can_user_access_tool(user, tool_name):
            return {"error": f"Access denied: {tool_name} requires higher access level"}

        tool_function = self.get_tool_function(tool_name)
        if not tool_function:
            return {"error": f"Tool not found: {tool_name}"}

        try:
            return tool_function(user.id, **kwargs)
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}

    # =============================================================================
    # USER MANAGEMENT TOOLS
    # =============================================================================

    def _update_user_profile_config(self) -> ToolConfig:
        return ToolConfig(
            name="update_user_profile",
            description="Update user profile information",
            tool_type=ToolType.TOOL,
            access_level="all",
            parameters=[
                ToolParameter("first_name", "string", False, "User's first name"),
                ToolParameter("last_name", "string", False, "User's last name"),
                ToolParameter("location", "string", False, "City and country"),
                ToolParameter("preferred_language", "string", False, "'en' or 'sw'"),
                ToolParameter("email", "string", False, "Contact email"),
                ToolParameter("date_of_birth", "string", False, "YYYY-MM-DD"),
            ],
            instructions="""Update user profile. Required for booking: first_name, last_name, email, date_of_birth.
            Collect all booking details upfront when user wants to book to minimize tool calls.""",
            examples=["<call>update_user_profile(first_name='John', last_name='Doe')</call>"],
            execute_function=lambda user_id, **kwargs: self.services["user_storage_service"].update_user(user_id, **kwargs),
            extract_context=self._extract_update_profile_context,
        )

    # =============================================================================
    # FLIGHT SEARCH TOOLS
    # =============================================================================

    def _search_flights_config(self) -> ToolConfig:
        return ToolConfig(
            name="search_flights",
            description="Search flight inventory for bookable options",
            tool_type=ToolType.TOOL,
            access_level="all",
            parameters=[
                ToolParameter("origin", "string", True, "3-letter airport code"),
                ToolParameter("destination", "string", True, "3-letter airport code"),
                ToolParameter("departure_date", "string", True, "YYYY-MM-DD"),
                ToolParameter("return_date", "string", False, "Return date for round trip"),
                ToolParameter("adults", "integer", False, "Adult passengers", 1),
                ToolParameter("children", "integer", False, "Children (2-11 years)", 0),
                ToolParameter("infants", "integer", False, "Infants (under 2)", 0),
            ],
            instructions="""INTELLIGENT SEARCH POLICY - Adapt search depth based on user certainty:

            **For Decisive Users (specific dates/airports):**
            Minimum 3-4 strategic searches:
            - Exact route requested
            - Primary nearby airport alternative
            - +/- 1 day flexibility if reasonable

            **For Uncertain/Flexible Users (vague dates, "sometime next week", "cheapest option"):**
            Minimum 10 comprehensive searches exploring:
            - Exact route + 2-3 date variations
            - Multiple origin airports (if user in metro area)
            - Multiple destination airports (if reasonable alternatives exist)
            - Weekday vs weekend departures
            - Different time periods (morning/evening if flexible dates)

            **Search Strategy Examples:**
            User: "SFO to NYC tomorrow" → 3-4 focused searches
            User: "get me to London sometime next week, flexible" → 10+ searches covering:
            - SFO-LHR multiple dates
            - OAK-LHR multiple dates  
            - SJC-LHR if viable
            - Different weekdays
            - Multiple London airports (LGW, STN)

            **Always:**
            - Cast wide net for flexible users to find hidden deals
            - Focus searches for decisive users to speed booking
            - Follow with display functions showing curated best options
            - Never show raw search data

            Your goal: Find the absolute best deals through intelligent, adaptive searching.""",
            examples=[
                "Decisive: <call>search_flights(origin='SFO', destination='LAX', departure_date='2025-09-21')</call>",
                "Flexible: <call>search_flights(origin='SFO', destination='LHR', departure_date='2025-09-22')</call>\n<call>search_flights(origin='OAK', destination='LHR', departure_date='2025-09-22')</call>\n<call>search_flights(origin='SFO', destination='LHR', departure_date='2025-09-24')</call>"
            ],
            execute_function=self._delegate_to_flight_service,
            extract_context=self._extract_flight_search_context,
        )

    # =============================================================================
    # FLIGHT DISPLAY UI FUNCTIONS
    # =============================================================================

    def _display_main_flight_config(self) -> ToolConfig:
        return ToolConfig(
            name="display_main_flight",
            description="Display primary flight option in formatted card",
            tool_type=ToolType.DISPLAY_UI,
            access_level="all",
            parameters=[
                ToolParameter("airline", "string", True, "Airline name"),
                ToolParameter("price", "string", True, "Price number only"),
                ToolParameter("origin_airport", "string", True, "Origin airport code"),
                ToolParameter("destination_airport", "string", True, "Destination airport code"),
                ToolParameter("departure_date", "string", True, "YYYY-MM-DD"),
                ToolParameter("departure_time", "string", True, "HH:MM"),
                ToolParameter("arrival_date", "string", True, "YYYY-MM-DD"),
                ToolParameter("arrival_time", "string", True, "HH:MM"),
                ToolParameter("duration", "string", True, "Flight duration"),
                ToolParameter("stops", "string", True, "Direct/1 stop/etc"),
                ToolParameter("connection_airport", "string", False, "Connection airport if stops > 0"),
                ToolParameter("connection_time", "string", False, "Layover duration if stops > 0"),
            ],
            instructions="""MANDATORY: Display exact route flight option in UI card.
            
            CRITICAL RULE: This function MUST be called 2-3 times for every flight search response.
            NEVER show flight search results without calling this function multiple times.
            This is not optional - it's required for product functionality and user experience.""",
            examples=[
                """
            <thinking>I have search results for SFO to LAX. I need to show the top exact route options first using display_main_flight. I'll select the 3 best options (optimized by price, time & airline reliability) from the search results and display them.</thinking>
            <response>
            Found excellent flights for your San Francisco to Los Angeles trip:
            
            🗺️ In your exact route:
            <display_ui>display_main_flight(airline='United Airlines', price='189', origin_airport='SFO', destination_airport='LAX', departure_date='2025-09-21', departure_time='10:30', arrival_date='2025-09-21', arrival_time='12:55', duration='2h 25m', stops='Direct')</display_ui>

            <display_ui>display_main_flight(airline='Alaska Airlines', price='204', origin_airport='SFO', destination_airport='LAX', departure_date='2025-09-21', departure_time='08:00', arrival_date='2025-09-21', arrival_time='10:25', duration='2h 25m', stops='Direct')</display_ui>

            <display_ui>display_main_flight(airline='Delta Airlines', price='219', origin_airport='SFO', destination_airport='LAX', departure_date='2025-09-21', departure_time='14:15', arrival_date='2025-09-21', arrival_time='16:40', duration='2h 25m', stops='Direct')</display_ui>

            [Nearvy airports shown here...]
            [Platform comparisons shown here...]
            </response>
                        """
            ],
            execute_function=self._render_flight_display,
        )

    def _display_nearby_flight_config(self) -> ToolConfig:
        return ToolConfig(
            name="display_nearby_flight", 
            description="Display alternative airport flight option",
            tool_type=ToolType.DISPLAY_UI,
            access_level="all",
            parameters=[
                ToolParameter("airline", "string", True, "Airline name"),
                ToolParameter("price", "string", True, "Price number only"),
                ToolParameter("origin_airport", "string", True, "Origin airport code"),
                ToolParameter("destination_airport", "string", True, "Destination airport code"),
                ToolParameter("departure_date", "string", True, "YYYY-MM-DD"),
                ToolParameter("departure_time", "string", True, "HH:MM"),
                ToolParameter("arrival_date", "string", True, "YYYY-MM-DD"),
                ToolParameter("arrival_time", "string", True, "HH:MM"),
                ToolParameter("duration", "string", True, "Flight duration"),
                ToolParameter("stops", "string", True, "Direct/1 stop/etc"),
                ToolParameter("connection_airport", "string", False, "Connection airport if stops > 0"),
                ToolParameter("connection_time", "string", False, "Layover duration if stops > 0"),
            ],
            instructions="""MANDATORY: Display nearby airport alternatives after main flights - display_main_flight.
            
            CRITICAL RULE: This function MUST be called 2-3 times after display_main_flight calls.
            NEVER skip nearby flights - users expect to see alternative airports with potential savings.""",
            examples=[
                """
            <thinking>After showing the main SFO flights, I need to show nearby airport alternatives. I'll show options from Oakland (OAK) and San Jose (SJC) that could save money or offer different times.</thinking>
            <response>
            [Main flights shown here...]

            🛩️ Alternative nearby airports:
            <display_ui>display_nearby_flight(airline='Southwest Airlines', price='149', origin_airport='OAK', destination_airport='LAX', departure_date='2025-09-21', departure_time='07:15', arrival_date='2025-09-21', arrival_time='09:45', duration='2h 30m', stops='Direct')</display_ui>

            <display_ui>display_nearby_flight(airline='JetBlue Airways', price='167', origin_airport='SJC', destination_airport='LAX', departure_date='2025-09-21', departure_time='11:20', arrival_date='2025-09-21', arrival_time='13:50', duration='2h 30m', stops='Direct')</display_ui>

            <display_ui>display_nearby_flight(airline='Frontier Airlines', price='134', origin_airport='OAK', destination_airport='LAX', departure_date='2025-09-21', departure_time='15:30', arrival_date='2025-09-21', arrival_time='18:05', duration='2h 35m', stops='Direct')</display_ui>

            [Platform comparisons shown here...]
            </response>
                """
            ],
            execute_function=self._render_flight_display,
        )

    def _display_comparison_sites_config(self) -> ToolConfig:
        return ToolConfig(
            name="display_comparison_sites",
            description="Show comparison links to other booking platforms",
            tool_type=ToolType.DISPLAY_UI,
            access_level="all",
            parameters=[
                ToolParameter("origin", "string", True, "Origin airport code"),
                ToolParameter("destination", "string", True, "Destination airport code"),
                ToolParameter("departure_date", "string", True, "YYYY-MM-DD"),
            ],
            instructions="""ABSOLUTELY MANDATORY: Show price comparison for transparency.
            
            CRITICAL RULE: This function MUST ALWAYS be called in the same response as display_main_flight & display_nearby_flight.
            IT IS IMPORTANT THAT WHEN PRESENTING A SEARCH RESPONSE TO THE USER THE ORDER IN YOUR SIGNLE RESPONSE IS display_main_flight, display_nearby_flight, then at the bottom display_comparison_sites.
            Users will not trust Rafiki without seeing competitive pricing.
            
            FAILURE TO INCLUDE THIS BREAKS THE USER SEARCH EXPERIENCE.""",
            examples=[
                """
            <thinking>After showing the main SFO flights, I need to show nearby airport alternatives. I'll show options from Oakland (OAK) and San Jose (SJC) that could save money or offer different times.</thinking>
            <response>
            [Main flights shown here...]
            [Nearvy airports shown here...]

            💰 Price comparisons with other platforms:
            <display_ui>display_comparison_sites(origin='JFK', destination='LHR', departure_date='2025-09-22')</display_ui>

            Ready to book one of these options, or would you like to explore different dates?
            </response>
                """
            ],
            execute_function=self._render_comparison_sites,
        )

    # =============================================================================
    # BOOKING TOOLS  
    # =============================================================================

    def _create_flight_booking_config(self) -> ToolConfig:
        return ToolConfig(
            name="create_flight_booking",
            description="Create draft booking from search results",
            tool_type=ToolType.TOOL,
            access_level="onboarded",
            parameters=[
                ToolParameter("search_id", "string", True, "Search ID from flight search"),
                ToolParameter("flight_offer_ids", "array", True, "Selected flight offer IDs"),
                ToolParameter("passenger_count", "integer", False, "Total travelers", 1),
            ],
            instructions="""Create booking draft. Use only after user selects flight and you have passenger count.
            Collect ALL passenger details conversationally before using this tool.""",
            examples=["<call>create_flight_booking(search_id='search_123', flight_offer_ids=['offer_456'], passenger_count=2)</call>"],
            execute_function=lambda user_id, **kwargs: self._delegate_to_booking_service(user_id, _tool_name="create_flight_booking", **kwargs),
            extract_context=self._extract_booking_creation_context,
        )

    def _manage_booking_passengers_config(self) -> ToolConfig:
        return ToolConfig(
            name="manage_booking_passengers",
            description="Add passenger details to booking",
            tool_type=ToolType.TOOL,
            access_level="active",
            parameters=[
                ToolParameter("booking_id", "string", True, "Booking identifier"),
                ToolParameter("action", "string", True, "'add', 'update', 'get'"),
                ToolParameter("first_name", "string", False, "Passenger first name"),
                ToolParameter("last_name", "string", False, "Passenger last name"),
                ToolParameter("date_of_birth", "string", False, "YYYY-MM-DD"),
                ToolParameter("nationality", "string", False, "2-letter country code"),
                ToolParameter("passport_number", "string", False, "Passport number"),
            ],
            instructions="""Add passenger details after create_flight_booking. Call multiple times for multiple passengers.
            Requires: first_name, last_name, date_of_birth, nationality, passport_number per passenger.""",
            examples=["<call>manage_booking_passengers(booking_id='BK123', action='add', first_name='John', last_name='Doe', date_of_birth='1990-01-01', nationality='US', passport_number='A12345678')</call>"],
            execute_function=lambda user_id, **kwargs: self._delegate_to_booking_service(user_id, _tool_name="manage_booking_passengers", **kwargs),
            extract_context=self._extract_passenger_management_context,
        )

    def _finalize_booking_config(self) -> ToolConfig:
        return ToolConfig(
            name="finalize_booking",
            description="Create airline reservation and get final pricing",
            tool_type=ToolType.TOOL,
            access_level="active",
            parameters=[
                ToolParameter("booking_id", "string", True, "Complete booking ID"),
            ],
            instructions="""Create PNR with airline after all passenger details added. Returns final price for user confirmation.""",
            examples=["<call>finalize_booking(booking_id='BK123')</call>"],
            execute_function=lambda user_id, **kwargs: self._delegate_to_booking_service(user_id, _tool_name="finalize_booking", **kwargs),
            extract_context=self._extract_finalize_booking_context,
        )

    # =============================================================================
    # BOOKING DISPLAY UI FUNCTIONS
    # =============================================================================

    def _display_booking_summary_config(self) -> ToolConfig:
        return ToolConfig(
            name="display_booking_summary",
            description="Show booking details with final pricing",
            tool_type=ToolType.DISPLAY_UI,
            access_level="active",
            parameters=[
                ToolParameter("booking_id", "string", True, "Booking ID"),
                ToolParameter("pnr", "string", False, "Airline confirmation code"),
                ToolParameter("total_price", "string", True, "Final price"),
                ToolParameter("passengers", "array", True, "Passenger list"),
            ],
            instructions="Display complete booking summary with PNR and final pricing",
            examples=["<display_ui>display_booking_summary(booking_id='BK123', pnr='ABC123', total_price='378', passengers=['John Doe', 'Jane Doe'])</display_ui>"],
            execute_function=self._render_booking_summary,
        )

    def _display_payment_link_config(self) -> ToolConfig:
        return ToolConfig(
            name="display_payment_link",
            description="Show secure payment link for booking",
            tool_type=ToolType.DISPLAY_UI,
            access_level="active",
            parameters=[
                ToolParameter("payment_url", "string", True, "Stripe payment URL"),
                ToolParameter("amount", "string", True, "Payment amount"),
                ToolParameter("expires_in", "string", False, "Link expiration", "24 hours"),
            ],
            instructions="Display secure payment link with amount and expiration",
            examples=["<display_ui>display_payment_link(payment_url='https://checkout.stripe.com/session_123', amount='378', expires_in='24 hours')</display_ui>"],
            execute_function=self._render_payment_link,
        )

    # =============================================================================
    # BOOKING MANAGEMENT TOOLS
    # =============================================================================

    def _get_booking_details_config(self) -> ToolConfig:
        return ToolConfig(
            name="get_booking_details",
            description="Retrieve booking information",
            tool_type=ToolType.TOOL,
            access_level="onboarded",
            parameters=[
                ToolParameter("booking_id", "string", False, "Specific booking ID"),
                ToolParameter("user_bookings", "boolean", False, "Get all user bookings", False),
            ],
            instructions="Get booking details or user's booking history.",
            examples=["<call>get_booking_details(booking_id='BK123')</call>"],
            execute_function=self._delegate_to_booking_service,
            extract_context=self._extract_booking_details_context,
        )

    def _cancel_booking_config(self) -> ToolConfig:
        return ToolConfig(
            name="cancel_booking",
            description="Cancel booking and process refunds",
            tool_type=ToolType.TOOL,
            access_level="onboarded",
            parameters=[
                ToolParameter("booking_id", "string", True, "Booking ID to cancel"),
                ToolParameter("reason", "string", False, "Cancellation reason"),
            ],
            instructions="Cancel booking with automatic refund processing.",
            examples=["<call>cancel_booking(booking_id='BK123', reason='Change of plans')</call>"],
            execute_function=self._delegate_to_booking_service,
            extract_context=self._extract_cancel_booking_context,
        )

    # =============================================================================
    # SERVICE DELEGATION
    # =============================================================================

    def _delegate_to_flight_service(self, user_id, **kwargs):
        try:
            summarized_results, raw_results = self.services["flight_service"].search_flights(**kwargs)
            search_id = self.services["shared_storage_service"].cache_search_results(user_id, kwargs, raw_results)
            summarized_results.search_params = kwargs
            summarized_results.search_id = search_id
            return summarized_results
        except Exception as e:
            return {"error": f"Flight search failed: {str(e)}"}

    def _delegate_to_booking_service(self, user_id, **kwargs):
        try:
            tool_name = kwargs.get("_tool_name", "unknown")
            if "action" not in kwargs:
                action_mapping = {
                    "create_flight_booking": "create",
                    "manage_booking_passengers": kwargs.get("action", "add"),
                    "finalize_booking": "finalize",
                    "get_booking_details": "get",
                    "cancel_booking": "cancel",
                }
                kwargs["action"] = action_mapping.get(tool_name, "create")

            return self.services["booking_storage_service"].handle_booking_operation(user_id, **kwargs)
        except Exception as e:
            return {"error": f"Booking operation failed: {str(e)}"}

    # =============================================================================
    # DISPLAY UI RENDERERS
    # =============================================================================

    def _render_flight_display(self, user_id, **kwargs):
        """Placeholder for flight display rendering"""
        return {"success": True, "display_type": "flight_card", "data": kwargs}

    def _render_comparison_sites(self, user_id, **kwargs):
        """Placeholder for comparison sites rendering"""
        return {"success": True, "display_type": "comparison_links", "data": kwargs}

    def _render_booking_summary(self, user_id, **kwargs):
        """Placeholder for booking summary rendering"""
        return {"success": True, "display_type": "booking_summary", "data": kwargs}

    def _render_payment_link(self, user_id, **kwargs):
        """Placeholder for payment link rendering"""
        return {"success": True, "display_type": "payment_link", "data": kwargs}

    # =============================================================================
    # CONTEXT EXTRACTION METHODS
    # =============================================================================

    def _extract_update_profile_context(self, result: Dict[str, Any], user_id: str) -> str:
        if isinstance(result, bool):
            return f"<call>update_user_profile(...)</call>\n{'Success' if result else 'Failed'}"
        if "error" in result:
            return f"<call>update_user_profile(...)</call>\nError: {result['error']}"
        return f"<call>update_user_profile(...)</call>\nProfile updated successfully"

    def _extract_flight_search_context(self, result: SimplifiedSearchResponse, user_id: str) -> str:
        search_params = getattr(result, "search_params", {})
        origin = search_params.get("origin", "") if search_params else ""
        destination = search_params.get("destination", "") if search_params else ""
        
        call_str = f"<call>search_flights(origin='{origin}', destination='{destination}')</call>"
        
        if hasattr(result, "error_message") and result.error_message:
            return f"{call_str}\nError: {result.error_message}"
            
        flights = getattr(result, "flights", [])
        search_id = getattr(result, "search_id", "")
        
        return f"{call_str}\nSUCCESS: Search ID {search_id}, Found {len(flights)} flights, Use display functions"

    def _extract_booking_creation_context(self, result: Dict[str, Any], user_id: str) -> str:
        return self.services["booking_storage_service"].extract_booking_operation_context(result, "create")

    def _extract_passenger_management_context(self, result: Dict[str, Any], user_id: str) -> str:
        action = result.get("action", "")
        return self.services["booking_storage_service"].extract_booking_operation_context(result, action)

    def _extract_finalize_booking_context(self, result: Dict[str, Any], user_id: str) -> str:
        return self.services["booking_storage_service"].extract_booking_operation_context(result, "finalize")

    def _extract_booking_details_context(self, result: Dict[str, Any], user_id: str) -> str:
        if "error" in result:
            return f"<call>get_booking_details(...)</call>\nError: {result['error']}"
        return f"<call>get_booking_details(...)</call>\nBooking details retrieved"

    def _extract_cancel_booking_context(self, result: Dict[str, Any], user_id: str) -> str:
        if "error" in result:
            return f"<call>cancel_booking(...)</call>\nError: {result['error']}"
        return f"<call>cancel_booking(...)</call>\nBooking cancelled successfully"
