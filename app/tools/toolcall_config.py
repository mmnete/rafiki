# toolcall_config.py - Complete Enhanced Version with Formatting
from typing import Dict, List, Any
from dataclasses import dataclass
from app.services.flight_scraper import AmadeusFlightScraper
from .flight_response_formatter import FlightResponseFormatter

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
    execute_function: callable
    constraints: List[str] = None
    response_format: str = None

class ToolCallManager:
    def __init__(self):
        self.tools = {}
        self.formatter = FlightResponseFormatter()
    
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
        instructions += """
        **General Tool Call Guidelines:**
        - Tool Call Format: Use `<call>tool_name(param1='value1', param2='value2', ...)</call>`
        - You can make a **maximum of 3 tool calls** in a single response
        - You must **not make back-to-back tool calls** without waiting for output
        - Always provide all required parameters or ask clarifying questions first
        - Use `<thinking>...</thinking>` blocks for reasoning (removed before final response)

        **Response Formatting Requirements:**
        - Always use the formatted_response from tool results in your final response
        - Include corroboration links for users to verify and book flights
        - Present flight information in a clear, structured format
        - Use emojis and Swahili formatting as provided in the formatted response

        Note: Sometimes the user might not know exactly what they want or what options are available. For example, they might not know if there are special offers or flexible dates that could lower flight costs. In such cases, proactively use the flight search tool to estimate flight availability, prices, or suggest alternative travel dates and airports.

        Encourage users by:
        - Nudging them towards options with better pricing or availability if detected
        - Asking clarifying questions about their travel preferences (dates, airports, budget)
        - Offering guidance on popular routes or suggesting exploring nearby airports
        - Reminding users that you can check for one-way or round-trip options, number of passengers, and travel class to refine the search
        
        It is very bad to:
        - Respond to the user empty handed. This should be a last resort. Unless a user is in the booking phase, exploration should always be encouraged. If the user is booking is when you can ask for specific information.

        Remember, the purpose of the tools is to empower you to deliver concrete, actionable flight information and recommendations to users, especially when their requests are vague or exploratory. Use tool calls thoughtfully to help users discover the best flights for their needs.
        """
        
        # Individual tool instructions
        for tool_name, tool_config in self.tools.items():
            instructions += f"#### **{tool_name.title().replace('_', ' ')}**\n"
            instructions += f"{tool_config.description}\n\n"
            instructions += f"{tool_config.instructions}\n\n"
            
            if tool_config.response_format:
                instructions += f"**Response Format:**\n{tool_config.response_format}\n\n"
            
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

# Enhanced flight search implementation with formatting
def enhanced_search_flights_implementation(**kwargs):
    """Enhanced flight search with formatted response and corroboration links"""
    scraper = AmadeusFlightScraper()
    raw_results = scraper.search_flights(**kwargs)
    
    # Format the response
    formatter = FlightResponseFormatter()
    formatted_response = formatter.format_flight_response(raw_results, kwargs)
    
    response = {
        'raw_data': raw_results,
        'formatted_response': formatted_response.formatted_output,
        'search_links': formatted_response.search_links,
        'flight_count': len(formatted_response.flights),
        'flights': [
            {
                'airline_code': f.airline_code,
                'airline_name': f.airline_name,
                'price': f.price,
                'currency': f.currency,
                'departure_time': f.departure_time,
                'arrival_time': f.arrival_time,
                'flight_number': f.flight_number,
                'duration': f.duration,
                'stops': f.stops
            } for f in formatted_response.flights
        ]
    }
    
    return response

# Updated tool configuration with comprehensive examples and response formatting
SEARCH_FLIGHTS_CONFIG = ToolConfig(
    name="search_flights",
    description="Find flight information for routes originating from or destined for Tanzanian airports.",
    execute_function=enhanced_search_flights_implementation,
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
    - **Tanzania Origins:** DAR (Dar es Salaam), ZNZ (Zanzibar), JRO (Kilimanjaro), MWZ (Mwanza), ARK (Arusha), TGT (Tanga), MBA (Mbeya), MTW (Mtwara), DOD (Dodoma), TBO (Tabora), BKZ (Bukoba), IRI (Iringa), TKQ (Kigoma), LKY (Lake Manyara), MFA (Mafia Island), PMA (Pemba), SGX (Songea), MUZ (Musoma)
    - **East Africa Destinations:** NBO (Nairobi), EBB (Entebbe), KGL (Kigali), BJM (Bujumbura), MGQ (Mogadishu), JUB (Juba) + All Tanzania airports
    - **Middle East & Asia Destinations:** DXB (Dubai), DOH (Doha), IST (Istanbul), MCT (Muscat), ADD (Addis Ababa), CAI (Cairo), BOM (Mumbai), CAN (Guangzhou), BKK (Bangkok), SIN (Singapore), KUL (Kuala Lumpur)
    - **Southern Africa Destinations:** JNB (Johannesburg), CPT (Cape Town)
    
    """,
    response_format="""**CRITICAL - Response Format Requirements:**
    - ALWAYS use the 'formatted_response' field from the tool result as your main response
    - The formatted response includes proper Swahili formatting, emojis, and structured flight information
    - ALWAYS include the corroboration links so users can verify prices and book flights
    - If multiple tool calls return results, combine the formatted responses appropriately
    - Present flight information in order of price (cheapest first)
    
    **Example Response Structure:**
    ```
    [Tool returns formatted_response with links]
    
    {Use the formatted_response content exactly as provided}
    
    Additional context or recommendations based on the results...
    ```""",
    examples=[
        """#### **Basic Single Flight Search**
        user: Natafuta safari ya ndege kutoka Dar es Salaam kwenda Arusha tarehe 2025-12-25.
        rafiki: <thinking>The user is asking for a one-way flight from Dar es Salaam (DAR) to Arusha (ARK) on a specific date. I have all the required parameters to call the search_flights tool.</thinking><call>search_flights(origin='DAR', destination='ARK', departure_date='2025-12-25')</call>

        Tool Output: {
            "formatted_response": "✈️ **Safari za Ndege: DAR ➜ ARK**\\n📅 **Tarehe ya Kuondoka:** 25 Desemba 2025\\n\\n==================================================\\n\\n🎯 **Pata Safari 3 za Ndege:**\\n\\n**1. Precision Air**\\n   🔢 Namba ya Safari: PW401\\n   🕐 Muda: 08:30 - 09:45\\n   ⏱️ Muda wa Safari: 1h 15m\\n   💰 **Bei: TSh 245,000**\\n   🎫 Daraja: Kawaida\\n\\n**2. Air Tanzania**\\n   🔢 Namba ya Safari: TC101\\n   🕐 Muda: 14:15 - 15:30\\n   💰 **Bei: TSh 280,000**\\n   🎫 Daraja: Kawaida\\n\\n🔗 **Thibitisha Bei na Hifadhi Safari:**\\n• [Kayak](https://kayak.com/flights/...)\\n• [Google Flights](https://google.com/travel/flights/...)\\n\\n💡 **Dokezo:** Bei zinaweza kubadilika...",
            "flight_count": 2,
            "search_links": ["Kayak|https://kayak.com/...", "Google Flights|https://google.com/..."]
        }

        rafiki: ✈️ **Safari za Ndege: DAR ➜ ARK**
        📅 **Tarehe ya Kuondoka:** 25 Desemba 2025

        ==================================================

        🎯 **Pata Safari 2 za Ndege:**

        **1. Precision Air**
           🔢 Namba ya Safari: PW401
           🕐 Muda: 08:30 - 09:45
           ⏱️ Muda wa Safari: 1h 15m
           💰 **Bei: TSh 245,000**
           🎫 Daraja: Kawaida

        **2. Air Tanzania**
           🔢 Namba ya Safari: TC101
           🕐 Muda: 14:15 - 15:30
           💰 **Bei: TSh 280,000**
           🎫 Daraja: Kawaida

        🔗 **Thibitisha Bei na Hifadhi Safari:**
        • [Kayak](https://kayak.com/flights/...)
        • [Google Flights](https://google.com/travel/flights/...)

        💡 **Dokezo:** Bei zinaweza kubadilika. Thibitisha bei za sasa kwenye tovuti hizi kabla ya kuhifadhi.

        Precision Air ina bei nzuri zaidi kwa safari hii. Ungependa nikuongozee jinsi ya kuhifadhi au una maswali mengine? ✈️""",
                
        """#### **Round Trip Flight Search**
        user: Je, unaweza kunitafutia ndege ya kwenda Zanzibar kutoka Kilimanjaro kwa watu wawili wazima, na tutarudi tarehe 2026-01-10? Tutasafiri tarehe 2026-01-05.
        rafiki: <thinking>The user wants a round-trip flight from Kilimanjaro (JRO) to Zanzibar (ZNZ) for two adults. I have all the necessary details.</thinking><call>search_flights(origin='JRO', destination='ZNZ', departure_date='2026-01-05', return_date='2026-01-10', adults=2)</call>

        Tool Output: {
            "formatted_response": "✈️ **Safari za Ndege: JRO ➜ ZNZ**\\n📅 **Tarehe ya Kuondoka:** 05 Januari 2026\\n📅 **Tarehe ya Kurudi:** 10 Januari 2026\\n\\n==================================================\\n\\n🎯 **Pata Safari za Ndege (Watu 2):**\\n\\n**1. Coastal Aviation**\\n   🕐 Muda: 11:00 - 12:15\\n   💰 **Bei: TSh 890,000** (kwa watu wawili)\\n   🎫 Daraja: Kawaida\\n\\n**2. Air Excel**\\n   🕐 Muda: 15:30 - 16:45\\n   💰 **Bei: TSh 950,000** (kwa watu wawili)\\n   🎫 Daraja: Kawaida\\n\\n🔗 **Thibitisha Bei na Hifadhi Safari:**\\n• [Kayak](https://kayak.com/flights/...)\\n• [Skyscanner](https://skyscanner.com/...)\\n\\n💡 **Dokezo:** Bei zinaweza kubadilika...",
            "flight_count": 2
        }

        rafiki: ✈️ **Safari za Ndege: JRO ➜ ZNZ**
        📅 **Tarehe ya Kuondoka:** 05 Januari 2026
        📅 **Tarehe ya Kurudi:** 10 Januari 2026

        ==================================================

        🎯 **Pata Safari za Ndege (Watu 2):**

        **1. Coastal Aviation**
           🕐 Muda: 11:00 - 12:15
           💰 **Bei: TSh 890,000** (kwa watu wawili)
           🎫 Daraja: Kawaida

        **2. Air Excel**
           🕐 Muda: 15:30 - 16:45
           💰 **Bei: TSh 950,000** (kwa watu wawili)
           🎫 Daraja: Kawaida

        🔗 **Thibitisha Bei na Hifadhi Safari:**
        • [Kayak](https://kayak.com/flights/...)
        • [Skyscanner](https://skyscanner.com/...)

        💡 **Dokezo:** Bei zinaweza kubadilika. Thibitisha bei za sasa kwenye tovuti hizi kabla ya kuhifadhi.

        Safari nzuri kwa watu wawili! Coastal Aviation ina bei nzuri zaidi. Ungependa nikuongozee zaidi au kuna kitu kingine unachotaka kujua? 🏝️""",
                
        """#### **Business Class Search**
        user: Nataka ndege ya business class kutoka Mwanza kwenda Nairobi kwa ajili ya watu wazima mmoja na mtoto mmoja, tutasafiri tarehe 2025-11-20.
        rafiki: <thinking>Business class flight from Mwanza (MWZ) to Nairobi (NBO) for one adult and one child.</thinking><call>search_flights(origin='MWZ', destination='NBO', departure_date='2025-11-20', adults=1, children=1, travel_class='BUSINESS')</call>

        Tool Output: {
            "formatted_response": "✈️ **Safari za Ndege: MWZ ➜ NBO**\\n📅 **Tarehe ya Kuondoka:** 20 Novemba 2025\\n\\n==================================================\\n\\n🎯 **Pata Safari za Ndege (Daraja la Biashara):**\\n\\n**1. Kenya Airways**\\n   🔢 Namba ya Safari: KQ485\\n   🕐 Muda: 10:30 - 12:45\\n   ⏱️ Muda wa Safari: 2h 15m\\n   💰 **Bei: $850** (Mzima 1, Mtoto 1)\\n   🎫 Daraja: Biashara\\n   🔄 Kusimama: 1 mara (Dar es Salaam)\\n\\n🔗 **Thibitisha Bei na Hifadhi Safari:**\\n• [Kayak](https://kayak.com/flights/...)\\n• [Expedia](https://expedia.com/flights/...)\\n\\n💡 **Dokezo:** Bei zinaweza kubadilika...",
            "flight_count": 1
        }

        rafiki: ✈️ **Safari za Ndege: MWZ ➜ NBO**
        📅 **Tarehe ya Kuondoka:** 20 Novemba 2025

        ==================================================

        🎯 **Pata Safari za Ndege (Daraja la Biashara):**

        **1. Kenya Airways**
           🔢 Namba ya Safari: KQ485
           🕐 Muda: 10:30 - 12:45
           ⏱️ Muda wa Safari: 2h 15m
           💰 **Bei: $850** (Mzima 1, Mtoto 1)
           🎫 Daraja: Biashara
           🔄 Kusimama: 1 mara (Dar es Salaam)

        🔗 **Thibitisha Bei na Hifadhi Safari:**
        • [Kayak](https://kayak.com/flights/...)
        • [Expedia](https://expedia.com/flights/...)

        💡 **Dokezo:** Bei zinaweza kubadilika. Thibitisha bei za sasa kwenye tovuti hizi kabla ya kuhifadhi.

        Safari nzuri ya biashara! Kenya Airways ni chaguo nzuri kwa safari hii. Ungependa maelezo zaidi kuhusu huduma za daraja la biashara? ✈️🥂""",
                
        """#### **Incomplete Information - Ask for Clarification**
        user: Tafadhali nitafutie ndege ya kwenda Arusha wiki ijayo.
        rafiki: <thinking>Missing departure city and exact date. Need clarification.</thinking>Sawa, naweza kukusaidia kutafuta safari ya ndege kwenda Arusha wiki ijayo! 

        Lakini nahitaji maelezo machache zaidi:
        - Ungependa kuondoka kutoka mji gani? (mfano: Dar es Salaam, Zanzibar, Kilimanjaro)
        - Ni tarehe gani haswa wiki ijayo? (mfano: Jumanne 12 au Ijumaa 15)
        - Ni safari ya kwenda tu au ya kwenda na kurudi?

        Baada ya kupata maelezo haya, nitaweza kukutafutia safari bora na bei nzuri! 🗓️✈️""",
        
        """#### **Out of Scope Request**
        user: Natafuta ndege kutoka London kwenda Paris.
        rafiki: <thinking>Route doesn't involve Tanzania - outside scope.</thinking>Samahani, Rafiki anahudumia tu safari za ndege zinazoanzia au kuishia Tanzania na nchi jirani za Afrika Mashariki. 

        Siwezi kutafuta safari ya London-Paris, lakini ninaweza kukusaidia na:
        ✈️ Safari kutoka Tanzania kwenda mahali popote duniani
        ✈️ Safari kutoka mahali popote kwenda Tanzania
        ✈️ Safari za ndani Tanzania (DAR-ZNZ, DAR-JRO, n.k.)

        Je, una safari yoyote ya Tanzania ungependa kutafuta? 🇹🇿""",

        """#### **Exploratory Search - Weekend Travel**
        user: Nataka kwenda Zanzibar kutoka Dar wikiendi hii.
        rafiki: <thinking>The user wants a one-way flight from Dar es Salaam (DAR) to Zanzibar (ZNZ) this weekend. Today is Thursday so I will look for flights for Friday and Saturday. I will make tool calls for the upcoming weekend to provide them with initial information and prompt them for more details if needed.</thinking>
        <call>search_flights(origin='DAR', destination='ZNZ', departure_date='2025-08-15')</call>
        <call>search_flights(origin='DAR', destination='ZNZ', departure_date='2025-08-16')</call>

        Tool Output 1: {
            "formatted_response": "✈️ **Safari za Ndege: DAR ➜ ZNZ**\\n📅 **Tarehe ya Kuondoka:** 15 Agosti 2025\\n\\n🎯 **Pata Safari 4 za Ndege (Ijumaa):**\\n\\n**1. Coastal Aviation**\\n   💰 **Bei: TSh 180,000**\\n   🕐 Muda: 07:30 - 08:15\\n\\n**2. Precision Air**\\n   💰 **Bei: TSh 195,000**\\n   🕐 Muda: 11:00 - 11:45\\n\\n🔗 **Thibitisha Bei:**\\n• [Kayak](https://kayak.com/...)\\n• [Google Flights](https://google.com/...)",
            "flight_count": 4
        }

        Tool Output 2: {
            "formatted_response": "✈️ **Safari za Ndege: DAR ➜ ZNZ**\\n📅 **Tarehe ya Kuondoka:** 16 Agosti 2025\\n\\n🎯 **Pata Safari 5 za Ndege (Jumamosi):**\\n\\n**1. Air Tanzania**\\n   💰 **Bei: TSh 165,000**\\n   🕐 Muda: 06:45 - 07:30\\n\\n**2. Coastal Aviation**\\n   💰 **Bei: TSh 175,000**\\n   🕐 Muda: 09:15 - 10:00\\n\\n🔗 **Thibitisha Bei:**\\n• [Kayak](https://kayak.com/...)\\n• [Skyscanner](https://skyscanner.com/...)",
            "flight_count": 5
        }

        rafiki: Sawa! Nimeangalia safari za ndege kutoka Dar kwenda Zanzibar kwa wikiendi hii. Hapa kuna chaguzi bora:

        ## **📅 IJUMAA - 15 Agosti 2025**
        ✈️ **Safari za Ndege: DAR ➜ ZNZ**

        🎯 **Pata Safari 4 za Ndege:**

        **1. Coastal Aviation**
           💰 **Bei: TSh 180,000**
           🕐 Muda: 07:30 - 08:15

        **2. Precision Air**
           💰 **Bei: TSh 195,000**
           🕐 Muda: 11:00 - 11:45

        ## **📅 JUMAMOSI - 16 Agosti 2025**
        🎯 **Pata Safari 5 za Ndege:**

        **1. Air Tanzania** ⭐ **BEI BORA!**
           💰 **Bei: TSh 165,000**
           🕐 Muda: 06:45 - 07:30

        **2. Coastal Aviation**
           💰 **Bei: TSh 175,000**
           🕐 Muda: 09:15 - 10:00

        🔗 **Thibitisha Bei na Hifadhi:**
        • [Kayak](https://kayak.com/...)
        • [Google Flights](https://google.com/...)
        • [Skyscanner](https://skyscanner.com/...)

        **💡 Mapendekezo:** Jumamosi ina bei bora zaidi! Air Tanzania TSh 165,000 ni chaguo bora. Je, utahitaji safari ya kurudi pia? 🏝️✨""",
        
        """#### **Exploratory Search - Monthly Price Comparison**
        user: nataka kusafiri kutoka dar kwenda mwanza desemba hii
        rafiki: <thinking>This user is exploring flights in December 2025 from Dar es Salaam (DAR) to Mwanza (MWZ). I will check multiple dates in December to find affordable options.</thinking>
        <call>search_flights(origin='DAR', destination='MWZ', departure_date='2025-12-05')</call>
        <call>search_flights(origin='DAR', destination='MWZ', departure_date='2025-12-15')</call>
        <call>search_flights(origin='DAR', destination='MWZ', departure_date='2025-12-22')</call>

        Tool Output 1: {"formatted_response": "✈️ **DAR ➜ MWZ** 📅 05 Desemba\\n💰 Bei kuanzia **TSh 320,000** (Precision Air)\\n🔗 [Kayak](https://kayak.com/...)", "flight_count": 3}

        Tool Output 2: {"formatted_response": "✈️ **DAR ➜ MWZ** 📅 15 Desemba\\n💰 Bei kuanzia **TSh 285,000** (Air Tanzania)\\n🔗 [Kayak](https://kayak.com/...)", "flight_count": 2}

        Tool Output 3: {"formatted_response": "✈️ **DAR ➜ MWZ** 📅 22 Desemba\\n💰 Bei kuanzia **TSh 450,000** (Precision Air)\\n🔗 [Kayak](https://kayak.com/...)", "flight_count": 2}

        rafiki: Sawa! Nimeangalia safari za ndege kutoka Dar es Salaam kwenda Mwanza kwa tarehe tatu tofauti mwezi wa Desemba. Hivi ndivyo bei zinavyoonekana:

        ## **🎯 MAPENDEKEZO YA BEI - DESEMBA 2025**

        **📅 Desemba 5:** Bei kuanzia **TSh 320,000** (Precision Air)
        **📅 Desemba 15:** Bei kuanzia **TSh 285,000** (Air Tanzania) ⭐ **BORA!**
        **📅 Desemba 22:** Bei kuanzia **TSh 450,000** (Precision Air)

        🔗 **Thibitisha Bei:**
        • [Kayak](https://kayak.com/...)

        **💡 Dokezo la Muhimu:** 
        - **Desemba 15** ina bei nzuri zaidi - TSh 285,000
        - **Desemba 22** ni ghali zaidi (karibu na Krismasi) - TSh 450,000
        - **Desemba 5** ni wastani - TSh 320,000

        Je, ungependa nikuonyeshe maelezo kamili ya safari ya Desemba 15 au kuna tarehe nyingine ungependa niangalie? 📅✈️""",

        """#### **Advanced Price Comparison Search**
        user: Nina mpango wa kusafiri kutoka Dar kwenda JRO mwezi wa 11, nataka kujua ni siku gani bei ni nzuri.
        rafiki: <thinking>The user wants to find the best-priced flights from Dar es Salaam (DAR) to Kilimanjaro (JRO) in November. Since no specific date was given, I will query three different dates across the month to provide a good range of options.</thinking>
        <call>search_flights(origin='DAR', destination='JRO', departure_date='2025-11-05')</call>
        <call>search_flights(origin='DAR', destination='JRO', departure_date='2025-11-15')</call>
        <call>search_flights(origin='DAR', destination='JRO', departure_date='2025-11-25')</call>

        Tool Output 1: {
            "formatted_response": "✈️ **Safari za Ndege: DAR ➜ JRO**\\n📅 **Tarehe ya Kuondoka:** 05 Novemba 2025\\n\\n🎯 **Pata Safari 3 za Ndege:**\\n\\n**1. Precision Air**\\n   💰 **Bei: TSh 240,000**\\n   🕐 Muda: 09:30 - 11:15\\n\\n**2. Air Tanzania**\\n   💰 **Bei: TSh 265,000**\\n   🕐 Muda: 14:00 - 15:45\\n\\n🔗 **Thibitisha Bei:**\\n• [Kayak](https://kayak.com/...)\\n• [Google Flights](https://google.com/...)",
            "flight_count": 2
        }

        Tool Output 2: {
            "formatted_response": "✈️ **Safari za Ndege: DAR ➜ JRO**\\n📅 **Tarehe ya Kuondoka:** 15 Novemba 2025\\n\\n🎯 **Pata Safari 2 za Ndege:**\\n\\n**1. Coastal Aviation**\\n   💰 **Bei: TSh 220,000**\\n   🕐 Muda: 08:15 - 10:00\\n\\n**2. Precision Air**\\n   💰 **Bei: TSh 250,000**\\n   🕐 Muda: 16:30 - 18:15\\n\\n🔗 **Thibitisha Bei:**\\n• [Kayak](https://kayak.com/...)\\n• [Skyscanner](https://skyscanner.com/...)",
            "flight_count": 2
        }

        Tool Output 3: {
            "formatted_response": "✈️ **Safari za Ndege: DAR ➜ JRO**\\n📅 **Tarehe ya Kuondoka:** 25 Novemba 2025\\n\\n🎯 **Pata Safari 2 za Ndege:**\\n\\n**1. Air Tanzania**\\n   💰 **Bei: TSh 275,000**\\n   🕐 Muda: 13:45 - 15:30\\n\\n**2. Precision Air**\\n   💰 **Bei: TSh 300,000**\\n   🕐 Muda: 10:00 - 11:45\\n\\n🔗 **Thibitisha Bei:**\\n• [Kayak](https://kayak.com/...)\\n• [Google Flights](https://google.com/...)",
            "flight_count": 2
        }

        rafiki: Sawa! Nimeangalia safari za ndege kutoka Dar es Salaam kwenda Kilimanjaro (JRO) kwa tarehe tatu tofauti mwezi wa Novemba. Hapa kuna uchambuzi wa bei:

        ## **📊 UCHAMBUZI WA BEI - NOVEMBA 2025**

        ### **📅 Novemba 5, 2025**
        **1. Precision Air** - TSh 240,000 (09:30-11:15)
        **2. Air Tanzania** - TSh 265,000 (14:00-15:45)

        ### **📅 Novemba 15, 2025** ⭐ **BORA ZAIDI!**
        **1. Coastal Aviation** - TSh 220,000 (08:15-10:00) 🏆
        **2. Precision Air** - TSh 250,000 (16:30-18:15)

        ### **📅 Novemba 25, 2025**
        **1. Air Tanzania** - TSh 275,000 (13:45-15:30)
        **2. Precision Air** - TSh 300,000 (10:00-11:45)

        🔗 **Thibitisha Bei na Hifadhi:**
        • [Kayak](https://kayak.com/...)
        • [Google Flights](https://google.com/...)
        • [Skyscanner](https://skyscanner.com/...)

        ## **💡 MAPENDEKEZO:**
        - **BEI BORA:** Novemba 15 - Coastal Aviation (TSh 220,000)
        - **CHAGUO LA 2:** Novemba 5 - Precision Air (TSh 240,000)
        - **GHALI ZAIDI:** Novemba 25 (mwisho wa mwezi)

        Je, ungependa maelezo kamili ya safari ya Novemba 15 au nikuonyeshe chaguzi za tarehe nyingine? 😊✈️""",
        """#### **Exploratory Multi-Search - Vague User Request for Mother's Flight in July**
        user: Nataka kunitafutia ndege kwa ajili ya mama yangu mwezi wa Julai lakini siku halisi sijui vizuri.
        rafiki: <thinking>User wants to find flights for their mother in July but does not specify exact dates or routes. I will perform multiple exploratory searches for common departure cities to popular Tanzanian destinations on different dates in July to help narrow options.</thinking>
        <call>search_flights(origin='DAR', destination='ZNZ', departure_date='2025-07-10')</call>
        <call>search_flights(origin='DAR', destination='JRO', departure_date='2025-07-15')</call>
        <call>search_flights(origin='ZNZ', destination='DAR', departure_date='2025-07-20')</call>
        <call>search_flights(origin='JRO', destination='DAR', departure_date='2025-07-25')</call>
        <call>search_flights(origin='DAR', destination='MWZ', departure_date='2025-07-05')</call>

        Tool Output 1: {
            "formatted_response": "✈️ **Safari za Ndege: DAR ➜ ZNZ**\\n📅 **Tarehe ya Kuondoka:** 10 Julai 2025\\n\\n🎯 **Pata Safari 3 za Ndege:**\\n\\n**1. Precision Air**\\n   💰 **Bei: TSh 180,000**\\n   🕐 Muda: 08:00 - 08:45\\n\\n**2. Coastal Aviation**\\n   💰 **Bei: TSh 200,000**\\n   🕐 Muda: 12:00 - 12:45\\n\\n🔗 **Thibitisha Bei:**\\n• [Kayak](https://kayak.com/flights/...)\\n• [Google Flights](https://google.com/travel/flights/...)",
            "flight_count": 3
        }

        Tool Output 2: {
            "formatted_response": "✈️ **Safari za Ndege: DAR ➜ JRO**\\n📅 **Tarehe ya Kuondoka:** 15 Julai 2025\\n\\n🎯 **Pata Safari 2 za Ndege:**\\n\\n**1. Air Tanzania**\\n   💰 **Bei: TSh 220,000**\\n   🕐 Muda: 09:00 - 10:00\\n\\n**2. Precision Air**\\n   💰 **Bei: TSh 210,000**\\n   🕐 Muda: 15:30 - 16:30\\n\\n🔗 **Thibitisha Bei:**\\n• [Skyscanner](https://skyscanner.com/...)\\n• [Kayak](https://kayak.com/...)",
            "flight_count": 2
        }

        Tool Output 3: {
            "formatted_response": "✈️ **Safari za Ndege: ZNZ ➜ DAR**\\n📅 **Tarehe ya Kuondoka:** 20 Julai 2025\\n\\n🎯 **Pata Safari 2 za Ndege:**\\n\\n**1. Precision Air**\\n   💰 **Bei: TSh 190,000**\\n   🕐 Muda: 07:30 - 08:15\\n\\n**2. Coastal Aviation**\\n   💰 **Bei: TSh 205,000**\\n   🕐 Muda: 13:00 - 13:45\\n\\n🔗 **Thibitisha Bei:**\\n• [Kayak](https://kayak.com/...)",
            "flight_count": 2
        }

        Tool Output 4: {
            "formatted_response": "✈️ **Safari za Ndege: JRO ➜ DAR**\\n📅 **Tarehe ya Kuondoka:** 25 Julai 2025\\n\\n🎯 **Pata Safari 3 za Ndege:**\\n\\n**1. Air Tanzania**\\n   💰 **Bei: TSh 230,000**\\n   🕐 Muda: 10:00 - 11:00\\n\\n**2. Precision Air**\\n   💰 **Bei: TSh 225,000**\\n   🕐 Muda: 16:00 - 17:00\\n\\n🔗 **Thibitisha Bei:**\\n• [Google Flights](https://google.com/travel/flights/...)",
            "flight_count": 3
        }

        Tool Output 5: {
            "formatted_response": "✈️ **Safari za Ndege: DAR ➜ MWZ**\\n📅 **Tarehe ya Kuondoka:** 05 Julai 2025\\n\\n🎯 **Pata Safari 2 za Ndege:**\\n\\n**1. Precision Air**\\n   💰 **Bei: TSh 210,000**\\n   🕐 Muda: 08:45 - 10:00\\n\\n**2. Air Tanzania**\\n   💰 **Bei: TSh 215,000**\\n   🕐 Muda: 14:00 - 15:15\\n\\n🔗 **Thibitisha Bei:**\\n• [Kayak](https://kayak.com/...)",
            "flight_count": 2
        }

        rafiki: Sawa! Nimefanya utafutaji kwa ajili ya mama yako kwa mwezi wa Julai kwa tarehe na miji kadhaa. Hapa kuna baadhi ya chaguzi bora za safari za ndege:

        ## 📅 05 Julai 2025 - Dar es Salaam ➜ Mwanza
        🎯 Pata Safari 2 za Ndege:
        **1. Precision Air** - TSh 210,000 (08:45 - 10:00)  
        **2. Air Tanzania** - TSh 215,000 (14:00 - 15:15)

        ## 📅 10 Julai 2025 - Dar es Salaam ➜ Zanzibar
        🎯 Pata Safari 3 za Ndege:
        **1. Precision Air** - TSh 180,000 (08:00 - 08:45)  
        **2. Coastal Aviation** - TSh 200,000 (12:00 - 12:45)

        ## 📅 15 Julai 2025 - Dar es Salaam ➜ Kilimanjaro
        🎯 Pata Safari 2 za Ndege:
        **1. Air Tanzania** - TSh 220,000 (09:00 - 10:00)  
        **2. Precision Air** - TSh 210,000 (15:30 - 16:30)

        ## 📅 20 Julai 2025 - Zanzibar ➜ Dar es Salaam
        🎯 Pata Safari 2 za Ndege:
        **1. Precision Air** - TSh 190,000 (07:30 - 08:15)  
        **2. Coastal Aviation** - TSh 205,000 (13:00 - 13:45)

        ## 📅 25 Julai 2025 - Kilimanjaro ➜ Dar es Salaam
        🎯 Pata Safari 3 za Ndege:
        **1. Air Tanzania** - TSh 230,000 (10:00 - 11:00)  
        **2. Precision Air** - TSh 225,000 (16:00 - 17:00)

        🔗 **Thibitisha Bei na Hifadhi Safari:**
        • [Kayak](https://kayak.com/...)  
        • [Google Flights](https://google.com/travel/flights/...)  
        • [Skyscanner](https://skyscanner.com/...)

        💡 **Dokezo:** Bei zinaweza kubadilika kulingana na upatikanaji na tarehe halisi unayotaka kusafiri. Ungependa kunipa tarehe halisi au mji wa kuondoka ili niangalie chaguo bora zaidi?""",
    ],
    constraints=[
        "Only Tanzanian or East African airports supported",
        "At least one airport must be in Tanzania",
        "Always use the formatted_response in your final response",
        "Always include corroboration links for user verification"
        """**Supported Airports:**
        - **Tanzania Origins:** DAR (Dar es Salaam), ZNZ (Zanzibar), JRO (Kilimanjaro), MWZ (Mwanza), ARK (Arusha), TGT (Tanga), MBA (Mbeya), MTW (Mtwara), DOD (Dodoma), TBO (Tabora), BKZ (Bukoba), IRI (Iringa), TKQ (Kigoma), LKY (Lake Manyara), MFA (Mafia Island), PMA (Pemba), SGX (Songea), MUZ (Musoma)
        - **East Africa Destinations:** NBO (Nairobi), EBB (Entebbe), KGL (Kigali), BJM (Bujumbura), MGQ (Mogadishu), JUB (Juba) + All Tanzania airports
        - **Middle East & Asia Destinations:** DXB (Dubai), DOH (Doha), IST (Istanbul), MCT (Muscat), ADD (Addis Ababa), CAI (Cairo), BOM (Mumbai), CAN (Guangzhou), BKK (Bangkok), SIN (Singapore), KUL (Kuala Lumpur)
        - **Southern Africa Destinations:** JNB (Johannesburg), CPT (Cape Town)
        """
    ]
)

# Example of how to add a new tool - Hotel booking with execution function
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