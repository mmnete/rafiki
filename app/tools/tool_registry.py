from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Callable
from enum import Enum

class AccessLevel(Enum):
    ALL = "all"
    ONBOARDED = "onboarded" 
    TRUSTED_TESTER = "trusted_tester"

@dataclass
class ToolParameter:
    name: str
    param_type: str
    required: bool
    description: str
    default: Any = None

@dataclass
class ToolDefinition:
    name: str
    description: str
    access_level: AccessLevel
    parameters: List[ToolParameter]
    instructions: str
    examples: List[str]

class ToolRegistry:
    """
    Registry of all available tools - pure definitions, no execution logic
    """
    
    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self._register_all_tools()
    
    def _register_all_tools(self):
        """Register all tool definitions"""
        # User Management Tools
        self._register_user_tools()
        
        # Flight Tools
        self._register_flight_tools()
        
        # Booking Tools
        self._register_booking_tools()
        
        # Payment Tools
        self._register_payment_tools()
        
        # Admin Tools
        self._register_admin_tools()
    
    def _register_user_tools(self):
        """Register user management tools"""
        self.tools["get_user_details"] = ToolDefinition(
            name="get_user_details",
            description="Get current user profile information",
            access_level=AccessLevel.ALL,
            parameters=[],
            instructions="Use to check user's current profile and onboarding status.",
            examples=["user: What info do you have about me?\nrafiki: <call>get_user_details()</call>"]
        )
        
        self.tools["update_user_profile"] = ToolDefinition(
            name="update_user_profile",
            description="Update user profile information",
            access_level=AccessLevel.ALL,
            parameters=[
                ToolParameter("first_name", "string", False, "User's first name"),
                ToolParameter("last_name", "string", False, "User's last name"),
                ToolParameter("location", "string", False, "User's location/city"),
                ToolParameter("preferred_language", "string", False, "Language preference ('en' or 'sw')"),
                ToolParameter("email", "string", False, "User's email address"),
            ],
            instructions="Update any user profile field. Only provide fields that need updating.",
            examples=["user: Change my language to English\nrafiki: <call>update_user_profile(preferred_language='en')</call>"]
        )
    
    def _register_flight_tools(self):
        """Register flight search tools"""
        self.tools["search_flights"] = ToolDefinition(
            name="search_flights",
            description="Search for flights across multiple APIs",
            access_level=AccessLevel.ONBOARDED,
            parameters=[
                ToolParameter("origin", "string", True, "3-letter IATA airport code for departure"),
                ToolParameter("destination", "string", True, "3-letter IATA airport code for arrival"),
                ToolParameter("departure_date", "string", True, "Departure date (YYYY-MM-DD)"),
                ToolParameter("return_date", "string", False, "Return date for round-trip"),
                ToolParameter("adults", "integer", False, "Number of adult passengers", 1),
            ],
            instructions="Search flights and return best options. For exploratory requests, perform multiple searches with variations.",
            examples=["user: Flights from NYC to London next month\nrafiki: <call>search_flights(origin='JFK', destination='LHR', departure_date='2025-09-15')</call>"]
        )
    
    def _register_booking_tools(self):
        """Register booking management tools"""
        self.tools["create_flight_booking"] = ToolDefinition(
            name="create_flight_booking",
            description="Create a new flight booking",
            access_level=AccessLevel.ONBOARDED,
            parameters=[
                ToolParameter("search_id", "string", True, "EXACT search_id from flight search results"),
                ToolParameter("flight_offer_ids", "array", True, "EXACT flight_offer_id(s) from search results"),
                ToolParameter("passenger_count", "integer", False, "Number of passengers", 1),
            ],
            instructions="CRITICAL: Only use search_id and flight_offer_ids from actual search results. Never make up values.",
            examples=["user: Book that United flight\nrafiki: <call>create_flight_booking(search_id='sfo_nrt_001', flight_offer_ids=['FO_UA_123'])</call>"]
        )
        
        self.tools["add_passenger_to_booking"] = ToolDefinition(
            name="add_passenger_to_booking", 
            description="Add passenger details to booking",
            access_level=AccessLevel.ONBOARDED,
            parameters=[
                ToolParameter("booking_id", "string", True, "Booking identifier"),
                ToolParameter("passenger_type", "string", True, "Type: 'adult', 'child', or 'infant'"),
                ToolParameter("first_name", "string", True, "Passenger's first name"),
                ToolParameter("last_name", "string", True, "Passenger's last name"),
                ToolParameter("date_of_birth", "string", True, "Date of birth (YYYY-MM-DD)"),
                ToolParameter("document_type", "string", False, "Document type for international travel"),
                ToolParameter("document_number", "string", False, "Document number"),
                ToolParameter("nationality", "string", False, "Passenger nationality"),
            ],
            instructions="Add passenger to booking. Ask for additional passengers after each addition.",
            examples=["user: John Doe, born 1990-05-15\nrafiki: <call>add_passenger_to_booking(booking_id='BK123', passenger_type='adult', first_name='John', last_name='Doe', date_of_birth='1990-05-15')</call>"]
        )
        
        self.tools["get_user_bookings"] = ToolDefinition(
            name="get_user_bookings",
            description="Get all bookings for the user",
            access_level=AccessLevel.ONBOARDED,
            parameters=[
                ToolParameter("status", "string", False, "Filter by status: 'pending', 'confirmed', 'cancelled'"),
                ToolParameter("include_past", "boolean", False, "Include past bookings", False),
            ],
            instructions="Retrieve user's booking history. Use for cancellations or inquiries.",
            examples=["user: Show my bookings\nrafiki: <call>get_user_bookings()</call>"]
        )
    
    def _register_payment_tools(self):
        """Register payment processing tools"""
        self.tools["process_booking_payment"] = ToolDefinition(
            name="process_booking_payment",
            description="Process payment for a booking",
            access_level=AccessLevel.TRUSTED_TESTER,
            parameters=[
                ToolParameter("booking_id", "string", True, "Booking identifier"),
                ToolParameter("payment_method", "string", True, "Payment method: 'credit_card' or 'stripe'"),
                ToolParameter("amount", "float", True, "Payment amount"),
            ],
            instructions="Process payment for confirmed booking.",
            examples=["user: Pay with credit card\nrafiki: <call>process_booking_payment(booking_id='BK123', payment_method='credit_card', amount=450.00)</call>"]
        )
        
        self.tools["cancel_booking_with_refund"] = ToolDefinition(
            name="cancel_booking_with_refund",
            description="Cancel booking and process refund",
            access_level=AccessLevel.TRUSTED_TESTER,
            parameters=[
                ToolParameter("booking_id", "string", True, "Booking identifier to cancel"),
                ToolParameter("cancellation_reason", "string", False, "Reason for cancellation"),
            ],
            instructions="Cancel booking and automatically process refund.",
            examples=["user: Cancel my booking\nrafiki: <call>cancel_booking_with_refund(booking_id='BK123')</call>"]
        )
    
    def _register_admin_tools(self):
        """Register admin/debugging tools"""
        self.tools["get_user_balance"] = ToolDefinition(
            name="get_user_balance", 
            description="Get user's virtual account balance",
            access_level=AccessLevel.TRUSTED_TESTER,
            parameters=[],
            instructions="Check available virtual balance for testing.",
            examples=["user: How much money do I have?\nrafiki: <call>get_user_balance()</call>"]
        )
    
    def get_tool_definition(self, tool_name: str) -> Optional[ToolDefinition]:
        """Get tool definition by name"""
        return self.tools.get(tool_name)
    
    def get_tools_for_access_level(self, access_level: AccessLevel) -> Dict[str, ToolDefinition]:
        """Get all tools for a specific access level"""
        return {
            name: tool for name, tool in self.tools.items() 
            if tool.access_level == access_level or tool.access_level == AccessLevel.ALL
        }
