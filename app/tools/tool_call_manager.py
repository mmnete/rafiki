# unified_toolcall_manager.py - Clean Tool Configuration Only
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from app.services.api.flights.response_models import ModelSearchResponse


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


@dataclass
class ToolConfig:
    name: str
    description: str
    parameters: List[ToolParameter]
    instructions: str
    examples: List[str]
    execute_function: Callable
    running_style: ToolRunningStyle = ToolRunningStyle.REQUESTED_BY_MODEL
    access_level: str = "all"
    extract_context: Optional[Callable[[Any, str], str]] = None


class ToolCallManager:
    """
    Tool configuration manager - handles tool definitions and access control only.
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
        """Register tools in progressive access order"""
        # Phase 1: Onboarding
        # self.register_tool(self._get_user_details_config())
        self.register_tool(self._update_user_profile_config())

        # Phase 2: Flight Search & Booking Creation
        self.register_tool(self._search_flights_config())
        self.register_tool(self._create_flight_booking_config())

        # Phase 3: Booking Management
        self.register_tool(self._manage_booking_passengers_config())
        self.register_tool(self._finalize_booking_config())

        # Phase 4: Booking Operations
        self.register_tool(self._get_booking_details_config())
        self.register_tool(self._cancel_booking_config())

    def register_tool(self, tool_config: ToolConfig):
        """Register a tool configuration"""
        self.tools[tool_config.name] = tool_config

    def get_available_tools_for_user(self, user) -> List[str]:
        """Get tools available based on user onboarding status"""
        available_tools = []

        for tool_name, tool_config in self.tools.items():
            # Forced toolcalls will always be run immediately when the request comes in.
            if tool_config.running_style == ToolRunningStyle.FORCED_ALWAYS:
                continue

            if tool_config.access_level == "all":
                available_tools.append(tool_name)
            elif tool_config.access_level == "onboarded" and self._is_user_onboarded(
                user
            ):
                available_tools.append(tool_name)
            elif tool_config.access_level == "active" and self._is_user_active(user):
                available_tools.append(tool_name)

        return available_tools

    def get_forced_tools(self) -> List[str]:
        """Get tools available based on user onboarding status"""
        available_tools = []

        for tool_name, tool_config in self.tools.items():
            # Forced toolcalls will always be run immediately when the request comes in.
            if tool_config.running_style == ToolRunningStyle.FORCED_ALWAYS:
                available_tools.append(tool_name)

        return available_tools

    def _is_user_onboarded(self, user) -> bool:
        """Check if user has completed required onboarding fields"""
        if not user:
            return False
        required_fields = ["first_name", "last_name", "location", "preferred_language"]
        return all(getattr(user, field, None) for field in required_fields)

    def _is_user_active(self, user) -> bool:
        """Check if user can perform booking operations"""
        return self._is_user_onboarded(user) and user is not None

    def get_tool_instructions_for_user(self, user) -> str:
        """Generate contextual instructions based on user's current phase"""
        available_tool_names = self.get_available_tools_for_user(user)
        available_tools = {name: self.tools[name] for name in available_tool_names}

        if not available_tools:
            return "No tools available. Please complete user onboarding first."

        user_phase = self._get_user_phase(user)
        instructions = f"### Available Tools - {user_phase} Phase\n"
        instructions += (
            f"Tools: {', '.join([f'`{name}`' for name in available_tools.keys()])}\n\n"
        )

        # Phase-specific guidance
        phase_guidance = {
            "Onboarding": "Focus on collecting user information before accessing flight tools.",
            "Flight Search": "User can now search flights and create bookings.",
            "Active User": "Full access to booking management and operations.",
        }
        instructions += f"**Phase Guidance:** {phase_guidance.get(user_phase)}\n\n"

        # Tool details
        for tool_name, tool_config in available_tools.items():
            instructions += f"#### {tool_name}\n{tool_config.description}\n"
            instructions += f"{tool_config.instructions}\n\n"

            if tool_config.parameters:
                instructions += "**Parameters:**\n"
                for param in tool_config.parameters:
                    req_text = "required" if param.required else "optional"
                    default_text = (
                        f" (default: {param.default})"
                        if param.default is not None
                        else ""
                    )
                    instructions += f"- `{param.name}` ({param.param_type}, {req_text}): {param.description}{default_text}\n"
                instructions += "\n"

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
        """Get executable function for a tool with attached config for context extraction"""
        if tool_name not in self.tools:
            return None

        tool_config = self.tools[tool_name]

        # Safely check if extract_context exists and is not None
        extract_context = getattr(tool_config, "extract_context", None)
        if extract_context is None:
            return None

        return extract_context

    def get_tool_function(self, tool_name: str) -> Optional[Callable]:
        """Get executable function for a tool with attached config for context extraction"""
        if tool_name not in self.tools:
            return None

        tool_config = self.tools[tool_name]
        tool_function = tool_config.execute_function

        return tool_function

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
    # TOOL CONFIGURATIONS - Interface definitions only, no business logic
    # =============================================================================

    def _get_user_details_config(self) -> ToolConfig:
        return ToolConfig(
            name="get_user_details",
            description="Retrieve user profile and onboarding status",
            access_level="all",
            parameters=[],
            instructions="""Check current user information and onboarding progress.

            **Required for onboarding completion:**
            - first_name, last_name: Required for flight bookings
            - location: Improves flight search recommendations  
            - preferred_language: 'en' or 'sw' for communication

            **Use this tool to:**
            - Start every conversation to assess user status
            - Determine which information needs collection
            - Guide user through onboarding process""",
            examples=["<call>get_user_details()</call>"],
            running_style=ToolRunningStyle.FORCED_ALWAYS,
            execute_function=self._get_user_details_wrapper,
            extract_context=self._extract_user_details_context,
        )

    def _get_user_details_wrapper(self, user_id: int) -> Dict[str, Any]:
        """Wrapper to convert User object to JSON-serializable dict"""
        user = self.services["user_storage_service"].get_or_create_user(user_id)

        if not user:
            return {"error": "Failed to retrieve user information"}

        return {
            "success": True,
            "user_id": user.id,
            "phone_number": user.phone_number,
            "first_name": user.first_name,
            "middle_name": user.middle_name,
            "last_name": user.last_name,
            "email": user.email,
            "date_of_birth": (
                user.date_of_birth.isoformat() if user.date_of_birth else None
            ),
            "gender": user.gender,
            "location": user.location,
            "preferred_language": user.preferred_language,
            "timezone": user.timezone,
            "status": user.status,
            "onboarding_completed_at": (
                user.onboarding_completed_at.isoformat()
                if user.onboarding_completed_at
                else None
            ),
            "is_trusted_tester": user.is_trusted_tester,
            "is_active": user.is_active,
            "travel_preferences": user.travel_preferences,
            "notification_preferences": user.notification_preferences,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "last_login_at": (
                user.last_login_at.isoformat() if user.last_login_at else None
            ),
        }

    def _update_user_profile_config(self) -> ToolConfig:
        return ToolConfig(
            name="update_user_profile",
            description="Update user profile information",
            access_level="all",
            parameters=[
                ToolParameter("first_name", "string", False, "User's first name"),
                ToolParameter("last_name", "string", False, "User's last name"),
                ToolParameter(
                    "location",
                    "string",
                    False,
                    "City and country (e.g., 'New York, USA')",
                ),
                ToolParameter(
                    "preferred_language",
                    "string",
                    False,
                    "'en' for English, 'sw' for Swahili",
                ),
                ToolParameter("email", "string", False, "Contact email"),
                ToolParameter(
                    "date_of_birth", "string", False, "Date of birth (YYYY-MM-DD)"
                ),
            ],
            instructions="""Update user profile fields during onboarding or anytime.
            
            By default every user has an account with us based on their phone number. But we never really fully register them if all they are doing is searching.
            The moment they want to book a flight is when we need to first get all their details. We need their first name, last name, date of birth and email - this is only a must when 
            the user is trying to book a flight. Be sure to ask for all details up front immedatialy when they want to book this reduces the number of toolcalls you make.

            **Usage patterns:**
            - Single field: update_user_profile(first_name='John')
            - Multiple fields: update_user_profile(first_name='John', location='NYC, USA')
            - Always confirm information with user before updating
            
            **Critical:**
            - Once you have successfully updated the user profile and the user was trying to do something prior like tried to initiate a booking do not respond with a promise of an action rather start asking the user for their details to start doing the booking.
            - NOTE: The user details & booking details are compeletly two different things! Think of user details as the user of the platform, we can use their info as contact info for the booking but the booking info is the details we send to airlines we need to manually collect those separately! Even if the user is booking for themselves we need to fill those in separately, if they are alone we may not need to ask them for the duplicate details but normally booking details need to be asked and confirmed for all passengers.
            """,
            examples=[
                "<call>update_user_profile(first_name='Sarah', last_name='Johnson')</call>",
                "<call>update_user_profile(location='London, UK', preferred_language='en')</call>",
            ],
            execute_function=lambda user_id, **kwargs: self.services[
                "user_storage_service"
            ].update_user(user_id, **kwargs),
            extract_context=self._extract_update_profile_context,
        )

    def _search_flights_config(self) -> ToolConfig:
        return ToolConfig(
            name="search_flights",
            description="Search flight inventory using backend flight APIs to find bookable options",
            access_level="all",
            parameters=[
                ToolParameter(
                    "origin", "string", True, "3-letter airport code (SFO, JFK)"
                ),
                ToolParameter(
                    "destination", "string", True, "3-letter airport code (LAX, LHR)"
                ),
                ToolParameter(
                    "departure_date", "string", True, "Departure date (YYYY-MM-DD)"
                ),
                ToolParameter(
                    "return_date", "string", False, "Return date for round trip"
                ),
                ToolParameter("adults", "integer", False, "Adult passengers", 1),
                ToolParameter("children", "integer", False, "Children (2-11 years)", 0),
                ToolParameter("infants", "integer", False, "Infants (under 2)", 0),
                ToolParameter(
                    "travel_class", "string", False, "Travel class", "ECONOMY"
                ),
            ],
            instructions="""**TOOL PURPOSE:** 
            This tool searches flight inventory through backend APIs to find available flights with real prices and booking identifiers. The goal is to get users booked as quickly as possible by presenting the best options clearly.

            **SEARCH STRATEGY - Adaptive Based on User Certainty:**
            
            **For Decisive Users (know what they want):**
            - 4-5 targeted searches maximum
            - Focus on exact request + nearby airports 
            - Present top options quickly to facilitate booking

            **For Uncertain Users (vague dates/locations):**
            - Cast wider net with 10-20 searches
            - Vary dates around target period
            - Include multiple airports and routing options
            - Still curate down to best options for presentation

            **Search combinations to consider:**
            - Exact route requested
            - Nearby airports if geographically reasonable
            - Alternative dates (±2-3 days for flexible timing)
            - Direct vs connecting options for long routes

            **CRITICAL - Always curate results:**
            After performing searches, analyze all results and select only the standout options:
            - Top 3 exact route flights (best price/time/reliability combination)
            - Top 3 nearby airport alternatives (if searched)
            - Do not overwhelm - quality over quantity

            **MANDATORY RESPONSE FORMAT - Use display functions:**
            
            After tool calls complete, you MUST use these display functions with properly formatted data:

            1. **Main flights display:**
            <display_main_flights search_id="[actual_search_id]" route="[ORIGIN] to [DESTINATION]" date="[YYYY-MM-DD]" return_date="[YYYY-MM-DD or empty]" flights="[formatted_flight_data]" />

            2. **Nearby flights display (if applicable):**
            <display_nearby_flights route="[ORIGIN] to [DESTINATION]" date="[YYYY-MM-DD]" return_date="[YYYY-MM-DD or empty]" flights="[formatted_flight_data]" />

            3. **Price comparison (always required):**
            <display_comparison_sites origin="[ORIGIN_CODE]" destination="[DESTINATION_CODE]" date="[YYYY-MM-DD]" return_date="[YYYY-MM-DD or empty]" />

            **CRITICAL - FLIGHT DATA CONVERSION:**
            
            You must convert the JSON tool response into this exact pipe-delimited format:
            flights="FLIGHT_ID:AIRLINE:PRICE:DEPARTURE:ARRIVAL:DURATION:STOPS|FLIGHT_ID:AIRLINE:PRICE:DEPARTURE:ARRIVAL:DURATION:STOPS"

            **Example Data Conversion:**
            
            Tool returns JSON:
            {
            "id": "amadeus_1", 
            "price": "$203", 
            "airline": "FRONTIER AIRLINES", 
            "departure": "05:45", 
            "arrival": "13:16", 
            "duration": "5h 31m", 
            "stops": "Direct"
            }

            Convert to:
            flights="amadeus_1:FRONTIER AIRLINES:$203:05:45:13:16:5h 31m:Direct"

            Multiple flights separated by | pipe character:
            flights="amadeus_1:FRONTIER AIRLINES:$203:05:45:13:16:5h 31m:Direct|amadeus_3:ALASKA AIRLINES:$264:08:00:17:58:7h 58m:Direct"

            **MANDATORY RESPONSE TEMPLATE:**

            Great news! I've found excellent options for your [ORIGIN] to [DESTINATION] trip [TIMEFRAME]

            **Your exact route ✈️:**
            <display_main_flights search_id="search_7401eab06742" route="SFO to SAT" date="2025-09-15" return_date="" flights="amadeus_1:FRONTIER AIRLINES:$203:05:45:13:16:5h 31m:Direct|amadeus_3:ALASKA AIRLINES:$264:08:00:17:58:7h 58m:Direct|amadeus_9:UNITED AIRLINES:$528:15:00:22:33:5h 33m:Direct" />

            **Some nearby airports, I strongly recommend these 🛫📍:**
            <display_nearby_flights route="OAK to SAT" date="2025-09-15" return_date="" flights="amadeus_1:ALASKA AIRLINES:$264:06:30:17:58:9h 28m:Direct" />

            **Here are the best rates other platforms will give you 💸📊 (Rafiki is clearly better):**
            <display_comparison_sites origin="SFO" destination="SAT" date="2025-09-15" return_date="" />

            Which option works best for your plans?

            **SUCCESS CRITERIA:**
            - User can see clearly formatted flight options
            - All display functions render properly 
            - User selects a flight and wants to proceed with booking
            - Data flows correctly from tool response to display functions

            **CRITICAL RULES:**
            1. ALWAYS convert JSON data to pipe-delimited format
            2. Use actual search_id from tool response
            3. Use exact route format: "ORIGIN to DESTINATION"
            4. Include all three display function types
            5. Curate to best 3 options per display function
            """,
            examples=[
                "user: flights from sfo to la tomorrow\nrafiki: <call>search_flights(origin='SFO', destination='LAX', departure_date='2025-09-21')</call>\n<call>search_flights(origin='OAK', destination='LAX', departure_date='2025-09-21')</call>",
                "user: need to get to london sometime next week, flexible on dates\nrafiki: <call>search_flights(origin='SFO', destination='LHR', departure_date='2025-09-22')</call>\n<call>search_flights(origin='SFO', destination='LHR', departure_date='2025-09-24')</call>\n<call>search_flights(origin='OAK', destination='LHR', departure_date='2025-09-22')</call>",
            ],
            execute_function=self._delegate_to_flight_service,
            extract_context=self._extract_flight_search_context,
        )
    
    def _create_flight_booking_config(self) -> ToolConfig:
        return ToolConfig(
            name="create_flight_booking",
            description="Create draft booking from search results",
            access_level="onboarded",
            parameters=[
                ToolParameter(
                    "search_id", "string", True, "Search ID from flight search"
                ),
                ToolParameter(
                    "flight_offer_ids", "array", True, "Selected flight offer IDs"
                ),
                ToolParameter(
                    "passenger_count", "integer", False, "Total number of travelers", 1
                ),
                ToolParameter(
                    "booking_type",
                    "string",
                    False,
                    "individual/family/group/corporate",
                    "individual",
                ),
            ],
            instructions="""Create draft booking. Next step: collect ALL passenger details with manage_booking_passengers.""",
            examples=[
                "<call>create_flight_booking(search_id='search_123', flight_offer_ids=['offer_456'], passenger_count=2, booking_type='family')</call>"
            ],
            execute_function=lambda user_id, **kwargs: self._delegate_to_booking_service(
                user_id, _tool_name="create_flight_booking", **kwargs
            ),
            extract_context=self._extract_booking_creation_context,
        )

    def _manage_booking_passengers_config(self) -> ToolConfig:
        return ToolConfig(
            name="manage_booking_passengers",
            description="Add passengers and collect complete travel details",
            access_level="active",
            parameters=[
                ToolParameter("booking_id", "string", True, "Booking identifier"),
                ToolParameter("action", "string", True, "'add', 'update', 'get'"),
                ToolParameter(
                    "passenger_id", "string", False, "Required for update action"
                ),
                ToolParameter("first_name", "string", False, "Passenger first name"),
                ToolParameter("last_name", "string", False, "Passenger last name"),
                ToolParameter(
                    "date_of_birth", "string", False, "Date of birth (YYYY-MM-DD)"
                ),
                ToolParameter("gender", "string", False, "male/female/other"),
                ToolParameter("passport_number", "string", False, "Passport number"),
                ToolParameter(
                    "nationality", "string", False, "Nationality (2-letter code)"
                ),
                ToolParameter("seat_preference", "string", False, "window/aisle/any"),
                ToolParameter(
                    "meal_preference",
                    "string",
                    False,
                    "vegetarian/vegan/kosher/halal/standard",
                ),
                ToolParameter(
                    "emergency_contact_name", "string", False, "Emergency contact name"
                ),
                ToolParameter(
                    "emergency_contact_phone",
                    "string",
                    False,
                    "Emergency contact phone",
                ),
                ToolParameter(
                    "emergency_contact_relationship",
                    "string",
                    False,
                    "Relationship to passenger",
                ),
            ],
            instructions="""Collect ALL required details before allowing finalization:

            **Required for each passenger:**
            - Personal: first_name, last_name, date_of_birth, gender, nationality
            - Travel: passport_number, seat_preference, meal_preference
            
            **Required for booking:**
            - Emergency contact: name, phone, relationship
            
            **DO NOT proceed to finalize_booking until ALL details collected.**
            Use action='get' to check completion status.""",
            examples=[
                "<call>manage_booking_passengers(booking_id='BK123', action='add', first_name='John', last_name='Doe', date_of_birth='1990-01-01', nationality='US', passport_number='A12345678', seat_preference='window', meal_preference='vegetarian')</call>",
                "<call>manage_booking_passengers(booking_id='BK123', action='get')</call>",
            ],
            execute_function=lambda user_id, **kwargs: self._delegate_to_booking_service(
                user_id, _tool_name="manage_booking_passengers", **kwargs
            ),
            extract_context=self._extract_passenger_management_context,
        )

    def _finalize_booking_config(self) -> ToolConfig:
        return ToolConfig(
            name="finalize_booking",
            description="Create airline reservation and get final pricing",
            access_level="active",
            parameters=[
                ToolParameter(
                    "booking_id", "string", True, "Booking with complete details"
                ),
            ],
            instructions="""Creates PNR with airline and returns final price for user confirmation.
            
            **Only use when:**
            - ALL passenger details complete (names, DOB, passport, seat/meal prefs)
            - Emergency contact provided
            - User wants to proceed with booking
            
            **This will:**
            - Create actual airline reservation (PNR)
            - Show final confirmed price
            - Ask user to confirm before payment collection""",
            examples=["<call>finalize_booking(booking_id='BK123')</call>"],
            execute_function=lambda user_id, **kwargs: self._delegate_to_booking_service(
                user_id, _tool_name="finalize_booking", **kwargs
            ),
            extract_context=self._extract_finalize_booking_context,
        )

    def _generate_payment_link_config(self) -> ToolConfig:
        return ToolConfig(
            name="generate_payment_link",
            description="Generate payment URL after user confirms final price",
            access_level="active",
            parameters=[
                ToolParameter("booking_id", "string", True, "Finalized booking ID"),
            ],
            instructions="""Generate Stripe payment link for confirmed booking.
            
            **Only use after:**
            - finalize_booking completed successfully
            - User explicitly confirms they want to pay
            
            Returns secure payment URL for user to complete purchase.""",
            examples=["<call>generate_payment_link(booking_id='BK123')</call>"],
            execute_function=lambda user_id, **kwargs: self._generate_payment_link(
                user_id, **kwargs
            ),
            extract_context=self._extract_payment_link_context,
        )

    def _get_booking_details_config(self) -> ToolConfig:
        return ToolConfig(
            name="get_booking_details",
            description="Retrieve booking information or user's booking history",
            access_level="onboarded",
            parameters=[
                ToolParameter("booking_id", "string", False, "Specific booking ID"),
                ToolParameter(
                    "user_bookings", "boolean", False, "Get all user bookings", False
                ),
            ],
            instructions="""Get booking information for status checks and management.

            **Usage:**
            - Specific booking: Provide booking_id
            - All bookings: Set user_bookings=true
            - Returns comprehensive details including passengers, flights, payment status""",
            examples=[
                "<call>get_booking_details(booking_id='BK123')</call>",
                "<call>get_booking_details(user_bookings=true)</call>",
            ],
            execute_function=self._delegate_to_booking_service,
            extract_context=self._extract_booking_details_context,
        )

    def _cancel_booking_config(self) -> ToolConfig:
        return ToolConfig(
            name="cancel_booking",
            description="Cancel booking and process refunds automatically",
            access_level="onboarded",
            parameters=[
                ToolParameter("booking_id", "string", True, "Booking ID to cancel"),
                ToolParameter("reason", "string", False, "Cancellation reason"),
            ],
            instructions="""Cancel booking with automatic refund processing.

            **Cancellation process:**
            1. Cancel PNR with airline (if exists)
            2. Process Stripe refund (if payment completed)  
            3. Update booking status to cancelled

            **Note:** Refund policies depend on airline fare rules and timing.""",
            examples=[
                "<call>cancel_booking(booking_id='BK123', reason='Change of plans')</call>"
            ],
            execute_function=self._delegate_to_booking_service,
            extract_context=self._extract_cancel_booking_context,
        )

    # =============================================================================
    # SERVICE DELEGATION - Simple pass-through to appropriate services
    # =============================================================================

    def _delegate_to_flight_service(self, user_id, **kwargs):
        try:
            # search_flights returns a tuple: (summarized_results, raw_results)
            summarized_results, raw_results = self.services[
                "flight_service"
            ].search_flights(**kwargs)

            # Cache the full raw results for booking purposes
            search_id = self.services["shared_storage_service"].cache_search_results(
                user_id, kwargs, raw_results
            )

            summarized_results.search_params = kwargs
            summarized_results.search_id = search_id

            # Return ONLY the summarized results to the model (not raw_results!)
            return summarized_results

        except Exception as e:
            return {"error": f"Flight search failed: {str(e)}"}

    def _delegate_to_booking_service(self, user_id, **kwargs):
        """Delegate to booking service with enhanced action handling"""
        print(f"Booking service delegation called with user_id: {user_id}")
        print(f"Input kwargs: {kwargs}")

        try:
            # Handle intelligent booking type determination for update_booking action
            if (
                kwargs.get("action") == "update_booking"
                and "passenger_count" in kwargs
                and "booking_type" not in kwargs
            ):
                passenger_count = kwargs.get("passenger_count", 1)
                if passenger_count == 1:
                    kwargs["booking_type"] = "individual"
                elif 2 <= passenger_count <= 6:
                    kwargs["booking_type"] = "family"
                elif passenger_count >= 7:
                    kwargs["booking_type"] = "group"

                print(
                    f"Auto-determined booking_type: {kwargs['booking_type']} for {passenger_count} passengers"
                )

            # Map the tool calls to the appropriate actions
            tool_name = kwargs.get("_tool_name", "unknown")

            # Determine action based on the tool call or explicit action
            if "action" not in kwargs:
                action_mapping = {
                    "create_flight_booking": "create",
                    "manage_booking_passengers": kwargs.get("action", "add"),
                    "finalize_booking": "finalize",
                    "get_booking_details": "get",
                    "cancel_booking": "cancel",
                }

                # Try to determine action from context
                if "search_id" in kwargs and "flight_offer_ids" in kwargs:
                    action = "create"
                elif "booking_id" in kwargs and "first_name" in kwargs:
                    action = "add"
                elif "booking_id" in kwargs and "passenger_id" in kwargs:
                    action = "update"
                elif "booking_id" in kwargs and kwargs.get("user_bookings"):
                    action = "get"
                elif "booking_id" in kwargs and "reason" in kwargs:
                    action = "cancel"
                elif "booking_id" in kwargs and (
                    "passenger_count" in kwargs or "booking_type" in kwargs
                ):
                    action = "update_booking"
                elif "booking_id" in kwargs and tool_name == "finalize_booking":
                    action = "finalize"
                else:
                    action = action_mapping.get(tool_name, "create")

                kwargs["action"] = action

            print(f"Determined action: {kwargs['action']}")
            print(f"Final kwargs being passed: {kwargs}")

            # Call the booking service
            result = self.services["booking_storage_service"].handle_booking_operation(
                user_id, **kwargs
            )

            print(f"Booking service result: {result}")
            return result

        except KeyError as ke:
            error_msg = f"Missing required service or parameter: {str(ke)}"
            print(f"KeyError in booking delegation: {error_msg}")
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Booking operation failed: {str(e)}"
            print(f"Exception in booking delegation: {error_msg}")
            import traceback

            traceback.print_exc()
            return {"error": error_msg}

    # =============================================================================
    # Functions that returnt he context of each search
    # =============================================================================

    # Add these methods to your ToolCallManager class

    def _extract_user_details_context(
        self, result: Dict[str, Any], user_id: str
    ) -> str:
        """Extract context for user details check with clear capability status"""
        if "error" in result:
            return f"<call>get_user_details()</call>\nError: {result['error']}"

        name = f"{result.get('first_name', '')} {result.get('last_name', '')}".strip()
        location = result.get("location", "")
        email = result.get("email", "")

        context = f"<call>get_user_details()</call>\n"
        context += f"User Profile: {name or '[No name provided]'}"
        if location:
            context += f" - {location}"
        if email:
            context += f" - {email}"
        context += "\n\n"

        # Clear capability status
        missing_for_search = result.get("needed_for_searching", [])
        missing_for_booking = result.get("needed_for_booking", [])

        if missing_for_search:
            context += "CAPABILITY STATUS: CANNOT SEARCH FLIGHTS\n"
            context += (
                f"Reason: Missing required field - {', '.join(missing_for_search)}\n"
            )
            context += "Action Required: Must collect phone number before user can search for any flights\n"
        elif missing_for_booking:
            context += "CAPABILITY STATUS: CAN SEARCH FLIGHTS ONLY\n"
            context += f"Missing for booking: {', '.join(missing_for_booking)}\n"
            context += "Action Required: User can browse and search flights, but cannot complete bookings until missing information is provided\n"
            context += (
                "Prompt user to provide missing details if they want to book flights\n"
            )
        else:
            context += "CAPABILITY STATUS: FULL ACCESS\n"
            context += "User can search flights AND complete bookings - all required information is available\n"

        return context

    def _extract_update_profile_context(
        self, result: Dict[str, Any], user_id: str
    ) -> str:
        """Extract context for profile updates"""

        # Handle case where result is a boolean (success/failure)
        if isinstance(result, bool):
            if result:
                return f"<call>update_user_profile(...)</call>\nProfile updated successfully"
            else:
                return f"<call>update_user_profile(...)</call>\nProfile update failed"

        # Handle case where result is None
        if result is None:
            return f"<call>update_user_profile(...)</call>\nNo result returned"

        # Handle case where result is not a dictionary
        if not isinstance(result, dict):
            return f"<call>update_user_profile(...)</call>\nUnexpected result type: {type(result).__name__} = {result}"

        # Handle dictionary result
        if "error" in result:
            return f"<call>update_user_profile(...)</call>\nError: {result['error']}"

        if "success" in result and result["success"]:
            updated_fields = result.get("updated_fields", [])
            if updated_fields:
                return f"<call>update_user_profile(...)</call>\nProfile updated successfully. Updated fields: {', '.join(updated_fields)}"
            else:
                return f"<call>update_user_profile(...)</call>\nProfile updated successfully"

        # Default case
        return f"<call>update_user_profile(...)</call>\nProfile operation completed with result: {result}"

    def _extract_flight_search_context(
        self, result: ModelSearchResponse, user_id: str
    ) -> str:
        """Extract flight search results - condensed context"""
        # Access dataclass attributes directly
        search_params = getattr(result, "search_params", {})
        origin = search_params.get("origin", "") if search_params else ""
        destination = search_params.get("destination", "") if search_params else ""
        date = search_params.get("departure_date", "") if search_params else ""

        call_str = f"<call>search_flights(origin='{origin}', destination='{destination}', departure_date='{date}')</call>"

        # Check for errors
        if hasattr(result, "error_message") and result.error_message:
            return f"{call_str}\nError: {result.error_message}"

        flights = getattr(result, "flights", [])
        search_id = getattr(result, "search_id", "")
        summary = getattr(result, "summary", {})

        if not flights:
            return f"{call_str}\nNo flights found for {origin} → {destination}"

        # Much shorter context - just the essentials
        context = f"{call_str}\n"
        context += f"SUCCESS: Search ID {search_id}\n"
        context += f"Found {summary.get('total_found', len(flights))} flights {origin}→{destination}\n"
        context += f"Organize all search results into exact vs nearby routes, select top 3 from each group, use display functions"

        return context

    def _extract_flight_details_context(
        self, result: Dict[str, Any], user_id: str
    ) -> str:
        """Extract context for flight details"""
        flight_id = result.get("flight_id", "unknown")
        call_str = f"<call>get_flight_details(flight_id='{flight_id}')</call>"

        if "error" in result:
            return f"{call_str}\nError: {result['error']}"

        # Include key details the user might reference later
        context = f"{call_str}\n"
        context += f"Retrieved details for flight {flight_id}\n"

        # Add key details if available
        if result.get("baggage_info"):
            context += (
                f"Baggage: {result.get('baggage_summary', 'Details available')}\n"
            )
        if result.get("seat_options"):
            context += "Seat selection available\n"

        return context

    def _extract_booking_details_context(
        self, result: Dict[str, Any], user_id: str
    ) -> str:
        """Extract context for booking lookup"""
        if result.get("user_bookings"):
            call_str = f"<call>get_booking_details(user_bookings=true)</call>"

            if "error" in result:
                return f"{call_str}\nError: {result['error']}"

            bookings = result.get("bookings", [])
            context = f"{call_str}\n"
            context += f"User has {len(bookings)} bookings:\n"
            for booking in bookings[:3]:  # Show recent 3
                bid = booking.get("booking_reference", booking.get("id", ""))
                status = booking.get("status", "")
                amount = booking.get("total_amount", 0)
                context += f"• {bid}: {status} (${amount})\n"
        else:
            booking_id = result.get("booking_id", "")
            call_str = f"<call>get_booking_details(booking_id='{booking_id}')</call>"

            if "error" in result:
                return f"{call_str}\nError: {result['error']}"

            status = result.get("status", "")
            pnr = result.get("pnr", "")
            context = f"{call_str}\n"
            context += f"Booking {booking_id}: {status}\n"
            if pnr:
                context += f"PNR: {pnr}\n"

        return context

    def _extract_cancel_booking_context(
        self, result: Dict[str, Any], user_id: str
    ) -> str:
        """Extract context for booking cancellation - FIXED VERSION"""
        booking_id = result.get("booking_id", "")
        reason = result.get("reason", "")
        call_str = (
            f"<call>cancel_booking(booking_id='{booking_id}', reason='{reason}')</call>"
        )

        if "error" in result:
            return f"{call_str}\nError: {result['error']}"

        refund_amount = result.get("refund_amount", 0)
        context = f"{call_str}\n"
        context += f"Booking {booking_id} cancelled\n"

        # FIX: Safely format refund amount
        try:
            if refund_amount and float(refund_amount) > 0:
                refund_str = f"${float(refund_amount):.0f}"
                context += f"Refund: {refund_str} processed"
            else:
                context += "No refund applicable"
        except (ValueError, TypeError):
            context += "Refund status: Processing"

        return context

    def _extract_booking_creation_context(
        self, result: Dict[str, Any], user_id: str
    ) -> str:
        """Extract context for booking creation"""
        booking_context = self.services[
            "booking_storage_service"
        ].extract_booking_operation_context(result, "create")

        print(f"Booking creation context: {booking_context}")

        return booking_context

    def _extract_passenger_management_context(
        self, result: Dict[str, Any], user_id: str
    ) -> str:
        """Extract context for enhanced passenger and booking management"""
        action = result.get("action", "")
        operation_map = {
            "add": "add_passenger",
            "update": "update_passenger",
            "update_booking": "update_booking",
            "get": "get",
            "add_emergency_contact": "add_emergency_contact",
        }

        operation = operation_map.get(action, action)
        booking_context = self.services[
            "booking_storage_service"
        ].extract_booking_operation_context(
            result, operation, **{k: v for k, v in result.items() if k != "action"}
        )

        return booking_context

    def _extract_finalize_booking_context(
        self, result: Dict[str, Any], user_id: str
    ) -> str:
        """Extract context for booking finalization"""
        booking_context = self.services[
            "booking_storage_service"
        ].extract_booking_operation_context(result, "finalize")

        return booking_context

    def _generate_payment_link(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Dummy payment link generator"""
        booking_id = kwargs.get("booking_id")

        # TODO: Integrate with actual Stripe payment link generation
        payment_url = f"https://checkout.stripe.com/pay/session_{booking_id}_{user_id}"

        return {
            "success": True,
            "booking_id": booking_id,
            "payment_url": payment_url,
            "expires_in": "24 hours",
            "message": "Payment link generated. Complete payment within 24 hours.",
        }

    def _extract_payment_link_context(
        self, result: Dict[str, Any], user_id: str
    ) -> str:
        """Extract context for payment link generation"""
        booking_id = result.get("booking_id", "")

        if "error" in result:
            return f"<call>generate_payment_link(booking_id='{booking_id}')</call>\nError: {result['error']}"

        payment_url = result.get("payment_url", "")
        expires_in = result.get("expires_in", "24 hours")

        return f"""<call>generate_payment_link(booking_id='{booking_id}')</call>
    SUCCESS: Payment link generated
    URL: {payment_url}
    Expires: {expires_in}
    User must complete payment to confirm booking."""
