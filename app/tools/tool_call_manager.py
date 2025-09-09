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
    extract_context: Optional[Callable[[Dict[str, Any], str], str]] = None
    

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
            execute_function=self._get_user_details_wrapper,
            extract_context=self._extract_user_details_context
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
            execute_function=lambda user_id, **kwargs: self.services['user_storage_service'].update_user(user_id, **kwargs),
            extract_context=self._extract_update_profile_context
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
            execute_function=self._delegate_to_flight_service,
            extract_context=self._extract_flight_search_context
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
            execute_function=lambda user_id, flight_id: self.services['flight_details_service'].get_flight_details(flight_id),
            extract_context=self._extract_flight_details_context
        )
    
    def _create_flight_booking_config(self) -> ToolConfig:
        return ToolConfig(
            name="create_flight_booking",
            description="Create draft booking from search results",
            access_level="onboarded",
            parameters=[
                ToolParameter("search_id", "string", True, "Search ID from flight search"),
                ToolParameter("flight_offer_ids", "array", True, "Selected flight offer IDs"),
                ToolParameter("passenger_count", "integer", False, "Total number of travelers", 1),
                ToolParameter("booking_type", "string", False, "individual/family/group/corporate", "individual"),
            ],
            instructions="""Create draft booking. Next step: collect ALL passenger details with manage_booking_passengers.""",
            examples=["<call>create_flight_booking(search_id='search_123', flight_offer_ids=['offer_456'], passenger_count=2, booking_type='family')</call>"],
            execute_function=lambda user_id, **kwargs: self._delegate_to_booking_service(user_id, _tool_name='create_flight_booking', **kwargs),
            extract_context=self._extract_booking_creation_context
        )

    def _manage_booking_passengers_config(self) -> ToolConfig:
        return ToolConfig(
            name="manage_booking_passengers",
            description="Add passengers and collect complete travel details",
            access_level="active",
            parameters=[
                ToolParameter("booking_id", "string", True, "Booking identifier"),
                ToolParameter("action", "string", True, "'add', 'update', 'get'"),
                ToolParameter("passenger_id", "string", False, "Required for update action"),
                ToolParameter("first_name", "string", False, "Passenger first name"),
                ToolParameter("last_name", "string", False, "Passenger last name"),
                ToolParameter("date_of_birth", "string", False, "Date of birth (YYYY-MM-DD)"),
                ToolParameter("gender", "string", False, "male/female/other"),
                ToolParameter("passport_number", "string", False, "Passport number"),
                ToolParameter("nationality", "string", False, "Nationality (2-letter code)"),
                ToolParameter("seat_preference", "string", False, "window/aisle/any"),
                ToolParameter("meal_preference", "string", False, "vegetarian/vegan/kosher/halal/standard"),
                ToolParameter("emergency_contact_name", "string", False, "Emergency contact name"),
                ToolParameter("emergency_contact_phone", "string", False, "Emergency contact phone"),
                ToolParameter("emergency_contact_relationship", "string", False, "Relationship to passenger"),
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
                "<call>manage_booking_passengers(booking_id='BK123', action='get')</call>"
            ],
            execute_function=lambda user_id, **kwargs: self._delegate_to_booking_service(user_id, _tool_name='manage_booking_passengers', **kwargs),
            extract_context=self._extract_passenger_management_context
        )

    def _finalize_booking_config(self) -> ToolConfig:
        return ToolConfig(
            name="finalize_booking",
            description="Create airline reservation and get final pricing",
            access_level="active",
            parameters=[
                ToolParameter("booking_id", "string", True, "Booking with complete details"),
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
            execute_function=lambda user_id, **kwargs: self._delegate_to_booking_service(user_id, _tool_name='finalize_booking', **kwargs),
            extract_context=self._extract_finalize_booking_context
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
            execute_function=lambda user_id, **kwargs: self._generate_payment_link(user_id, **kwargs),
            extract_context=self._extract_payment_link_context
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
            execute_function=self._delegate_to_booking_service,
            extract_context=self._extract_booking_details_context
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
            execute_function=self._delegate_to_booking_service,
            extract_context=self._extract_cancel_booking_context
        )
    
    # =============================================================================
    # SERVICE DELEGATION - Simple pass-through to appropriate services
    # =============================================================================
    
    def _delegate_to_flight_service(self, user_id, **kwargs):
        try:
            # search_flights returns a tuple: (summarized_results, raw_results)
            summarized_results, raw_results = self.services['flight_service'].search_flights(**kwargs)
            
            # Cache the full raw results for booking purposes
            search_id = self.services['shared_storage_service'].cache_search_results(
                user_id, kwargs, raw_results
            )
            
            # Add search_id to summarized results if not already there
            if isinstance(summarized_results, dict):
                summarized_results['search_id'] = search_id
                
            # Add search params to summarized results for context
            summarized_results['search_params'] = kwargs
            
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
            if kwargs.get('action') == 'update_booking' and 'passenger_count' in kwargs and 'booking_type' not in kwargs:
                passenger_count = kwargs.get('passenger_count', 1)
                if passenger_count == 1:
                    kwargs['booking_type'] = 'individual'
                elif 2 <= passenger_count <= 6:
                    kwargs['booking_type'] = 'family'
                elif passenger_count >= 7:
                    kwargs['booking_type'] = 'group'
                
                print(f"Auto-determined booking_type: {kwargs['booking_type']} for {passenger_count} passengers")
            
            # Map the tool calls to the appropriate actions
            tool_name = kwargs.get('_tool_name', 'unknown')
            
            # Determine action based on the tool call or explicit action
            if 'action' not in kwargs:
                action_mapping = {
                    'create_flight_booking': 'create',
                    'manage_booking_passengers': kwargs.get('action', 'add'),
                    'finalize_booking': 'finalize',
                    'get_booking_details': 'get',
                    'cancel_booking': 'cancel'
                }
                
                # Try to determine action from context
                if 'search_id' in kwargs and 'flight_offer_ids' in kwargs:
                    action = 'create'
                elif 'booking_id' in kwargs and 'first_name' in kwargs:
                    action = 'add'
                elif 'booking_id' in kwargs and 'passenger_id' in kwargs:
                    action = 'update'
                elif 'booking_id' in kwargs and kwargs.get('user_bookings'):
                    action = 'get'
                elif 'booking_id' in kwargs and 'reason' in kwargs:
                    action = 'cancel'
                elif 'booking_id' in kwargs and ('passenger_count' in kwargs or 'booking_type' in kwargs):
                    action = 'update_booking'
                elif 'booking_id' in kwargs and tool_name == 'finalize_booking':
                    action = 'finalize'
                else:
                    action = action_mapping.get(tool_name, 'create')
                
                kwargs['action'] = action
            
            print(f"Determined action: {kwargs['action']}")
            print(f"Final kwargs being passed: {kwargs}")
            
            # Call the booking service
            result = self.services['booking_storage_service'].handle_booking_operation(user_id, **kwargs)
            
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

    def _extract_user_details_context(self, result: Dict[str, Any], user_id: str) -> str:
        """Extract context for user details check"""
        if 'error' in result:
            return f"<call>get_user_details()</call>\nError: {result['error']}"
        
        name = f"{result.get('first_name', '')} {result.get('last_name', '')}".strip()
        location = result.get('location', '')
        language = result.get('preferred_language', '')
        
        context = f"<call>get_user_details()</call>\n"
        
        if result.get('onboarding_complete'):
            context += f"User: {name} from {location} (language: {language})\n"
            context += "Status: Onboarding complete"
        else:
            missing = result.get('missing_fields', [])
            context += f"User: {name or 'Name missing'}\n"
            context += f"Missing required fields: {', '.join(missing)}"
        
        return context

    def _extract_update_profile_context(self, result: Dict[str, Any], user_id: str) -> str:
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
        if 'error' in result:
            return f"<call>update_user_profile(...)</call>\nError: {result['error']}"
        
        if 'success' in result and result['success']:
            updated_fields = result.get('updated_fields', [])
            if updated_fields:
                return f"<call>update_user_profile(...)</call>\nProfile updated successfully. Updated fields: {', '.join(updated_fields)}"
            else:
                return f"<call>update_user_profile(...)</call>\nProfile updated successfully"
        
        # Default case
        return f"<call>update_user_profile(...)</call>\nProfile operation completed with result: {result}"

    def _extract_flight_search_context(self, result: Dict[str, Any], user_id: str) -> str:
        """Extract concise but complete context for flight search results - FIXED VERSION"""
        search_params = result.get('search_params', {})
        origin = search_params.get('origin', '')
        destination = search_params.get('destination', '')
        date = search_params.get('departure_date', '')
        
        call_str = f"<call>search_flights(origin='{origin}', destination='{destination}', departure_date='{date}')</call>"
        
        if 'error' in result:
            return f"{call_str}\nError: {result['error']}"
        
        flights = result.get('flights', [])
        search_id = result.get('search_id', '')
        summary = result.get('summary', {})
        
        if not flights:
            return f"{call_str}\nNo flights found for {origin} → {destination}"
        
        context = f"{call_str}\n"
        context += f"Search ID: {search_id}\n"
        context += f"Found {summary.get('total_found', len(flights))} flights {origin}→{destination} on {date}. "
        context += f"Prices: {summary.get('price_range', 'varies')}\n"
        context += "Available flights:\n"
        
        # Show top flights with booking essentials - FIXED COMPARISON
        for i, flight in enumerate(flights[:5], 1):
            flight_id = flight.get('id') or flight.get('flight_offer_id', '')
            price = flight.get('price', flight.get('price_total', 0))
            airline = flight.get('airline', flight.get('airline_name', ''))
            departure = flight.get('departure', '')
            arrival = flight.get('arrival', '')
            stops = flight.get('stops', 0)
            
            # FIX: Handle price formatting more safely
            try:
                if isinstance(price, str):
                    # If price is already a string like "$103", use it directly
                    price_str = price
                elif isinstance(price, (int, float)):
                    price_str = f"${price:.0f}"
                else:
                    price_str = "Price TBD"
            except (ValueError, TypeError):
                price_str = "Price TBD"
            
            # FIX: Safely handle stops comparison
            try:
                stops_int = int(stops) if stops is not None else 0
                stops_text = "direct" if stops_int == 0 else f"{stops_int} stop{'s' if stops_int > 1 else ''}"
            except (ValueError, TypeError):
                stops_text = "connection info unavailable"
            
            context += f"{i}. ID:{flight_id} | {airline} {price_str} | {departure}-{arrival} | {stops_text}\n"
        
        context += f"\nTo book: use search_id='{search_id}' with exact flight ID from above"
        return context

    def _extract_flight_details_context(self, result: Dict[str, Any], user_id: str) -> str:
        """Extract context for flight details"""
        flight_id = result.get('flight_id', 'unknown')
        call_str = f"<call>get_flight_details(flight_id='{flight_id}')</call>"
        
        if 'error' in result:
            return f"{call_str}\nError: {result['error']}"
        
        # Include key details the user might reference later
        context = f"{call_str}\n"
        context += f"Retrieved details for flight {flight_id}\n"
        
        # Add key details if available
        if result.get('baggage_info'):
            context += f"Baggage: {result.get('baggage_summary', 'Details available')}\n"
        if result.get('seat_options'):
            context += "Seat selection available\n"
        
        return context

    def _extract_booking_details_context(self, result: Dict[str, Any], user_id: str) -> str:
        """Extract context for booking lookup"""
        if result.get('user_bookings'):
            call_str = f"<call>get_booking_details(user_bookings=true)</call>"
            
            if 'error' in result:
                return f"{call_str}\nError: {result['error']}"
            
            bookings = result.get('bookings', [])
            context = f"{call_str}\n"
            context += f"User has {len(bookings)} bookings:\n"
            for booking in bookings[:3]:  # Show recent 3
                bid = booking.get('booking_reference', booking.get('id', ''))
                status = booking.get('status', '')
                amount = booking.get('total_amount', 0)
                context += f"• {bid}: {status} (${amount})\n"
        else:
            booking_id = result.get('booking_id', '')
            call_str = f"<call>get_booking_details(booking_id='{booking_id}')</call>"
            
            if 'error' in result:
                return f"{call_str}\nError: {result['error']}"
            
            status = result.get('status', '')
            pnr = result.get('pnr', '')
            context = f"{call_str}\n"
            context += f"Booking {booking_id}: {status}\n"
            if pnr:
                context += f"PNR: {pnr}\n"
        
        return context

    def _extract_cancel_booking_context(self, result: Dict[str, Any], user_id: str) -> str:
        """Extract context for booking cancellation - FIXED VERSION"""
        booking_id = result.get('booking_id', '')
        reason = result.get('reason', '')
        call_str = f"<call>cancel_booking(booking_id='{booking_id}', reason='{reason}')</call>"
        
        if 'error' in result:
            return f"{call_str}\nError: {result['error']}"
        
        refund_amount = result.get('refund_amount', 0)
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

    def _extract_booking_creation_context(self, result: Dict[str, Any], user_id: str) -> str:
        """Extract context for booking creation"""
        booking_context = self.services['booking_storage_service'].extract_booking_operation_context(
            result, 'create'
        )
        
        print(f"Booking creation context: {booking_context}")
        
        return booking_context

    def _extract_passenger_management_context(self, result: Dict[str, Any], user_id: str) -> str:
        """Extract context for enhanced passenger and booking management"""
        action = result.get('action', '')
        operation_map = {
            'add': 'add_passenger',
            'update': 'update_passenger', 
            'update_booking': 'update_booking',
            'get': 'get',
            'add_emergency_contact': 'add_emergency_contact'
        }
        
        operation = operation_map.get(action, action)
        booking_context = self.services['booking_storage_service'].extract_booking_operation_context(
            result, operation, **{k: v for k, v in result.items() if k != 'action'}
        )
        
        return booking_context

    def _extract_finalize_booking_context(self, result: Dict[str, Any], user_id: str) -> str:
        """Extract context for booking finalization"""
        booking_context = self.services['booking_storage_service'].extract_booking_operation_context(
            result, 'finalize'
        )
        
        return booking_context

    def _generate_payment_link(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Dummy payment link generator"""
        booking_id = kwargs.get('booking_id')
        
        # TODO: Integrate with actual Stripe payment link generation
        payment_url = f"https://checkout.stripe.com/pay/session_{booking_id}_{user_id}"
        
        return {
            'success': True,
            'booking_id': booking_id,
            'payment_url': payment_url,
            'expires_in': '24 hours',
            'message': 'Payment link generated. Complete payment within 24 hours.'
        }

    def _extract_payment_link_context(self, result: Dict[str, Any], user_id: str) -> str:
        """Extract context for payment link generation"""
        booking_id = result.get('booking_id', '')
        
        if 'error' in result:
            return f"<call>generate_payment_link(booking_id='{booking_id}')</call>\nError: {result['error']}"
        
        payment_url = result.get('payment_url', '')
        expires_in = result.get('expires_in', '24 hours')
        
        return f"""<call>generate_payment_link(booking_id='{booking_id}')</call>
    SUCCESS: Payment link generated
    URL: {payment_url}
    Expires: {expires_in}
    User must complete payment to confirm booking."""

