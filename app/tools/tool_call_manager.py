# unified_toolcall_manager.py - Clean Tool Configuration Only
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass

@dataclass
class ToolParameter:
    name: str
    param_type: str
    required: bool
    description: str
    default: Any = None

@dataclass
class ToolConfig:
    name: str
    description: str
    parameters: List[ToolParameter]
    instructions: str
    examples: List[str]
    execute_function: Callable
    access_level: str = "all"

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
            'user_storage_service', 'flight_service', 'flight_details_service',
            'booking_storage_service', 'shared_storage_service'
        ]
        
        for service_name in required_services:
            if service_name not in self.services or self.services[service_name] is None:
                raise ValueError(f"Required service not provided: {service_name}")
    
    def _register_all_tools(self):
        """Register tools in progressive access order"""
        # Phase 1: Onboarding
        self.register_tool(self._get_user_details_config())
        self.register_tool(self._update_user_profile_config())
        
        # Phase 2: Flight Search & Booking Creation
        self.register_tool(self._search_flights_config())
        self.register_tool(self._get_flight_details_config())
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
            if tool_config.access_level == "all":
                available_tools.append(tool_name)
            elif tool_config.access_level == "onboarded" and self._is_user_onboarded(user):
                available_tools.append(tool_name)
            elif tool_config.access_level == "active" and self._is_user_active(user):
                available_tools.append(tool_name)
        
        return available_tools
    
    def _is_user_onboarded(self, user) -> bool:
        """Check if user has completed required onboarding fields"""
        if not user:
            return False
        required_fields = ['first_name', 'last_name', 'location', 'preferred_language']
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
        instructions += f"Tools: {', '.join([f'`{name}`' for name in available_tools.keys()])}\n\n"
        
        # Phase-specific guidance
        phase_guidance = {
            "Onboarding": "Focus on collecting user information before accessing flight tools.",
            "Flight Search": "User can now search flights and create bookings.",
            "Active User": "Full access to booking management and operations."
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
                    default_text = f" (default: {param.default})" if param.default is not None else ""
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
    
    def get_tool_function(self, tool_name: str) -> Optional[Callable]:
        """Get executable function for a tool"""
        return self.tools.get(tool_name, {}).execute_function if tool_name in self.tools else None
    
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
            execute_function=self._get_user_details_wrapper
        )
    
    def _get_user_details_wrapper(self, user_id: int) -> Dict[str, Any]:
        """Wrapper to convert User object to JSON-serializable dict"""
        user = self.services['user_storage_service'].get_or_create_user(user_id)
        
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
            "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
            "gender": user.gender,
            "location": user.location,
            "preferred_language": user.preferred_language,
            "timezone": user.timezone,
            "status": user.status,
            "onboarding_completed_at": user.onboarding_completed_at.isoformat() if user.onboarding_completed_at else None,
            "is_trusted_tester": user.is_trusted_tester,
            "is_active": user.is_active,
            "travel_preferences": user.travel_preferences,
            "notification_preferences": user.notification_preferences,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            
            # Onboarding status helpers
            "onboarding_complete": all([
                user.first_name, user.last_name, user.location, user.preferred_language
            ]),
            "missing_fields": [
                field for field, value in {
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "location": user.location,
                    "preferred_language": user.preferred_language
                }.items() if not value
            ]
        }
    
    def _update_user_profile_config(self) -> ToolConfig:
        return ToolConfig(
            name="update_user_profile",
            description="Update user profile information",
            access_level="all",
            parameters=[
                ToolParameter("first_name", "string", False, "User's first name"),
                ToolParameter("last_name", "string", False, "User's last name"),
                ToolParameter("location", "string", False, "City and country (e.g., 'New York, USA')"),
                ToolParameter("preferred_language", "string", False, "'en' for English, 'sw' for Swahili"),
                ToolParameter("email", "string", False, "Contact email"),
                ToolParameter("date_of_birth", "string", False, "Date of birth (YYYY-MM-DD)"),
            ],
            instructions="""Update user profile fields during onboarding or anytime.

            **Usage patterns:**
            - Single field: update_user_profile(first_name='John')
            - Multiple fields: update_user_profile(first_name='John', location='NYC, USA')
            - Always confirm information with user before updating""",
            examples=[
                "<call>update_user_profile(first_name='Sarah', last_name='Johnson')</call>",
                "<call>update_user_profile(location='London, UK', preferred_language='en')</call>"
            ],
            execute_function=lambda user_id, **kwargs: self.services['user_storage_service'].update_user(user_id, **kwargs)
        )
    
    def _search_flights_config(self) -> ToolConfig:
        return ToolConfig(
            name="search_flights",
            description="Search flights across multiple booking platforms",
            access_level="onboarded",
            parameters=[
                ToolParameter("origin", "string", True, "3-letter airport code (SFO, JFK)"),
                ToolParameter("destination", "string", True, "3-letter airport code (LAX, LHR)"),
                ToolParameter("departure_date", "string", True, "Departure date (YYYY-MM-DD)"),
                ToolParameter("return_date", "string", False, "Return date for round trip"),
                ToolParameter("adults", "integer", False, "Adult passengers", 1),
                ToolParameter("children", "integer", False, "Children (2-11 years)", 0),
                ToolParameter("infants", "integer", False, "Infants (under 2)", 0),
                ToolParameter("travel_class", "string", False, "Travel class", "ECONOMY"),
            ],
            instructions="""Search for flights and return options with search_id for booking.

            **Search strategy:**
            - For flexible dates: try multiple departure dates
            - For price comparison: search nearby airports
            - Always return search_id - required for creating bookings""",
            examples=["<call>search_flights(origin='SFO', destination='LAX', departure_date='2025-09-15')</call>"],
            execute_function=self._delegate_to_flight_service
        )
    
    def _get_flight_details_config(self) -> ToolConfig:
        return ToolConfig(
            name="get_flight_details",
            description="Get detailed flight information including baggage, seats, requirements",
            access_level="onboarded",
            parameters=[
                ToolParameter("flight_id", "string", True, "Flight offer ID from search results"),
            ],
            instructions="""Retrieve comprehensive flight details for booking decisions.

            **Provides information on:**
            - Pricing breakdown and fare rules
            - Baggage allowances and fees
            - Seat selection options
            - Booking requirements and documents needed""",
            examples=["<call>get_flight_details(flight_id='offer_123')</call>"],
            execute_function=lambda user_id, flight_id: self.services['flight_details_service'].get_flight_details(flight_id)
        )
    
    def _create_flight_booking_config(self) -> ToolConfig:
        return ToolConfig(
            name="create_flight_booking",
            description="Create draft booking from search results - no PNR created yet",
            access_level="onboarded",
            parameters=[
                ToolParameter("search_id", "string", True, "Search ID from flight search"),
                ToolParameter("flight_offer_ids", "array", True, "Selected flight offer IDs"),
            ],
            instructions="""Create initial booking record for passenger collection phase.

            **Important:** This only creates a draft booking in database. PNR creation 
            with airlines happens later in finalize_booking after all passenger details collected.

            **Next steps after this tool:**
            1. Add passenger details with manage_booking_passengers
            2. Finalize booking to create PNR and payment link""",
            examples=["<call>create_flight_booking(search_id='search_123', flight_offer_ids=['offer_456'])</call>"],
            execute_function=self._delegate_to_booking_service
        )
    
    def _manage_booking_passengers_config(self) -> ToolConfig:
        return ToolConfig(
            name="manage_booking_passengers",
            description="Add, update, or retrieve passenger details for booking",
            access_level="active",
            parameters=[
                ToolParameter("booking_id", "string", True, "Booking identifier"),
                ToolParameter("action", "string", True, "'add', 'update', or 'get'"),
                ToolParameter("passenger_id", "string", False, "Required for update action"),
                ToolParameter("passenger_type", "string", False, "'adult', 'child', or 'infant'"),
                ToolParameter("first_name", "string", False, "Passenger first name"),
                ToolParameter("last_name", "string", False, "Passenger last name"),
                ToolParameter("date_of_birth", "string", False, "Date of birth (YYYY-MM-DD) - Required for booking"),
                ToolParameter("gender", "string", False, "Gender (male/female/other)"),
                ToolParameter("passport_number", "string", False, "Passport number - Required for international flights"),
                ToolParameter("document_expiry", "string", False, "Passport expiry date (YYYY-MM-DD)"),
                ToolParameter("nationality", "string", False, "Nationality (2-letter country code)"),
                ToolParameter("email", "string", False, "Email address"),
                ToolParameter("phone", "string", False, "Phone number"),
                ToolParameter("is_primary", "boolean", False, "Is primary passenger"),
                ToolParameter("seat_preference", "string", False, "Seat preference"),
                ToolParameter("meal_preference", "string", False, "Meal preference"),
            ],
            instructions="""Unified passenger management for bookings.

            **Actions:**
            - add: Add new passenger to booking (requires first_name, last_name, date_of_birth, passport_number, nationality)
            - update: Modify existing passenger details  
            - get: Retrieve passenger list or search history

            **Required for Amadeus booking:**
            - first_name, last_name, date_of_birth, nationality, passport_number

            **Workflow:**
            1. Add all required passengers with complete details
            2. Update any details as needed
            3. Proceed to finalize_booking when complete""",
            examples=[
                "<call>manage_booking_passengers(booking_id='BK123', action='add', passenger_type='adult', first_name='John', last_name='Doe', date_of_birth='1990-01-01', passport_number='A12345678', nationality='US')</call>",
                "<call>manage_booking_passengers(booking_id='BK123', action='get')</call>"
            ],
            execute_function=self._delegate_to_booking_service
        )
        
    def _finalize_booking_config(self) -> ToolConfig:
        return ToolConfig(
            name="finalize_booking",
            description="Create PNR with airline, get final pricing, generate payment link",
            access_level="active",
            parameters=[
                ToolParameter("booking_id", "string", True, "Booking with complete passenger details"),
            ],
            instructions="""Critical step that completes the booking process.

            **This tool will:**
            1. Create PNR (booking reference) with airline via Amadeus
            2. Get final confirmed pricing from airline
            3. Generate Stripe payment session URL
            4. Return payment link for user

            **Prerequisites:**
            - All passenger details must be complete
            - Booking must be in draft status

            **After this step:**
            - User receives payment URL to complete purchase
            - Booking status becomes 'pending_payment'""",
            examples=["<call>finalize_booking(booking_id='BK123')</call>"],
            execute_function=self._delegate_to_booking_service
        )
    
    def _get_booking_details_config(self) -> ToolConfig:
        return ToolConfig(
            name="get_booking_details", 
            description="Retrieve booking information or user's booking history",
            access_level="onboarded",
            parameters=[
                ToolParameter("booking_id", "string", False, "Specific booking ID"),
                ToolParameter("user_bookings", "boolean", False, "Get all user bookings", False),
            ],
            instructions="""Get booking information for status checks and management.

            **Usage:**
            - Specific booking: Provide booking_id
            - All bookings: Set user_bookings=true
            - Returns comprehensive details including passengers, flights, payment status""",
            examples=[
                "<call>get_booking_details(booking_id='BK123')</call>",
                "<call>get_booking_details(user_bookings=true)</call>"
            ],
            execute_function=self._delegate_to_booking_service
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
            examples=["<call>cancel_booking(booking_id='BK123', reason='Change of plans')</call>"],
            execute_function=self._delegate_to_booking_service
        )
    
    # =============================================================================
    # SERVICE DELEGATION - Simple pass-through to appropriate services
    # =============================================================================
    
    def _delegate_to_flight_service(self, user_id, **kwargs):
        """Delegate to flight service and cache results"""
        try:
            results = self.services['flight_service'].search_flights(**kwargs)
            search_id = self.services['shared_storage_service'].cache_search_results(user_id, kwargs, results)
            return {'search_id': search_id, 'flights': results, 'search_params': kwargs}
        except Exception as e:
            return {"error": f"Flight search failed: {str(e)}"}
    
    def _delegate_to_booking_service(self, user_id, **kwargs):
        """Delegate to booking service"""
        try:
            return self.services['booking_storage_service'].handle_booking_operation(user_id, **kwargs)
        except Exception as e:
            return {"error": f"Booking operation failed: {str(e)}"}

