from app.services.conversation_service import ConversationService
from app.services.prompt_service import PromptService
from app.services.user_service import FakeUserService # Assuming this is the updated one
import re
from app.services.gemini_service import EnhancedGeminiService
from app.storage.db_service import StorageService
from app.tools.location_standardizer import LocationOnboardingHandler
import random

class ConversationManager:
    YES_RESPONSES = {"ndio", "ndiyo", "yes", "yeah", "yep", "nd",
                     "yess", "yea", "yaa", "yup", "yee", "ydi", "ndi", "ndy"}

    NO_RESPONSES = {"hapana", "no", "nope",
                    "nop", "na", "nap", "np", "hapan", "hapn"}
    
     # Encouraging messages for long-running processes
    THINKING_MESSAGES = [
        # Standard thinking messages
        "Nafikiri... Nitakujibu hivi karibuni! 🤔✨",
        "Subiri kidogo, naandaa jibu lako... 💭",
        "Nimesikia! Nafikiri kuhusu hili... 🧠",
        "Just a moment, preparing your response... 💭",
        "Processing your message... ⏳",
        "Working on your answer... 📝",
        
        # Rafiki introduction messages
        "Mimi ni Rafiki, msaidizi wako wa AI kutoka Afrika! Nafikiri kuhusu swali lako... 🌍✨",
        "I'm Rafiki, your AI assistant built for Africa! Let me think about this... 🤖🌍",
        "Rafiki hapa! Msaidizi wako wa kila siku. Nafikiri jinsi ya kukusaidia... 💡",
        "Hi! I'm Rafiki, always here to help. Processing your request... 🤝",
        
        # Flight booking promotion
        "Nafikiri... Pia, najua umejua kwamba ninaweza kukusaidia kupanga safari za anga Tanzania? ✈️🇹🇿",
        "Thinking... By the way, I can help you explore and book flights to Tanzania! ✈️💫",
        "Subiri kidogo... Je, umejua ninaweza kukusaidia na tiketi za ndege kwenda Tanzania? 🛫🌍",
        "Processing... Did you know I specialize in Tanzania flight bookings? ✈️📍",
        "Nafikiri... Rafiki anaweza kukusaidia kupata tiketi za ndege bora za Tanzania! 🎫✨",
        "Just a sec... I'm also here to help with your Tanzania travel plans! 🗺️✈️",
        
        # Service promotion
        "Naandaa jibu... Rafiki ni msaidizi wako wa AI, daima tayari kukusaidia! 🤖💪",
        "Thinking... Rafiki is built by Africans, for Africa - always here for you! 🌍❤️",
        "Nafikiri... Kumbuka, Rafiki yuko hapa kila wakati kukusaidia! 24/7 📞",
        "Processing... Your African AI assistant Rafiki is working on it! 🇹🇿🤖",
        "Subiri, nafikiri... Rafiki - rafiki wako wa kweli katika safari na maisha! 🌟",
        "Hold on... Rafiki makes exploring Africa easier, starting with Tanzania flights! 🛫🌍",
        
        # Helpful/encouraging messages
        "Dakika moja... Rafiki anatafuta njia bora ya kukusaidia! 🔍💡",
        "Almost there... Rafiki is connecting you to the best solutions! 🔗✨",
        "Nafikiri kwa bidii... Your African AI companion is on it! 💪🌍",
        "Working hard for you... Rafiki hakuachi, daima anasaidia! 🚀",
        "Karibu tayari... Rafiki - more than AI, ni rafiki wako wa kweli! 🤝💫"
    ]
        
    STILL_THINKING_MESSAGES = [
        "Bado nafikiri kuhusu swali lako la awali... Tafadhali subiri kidogo. 🤔",
        "Ninashughulika na maombi yako ya mwanzo. Subiri kidogo tafadhali... ⏳",
        "Bado ninakusanyisha majibu yako. Haitachukua muda mrefu! 💭",
        "Usijali {first_name}... subiri kidogo nipo nakusaidia hapa! 😊",
        "Pole {first_name}, bado ninafanya kazi... Hivi karibuni nitakujibu! 🚀",
        "Usijali {first_name}... ninakusanyisha majibu mazuri kwako! ✨",
        "Subiri tu kidogo {first_name}... ninakuhakikishia majibu bora! 💪"
    ]
            
    def __init__(self, test_mode=False):
        self.test_mode = test_mode  # Add test mode flag
        self.location_handler = LocationOnboardingHandler()
        self.shared_storage = StorageService()
        self.user_service = FakeUserService(storage=self.shared_storage)
        self.prompt_service = PromptService()
        self.gemini_service = EnhancedGeminiService()
        self.conversation_service = ConversationService(storage=self.shared_storage)
        self.test_responses = []  # Store responses for testing
    
    def delete_all_users(self):
        self.user_service.delete_all_users()
    
    def get_thinking_message(self):
        """Get a random thinking message for immediate response"""
        return random.choice(self.THINKING_MESSAGES)
    
    def get_still_thinking_message(self, phone_number):
        """Get a personalized 'still thinking' message"""
        try:
            user, _ = self.user_service.get_or_create_user(phone_number)
            first_name = user.first_name if user and user.first_name else ""
            
            # Choose messages that can be personalized if we have a name
            if first_name:
                personalizable_messages = [msg for msg in self.STILL_THINKING_MESSAGES if "{first_name}" in msg]
                if personalizable_messages:
                    return random.choice(personalizable_messages).format(first_name=first_name)
            
            # Fallback to non-personalized messages
            non_personal_messages = [msg for msg in self.STILL_THINKING_MESSAGES if "{first_name}" not in msg]
            return random.choice(non_personal_messages)
            
        except:
            return "Bado nafikiri kuhusu swali lako la awali... Tafadhali subiri kidogo. 🤔"
    
    def get_quick_response(self, phone_number, user_message):
        """Handle quick responses that don't need AI processing"""
        try:
            user_message_lower = user_message.lower().strip()
            
            # Get user
            user, _ = self.user_service.get_or_create_user(phone_number)
            if not user:
                return None
            
            # Onboarding states always need AI
            onboarding_states = {
                "onboarding_greet", "onboarding_greeted", "onboarding_name",
                "onboarding_confirm_name", "onboarding_location",
                "repeat_onboarding_location", "onboarding_confirm_location"
            }
            if user.status in onboarding_states:
                return None
            
            if user.status == "active":
                greetings = {
                    # Swahili
                    "hujambo", "mambo", "habari", "habari yako", "habari gani", "salamu", "shikamoo",
                    "vipi", "mambo vipi", "hujambo sana", "salamu za mchana", "asubuhi njema",
                    "mchana mwema", "jioni njema",
                    # English
                    "hello", "hi", "hey", "good morning", "good afternoon", "good evening", "how are you",
                    "howdy", "greetings", "hiya"
                }

                thanks = {
                    # Swahili
                    "asante", "ahsante", "asanteni", "asante sana", "ahsante sana", "shukrani", "shukran",
                    "namshukuru", "nashukuru",
                    # English
                    "thank you", "thanks", "many thanks", "thanks a lot", "thanks so much", "thx",
                    "ty", "much appreciated", "appreciate it", "cheers"
                }

                confirmations = {
                    # Swahili
                    "sawa", "poa", "poa sana", "nzuri", "ndiyo", "ndio", "basi", "sawa kabisa", "hakuna shida",
                    # English
                    "ok", "okay", "alright", "fine", "cool", "all good", "no problem", "sure", "yep", "yeah", "yes"
                }

                help_keywords = {
                    # Swahili
                    "msaada", "nisaidie", "naomba msaada", "naomba unisaidie", "tafadhali nisaidie",
                    "tafadhali msaada", "nisaidie tafadhali", "nisaidie tafadhari",
                    # English
                    "help", "assist me", "i need help", "please help", "can you help", "help me", "help please"
                }

                travel_keywords = {
                    # Swahili
                    "ndege", "tiketi", "tiketi ya ndege", "nenda", "safari", "nafasi", "ratiba", "usafiri", "nauli",
                    "kuhifadhi", "kukata tiketi", "kuhifadhi tiketi", "kusafiri", "bandarini", "urejeo",
                    # English
                    "flight", "flights", "ticket", "tickets", "book", "booking", "reserve", "reservation",
                    "travel", "trip", "journey", "itinerary", "fare", "schedule", "boarding", "departure", "return"
                }

                
                words = set(user_message_lower.replace(",", "").replace(".", "").split())
                word_count = len(words)
                
                # --- Rule 1: Message length check ---
                if word_count > 3:
                    # If contains greeting/help + travel → complex → needs AI
                    if (words & greetings or words & help_keywords) and (words & travel_keywords):
                        return None
                
                # --- Rule 2: Pure match check ---
                if user_message_lower in greetings:
                    return f"Hujambo {user.first_name}! 😊 Naweza kukusaidia namna gani leo? Unataka kutafuta safari za ndege?"
                if user_message_lower in thanks:
                    return f"Karibu sana {user.first_name}! 😊 Je, kuna kitu kingine unachohitaji?"
                if user_message_lower in confirmations:
                    return f"Vizuri {user.first_name}! 👍 Naweza kukusaidia kitu kingine?"
                if user_message_lower in help_keywords:
                    return f"Bila shaka {user.first_name}! Naweza kukusaidia kutafuta safari za ndege. Niambie unataka kwenda wapi na lini? ✈️"
            
            return None  # Needs full AI processing
        
        except Exception:
            return None

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
