import datetime
from app.services.user_service import User
from app.tools.toolcall_config import get_tool_manager
from datetime import datetime

class PromptService:
    def __init__(self):
        self.tool_manager = get_tool_manager()
        
    def build_prompt(self, history: list, user: User, new_message = "") -> str:
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
        elif user_status == "repeat_onboarding_location":
            return self._build_onboarding_location_prompt(repeated=True)
        elif user_status == "onboarding_confirm_location":
            return self._build_confirm_location_prompt(user)
        elif user_status == "active":
            return self._build_main_prompt(history, user, new_message)
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
            "Tafadhali tupe jina lako kamili, la kwanza na la mwisho. Linapaswa kuwa na maneno mawili au matatu.\n\n"
            "Mfano (Example):\n"
            "✅ **Morgan Mnete**\n"
            "✅ **Peter Joshua Mwangi**\n"
        )

    def _build_confirm_name_prompt(self, user: User) -> str:
        return (
            f"Asante {user.first_name} {user.last_name}! Je, hili ndilo jina sahihi? "
            "Tafadhali jibu 'Ndio' au 'Hapana'."
        )

    def _build_onboarding_location_prompt(self, repeated=False) -> str:
        if repeated:
            return (
                "Samahani, sijaelewa. Tafadhali tafadhali nipe jina sahihi la mji au mkoa unaoishi hapa Tanzania. "
                "Kwa mfano: Dar es Salaam, Arusha, au Mbeya."
            )
        return (
            "Vizuri! Sasa, ili nikuhudumie vizuri, naomba unipe jina la mji au jina la mkoa unaoishi hapa Tanzania."
        )


    def _build_confirm_location_prompt(self, user: User) -> str:
        return (
            f"Je, unaishi {user.location}? Tafadhali jibu 'Ndio' au 'Hapana'."
        )

    def _build_main_prompt(self, history: list, user: User, new_message = "") -> str:
        # The prompt for an active user, as defined in previous examples
        user_name = f"{user.first_name} {user.last_name}" if user.first_name and user.last_name else "Mteja"
        user_location = (user.location if user.location else "Tanzania") + " Tanzania"
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        context_string = (
            f"User Context:\n"
            f"User Name: {user_name}\n"
            f"User Saved Location (May not be current): {user_location}\n\n"
            f"Current Time: {current_time}\n"
        )
        
        previous_messages = [
            f"user: {msg.request}\n rafiki: {msg.response}"
            for msg in history
        ]

        conversation_history = "\n\n" + "\n".join(previous_messages)
        
        # Generate tool instructions and examples dynamically
        tool_instructions = self.tool_manager.get_tool_instructions()
        tool_examples = self.tool_manager.get_examples()
        
        # Build complete system instruction
        system_instruction = f"""
        Current conversation:
        {conversation_history}

        **System Instructions:**
        
        YOU MUST FOLLOW THE INSTRUCTIONS BELOW

        You are Rafiki, a friendly and helpful digital assistant for Tanzanians using WhatsApp. Your purpose is to assist users with various services including flights, hotels, and other travel-related bookings. Adhere to the following guidelines strictly.

        The conversation may be continuous, exploratory, or direct. If the user gives specific details then make sure to follow those but if the user is exploring try your best to explore with them and be helpful based on the tools you are provided. Be friendly too.

        {context_string}

        {tool_instructions}

        {tool_examples}
        
        user: {new_message}
        
        There is a strict 1600 character limit in your final response!

        """
        
        return system_instruction
