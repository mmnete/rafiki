from typing import Optional, Tuple, List
import uuid
from datetime import datetime
from .amadeus_provider import AmadeusProvider
from .duffel_provider import DuffelProvider
from .response_models import (
    FlightSearchResponse, ModelSearchResponse, PricingResponse, 
    BookingResponse, CancellationResponse, Passenger,
    create_error_model_response, create_error_search_response
)
import os


class FlightService:
    """Provider-agnostic flight service orchestration with object-based responses"""
    
    def __init__(self, flight_storage=None, booking_storage=None, user_storage=None):
        self.flight_storage = flight_storage
        self.booking_storage = booking_storage
        self.user_storage = user_storage

        # Initialize providers
        self.providers = {}
        for name, provider_cls in [("amadeus", AmadeusProvider), ("duffel", DuffelProvider)]:
            try:
                self.providers[name] = provider_cls()
            except Exception as e:
                print(f"⚠️ Failed to initialize {name.title()} provider: {e}")

        # Resolve default provider
        env_default = os.getenv("DEFAULT_FLIGHT_PROVIDER", "").lower()
        if env_default and env_default in self.providers:
            self.default_provider = env_default
        elif self.providers:
            # Pick first available if env is missing or invalid
            self.default_provider = next(iter(self.providers.keys()))
            if env_default:
                print(
                    f"⚠️ Default provider '{env_default}' not available. "
                    f"Falling back to '{self.default_provider}'."
                )
        else:
            raise ValueError("❌ No flight providers are available")
    
    def _get_env_var(self, key: str) -> str:
        from os import getenv
        return getenv(key) or ""
    
    def search_flights(self, origin: str, destination: str, departure_date: str,
                      return_date: Optional[str] = None, 
                      adults: int = 1, children: int = 0, infants: int = 0,
                      travel_class: str = "ECONOMY", 
                      user_id: Optional[int] = None,
                      provider: Optional[str] = None) -> Tuple[ModelSearchResponse, FlightSearchResponse]:
        """Search flights using specified or default provider"""
        
        # Select provider
        provider_name = provider or self.default_provider
        if provider_name not in self.providers:
            error_msg = f"Provider '{provider_name}' not available"
            return (
                create_error_model_response(error_msg),
                create_error_search_response(error_msg, provider_name)
            )
        
        flight_provider = self.providers[provider_name]
        
        # Build passenger list
        passengers = []
        passengers.extend([
            Passenger(
                passenger_type="adult", first_name="", last_name="", 
                date_of_birth="1990-01-01", gender="", email="", 
                phone="", nationality=""
            )
        ] * adults)
        passengers.extend([
            Passenger(
                passenger_type="child", first_name="", last_name="", 
                date_of_birth="2015-01-01", gender="", email="", 
                phone="", nationality="", age=8
            )
        ] * children)
        passengers.extend([
            Passenger(
                passenger_type="infant", first_name="", last_name="", 
                date_of_birth="2023-01-01", gender="", email="", 
                phone="", nationality="", age=1
            )
        ] * infants)
        
        # Search flights
        model_response, full_response = flight_provider.search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            passengers=passengers,
            travel_class=travel_class
        )
        
        # Store search results if we have a user and successful results
        if user_id and full_response.success and self.flight_storage:
            try:
                search_params = {
                    'origin': origin,
                    'destination': destination,
                    'departure_date': departure_date,
                    'return_date': return_date,
                    'passengers': {'adults': adults, 'children': children, 'infants': infants},
                    'travel_class': travel_class,
                    'provider': provider_name
                }
                
                trip_type = 'round_trip' if return_date else 'one_way'
                custom_search_id = f"search_{user_id}_{origin}_{destination}_{departure_date}_{uuid.uuid4().hex[:8]}"
                
                # Store flight search
                search_id = self.flight_storage.create_flight_search(
                    user_id=user_id,
                    custom_search_id=custom_search_id,
                    search_type=trip_type,
                    search_params=search_params,
                    raw_results=full_response.__dict__,  # Convert object to dict for storage
                    processed_results=model_response.__dict__,
                    result_count=len(full_response.flights),
                    apis_used=[provider_name],
                    cache_hit=False
                )
                
                # Add search_id to responses
                model_response.search_id = search_id
                full_response.search_id = search_id
                    
            except Exception as e:
                print(f"Error storing search results: {e}")
        
        return model_response, full_response
    
    def get_final_price(self, offer_id: str, provider: Optional[str] = None) -> PricingResponse:
        """Get confirmed pricing for an offer"""
        provider_name = provider or self.default_provider
        if provider_name not in self.providers:
            return self.create_error_pricing_response(offer_id, f"Provider '{provider_name}' not available")
        
        return self.providers[provider_name].get_final_price(offer_id)

    def create_error_pricing_response(self, offer_id: str, error_message: str) -> PricingResponse:
        """Factory for error responses when pricing fails"""
        return PricingResponse(
            success=False,
            offer_id=offer_id,
            base_amount=0.0,
            tax_amount=0.0,
            total_amount=0.0,
            currency="USD",  # or make configurable if multi-currency
            error_message=error_message,
        )
    
    def create_booking(self, offer_id: str, passengers: List[Passenger], 
                      booking_reference: str, 
                      provider: Optional[str] = None) -> BookingResponse:
        """Create booking with specified provider"""
        provider_name = provider or self.default_provider
        if provider_name not in self.providers:
            return BookingResponse(
                success=False,
                booking_id="",
                booking_reference="",
                total_amount=0.0,
                currency="USD",
                created_at="",
                error_message=f"Provider '{provider_name}' not available"
            )
        
        return self.providers[provider_name].create_booking(
            offer_id=offer_id,
            passengers=passengers,
            booking_reference=booking_reference
        )
    
    def cancel_booking(self, booking_reference: str, provider: Optional[str] = None) -> CancellationResponse:
        """Cancel booking with specified provider"""
        provider_name = provider or self.default_provider
        if provider_name not in self.providers:
            return CancellationResponse(
                success=False,
                cancellation_id=None,
                refund_amount=0.0,
                refund_currency="USD",
                cancellation_confirmed_at=None,
                error_message=f"Provider '{provider_name}' not available"
            )
        
        return self.providers[provider_name].cancel_booking(booking_reference)
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        return list(self.providers.keys())
    
    def get_provider_status(self) -> dict:
        """Get status of all providers"""
        status = {}
        for name, provider in self.providers.items():
            try:
                # Simple health check - attempt to get provider name
                provider_name = provider.get_provider_name()
                status[name] = {"available": True, "name": provider_name}
            except Exception as e:
                status[name] = {"available": False, "error": str(e)}
        
        return status
    
    def _generate_booking_reference(self) -> str:
        """Generate unique booking reference"""
        import random
        import string
        letters = ''.join(random.choices(string.ascii_uppercase, k=3))
        numbers = ''.join(random.choices(string.digits, k=3))
        suffix = ''.join(random.choices(string.ascii_uppercase, k=2))
        return f"{letters}{numbers}{suffix}"

