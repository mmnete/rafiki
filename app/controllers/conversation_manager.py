from app.services.conversation_service import ConversationService
from app.services.prompt_service import PromptService
from app.services.user_service import FakeUserService # Assuming this is the updated one
import re
from app.services.gemini_service import GeminiService
from app.services.flight_scraper import AmadeusFlightScraper

def search_flights_tool_wrapper(**kwargs):
    scraper = AmadeusFlightScraper()
    return scraper.search_flights(**kwargs)

class ConversationManager:
    def __init__(self):
        self.user_service = FakeUserService()
        self.prompt_service = PromptService()
        self.gemini_service = GeminiService()
        self.conversation_service = ConversationService()
        
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
        # This block handles both the initial attempt after the greeting and failed attempts.
        elif user.status in ["onboarding_greeted", "onboarding_name"]:
            match = re.match(r"(\w+)\s+(\w+)(?:\s+(\w+))?", user_message, re.IGNORECASE)
            
            if match:
                first_name = match.group(1).capitalize()
                last_name_raw = match.group(3) if match.group(3) else match.group(2)
                last_name = last_name_raw.capitalize()
                
                self.user_service.update_user_details(phone_number, first_name=first_name, last_name=last_name)
                self.conversation_service.update_conversation(phone_number, {"role": "user", "content": user_message})
                
                # Update status and get the new user object for the next prompt.
                user = self.user_service.update_user_status(phone_number, "onboarding_confirm_name")
                return self.prompt_service.build_prompt(self.conversation_service.get_conversation(phone_number), user)
            else:
                # If the name format is incorrect, update status for the retry prompt.
                user = self.user_service.update_user_status(phone_number, "onboarding_name")
                return self.prompt_service.build_prompt(self.conversation_service.get_conversation(phone_number), user)

        # --- Onboarding Name Confirmation Logic ---
        elif user.status == "onboarding_confirm_name":
            self.conversation_service.update_conversation(phone_number, {"role": "user", "content": user_message})
            
            if user_message.lower() in ["ndio", "yes"]:
                user = self.user_service.update_user_status(phone_number, "onboarding_location")
            elif user_message.lower() in ["hapana", "no"]:
                user = self.user_service.update_user_status(phone_number, "onboarding_name")
            else:
                return "Tafadhali jibu 'Ndio' au 'Hapana'."

            return self.prompt_service.build_prompt(self.conversation_service.get_conversation(phone_number), user)

        # --- Onboarding Location Capture Logic ---
        elif user.status == "onboarding_location":
            self.user_service.update_user_details(phone_number, location=user_message.title())
            self.conversation_service.update_conversation(phone_number, {"role": "user", "content": user_message})
            
            user = self.user_service.update_user_status(phone_number, "onboarding_confirm_location")
            return self.prompt_service.build_prompt(self.conversation_service.get_conversation(phone_number), user)

        # --- Onboarding Location Confirmation Logic ---
        elif user.status == "onboarding_confirm_location":
            self.conversation_service.update_conversation(phone_number, {"role": "user", "content": user_message})
            
            if user_message.lower() in ["ndio", "yes"]:
                user = self.user_service.update_user_status(phone_number, "active")
                return f"Asante {user.first_name}! Sasa unaweza kuanza kutafuta safari za ndege. Uko tayari kuanza? 😄"
            elif user_message.lower() in ["hapana", "no"]:
                user = self.user_service.update_user_status(phone_number, "onboarding_location")
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
            gemini_response_text = self.gemini_service.ask_gemini(prompt, tools_for_gemini)

            # 5. Add Rafiki's reply to the conversation history
            # gemini_response is an object. You need to store the text content.
            self.conversation_service.update_conversation(phone_number, {"role": "rafiki", "content": gemini_response_text})
            
            # 6. Return the final text response to the user
            # The placeholder return was bypassing the Gemini call
            return gemini_response_text
        
        # Fallback for any other status, though this should not be reached
        return "Samahani, kuna tatizo. Tafadhali jaribu tena baadaye."