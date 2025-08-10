from app.services.conversation_service import ConversationService
from app.services.prompt_service import PromptService
from app.services.user_service import FakeUserService # Assuming this is the updated one
import re
from app.services.gemini_service import EnhancedGeminiService
from app.storage.db_service import StorageService
from app.tools.location_standardizer import LocationOnboardingHandler


class ConversationManager:
    YES_RESPONSES = {"ndio", "ndiyo", "yes", "yeah", "yep", "nd",
                     "yess", "yea", "yaa", "yup", "yee", "ydi", "ndi", "ndy"}

    NO_RESPONSES = {"hapana", "no", "nope",
                    "nop", "na", "nap", "np", "hapan", "hapn"}
            
    def __init__(self):
        self.location_handler = LocationOnboardingHandler()
        self.shared_storage = StorageService()
        self.user_service = FakeUserService(storage=self.shared_storage)
        self.prompt_service = PromptService()
        self.gemini_service = EnhancedGeminiService()
        self.conversation_service = ConversationService(storage=self.shared_storage)
    
    def delete_all_users(self):
        self.user_service.delete_all_users()
        
    def handle_message(self, phone_number, user_message):
        user_message = user_message.strip()
        model_response = ""
        
        # 1. Get or create user and check for phone number validity.
        user, error_message = self.user_service.get_or_create_user(phone_number)
        if error_message or user == None:
            model_response = error_message
        elif user.status == "onboarding_greet":
            # Update user status to signal that the initial long greeting has been sent.
            user = self.user_service.update_user_status(phone_number, "onboarding_greeted")
            model_response = self.prompt_service.build_prompt(self.conversation_service.get_conversation(phone_number), user)
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
                user = self.user_service.update_user_status(phone_number, "onboarding_confirm_name")
                model_response = self.prompt_service.build_prompt(
                    self.conversation_service.get_conversation(phone_number), user
                )
            else:
                user = self.user_service.update_user_status(phone_number, "onboarding_name")
                model_response = self.prompt_service.build_prompt(
                    self.conversation_service.get_conversation(phone_number), user
                )
        elif user.status == "onboarding_confirm_name":
            response = user_message.strip().lower()

            if response in self.YES_RESPONSES:
                user = self.user_service.update_user_status(phone_number, "onboarding_location")
                model_response = self.prompt_service.build_prompt(
                    self.conversation_service.get_conversation(phone_number), user
                )
            elif response in self.NO_RESPONSES:
                user = self.user_service.update_user_status(phone_number, "onboarding_name")
                model_response = self.prompt_service.build_prompt(
                    self.conversation_service.get_conversation(phone_number), user
                )
            else:
                model_response = "Tafadhali jibu kwa 'Ndio' au 'Hapana'."
        elif user.status == "onboarding_location":
            response, new_status = self.location_handler.handle_location_input(user_message)
            user = self.user_service.update_user_status(phone_number, new_status)
            model_response = response
            
        elif user.status == "repeat_onboarding_location":
            response, new_status = self.location_handler.handle_location_input(user_message)
            user = self.user_service.update_user_status(phone_number, new_status)
            model_response = response
            
        elif user.status == "onboarding_confirm_location":
            response = user_message.strip().lower()
            
            if response in self.YES_RESPONSES:
                user = self.user_service.update_user_status(phone_number, "active")
                
                # Get the standardized location for personalized message
                user_location = user.location if user.location else "Tanzania"
                model_response = f"Asante {user.first_name}! Umesajiliwa kutoka *{user_location}*. 🎉\n\nSasa unaweza kuanza kutafuta safari za ndege. Uko tayari kuanza? ✈️\n\nUliza chochote kile unachohitaji!"
                
            elif response in self.NO_RESPONSES:
                # Reset to ask for location again
                user = self.user_service.update_user_status(phone_number, "repeat_onboarding_location")
                model_response = "Sawa, tafadhali niambie tena ni mji gani wa Tanzania unapoishi?\n\nKwa mfano: *Dar es Salaam*, *Arusha*, *Mwanza*, *Zanzibar*, n.k."
                
            else:
                model_response = "Tafadhali jibu 'Ndio' ikiwa jina la mji ni sahihi, au 'Hapana' ikiwa sio sahihi. 😊"
        elif user.status == "active":
            # 1. Get the conversation history for the user
            history = self.conversation_service.get_conversation(phone_number)

            # 3. Build the prompt using the full conversation history and user info
            prompt = self.prompt_service.build_prompt(history, user, user_message)
            
            final_reply,_ = self.gemini_service.ask_gemini(prompt)
            
            # 6. Return the final text response to the user
            # The placeholder return was bypassing the Gemini call
            model_response = final_reply
        else:
            model_response = "Samahani, kuna tatizo. Tafadhali jaribu tena baadaye."
        
        self.conversation_service.update_conversation(phone_number, user_message, model_response)
        return model_response
