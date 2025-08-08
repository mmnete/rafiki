import datetime
from app.services.user_service import User

class PromptService:
    def build_prompt(self, history: list, user: User) -> str:
        user_status = user.status

        if user_status == "onboarding_greeted":
            # This is the initial long message, shown only once.
            return self._build_onboarding_name_prompt()
        elif user_status == "onboarding_name":
            # This is the short message for a failed name attempt.
            return self._build_onboarding_name_prompt_repeat()
        elif user_status == "onboarding_confirm_name":
            return self._build_confirm_name_prompt(user)
        elif user_status == "onboarding_location":
            return self._build_onboarding_location_prompt()
        elif user_status == "onboarding_confirm_location":
            return self._build_confirm_location_prompt(user)
        elif user_status == "active":
            return self._build_main_prompt(history, user)
        else:
            return "Samahani, kuna tatizo. Tafadhali jaribu tena baadaye."

    def _build_onboarding_name_prompt(self) -> str:
        # This is the initial long message
        return (
            "Habari! Mimi ni Rafiki, msaidizi wako wa safari za ndege. ✈️🌍\n\n"
            "Rafiki yuko hapa kukusaidia kufanya kila kitu rahisi na haraka — "
            "kutoka kutafuta ndege, kufanya booking, hadi kuhakikisha safari yako inakufaa. 🛫✨\n"
            "Ukizungumza nami, unaweza kuweka booking ya ndege kwa dakika 3 au chini ya hapo! ⏱️🔥\n\n"
            "Kazi yangu ni kuchukua mzigo mzito kutoka mikononi mwako ili uweze kufurahia safari bila wasiwasi. 😊💼\n\n"
            "🛩️ Huduma zangu zinajumuisha:\n"
            "✅ Safari za ndani Tanzania 🇹🇿\n"
            "✅ Safari za kimataifa kutoka na kwenda Tanzania 🌐✈️\n\n"
            "Ili tuanze, tafadhali nipe jina lako kamili. Linapaswa kuwa na maneno mawili au matatu tu, tafadhali.\n\n"
            "Mfano:\n"
            "✅ **Morgan Mnete**\n"
            "✅ **Peter Joshua Mwangi**\n"
            "❌ Morgan\n"
            "❌ Morgan Chris Jabari Juma\n\n"
        )
        
    def _build_onboarding_name_prompt_repeat(self) -> str:
        # This is the concise, simple message for when the user needs to try again.
        return (
            "Samahani, jina lako halikueleweka. 🙏\n"
            "Tafadhali jina lako kamili, la kwanza na la mwisho. Linapaswa kuwa na maneno mawili au matatu.\n\n"
            "Mfano (Example):\n"
            "✅ **Morgan Mnete**\n"
            "✅ **Peter Joshua Mwangi**\n"
        )

    def _build_confirm_name_prompt(self, user: User) -> str:
        return (
            f"Asante {user.first_name} {user.last_name}! Je, hili ndilo jina sahihi? "
            "Tafadhali jibu 'Ndio' au 'Hapana'."
        )

    def _build_onboarding_location_prompt(self) -> str:
        return (
            "Vizuri! Sasa, ili nikuhudumie vizuri, naomba unipe jina la mji au jina la mkoa unaoishi hapa Tanzania."
        )

    def _build_confirm_location_prompt(self, user: User) -> str:
        return (
            f"Je, unaishi {user.location}? Tafadhali jibu 'Ndio' au 'Hapana'."
        )

    def _build_main_prompt(self, history: list, user: User) -> str:
        # The prompt for an active user, as defined in previous examples
        user_name = f"{user.first_name} {user.last_name}" if user.first_name and user.last_name else "Mteja"
        user_location = user.location if user.location else "Tanzania"
        
        context_string = (
            f"User Context:\n"
            f"User Name: {user_name}\n"
            f"User Location: {user_location}\n\n"
        )
        
        system_instruction = (
            "**System Instructions:**\n\n"
            "You are Rafiki, a friendly and helpful digital assistant for Tanzanians using WhatsApp. Your purpose is to assist users with searching for and booking flights. Adhere to the following guidelines strictly.\n\n"
            f"{context_string} \n\n"
            "### **Tool Usage**\n"
            "You have access to a tool called `search_flights` to find flight information. Use this tool when the user explicitly asks to search for flights or implies a flight search.\n"
            "- **Tool Call Format**: If you need to call the tool, you must respond in the following exact format: `<call>search_flights(origin='...', destination='...', departure_date='...', ...)</call>`. "
            "You MUST provide all required parameters. If information is missing, ask clarifying questions before attempting a tool call.\n"
            "- **Parameters for `search_flights`:**\n"
            "    - `origin` (string, required): The 3-letter IATA airport code for the departure city (e.g., 'DAR').\n"
            "    - `destination` (string, required): The 3-letter IATA airport code for the arrival city (e.g., 'ZNZ').\n"
            "    - `departure_date` (string, required): The date of departure in YYYY-MM-DD format.\n"
            "    - `return_date` (string, optional): The date of return in YYYY-MM-DD format. Omit for one-way flights.\n"
            "    - `adults` (integer, optional): Number of adult passengers. Defaults to 1.\n"
            "    - `children` (integer, optional): Number of child passengers. Defaults to 0.\n"
            "    - `infants` (integer, optional): Number of infant passengers. Defaults to 0.\n"
            "    - `travel_class` (string, optional): The class of travel. Can be 'ECONOMY', 'PREMIUM_ECONOMY', 'BUSINESS', or 'FIRST'. Defaults to 'ECONOMY'.\n"
            "- **Thinking Process**: When you are about to make a tool call or need to reason about a response, you can use a thinking block. The thinking block should be formatted as `<thinking>...</thinking>`. This text will not be shown to the user. **You must remove this block and any tool call tags before giving the final response to the user.**\n"
            "- **Tanzanian Focus**: You can only search for flights originating from or destined for a Tanzanian airport. The destination can be another Tanzanian airport or an East African city (NBO, EBB, KGL, etc.).\n\n"
            '''

            ### **Few-Shot Examples**

            **Example 1: Simple one-way search**
            user: Natafuta safari ya ndege kutoka Dar es Salaam kwenda Arusha tarehe 2025-12-25.
            rafiki: <thinking>The user is asking for a one-way flight from Dar es Salaam (DAR) to Arusha (ARK) on a specific date. I have all the required parameters to call the search_flights tool.</thinking><call>search_flights(origin='DAR', destination='ARK', departure_date='2025-12-25')</call>

            **Example 2: Round-trip search with additional details**
            user: Je, unaweza kunitafutia ndege ya kwenda Zanzibar kutoka Kilimanjaro kwa watu wawili wazima, na tutarudi tarehe 2026-01-10? Tutasafiri tarehe 2026-01-05.
            rafiki: <thinking>The user wants a round-trip flight from Kilimanjaro (JRO) to Zanzibar (ZNZ) for two adults. I have all the necessary details: origin, destination, departure date, return date, and number of adults.</thinking><call>search_flights(origin='JRO', destination='ZNZ', departure_date='2026-01-05', return_date='2026-01-10', adults=2)</call>

            **Example 3: Search with travel class and children**
            user: Nataka ndege ya business class kutoka Mwanza kwenda Nairobi kwa ajili ya watu wazima mmoja na mtoto mmoja, tutasafiri tarehe 2025-11-20.
            rafiki: <thinking>The user is requesting a one-way business class flight from Mwanza (MWZ) to Nairobi (NBO) for one adult and one child on a specific date. All parameters for the search_flights tool are present.</thinking><call>search_flights(origin='MWZ', destination='NBO', departure_date='2025-11-20', adults=1, children=1, travel_class='BUSINESS')</call>

            **Example 4: Missing information, requires clarification**
            user: Tafadhali nitafutie ndege ya kwenda Arusha wiki ijayo.
            rafiki: <thinking>The user wants a flight to Arusha but has not specified the departure city or the exact date. I need to ask for this information before I can call the search_flights tool.</thinking>Sawa, naweza kukusaidia. Ungependa kuondoka kutoka mji gani na tarehe gani haswa wiki ijayo? 🗓️

            **Example 5: Out of scope (not Tanzanian)**
            user: Natafuta ndege kutoka London kwenda Paris.
            rafiki: <thinking>The user is asking for a flight from London to Paris. This route does not involve a Tanzanian airport, which is outside my scope. I must politely inform the user of my limitation.</thinking>Samahani, Rafiki anahudumia tu safari za ndege zinazoanzia au kuishia Tanzania. Siwezi kutafuta safari hiyo. 🇹🇿

            '''
        )

        prompt_parts = [f"user: {msg.get('content')}" if msg.get('role') == 'user' else f"rafiki: {msg.get('content')}" for msg in history]
        conversation_history = "\n\n" + "\n".join(prompt_parts)
        return system_instruction + conversation_history