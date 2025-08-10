# toolcall_config.py
from typing import Dict, List, Any
from dataclasses import dataclass
from app.services.flight_scraper import AmadeusFlightScraper

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
    execute_function: callable  # The actual execution function
    constraints: List[str] = None

class ToolCallManager:
    def __init__(self):
        self.tools = {}
    
    def register_tool(self, tool_config: ToolConfig):
        """Register a new tool configuration"""
        self.tools[tool_config.name] = tool_config
    
    def get_tool_instructions(self) -> str:
        """Generate tool instructions for all registered tools"""
        if not self.tools:
            return ""
        
        instructions = "### **Tool Usage**\n"
        instructions += f"You have access to {len(self.tools)} tool(s): {', '.join([f'`{name}`' for name in self.tools.keys()])}.\n\n"
        
        # General tool call guidelines
        instructions += """**General Tool Call Guidelines:**
- Tool Call Format: Use `<call>tool_name(param1='value1', param2='value2', ...)</call>`
- You can make a **maximum of 3 tool calls** in a single response
- You must **not make back-to-back tool calls** without waiting for output
- Always provide all required parameters or ask clarifying questions first
- Use `<thinking>...</thinking>` blocks for reasoning (removed before final response)

"""
        
        # Individual tool instructions
        for tool_name, tool_config in self.tools.items():
            instructions += f"#### **{tool_name.title().replace('_', ' ')}**\n"
            instructions += f"{tool_config.description}\n\n"
            instructions += f"{tool_config.instructions}\n\n"
            
            if tool_config.parameters:
                instructions += f"**Parameters for `{tool_name}`:**\n"
                for param in tool_config.parameters:
                    required_text = "required" if param.required else "optional"
                    default_text = f" Defaults to {param.default}." if param.default is not None else ""
                    instructions += f"- `{param.name}` ({param.param_type}, {required_text}): {param.description}{default_text}\n"
                instructions += "\n"
            
            if tool_config.constraints:
                instructions += "**Constraints:**\n"
                for constraint in tool_config.constraints:
                    instructions += f"- {constraint}\n"
                instructions += "\n"
        
        return instructions
    
    def get_examples(self) -> str:
        """Generate few-shot examples for all tools"""
        if not self.tools:
            return ""
        
        examples = "### **Few-Shot Examples**\n\n"
        
        for tool_name, tool_config in self.tools.items():
            if tool_config.examples:
                examples += f"#### **{tool_name.title().replace('_', ' ')} Examples**\n"
                for i, example in enumerate(tool_config.examples, 1):
                    examples += f"**Example {i}:**\n{example}\n\n"
        
        return examples
    
    def get_tool_function(self, tool_name: str) -> callable:
        """Get the execution function for a specific tool"""
        if tool_name in self.tools:
            return self.tools[tool_name].execute_function
        return None
    
    def get_all_tool_functions(self) -> Dict[str, callable]:
        """Get all tool execution functions as a dictionary"""
        return {name: config.execute_function for name, config in self.tools.items()}

# Tool implementation functions
def search_flights_implementation(**kwargs):
    scraper = AmadeusFlightScraper()
    return scraper.search_flights(**kwargs)

def search_hotels_implementation(**kwargs):
    """Mock implementation of hotel search - replace with your actual logic"""
    # Mock response for demonstration
    return [
        {
            "name": "Safari Hotel Arusha",
            "rating": 4,
            "price_per_night": 150000,
            "currency": "TZS",
            "amenities": ["WiFi", "Restaurant", "Pool"]
        }
    ]

def search_car_rental_implementation(**kwargs):
    """Mock implementation of car rental search"""
    return [
        {
            "company": "Avis Tanzania",
            "car_model": "Toyota RAV4",
            "price_per_day": 75000,
            "currency": "TZS"
        }
    ]

# Tool configurations with embedded execution functions
SEARCH_FLIGHTS_CONFIG = ToolConfig(
    name="search_flights",
    description="Find flight information for routes originating from or destined for Tanzanian airports.",
    execute_function=search_flights_implementation,
    parameters=[
        ToolParameter("origin", "string", True, "The 3-letter IATA airport code for departure city (e.g., 'DAR')"),
        ToolParameter("destination", "string", True, "The 3-letter IATA airport code for arrival city (e.g., 'ZNZ')"),
        ToolParameter("departure_date", "string", True, "Date of departure in YYYY-MM-DD format"),
        ToolParameter("return_date", "string", False, "Date of return in YYYY-MM-DD format. Omit for one-way flights"),
        ToolParameter("adults", "integer", False, "Number of adult passengers", 1),
        ToolParameter("children", "integer", False, "Number of child passengers", 0),
        ToolParameter("infants", "integer", False, "Number of infant passengers", 0),
        ToolParameter("travel_class", "string", False, "Class of travel: 'ECONOMY', 'PREMIUM_ECONOMY', 'BUSINESS', 'FIRST'", "ECONOMY")
    ],
    instructions="""**Usage Guidelines:**
- Only search for flights originating from or destined for Tanzanian airports
- Destination can be another Tanzanian airport or East African city
- Always validate airport codes before making calls

**Supported Airports:**
- **Tanzania Origins:** DAR (Dar es Salaam), ZNZ (Zanzibar), JRO (Kilimanjaro), MWZ (Mwanza), ARK (Arusha), TGT (Tanga), MBA (Mbeya), MTW (Mtwara), DOD (Dodoma)
- **East Africa Destinations:** NBO (Nairobi), EBB (Entebbe), KGL (Kigali), BJM (Bujumbura), MGQ (Mogadishu), JUB (Juba) + All Tanzania airports""",
    examples=[
        """user: Natafuta safari ya ndege kutoka Dar es Salaam kwenda Arusha tarehe 2025-12-25.
rafiki: <thinking>The user is asking for a one-way flight from Dar es Salaam (DAR) to Arusha (ARK) on a specific date. I have all the required parameters to call the search_flights tool.</thinking><call>search_flights(origin='DAR', destination='ARK', departure_date='2025-12-25')</call>""",
        
        """user: Je, unaweza kunitafutia ndege ya kwenda Zanzibar kutoka Kilimanjaro kwa watu wawili wazima, na tutarudi tarehe 2026-01-10? Tutasafiri tarehe 2026-01-05.
rafiki: <thinking>The user wants a round-trip flight from Kilimanjaro (JRO) to Zanzibar (ZNZ) for two adults. I have all the necessary details.</thinking><call>search_flights(origin='JRO', destination='ZNZ', departure_date='2026-01-05', return_date='2026-01-10', adults=2)</call>""",
        
        """user: Nataka ndege ya business class kutoka Mwanza kwenda Nairobi kwa ajili ya watu wazima mmoja na mtoto mmoja, tutasafiri tarehe 2025-11-20.
rafiki: <thinking>Business class flight from Mwanza (MWZ) to Nairobi (NBO) for one adult and one child.</thinking><call>search_flights(origin='MWZ', destination='NBO', departure_date='2025-11-20', adults=1, children=1, travel_class='BUSINESS')</call>""",
        
        """user: Tafadhali nitafutie ndege ya kwenda Arusha wiki ijayo.
rafiki: <thinking>Missing departure city and exact date. Need clarification.</thinking>Sawa, naweza kukusaidia. Ungependa kuondoka kutoka mji gani na tarehe gani haswa wiki ijayo? 🗓️""",
        
        """user: Natafuta ndege kutoka London kwenda Paris.
rafiki: <thinking>Route doesn't involve Tanzania - outside scope.</thinking>Samahani, Rafiki anahudumia tu safari za ndege zinazoanzia au kuishia Tanzania. Siwezi kutafuta safari hiyo. 🇹🇿"""
    ],
    constraints=[
        "Only Tanzanian or East African airports supported",
        "At least one airport must be in Tanzania"
    ]
)

# Example of how to add a new tool - Hotel booking with execution function
SEARCH_HOTELS_CONFIG = ToolConfig(
    name="search_hotels",
    description="Find hotel accommodations in Tanzania and East Africa.",
    execute_function=search_hotels_implementation,
    parameters=[
        ToolParameter("city", "string", True, "City name for hotel search"),
        ToolParameter("check_in", "string", True, "Check-in date in YYYY-MM-DD format"),
        ToolParameter("check_out", "string", True, "Check-out date in YYYY-MM-DD format"),
        ToolParameter("guests", "integer", False, "Number of guests", 2),
        ToolParameter("rooms", "integer", False, "Number of rooms", 1),
        ToolParameter("star_rating", "integer", False, "Minimum star rating (1-5)")
    ],
    instructions="""**Usage Guidelines:**
- Search for hotels in major Tanzanian and East African cities
- Always validate dates (check-out must be after check-in)
- Consider local holidays and peak seasons""",
    examples=[
        """user: Natafuta hoteli Arusha kwa siku 3, kuanzia kesho.
rafiki: <thinking>User wants hotel in Arusha for 3 days starting tomorrow. Need check-in and check-out dates.</thinking><call>search_hotels(city='Arusha', check_in='2025-08-10', check_out='2025-08-13')</call>"""
    ],
    constraints=[
        "Only major cities in Tanzania and East Africa",
        "Maximum 30 days booking period"
    ]
)

# Initialize the tool manager
def get_tool_manager() -> ToolCallManager:
    """Initialize and return configured tool manager"""
    manager = ToolCallManager()
    
    # Register all available tools
    manager.register_tool(SEARCH_FLIGHTS_CONFIG)
    # manager.register_tool(SEARCH_HOTELS_CONFIG)  # Uncomment when ready to add
    
    return manager