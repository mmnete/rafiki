from app.services.conversation_service import ConversationService
from app.services.prompt_service import PromptService
from app.services.user_service import FakeUserService # Assuming this is the updated one
import re
from app.services.gemini_service import GeminiService
from app.services.flight_scraper import AmadeusFlightScraper
from app.storage.in_memory import InMemoryStorage

def search_flights_tool_wrapper(**kwargs):
    scraper = AmadeusFlightScraper()
    return scraper.search_flights(**kwargs)

class ConversationManager:
    def __init__(self):
        self.shared_storage = InMemoryStorage()
        self.user_service = FakeUserService(storage=self.shared_storage)
        self.prompt_service = PromptService()
        self.gemini_service = GeminiService()
        self.conversation_service = ConversationService(storage=self.shared_storage)
        
    def handle_message(self, phone_number, user_message):
        user_message = user_message.strip()
        
        # 1. Get or create user and check for phone number validity.
        user, error_message = self.user_service.get_or_create_user(phone_number)
        if error_message:
            return error_message

        # A robust way to manage state is to handle each status in a distinct block.
        # This prevents logic from "falling through" to the wrong state.

        # --- Onboarding Greet Logic (Initial message for brand new users) ---
        if user.status == "onboarding_greet":
            # Update user status to signal that the initial long greeting has been sent.
            user = self.user_service.update_user_status(phone_number, "onboarding_greeted")
            return self.prompt_service.build_prompt(self.conversation_service.get_conversation(phone_number), user)

        # --- Onboarding Name Capture Logic ---
        elif user.status in ["onboarding_greeted", "onboarding_name"]:
            name_parts = user_message.strip().split()

            if len(name_parts) >= 2:
                first_name = name_parts[0].capitalize()
                last_name = name_parts[-1].capitalize()
                middle_name = " ".join(name_parts[1:-1]).capitalize() if len(name_parts) > 2 else None

                self.user_service.update_user_details(
                    phone_number,
                    first_name=first_name,
                    middle_name=middle_name,
                    last_name=last_name
                )
                self.conversation_service.update_conversation(
                    phone_number, {"role": "user", "content": user_message}
                )
                user = self.user_service.update_user_status(phone_number, "onboarding_confirm_name")
                return self.prompt_service.build_prompt(
                    self.conversation_service.get_conversation(phone_number), user
                )
            else:
                user = self.user_service.update_user_status(phone_number, "onboarding_name")
                return self.prompt_service.build_prompt(
                    self.conversation_service.get_conversation(phone_number), user
                )

        # --- Onboarding Name Confirmation Logic ---
        elif user.status == "onboarding_confirm_name":
            self.conversation_service.update_conversation(
                phone_number, {"role": "user", "content": user_message}
            )

            response = user_message.strip().lower()
            yes_responses = {"ndio", "ndiyo", "yes", "yeah", "yep", "nd"}
            no_responses = {"hapana", "no", "nope"}

            if response in yes_responses:
                user = self.user_service.update_user_status(phone_number, "onboarding_location")
            elif response in no_responses:
                user = self.user_service.update_user_status(phone_number, "onboarding_name")
            else:
                return "Tafadhali jibu kwa 'Ndio' au 'Hapana'."

            return self.prompt_service.build_prompt(
                self.conversation_service.get_conversation(phone_number), user
            )


        # --- Onboarding Location Capture Logic ---
        elif user.status == "onboarding_location" or user.status == "repeat_onboarding_location":
            self.user_service.update_user_details(phone_number, location=user_message.strip().lower())
            self.conversation_service.update_conversation(phone_number, {"role": "user", "content": user_message.strip().lower()})
            
            user = self.user_service.update_user_status(phone_number, "onboarding_confirm_location")
            return self.prompt_service.build_prompt(self.conversation_service.get_conversation(phone_number), user)

        # --- Onboarding Location Confirmation Logic ---
        elif user.status == "onboarding_confirm_location":
            self.conversation_service.update_conversation(phone_number, {"role": "user", "content": user_message})
            
            response = user_message.strip().lower()
            yes_responses = {"ndio", "ndiyo", "yes", "yeah", "yep", "nd"}
            no_responses = {"hapana", "no", "nope"}
            
            if response in yes_responses:
                user = self.user_service.update_user_status(phone_number, "active")
                return f"Asante {user.first_name}! Sasa unaweza kuanza kutafuta safari za ndege. Uko tayari kuanza? 😄 Uliza chochote kile?"
            elif response in no_responses:
                user = self.user_service.update_user_status(phone_number, "repeat_onboarding_location")
                return self.prompt_service.build_prompt(self.conversation_service.get_conversation(phone_number), user)
            else:
                return "Tafadhali jibu 'Ndio' au 'Hapana'."
        
        # --- Active User Logic ---
        if user.status == "active":
            # 1. Get the conversation history for the user
            history = self.conversation_service.get_conversation(phone_number)
            
            # 2. Add the user's new message to the history
            history.append({"role": "user", "content": user_message})
            self.conversation_service.update_conversation(phone_number, {"role": "user", "content": user_message})

            # 3. Build the prompt using the full conversation history and user info
            prompt = self.prompt_service.build_prompt(history, user)
            
            # 4. Call the Gemini service to get a response
            # gemini_model is not defined. You must use the instantiated self.gemini_service
            tools_for_gemini = {"search_flights": search_flights_tool_wrapper}
            final_reply, gemini_all_messages = self.gemini_service.ask_gemini(prompt, tools_for_gemini)

            # Save all model interactions (tool steps, etc.)
            for message in gemini_all_messages:
                self.conversation_service.update_conversation(phone_number, {"role": "rafiki", "content": message})
            
            # 6. Return the final text response to the user
            # The placeholder return was bypassing the Gemini call
            return final_reply
        
        # Fallback for any other status, though this should not be reached
        return "Samahani, kuna tatizo. Tafadhali jaribu tena baadaye."