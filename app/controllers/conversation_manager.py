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
        user, error_message = self.user_service.get_or_create_user(phone_number)

        if error_message:
            return error_message

        status = user.status
        conversation = self.conversation_service.get_conversation(phone_number)

        # --- Onboarding Greet Logic ---
        if status == "onboarding_greet":
            prompt = self.prompt_service.build_prompt(conversation, user)
            self.user_service.update_user_status(phone_number, "onboarding_greeted")
            return prompt

        # --- Name Capture ---
        if status in ["onboarding_greeted", "onboarding_name"]:
            match = re.match(r"(\w+)\s+(\w+)(?:\s+(\w+))?", user_message, re.IGNORECASE)
            if match:
                first_name = match.group(1).capitalize()
                last_name = (match.group(3) if match.group(3) else match.group(2)).capitalize()
                self.user_service.update_user_details(phone_number, first_name=first_name, last_name=last_name)
                self.conversation_service.update_conversation(phone_number, {"role": "user", "content": user_message})
                prompt = self.prompt_service.build_prompt(conversation, user)
                self.user_service.update_user_status(phone_number, "onboarding_confirm_name")
                return prompt
            else:
                self.user_service.update_user_status(phone_number, "onboarding_name")
                return self.prompt_service.build_prompt(conversation, user)

        # --- Confirm Name ---
        if status == "onboarding_confirm_name":
            if user_message.lower() in ["ndio", "yes"]:
                self.user_service.update_user_status(phone_number, "onboarding_location")
            elif user_message.lower() in ["hapana", "no"]:
                self.user_service.update_user_status(phone_number, "onboarding_name")
            else:
                return "Tafadhali jibu 'Ndio' au 'Hapana'."
            self.conversation_service.update_conversation(phone_number, {"role": "user", "content": user_message})
            return self.prompt_service.build_prompt(conversation, user)

        # --- Capture Location ---
        if status == "onboarding_location":
            self.user_service.update_user_details(phone_number, location=user_message.title())
            self.conversation_service.update_conversation(phone_number, {"role": "user", "content": user_message})
            prompt = self.prompt_service.build_prompt(conversation, user)
            self.user_service.update_user_status(phone_number, "onboarding_confirm_location")
            return prompt

        # --- Confirm Location ---
        if status == "onboarding_confirm_location":
            if user_message.lower() in ["ndio", "yes"]:
                self.user_service.update_user_status(phone_number, "active")
                self.conversation_service.update_conversation(phone_number, {"role": "user", "content": user_message})
                return f"Asante {user.first_name}! Sasa unaweza kuanza kutafuta safari za ndege. Uko tayari kuanza? 😄"
            elif user_message.lower() in ["hapana", "no"]:
                self.user_service.update_user_status(phone_number, "onboarding_location")
                self.conversation_service.update_conversation(phone_number, {"role": "user", "content": user_message})
                return self.prompt_service.build_prompt(conversation, user)
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