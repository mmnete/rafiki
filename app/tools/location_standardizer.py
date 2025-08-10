import re
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher
from dataclasses import dataclass

@dataclass
class LocationMatch:
    original_input: str
    standardized_name: str
    confidence: float
    match_type: str  # "exact", "fuzzy", "alias", "partial"
    suggestions: List[str] = None

class TanzanianLocationStandardizer:
    """
    Standardizes Tanzanian city names with fuzzy matching and common variations
    """
    
    def __init__(self):
        # Standard city names (official/preferred names)
        self.STANDARD_CITIES = {
            "dar es salaam": {
                "standard": "Dar es Salaam",
                "aliases": ["dar", "darussalam", "dar-es-salaam", "dares salaam", "dar es salam", 
                           "dar essalam", "dsm", "jiji kubwa", "bongo"],
                "region": "Dar es Salaam",
                "airport_code": "DAR"
            },
            "arusha": {
                "standard": "Arusha",
                "aliases": ["arusha town", "arusha city", "arusha mjini"],
                "region": "Arusha",
                "airport_code": "ARK"
            },
            "mwanza": {
                "standard": "Mwanza",
                "aliases": ["mwanza city", "mwanza mjini", "rock city"],
                "region": "Mwanza",
                "airport_code": "MWZ"
            },
            "zanzibar": {
                "standard": "Zanzibar",
                "aliases": ["unguja", "stone town", "zanzibar city", "zanzibar town", 
                           "zanzibar mjini", "unguja mjini"],
                "region": "Zanzibar Urban/West",
                "airport_code": "ZNZ"
            },
            "dodoma": {
                "standard": "Dodoma",
                "aliases": ["dodoma city", "dodoma mjini", "capital"],
                "region": "Dodoma",
                "airport_code": "DOD"
            },
            "mbeya": {
                "standard": "Mbeya",
                "aliases": ["mbeya city", "mbeya mjini"],
                "region": "Mbeya",
                "airport_code": "MBA"
            },
            "morogoro": {
                "standard": "Morogoro",
                "aliases": ["morogoro city", "morogoro mjini"],
                "region": "Morogoro",
                "airport_code": None
            },
            "tanga": {
                "standard": "Tanga",
                "aliases": ["tanga city", "tanga mjini"],
                "region": "Tanga",
                "airport_code": "TGT"
            },
            "mtwara": {
                "standard": "Mtwara",
                "aliases": ["mtwara city", "mtwara mjini"],
                "region": "Mtwara",
                "airport_code": "MTW"
            },
            "kilimanjaro": {
                "standard": "Kilimanjaro",
                "aliases": ["moshi", "kilimanjaro region", "jro area"],
                "region": "Kilimanjaro",
                "airport_code": "JRO"
            },
            "iringa": {
                "standard": "Iringa",
                "aliases": ["iringa city", "iringa mjini"],
                "region": "Iringa",
                "airport_code": None
            },
            "tabora": {
                "standard": "Tabora",
                "aliases": ["tabora city", "tabora mjini"],
                "region": "Tabora",
                "airport_code": None
            },
            "kigoma": {
                "standard": "Kigoma",
                "aliases": ["kigoma city", "kigoma mjini"],
                "region": "Kigoma",
                "airport_code": None
            },
            "singida": {
                "standard": "Singida",
                "aliases": ["singida city", "singida mjini"],
                "region": "Singida",
                "airport_code": None
            },
            "songea": {
                "standard": "Songea",
                "aliases": ["songea city", "songea mjini"],
                "region": "Ruvuma",
                "airport_code": None
            },
            "musoma": {
                "standard": "Musoma",
                "aliases": ["musoma city", "musoma mjini"],
                "region": "Mara",
                "airport_code": None
            }
        }
        
        # Build reverse lookup for aliases
        self.alias_to_standard = {}
        for standard_key, city_data in self.STANDARD_CITIES.items():
            # Add the standard name itself
            self.alias_to_standard[standard_key] = standard_key
            # Add all aliases
            for alias in city_data["aliases"]:
                self.alias_to_standard[alias.lower()] = standard_key
        
        # Common misspellings and their corrections
        self.COMMON_CORRECTIONS = {
            "dares salaam": "dar es salaam",
            "dar-es-salaam": "dar es salaam", 
            "darussalam": "dar es salaam",
            "dar essalam": "dar es salaam",
            "arush": "arusha",
            "arusha city": "arusha",
            "mwanz": "mwanza",
            "zanzibar city": "zanzibar",
            "stone town": "zanzibar",
            "unguj": "zanzibar",
            "dodom": "dodoma",
            "mbey": "mbeya",
            "morogor": "morogoro",
            "tang": "tanga",
            "mtwar": "mtwara",
            "moshi": "kilimanjaro",
            "iring": "iringa",
            "tabor": "tabora",
            "kigom": "kigoma",
            "singid": "singida",
            "songe": "songea",
            "musom": "musoma"
        }
    
    def normalize_input(self, user_input: str) -> str:
        """Normalize user input for comparison"""
        if not user_input:
            return ""
        
        # Convert to lowercase and strip
        normalized = user_input.lower().strip()
        
        # Remove extra spaces
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove common prefixes/suffixes
        prefixes_to_remove = ["mji wa ", "mkoa wa ", "wilaya ya "]
        suffixes_to_remove = [" city", " town", " mjini"]
        
        for prefix in prefixes_to_remove:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
                break
        
        for suffix in suffixes_to_remove:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
                break
        
        return normalized.strip()
    
    def calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings"""
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
    
    def find_exact_match(self, normalized_input: str) -> Optional[str]:
        """Find exact match in aliases or standard names"""
        # Check direct aliases
        if normalized_input in self.alias_to_standard:
            return self.alias_to_standard[normalized_input]
        
        # Check common corrections
        if normalized_input in self.COMMON_CORRECTIONS:
            corrected = self.COMMON_CORRECTIONS[normalized_input]
            if corrected in self.alias_to_standard:
                return self.alias_to_standard[corrected]
        
        return None
    
    def find_fuzzy_matches(self, normalized_input: str, min_similarity: float = 0.6) -> List[Tuple[str, float]]:
        """Find fuzzy matches with similarity scores"""
        matches = []
        
        # Check against all standard names and aliases
        all_searchable = set()
        
        # Add standard city names
        for standard_key, city_data in self.STANDARD_CITIES.items():
            all_searchable.add((standard_key, city_data["standard"]))
            # Add aliases
            for alias in city_data["aliases"]:
                all_searchable.add((standard_key, alias.lower()))
        
        for standard_key, searchable_name in all_searchable:
            similarity = self.calculate_similarity(normalized_input, searchable_name)
            if similarity >= min_similarity:
                matches.append((standard_key, similarity))
        
        # Sort by similarity score (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)
        
        # Remove duplicates, keeping highest score
        seen = set()
        unique_matches = []
        for standard_key, score in matches:
            if standard_key not in seen:
                seen.add(standard_key)
                unique_matches.append((standard_key, score))
        
        return unique_matches[:5]  # Return top 5 matches
    
    def standardize_location(self, user_input: str) -> LocationMatch:
        """
        Main method to standardize location input
        
        Returns LocationMatch with standardized name and confidence
        """
        if not user_input or not user_input.strip():
            return LocationMatch(
                original_input=user_input,
                standardized_name="",
                confidence=0.0,
                match_type="invalid",
                suggestions=list(self.get_major_cities())
            )
        
        normalized_input = self.normalize_input(user_input)
        
        # Try exact match first
        exact_match = self.find_exact_match(normalized_input)
        if exact_match:
            return LocationMatch(
                original_input=user_input,
                standardized_name=self.STANDARD_CITIES[exact_match]["standard"],
                confidence=1.0,
                match_type="exact"
            )
        
        # Try fuzzy matching
        fuzzy_matches = self.find_fuzzy_matches(normalized_input)
        
        if fuzzy_matches:
            best_match, similarity = fuzzy_matches[0]
            
            # High confidence fuzzy match
            if similarity >= 0.8:
                return LocationMatch(
                    original_input=user_input,
                    standardized_name=self.STANDARD_CITIES[best_match]["standard"],
                    confidence=similarity,
                    match_type="fuzzy",
                    suggestions=[self.STANDARD_CITIES[match[0]]["standard"] for match in fuzzy_matches[:3]]
                )
            
            # Medium confidence - provide suggestions
            elif similarity >= 0.6:
                return LocationMatch(
                    original_input=user_input,
                    standardized_name="",
                    confidence=similarity,
                    match_type="partial",
                    suggestions=[self.STANDARD_CITIES[match[0]]["standard"] for match in fuzzy_matches[:3]]
                )
        
        # No good matches found
        return LocationMatch(
            original_input=user_input,
            standardized_name="",
            confidence=0.0,
            match_type="not_found",
            suggestions=list(self.get_major_cities())
        )
    
    def get_major_cities(self) -> List[str]:
        """Get list of major cities for suggestions"""
        major_cities = [
            "Dar es Salaam", "Arusha", "Mwanza", "Zanzibar", 
            "Dodoma", "Mbeya", "Morogoro", "Tanga"
        ]
        return major_cities
    
    def get_all_supported_cities(self) -> List[str]:
        """Get all supported cities"""
        return [city_data["standard"] for city_data in self.STANDARD_CITIES.values()]
    
    def get_city_info(self, standardized_name: str) -> Optional[Dict]:
        """Get detailed city information"""
        for city_data in self.STANDARD_CITIES.values():
            if city_data["standard"] == standardized_name:
                return city_data
        return None
    
    def format_suggestions_message(self, suggestions: List[str]) -> str:
        """Format suggestions for user display"""
        if not suggestions:
            return "Miji mikuu ya Tanzania: Dar es Salaam, Arusha, Mwanza, Zanzibar, Dodoma, Mbeya"
        
        if len(suggestions) == 1:
            return f"Je, unamaanisha: *{suggestions[0]}*?"
        elif len(suggestions) <= 3:
            suggestion_text = ", ".join(f"*{city}*" for city in suggestions[:-1])
            suggestion_text += f" au *{suggestions[-1]}*"
            return f"Je, unamaanisha: {suggestion_text}?"
        else:
            return f"Miji inayofanana: {', '.join(f'*{city}*' for city in suggestions[:3])}"

# Usage integration for your onboarding flow
class LocationOnboardingHandler:
    """Handler for location-based onboarding with standardization"""
    
    def __init__(self):
        self.standardizer = TanzanianLocationStandardizer()
    
    def handle_location_input(self, user_message: str) -> Tuple[str, str]:
        """
        Handle location input during onboarding
        
        Returns: (response_message, new_user_status)
        """
        location_match = self.standardizer.standardize_location(user_message)
        
        if location_match.match_type == "exact":
            response = f"Vizuri! Umechagua *{location_match.standardized_name}*. Je, hii ni sahihi? 📍\n\nJibu 'Ndio' au 'Hapana'."
            return response, "onboarding_confirm_location"
        
        elif location_match.match_type == "fuzzy" and location_match.confidence >= 0.8:
            response = f"Je, unamaanisha *{location_match.standardized_name}*? 🤔\n\n(Uliandika: _{location_match.original_input}_)\n\nJibu 'Ndio' au 'Hapana'."
            return response, "onboarding_confirm_location"
        
        elif location_match.match_type in ["partial", "fuzzy"] and location_match.suggestions:
            # Partial match with suggestions
            suggestions_text = self.standardizer.format_suggestions_message(location_match.suggestions)
            
            response = f"Sijaelewa vizuri jina la mji uliloandika: _{user_message}_\n\n{suggestions_text}\n\nTafadhali andika jina la mji tena."
            return response, "repeat_onboarding_location"
        
        else:
            # No match found
            major_cities = self.standardizer.get_major_cities()
            cities_text = ", ".join(f"*{city}*" for city in major_cities)
            
            response = f"Samahani, sijaelewa jina la mji: _{user_message}_\n\nTafadhali chagua moja ya miji hii mikuu ya Tanzania:\n\n{cities_text}\n\nAu andika jina lingine la mji wa Tanzania."
            return response, "repeat_onboarding_location"

# Testing and examples
if __name__ == "__main__":
    standardizer = TanzanianLocationStandardizer()
    handler = LocationOnboardingHandler()
    
    # Test various inputs
    test_inputs = [
        "dar es salaam",
        "dar",
        "darussalam", 
        "arusha",
        "arush",
        "mwanza",
        "zanzibar",
        "stone town",
        "dodoma",
        "mbeya",
        "xyz city",  # Invalid
        "",  # Empty
        "mosh",  # Partial match
        "dares salam"  # Misspelling
    ]
    
    print("=== Location Standardization Tests ===")
    for test_input in test_inputs:
        result = standardizer.standardize_location(test_input)
        print(f"Input: '{test_input}' -> {result.standardized_name} ({result.confidence:.2f}, {result.match_type})")
        if result.suggestions:
            print(f"  Suggestions: {result.suggestions}")
        print()
    
    print("=== Onboarding Handler Tests ===")
    
    class MockUserService:
        def update_user_details(self, phone, **kwargs):
            print(f"Updated user {phone} with {kwargs}")
        
        def update_user_status(self, phone, status):
            print(f"Updated user {phone} status to {status}")
            return type('User', (), {'status': status})()
    
    mock_service = MockUserService()
    
    for test_input in ["dar", "arusha city", "xyz", "mosh"]:
        print(f"\nTesting onboarding with input: '{test_input}'")
        response, status = handler.handle_location_input(test_input, mock_service, "+255123456789")
        print(f"Response: {response}")
        print(f"New status: {status}")
        print("-" * 50)