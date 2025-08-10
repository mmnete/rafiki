import requests
from typing import Dict, Any, Optional, List
import datetime
from os import getenv

# All supported Tanzanian airports
# All supported Tanzanian airports
TANZANIAN_AIRPORTS = {
    "DAR": "Dar es Salaam",
    "ZNZ": "Zanzibar",
    "JRO": "Kilimanjaro",
    "MWZ": "Mwanza",
    "ARK": "Arusha",
    "TGT": "Tanga",
    "MBA": "Mbeya",
    "MTW": "Mtwara",
    "DOD": "Dodoma",
    "TBO": "Tabora",
    "BKZ": "Bukoba",
    "IRI": "Iringa",
    "TKQ": "Kigoma",
    "LKY": "Lake Manyara",
    "MFA": "Mafia Island",
    "PMA": "Pemba",
    "SGX": "Songea",
    "MUZ": "Musoma"
}

# All supported Middle Eastern airports
MIDDLE_EAST_AIRPORTS = {
    "DXB": "Dubai",
    "DOH": "Doha",
    "IST": "Istanbul",
    "MCT": "Muscat",
    "ADD": "Addis Ababa",  # Often serves as a Middle East connection hub
    "CAI": "Cairo"
}

# All supported Asian airports
ASIAN_AIRPORTS = {
    "BOM": "Mumbai",
    "CAN": "Guangzhou",
    "BKK": "Bangkok",
    "SIN": "Singapore",
    "KUL": "Kuala Lumpur"
}

# All supported South African airports
SOUTH_AFRICAN_AIRPORTS = {
    "JNB": "Johannesburg",
    "CPT": "Cape Town"
}

# Supported destination codes (Tanzania + East Africa + Middle East + Asia + South Africa)
SUPPORTED_DESTINATIONS = {
    **TANZANIAN_AIRPORTS,
    "NBO": "Nairobi",
    "EBB": "Entebbe",
    "KGL": "Kigali",
    "BJM": "Bujumbura",
    "MGQ": "Mogadishu",
    "JUB": "Juba",
    **MIDDLE_EAST_AIRPORTS,
    **ASIAN_AIRPORTS,
    **SOUTH_AFRICAN_AIRPORTS
}
    
class AmadeusFlightScraper:
    # Use a single, unified source of truth for supported airports
    # This makes the validation logic much cleaner and more reliable.


    def __init__(self):
        self.client_id = getenv("AMADEUS_CLIENT_ID")
        self.client_secret = getenv("AMADEUS_CLIENT_SECRET")
        if not self.client_id or not self.client_secret:
            raise ValueError("Amadeus credentials not found in environment.")
        
        self.token = self._get_access_token()
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def _get_access_token(self) -> str:
        """Fetches a new access token from the Amadeus API."""
        url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        try:
            response = requests.post(url, data=data)
            response.raise_for_status()
            return response.json()["access_token"]
        except requests.exceptions.RequestException as e:
            print(f"Error fetching Amadeus token: {e}")
            raise ConnectionError("Failed to authenticate with Amadeus API.")

    def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        travel_class: str = "ECONOMY",
        currency: str = "USD",
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        Searches for flight offers using the Amadeus Flight Offers Search API.
        """
        origin = origin.upper()
        destination = destination.upper()

        # Validate routes based on the scope: inside or from Tanzania.
        if origin not in TANZANIAN_AIRPORTS:
            return {"error": f"Origin '{origin}' not supported. Must be a Tanzanian airport. Please try again."}
        
        if destination not in SUPPORTED_DESTINATIONS:
            return {"error": f"Destination '{destination}' not supported. Please choose a destination in Tanzania or East Africa."}

        # Validate dates
        try:
            dep_dt = datetime.datetime.strptime(departure_date, "%Y-%m-%d").date()
            if return_date:
                ret_dt = datetime.datetime.strptime(return_date, "%Y-%m-%d").date()
                if ret_dt < dep_dt:
                    return {"error": "Tarehe ya kurudi haiwezi kuwa kabla ya tarehe ya kuondoka."}
            if dep_dt < datetime.date.today():
                 return {"error": "Tarehe ya kuondoka haiwezi kuwa ya zamani."}
        except ValueError:
            return {"error": "Tafadhali tumia muundo sahihi wa tarehe (YYYY-MM-DD)."}

        # API call
        url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "adults": adults,
            "children": children,
            "infants": infants,
            "travelClass": travel_class,
            "currencyCode": currency,
            "max": max_results,
        }
        if return_date:
            params["returnDate"] = return_date

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            # print(response.json())
            
            # The API response is too verbose, we'll extract and simplify it.
            return self._parse_api_response(response.json())
        except requests.exceptions.RequestException as e:
            print(f"Amadeus API request error: {e}")
            return {"error": "Samahani, kuna tatizo la muunganisho wa Amadeus. Jaribu tena."}

    def _parse_api_response(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses the raw Amadeus API response into a simplified, more manageable format,
        including detailed information for each flight segment. This version creates a
        flatter structure to be compatible with the existing _parse_flight_data method.
        """
        flights = []
        
        # Dictionaries for looking up full names from codes
        airline_dict = api_response.get("dictionaries", {}).get("carriers", {})
        aircraft_dict = api_response.get("dictionaries", {}).get("aircraft", {})

        for offer in api_response.get("data", []):
            # We'll focus on the first itinerary for simplicity, as is common for a basic flight scraper
            itinerary = offer.get("itineraries", [{}])[0]
            segments = itinerary.get("segments", [])
            
            # Get details from the first and last segments for the overall trip
            first_segment = segments[0]
            last_segment = segments[-1]

            # Get airline details from the first segment
            airline_code = first_segment.get("carrierCode")
            airline_name = airline_dict.get(airline_code, "Unknown Airline")

            # Get aircraft details from the first segment
            aircraft_code = first_segment.get("aircraft", {}).get("code")
            aircraft_name = aircraft_dict.get(aircraft_code, "Unknown Aircraft")

            # Get baggage details for the first segment
            fare_details_by_segment = next((item for item in offer.get("travelerPricings", [])[0].get("fareDetailsBySegment", []) if item["segmentId"] == first_segment["id"]), {})
            checked_bags = fare_details_by_segment.get("includedCheckedBags", {})
            cabin_bags = fare_details_by_segment.get("includedCabinBags", {})

            flight_details = {
                "price_total": float(offer["price"]["grandTotal"]),
                "currency": offer["price"]["currency"],
                "origin": first_segment["departure"]["iataCode"],
                "destination": last_segment["arrival"]["iataCode"],
                "departure_time": first_segment["departure"]["at"],
                "arrival_time": last_segment["arrival"]["at"],
                "duration": itinerary.get("duration"),
                "number_of_segments": len(segments),
                "airline_code": airline_code,
                "airline_name": airline_name,
                "aircraft_name": aircraft_name,
                "included_checked_bags": checked_bags,
                "included_cabin_bags": cabin_bags,
                "last_ticketing_date": offer.get("lastTicketingDate")
            }
            
            # Add a list of all segments for detailed view
            flight_details["segments"] = [
                {
                    "airline_code": s.get("carrierCode"),
                    "airline_name": airline_dict.get(s.get("carrierCode"), "Unknown Airline"),
                    "flight_number": s.get("number"),
                    "departure_iata": s["departure"]["iataCode"],
                    "arrival_iata": s["arrival"]["iataCode"],
                    "departure_time": s["departure"]["at"],
                    "arrival_time": s["arrival"]["at"],
                    "duration": s.get("duration"),
                    "stops": s.get("numberOfStops", 0)
                } for s in segments
            ]
            
            flights.append(flight_details)

        return {"flights": flights}
