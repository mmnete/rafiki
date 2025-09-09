from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from .response_models import (
    FlightSearchResponse, ModelSearchResponse, PricingResponse, 
    BookingResponse, CancellationResponse, Passenger
)

class FlightProvider(ABC):
    """Abstract base class for flight providers"""
    
    @abstractmethod
    def search_flights(self, origin: str, destination: str, departure_date: str,
                      return_date: Optional[str] = None, passengers: List[Passenger] = [],
                      travel_class: str = "ECONOMY") -> Tuple[ModelSearchResponse, FlightSearchResponse]:
        """
        Search for flights. Returns (model_response, full_response) tuple.
        
        Args:
            origin: IATA code for departure airport/city
            destination: IATA code for arrival airport/city  
            departure_date: Departure date in YYYY-MM-DD format
            return_date: Return date in YYYY-MM-DD format (for round trip)
            passengers: List of Passenger objects with type info
            travel_class: Cabin class (ECONOMY, BUSINESS, etc.)
            
        Returns:
            Tuple of (ModelSearchResponse, FlightSearchResponse)
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
