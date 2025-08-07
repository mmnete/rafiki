from app.services.conversation_service import ConversationService
from app.services.prompt_service import PromptService
from app.services.user_service import FakeUserService # Assuming this is the updated one
import re
from app.services.gemini_service import GeminiService

class ConversationManager:
    def __init__(self):
        self.user_service = FakeUserService()
        self.prompt_service = PromptService()
        self.gemini_service = GeminiService()
        self.conversation_service = ConversationService()
        
    def handle_message(self, phone_number, user_message):
        user_message = user_message.strip()
        
        # Get or create user, and check for phone number validity
        user, error_message = self.user_service.get_or_create_user(phone_number)
        
        # If the phone number is invalid, return the error message immediately
        if error_message:
            return error_message

        # --- Onboarding Greet Logic (Initial message for brand new users) ---
        if user.status == "onboarding_greet":
            self.user_service.update_user_status(phone_number, "onboarding_greeted")
            # The prompt service will provide the long introductory message for 'onboarding_greeted' status
            return self.prompt_service.build_prompt(self.conversation_service.get_conversation(phone_number), user)

        # --- Onboarding Name Capture Logic (After greeting, or after invalid name) ---
        # This handles both the first attempt after greeting (onboarding_greeted)
        # and subsequent attempts if the name format is incorrect (onboarding_name)
        if user.status == "onboarding_greeted" or user.status == "onboarding_name":
            # This regex is more flexible, allowing for 2 or 3 names and less strict capitalization.
            # It captures the first and last words as the primary name parts.
            # Example: "Juma Hassan", "Peter Joshua Mwangi"
            match = re.match(r"(\w+)\s+(\w+)(?:\s+(\w+))?", user_message, re.IGNORECASE)

            if match:
                first_name = match.group(1)
                # If a third word exists, use it as the last name. Otherwise, use the second word.
                last_name = match.group(3) if match.group(3) else match.group(2)
                
                # Capitalize names for consistency before storing
                first_name = first_name.capitalize()
                last_name = last_name.capitalize()
                
                self.user_service.update_user_details(phone_number, first_name=first_name, last_name=last_name)
                self.user_service.update_user_status(phone_number, "onboarding_confirm_name")
                self.conversation_service.update_conversation(phone_number, {"role": "user", "content": user_message})
                return self.prompt_service.build_prompt(self.conversation_service.get_conversation(phone_number), user)
            else:
                # If the name format is incorrect, update status to 'onboarding_name'
                # and prompt again using the concise retry message.
                self.user_service.update_user_status(phone_number, "onboarding_name")
                return self.prompt_service.build_prompt(self.conversation_service.get_conversation(phone_number), user)

        # --- Onboarding Confirmation Name Logic ---
        elif user.status == "onboarding_confirm_name":
            if user_message.lower() in ["ndio", "yes"]:
                self.user_service.update_user_status(phone_number, "onboarding_location")
                self.conversation_service.update_conversation(phone_number, {"role": "user", "content": user_message})
                return self.prompt_service.build_prompt(self.conversation_service.get_conversation(phone_number), user)
            elif user_message.lower() in ["hapana", "no"]:
                self.user_service.update_user_status(phone_number, "onboarding_name") # Go back to name input
                self.conversation_service.update_conversation(phone_number, {"role": "user", "content": user_message})
                return self.prompt_service.build_prompt(self.conversation_service.get_conversation(phone_number), user)
            else:
                return "Tafadhali jibu 'Ndio' au 'Hapana'."

        # --- Onboarding Location Capture Logic ---
        elif user.status == "onboarding_location":
            self.user_service.update_user_details(phone_number, location=user_message.title())
            self.user_service.update_user_status(phone_number, "onboarding_confirm_location")
            self.conversation_service.update_conversation(phone_number, {"role": "user", "content": user_message})
            return self.prompt_service.build_prompt(self.conversation_service.get_conversation(phone_number), user)

        # --- Onboarding Confirmation Location Logic ---
        elif user.status == "onboarding_confirm_location":
            if user_message.lower() in ["ndio", "yes"]:
                self.user_service.update_user_status(phone_number, "active")
                self.conversation_service.update_conversation(phone_number, {"role": "user", "content": user_message})
                return f"Asante {user.first_name}! Sasa unaweza kuanza kutafuta safari za ndege. Uko tayari kuanza? 😄"
            elif user_message.lower() in ["hapana", "no"]:
                self.user_service.update_user_status(phone_number, "onboarding_location") # Go back to location input
                self.conversation_service.update_conversation(phone_number, {"role": "user", "content": user_message})
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
            gemini_response_text = self.gemini_service.ask_gemini(prompt)

            # 5. Add Rafiki's reply to the conversation history
            # gemini_response is an object. You need to store the text content.
            self.conversation_service.update_conversation(phone_number, {"role": "rafiki", "content": gemini_response_text})
            
            # 6. Return the final text response to the user
            # The placeholder return was bypassing the Gemini call
            return gemini_response_text
        
        # Fallback for any other status, though this should not be reached
        return "Samahani, kuna tatizo. Tafadhali jaribu tena baadaye."