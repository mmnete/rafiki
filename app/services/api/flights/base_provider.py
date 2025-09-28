from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from .response_models import (
    FlightSearchResponse, SimplifiedSearchResponse, PricingResponse, 
    BookingResponse, CancellationResponse, Passenger
)

class FlightProvider(ABC):
    """Abstract base class for flight providers"""
    
    @abstractmethod
    def search_flights(self, origin: str, destination: str, departure_date: str,
                      return_date: Optional[str] = None, passengers: List[Passenger] = [],
                      travel_class: str = "ECONOMY") -> Tuple[SimplifiedSearchResponse, FlightSearchResponse]:
        """
        Search for flights. Returns (simplified_response, full_response) tuple.
        
        Args:
            origin: IATA code for departure airport/city
            destination: IATA code for arrival airport/city  
            departure_date: Departure date in YYYY-MM-DD format
            return_date: Return date in YYYY-MM-DD format (for round trip)
            passengers: List of Passenger objects with type info
            travel_class: Cabin class (ECONOMY, BUSINESS, etc.)
            
        Returns:
            Tuple of (SimplifiedSearchResponse, FlightSearchResponse)
        """
        pass
    
    @abstractmethod
    def get_final_price(self, offer_id: str) -> PricingResponse:
        """
        Get final confirmed pricing WITHOUT passenger details - for price display.
        
        Args:
            offer_id: Provider-specific offer ID
            
        Returns:
            PricingResponse object with pricing information or error
        """
        pass
    
    @abstractmethod
    def create_booking(self, offer_id: str, passengers: List[Passenger], 
                      booking_reference: str) -> BookingResponse:
        """
        Create actual PNR/booking WITH full passenger details.
        
        Args:
            offer_id: Provider-specific offer ID
            passengers: Full passenger details for booking
            booking_reference: Unique booking reference string
            
        Returns:
            BookingResponse object with booking confirmation or error
        """
        pass
    
    @abstractmethod
    def cancel_booking(self, booking_reference: str) -> CancellationResponse:
        """
        Cancel a booking.
        
        Args:
            booking_reference: Booking reference to cancel
            
        Returns:
            CancellationResponse object with cancellation confirmation or error
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return provider name identifier"""
        pass
    
    def _create_contact_info(self) -> List[Dict]:
        """Create agency contact information for booking"""
        contact = {
            "addresseeName": {
                "firstName": "Travel",
                "lastName": "Agent"
            },
            "companyName": "YOUR_TRAVEL_AGENCY_NAME",
            "purpose": "STANDARD",
            "phones": [{
                "deviceType": "LANDLINE",  # or "MOBILE" 
                "countryCallingCode": "1",
                "number": "5551234567"  # Your agency phone
            }],
            "emailAddress": "bookings@youragency.com",  # Your agency email
            "address": {
                "lines": ["123 Travel Agency Street", "Suite 100"],
                "postalCode": "12345",
                "cityName": "Your City", 
                "countryCode": "US"
            }
        }
        
        return [contact]
