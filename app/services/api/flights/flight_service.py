import logging
from typing import Optional, Tuple, List
import uuid
import os
from datetime import datetime
from .amadeus_provider import AmadeusProvider
from .duffel_provider import DuffelProvider
from .response_models import (
    FlightSearchResponse, SimplifiedSearchResponse, PricingResponse, 
    BookingResponse, CancellationResponse, Passenger, PassengerType,
    create_error_model_response, create_error_search_response,
    create_error_pricing_response, create_error_booking_response,
    create_error_cancellation_response
)

logger = logging.getLogger(__name__)


class FlightService:
    """Provider-agnostic flight service orchestration with object-based responses"""
    
    def __init__(self, flight_storage=None, booking_storage=None, user_storage=None):
        self.flight_storage = flight_storage
        self.booking_storage = booking_storage
        self.user_storage = user_storage

        logger.info("Initializing FlightService")
        
        # Initialize providers
        self.providers = {}
        for name, provider_cls in [("amadeus", AmadeusProvider), ("duffel", DuffelProvider)]:
            try:
                self.providers[name] = provider_cls()
                logger.info(f"Successfully initialized {name} provider")
            except Exception as e:
                logger.error(f"Failed to initialize {name} provider", extra={
                    'provider': name,
                    'error': str(e),
                    'error_type': type(e).__name__
                }, exc_info=True)

        # Resolve default provider
        env_default = os.getenv("DEFAULT_FLIGHT_PROVIDER", "").lower()
        if env_default and env_default in self.providers:
            self.default_provider = env_default
            logger.info(f"Using default provider from environment: {env_default}")
        elif self.providers:
            # Pick first available if env is missing or invalid
            self.default_provider = next(iter(self.providers.keys()))
            if env_default:
                logger.warning(f"Default provider '{env_default}' not available, falling back to '{self.default_provider}'")
            else:
                logger.info(f"No default provider specified, using first available: {self.default_provider}")
        else:
            logger.error("No flight providers are available")
            raise ValueError("No flight providers are available")
        
        logger.info(f"FlightService initialized with {len(self.providers)} providers", extra={
            'available_providers': list(self.providers.keys()),
            'default_provider': self.default_provider
        })
    
    def search_flights(self, origin: str, destination: str, departure_date: str,
                      return_date: Optional[str] = None, 
                      adults: int = 1, children: int = 0, infants: int = 0,
                      travel_class: str = "ECONOMY", 
                      user_id: Optional[int] = None,
                      provider: Optional[str] = None) -> Tuple[SimplifiedSearchResponse, FlightSearchResponse]:
        """Search flights using specified or default provider"""
        
        logger.info("Flight search initiated", extra={
            'origin': origin,
            'destination': destination,
            'departure_date': departure_date,
            'return_date': return_date,
            'passengers': {'adults': adults, 'children': children, 'infants': infants},
            'travel_class': travel_class,
            'user_id': user_id,
            'requested_provider': provider
        })
        
        # Select provider
        provider_name = provider or self.default_provider
        if provider_name not in self.providers:
            error_msg = f"Provider '{provider_name}' not available"
            logger.error("Provider not available", extra={
                'requested_provider': provider_name,
                'available_providers': list(self.providers.keys())
            })
            return (
                create_error_model_response(error_msg),
                create_error_search_response(error_msg, provider_name)
            )
        
        flight_provider = self.providers[provider_name]
        logger.debug(f"Using provider: {provider_name}")
        
        # Build passenger list
        passengers = []
        
        # Add adults
        passengers.extend([
            Passenger(
                passenger_type=PassengerType.ADULT,
                first_name="",
                last_name="",
                date_of_birth=datetime(1990, 1, 1),
                gender="",
                email="",
                phone="",
                nationality=""
            )
        ] * adults)
        
        # Add children
        passengers.extend([
            Passenger(
                passenger_type=PassengerType.CHILD,
                first_name="",
                last_name="",
                date_of_birth=datetime(2015, 1, 1),
                gender="",
                email="",
                phone="",
                nationality="",
                age=8
            )
        ] * children)
        
        # Add infants
        passengers.extend([
            Passenger(
                passenger_type=PassengerType.INFANT,
                first_name="",
                last_name="",
                date_of_birth=datetime(2023, 1, 1),
                gender="",
                email="",
                phone="",
                nationality="",
                age=1
            )
        ] * infants)
        
        logger.debug(f"Created {len(passengers)} passenger objects for search")
        
        try:
            # Search flights
            model_response, full_response = flight_provider.search_flights(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date,
                passengers=passengers,
                travel_class=travel_class
            )
            
            logger.info("Flight search completed", extra={
                'provider': provider_name,
                'success': model_response.success,
                'flight_count': len(model_response.flights) if model_response.success else 0,
                'error_message': model_response.error_message if not model_response.success else None
            })
            
        except Exception as e:
            logger.error("Flight search failed with exception", extra={
                'provider': provider_name,
                'error': str(e),
                'error_type': type(e).__name__
            }, exc_info=True)
            
            error_msg = f"Flight search failed: {str(e)}"
            return (
                create_error_model_response(error_msg),
                create_error_search_response(error_msg, provider_name)
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
                
                logger.debug("Storing flight search results", extra={
                    'user_id': user_id,
                    'custom_search_id': custom_search_id,
                    'result_count': len(full_response.flights)
                })
                
                # Store flight search
                search_id = self.flight_storage.create_flight_search(
                    user_id=user_id,
                    custom_search_id=custom_search_id,
                    search_type=trip_type,
                    search_params=search_params,
                    raw_results=self._convert_to_dict(full_response),
                    processed_results=self._convert_to_dict(model_response),
                    result_count=len(full_response.flights),
                    apis_used=[provider_name],
                    cache_hit=False
                )
                
                # Add search_id to responses
                model_response.search_id = search_id
                full_response.search_id = search_id
                
                logger.info("Flight search results stored successfully", extra={
                    'user_id': user_id,
                    'search_id': search_id
                })
                    
            except Exception as e:
                logger.error("Error storing search results", extra={
                    'user_id': user_id,
                    'error': str(e),
                    'error_type': type(e).__name__
                }, exc_info=True)
        
        return model_response, full_response
    
    def get_final_price(self, offer_id: str, provider: Optional[str] = None) -> PricingResponse:
        """Get confirmed pricing for an offer"""
        logger.info("Getting final price", extra={
            'offer_id': offer_id,
            'requested_provider': provider
        })
        
        provider_name = provider or self.default_provider
        if provider_name not in self.providers:
            error_msg = f"Provider '{provider_name}' not available"
            logger.error("Provider not available for pricing", extra={
                'requested_provider': provider_name,
                'offer_id': offer_id
            })
            return create_error_pricing_response(offer_id, error_msg)
        
        try:
            pricing_response = self.providers[provider_name].get_final_price(offer_id)
            logger.info("Final price retrieved", extra={
                'offer_id': offer_id,
                'provider': provider_name,
                'success': pricing_response.success,
                'total_amount': pricing_response.total_amount if pricing_response.success else None
            })
            return pricing_response
            
        except Exception as e:
            logger.error("Error getting final price", extra={
                'offer_id': offer_id,
                'provider': provider_name,
                'error': str(e),
                'error_type': type(e).__name__
            }, exc_info=True)
            return create_error_pricing_response(offer_id, f"Pricing failed: {str(e)}")
    
    def create_booking(self, offer_id: str, passengers: List[Passenger], 
                      booking_reference: str, 
                      provider: Optional[str] = None) -> BookingResponse:
        """Create booking with specified provider"""
        logger.info("Creating booking", extra={
            'offer_id': offer_id,
            'booking_reference': booking_reference,
            'passenger_count': len(passengers),
            'requested_provider': provider
        })
        
        provider_name = provider or self.default_provider
        if provider_name not in self.providers:
            error_msg = f"Provider '{provider_name}' not available"
            logger.error("Provider not available for booking", extra={
                'requested_provider': provider_name,
                'offer_id': offer_id
            })
            return create_error_booking_response(error_msg)
        
        try:
            booking_response = self.providers[provider_name].create_booking(
                offer_id=offer_id,
                passengers=passengers,
                booking_reference=booking_reference
            )
            
            logger.info("Booking creation completed", extra={
                'offer_id': offer_id,
                'booking_reference': booking_reference,
                'provider': provider_name,
                'success': booking_response.success,
                'booking_id': booking_response.booking_id if booking_response.success else None
            })
            
            return booking_response
            
        except Exception as e:
            logger.error("Error creating booking", extra={
                'offer_id': offer_id,
                'booking_reference': booking_reference,
                'provider': provider_name,
                'error': str(e),
                'error_type': type(e).__name__
            }, exc_info=True)
            return create_error_booking_response(f"Booking failed: {str(e)}")
    
    def cancel_booking(self, booking_reference: str, provider: Optional[str] = None) -> CancellationResponse:
        """Cancel booking with specified provider"""
        logger.info("Cancelling booking", extra={
            'booking_reference': booking_reference,
            'requested_provider': provider
        })
        
        provider_name = provider or self.default_provider
        if provider_name not in self.providers:
            error_msg = f"Provider '{provider_name}' not available"
            logger.error("Provider not available for cancellation", extra={
                'requested_provider': provider_name,
                'booking_reference': booking_reference
            })
            return create_error_cancellation_response(error_msg)
        
        try:
            cancellation_response = self.providers[provider_name].cancel_booking(booking_reference)
            
            logger.info("Booking cancellation completed", extra={
                'booking_reference': booking_reference,
                'provider': provider_name,
                'success': cancellation_response.success,
                'refund_amount': cancellation_response.refund_amount if cancellation_response.success else None
            })
            
            return cancellation_response
            
        except Exception as e:
            logger.error("Error cancelling booking", extra={
                'booking_reference': booking_reference,
                'provider': provider_name,
                'error': str(e),
                'error_type': type(e).__name__
            }, exc_info=True)
            return create_error_cancellation_response(f"Cancellation failed: {str(e)}")
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        providers = list(self.providers.keys())
        logger.debug("Available providers requested", extra={
            'providers': providers
        })
        return providers
    
    def get_provider_status(self) -> dict:
        """Get status of all providers"""
        logger.debug("Provider status check initiated")
        status = {}
        
        for name, provider in self.providers.items():
            try:
                # Simple health check - attempt to get provider name
                provider_name = provider.get_provider_name()
                status[name] = {"available": True, "name": provider_name}
                logger.debug(f"Provider {name} is available")
            except Exception as e:
                status[name] = {"available": False, "error": str(e)}
                logger.warning(f"Provider {name} health check failed", extra={
                    'provider': name,
                    'error': str(e)
                })
        
        logger.info("Provider status check completed", extra={
            'status_summary': {name: info['available'] for name, info in status.items()}
        })
        
        return status
    
    def _generate_booking_reference(self) -> str:
        """Generate unique booking reference"""
        import random
        import string
        letters = ''.join(random.choices(string.ascii_uppercase, k=3))
        numbers = ''.join(random.choices(string.digits, k=3))
        suffix = ''.join(random.choices(string.ascii_uppercase, k=2))
        reference = f"{letters}{numbers}{suffix}"
        
        logger.debug("Generated booking reference", extra={
            'booking_reference': reference
        })
        
        return reference
    
    def _convert_to_dict(self, obj) -> dict:
        """Convert dataclass or object to dictionary for storage"""
        try:
            if hasattr(obj, '__dict__'):
                return obj.__dict__
            else:
                return {}
        except Exception as e:
            logger.warning("Failed to convert object to dict", extra={
                'object_type': type(obj).__name__,
                'error': str(e)
            })
            return {}
    