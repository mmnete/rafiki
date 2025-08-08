from typing import Any
import unittest
from unittest.mock import MagicMock, call
import re

# Assuming ConversationManager and its dependencies are in the same directory or accessible
from app.controllers.conversation_manager import ConversationManager
from app.services.user_service import User # You may need to create a User class for this test
from app.services.conversation_service import ConversationService
from app.services.prompt_service import PromptService
from app.services.gemini_service import GeminiService

class TestConversationManager(unittest.TestCase):

    def setUp(self):
        """Set up mock objects and the ConversationManager instance before each test."""
        
        # We don't need a real User class, just a mock with a 'status' attribute
        self.mock_user = MagicMock(spec=User)
        self.mock_user.phone_number = "+255712345678"
        self.mock_user.first_name = "Morgan"
        self.mock_user.last_name = "Mnete"
        self.mock_user.location = "Dar es Salaam"

        # Mock all external dependencies
        self.mock_user_service = MagicMock()
        self.mock_prompt_service = MagicMock()
        self.mock_gemini_service = MagicMock()
        self.mock_conversation_service = MagicMock()

        # Instantiate ConversationManager with the mock dependencies
        self.manager = ConversationManager()
        self.manager.user_service = self.mock_user_service
        self.manager.prompt_service = self.mock_prompt_service
        self.manager.gemini_service = self.mock_gemini_service
        self.manager.conversation_service = self.mock_conversation_service

    # ----------------------------------------
    # Test Scenarios for Phone Number Validation
    # ----------------------------------------
    def test_handle_message_with_invalid_phone_number(self):
        """Tests that an invalid phone number returns the correct error message."""
        self.mock_user_service.get_or_create_user.return_value = (None, "Invalid phone number error")
        response = self.manager.handle_message("+15551234567", "hello")
        self.assertIn("Invalid phone number error", response)
        self.mock_user_service.get_or_create_user.assert_called_with("+15551234567")

    # ----------------------------------------
    # Test Scenarios for Onboarding - Name Capture
    # ----------------------------------------
    def test_handle_message_onboarding_greet(self):
        """Tests the initial greeting for a brand new user."""
        self.mock_user.status = "onboarding_greet"
        self.mock_user_service.get_or_create_user.return_value = (self.mock_user, None)
        self.mock_user_service.update_user_status.return_value = self.mock_user
        
        self.mock_prompt_service.build_prompt.return_value = "Long intro prompt"
        response = self.manager.handle_message("+255712345678", "start")
        
        self.assertEqual(response, "Long intro prompt")
        self.mock_user_service.update_user_status.assert_called_once_with("+255712345678", "onboarding_greeted")
        self.mock_prompt_service.build_prompt.assert_called_once()
    
    def test_handle_message_valid_two_word_name(self):
        """Tests a valid two-word name input."""
        self.mock_user.status = "onboarding_greeted"
        self.mock_user_service.get_or_create_user.return_value = (self.mock_user, None)
        self.mock_user_service.update_user_status.return_value = self.mock_user
        self.mock_prompt_service.build_prompt.return_value = "Confirm name prompt"

        response = self.manager.handle_message("+255712345678", "Morgan Mnete")

        self.assertEqual(response, "Confirm name prompt")
        self.mock_user_service.update_user_details.assert_called_once_with(
            "+255712345678", first_name="Morgan", last_name="Mnete"
        )
        self.mock_user_service.update_user_status.assert_called_once_with(
            "+255712345678", "onboarding_confirm_name"
        )
        self.mock_prompt_service.build_prompt.assert_called_once()

    def test_handle_message_valid_three_word_name(self):
        """Tests a valid three-word name input."""
        self.mock_user.status = "onboarding_greeted"
        self.mock_user_service.get_or_create_user.return_value = (self.mock_user, None)
        self.mock_user_service.update_user_status.return_value = self.mock_user
        self.mock_prompt_service.build_prompt.return_value = "Confirm name prompt"

        response = self.manager.handle_message("+255712345678", "Peter Joshua Mwangi")

        self.assertEqual(response, "Confirm name prompt")
        self.mock_user_service.update_user_details.assert_called_once_with(
            "+255712345678", first_name="Peter", last_name="Mwangi"
        )
        self.mock_user_service.update_user_status.assert_called_once_with(
            "+255712345678", "onboarding_confirm_name"
        )

    def test_handle_message_invalid_name(self):
        """Tests an invalid name format, which should lead to a retry prompt."""
        self.mock_user.status = "onboarding_greeted"
        self.mock_user_service.get_or_create_user.return_value = (self.mock_user, None)
        self.mock_user_service.update_user_status.return_value = self.mock_user
        self.mock_prompt_service.build_prompt.return_value = "Repeat name prompt"

        response = self.manager.handle_message("+255712345678", "Morgan")

        self.assertEqual(response, "Repeat name prompt")
        self.mock_user_service.update_user_status.assert_called_once_with("+255712345678", "onboarding_name")
        self.mock_user_service.update_user_details.assert_not_called()

    # ----------------------------------------
    # Test Scenarios for Onboarding - Confirmation
    # ----------------------------------------
    def test_handle_message_confirm_name_yes(self):
        """Tests confirmation of the user's name with 'yes'."""
        self.mock_user.status = "onboarding_confirm_name"
        self.mock_user_service.get_or_create_user.return_value = (self.mock_user, None)
        self.mock_user_service.update_user_status.return_value = self.mock_user
        self.mock_prompt_service.build_prompt.return_value = "Location prompt"

        response = self.manager.handle_message("+255712345678", "yes")

        self.assertEqual(response, "Location prompt")
        self.mock_user_service.update_user_status.assert_called_once_with(
            "+255712345678", "onboarding_location"
        )

    def test_handle_message_confirm_name_no(self):
        """Tests a negative confirmation of the user's name."""
        self.mock_user.status = "onboarding_confirm_name"
        self.mock_user_service.get_or_create_user.return_value = (self.mock_user, None)
        self.mock_user_service.update_user_status.return_value = self.mock_user
        self.mock_prompt_service.build_prompt.return_value = "Name repeat prompt"

        response = self.manager.handle_message("+255712345678", "hapana")
        
        self.assertEqual(response, "Name repeat prompt")
        self.mock_user_service.update_user_status.assert_called_once_with(
            "+255712345678", "onboarding_name"
        )

    def test_handle_message_confirm_name_invalid_response(self):
        """Tests an invalid response to the name confirmation prompt."""
        self.mock_user.status = "onboarding_confirm_name"
        self.mock_user_service.get_or_create_user.return_value = (self.mock_user, None)

        response = self.manager.handle_message("+255712345678", "maybe")

        self.assertEqual(response, "Tafadhali jibu 'Ndio' au 'Hapana'.")
        self.mock_user_service.update_user_status.assert_not_called()

    # ----------------------------------------
    # Test Scenarios for Onboarding - Location
    # ----------------------------------------
    def test_handle_message_onboarding_location_capture(self):
        """Tests capturing a user's location."""
        self.mock_user.status = "onboarding_location"
        self.mock_user_service.get_or_create_user.return_value = (self.mock_user, None)
        self.mock_user_service.update_user_status.return_value = self.mock_user
        self.mock_prompt_service.build_prompt.return_value = "Confirm location prompt"

        response = self.manager.handle_message("+255712345678", "Tanga")

        self.assertEqual(response, "Confirm location prompt")
        self.mock_user_service.update_user_details.assert_called_once_with(
            "+255712345678", location="Tanga"
        )
        self.mock_user_service.update_user_status.assert_called_once_with(
            "+255712345678", "onboarding_confirm_location"
        )
    
    def test_handle_message_confirm_location_yes(self):
        """Tests a positive confirmation of the user's location."""
        self.mock_user.status = "onboarding_confirm_location"
        self.mock_user_service.get_or_create_user.return_value = (self.mock_user, None)
        self.mock_user_service.update_user_status.return_value = self.mock_user

        response = self.manager.handle_message("+255712345678", "ndio")

        self.assertIn("Asante Morgan!", response)
        self.assertIn("Uko tayari kuanza?", response)
        self.mock_user_service.update_user_status.assert_called_once_with(
            "+255712345678", "active"
        )

    def test_handle_message_confirm_location_no(self):
        """Tests a negative confirmation of the user's location."""
        self.mock_user.status = "onboarding_confirm_location"
        self.mock_user_service.get_or_create_user.return_value = (self.mock_user, None)
        self.mock_user_service.update_user_status.return_value = self.mock_user
        self.mock_prompt_service.build_prompt.return_value = "Location prompt"

        response = self.manager.handle_message("+255712345678", "hapana")
        
        self.assertEqual(response, "Location prompt")
        self.mock_user_service.update_user_status.assert_called_once_with(
            "+255712345678", "onboarding_location"
        )

    # ----------------------------------------
    # Test Scenarios for Active User
    # ----------------------------------------
    def test_handle_message_active_user(self):
        """Tests a message from an active user is sent to Gemini."""
        self.mock_user.status = "active"
        self.mock_user_service.get_or_create_user.return_value = (self.mock_user, None)
        self.mock_conversation_service.get_conversation.return_value = [{"role": "user", "content": "previous message"}]
        self.mock_prompt_service.build_prompt.return_value = "Gemini prompt"
        self.mock_gemini_service.ask_gemini.return_value = "Gemini response text"

        response = self.manager.handle_message("+255712345678", "Search for flights to Arusha.")

        self.assertEqual(response, "Gemini response text")
        self.mock_gemini_service.ask_gemini.assert_called()
        self.mock_conversation_service.update_conversation.assert_has_calls([
            call("+255712345678", {"role": "user", "content": "Search for flights to Arusha."}),
            call("+255712345678", {"role": "rafiki", "content": "Gemini response text"})
        ])

if __name__ == '__main__':
    unittest.main()