import unittest
from unittest.mock import MagicMock
import os
import sys

# Add the parent directory to the path to allow imports from `app`
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# We need to import the real GeminiService to test its methods
from app.services.gemini_service import GeminiService

# Mock the environment variable for Amadeus, as it will be used by the scraper
os.environ["AMADEUS_CLIENT_ID"] = "dummy_id"
os.environ["AMADEUS_CLIENT_SECRET"] = "dummy_secret"

class TestGeminiServiceParsing(unittest.TestCase):
    def setUp(self):
        """Set up an instance of GeminiService for testing the parser."""
        # We need to mock the environment variable for Gemini's API key
        os.environ["GEMINI_API_KEY"] = "dummy_key"
        self.gemini_service = GeminiService()

    def tearDown(self):
        """Clean up the environment variable after tests."""
        del os.environ["GEMINI_API_KEY"]

    def test_parse_tool_call_valid_full_call(self):
        """Tests parsing a well-formed tool call with all parameters."""
        gemini_response = "<call>search_flights(origin='DAR', destination='ZNZ', departure_date='2025-12-25', return_date='2026-01-05', adults=2, children=1, infants=0, travel_class='BUSINESS')</call>"
        expected_output = {
            "name": "search_flights",
            "args": {
                "origin": "DAR",
                "destination": "ZNZ",
                "departure_date": "2025-12-25",
                "return_date": "2026-01-05",
                "adults": 2,
                "children": 1,
                "infants": 0,
                "travel_class": "BUSINESS"
            }
        }
        result = self.gemini_service._parse_tool_call(gemini_response)
        self.assertEqual(result, expected_output)

    def test_parse_tool_call_valid_minimum_call(self):
        """Tests parsing a tool call with only required parameters."""
        gemini_response = "<call>search_flights(origin='JRO', destination='NBO', departure_date='2025-08-20')</call>"
        expected_output = {
            "name": "search_flights",
            "args": {
                "origin": "JRO",
                "destination": "NBO",
                "departure_date": "2025-08-20"
            }
        }
        result = self.gemini_service._parse_tool_call(gemini_response)
        self.assertEqual(result, expected_output)

    def test_parse_tool_call_with_thinking_block(self):
        """Tests parsing a tool call embedded in text, including a thinking block."""
        gemini_response = "Sawa, naweza kusaidia. <thinking>User wants flights, I have all the details. I will call the tool now.</thinking><call>search_flights(origin='DAR', destination='ARK', departure_date='2025-10-15')</call> "
        expected_output = {
            "name": "search_flights",
            "args": {
                "origin": "DAR",
                "destination": "ARK",
                "departure_date": "2025-10-15"
            }
        }
        result = self.gemini_service._parse_tool_call(gemini_response)
        self.assertEqual(result, expected_output)
        
    def test_parse_tool_call_invalid_format_no_tags(self):
        """Tests that a malformed response without tags returns None."""
        gemini_response = "search_flights(origin='DAR', destination='ARK', departure_date='2025-10-15')"
        result = self.gemini_service._parse_tool_call(gemini_response)
        self.assertIsNone(result)

    def test_parse_tool_call_invalid_format_empty_call(self):
        """Tests an empty call returns None."""
        gemini_response = "<call></call>"
        result = self.gemini_service._parse_tool_call(gemini_response)
        self.assertIsNone(result)

    def test_parse_tool_call_invalid_format_no_function_name(self):
        """Tests a call with no function name returns None."""
        gemini_response = "<call>(origin='DAR')</call>"
        result = self.gemini_service._parse_tool_call(gemini_response)
        self.assertIsNone(result)

    def test_parse_tool_call_no_call_in_text(self):
        """Tests that a normal text response with no tool call returns None."""
        gemini_response = "Samahani, tarehe ya kuondoka haiwezi kuwa zamani. Tafadhali chagua tarehe ya baadaye."
        result = self.gemini_service._parse_tool_call(gemini_response)
        self.assertIsNone(result)
        
    def test_parse_tool_call_with_different_argument_order(self):
        """Tests that the parser works regardless of argument order."""
        gemini_response = "<call>search_flights(departure_date='2025-10-15', origin='DAR', destination='ARK')</call>"
        expected_output = {
            "name": "search_flights",
            "args": {
                "departure_date": "2025-10-15",
                "origin": "DAR",
                "destination": "ARK"
            }
        }
        result = self.gemini_service._parse_tool_call(gemini_response)
        self.assertEqual(result, expected_output)

if __name__ == '__main__':
    unittest.main()