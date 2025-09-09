from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
from datetime import datetime
from decimal import Decimal


@dataclass
class FlightSearchSummary:
    """Summary statistics for flight search results"""
    total_offers: int
    price_range_min: float
    price_range_max: float
    currency: str
    airlines: List[str]
    routes_available: int


@dataclass
class FlightSegment:
    """Individual flight segment information"""
    airline_code: str
    airline_name: str
    flight_number: str
    departure_iata: str
    arrival_iata: str
    departure_terminal: Optional[str]
    arrival_terminal: Optional[str]
    departure_time: str
    arrival_time: str
    duration: str
    duration_minutes: int
    stops: int
    aircraft_code: Optional[str]
    aircraft_name: Optional[str]
    operating_carrier: Optional[str]
    segment_id: Optional[str]


@dataclass
class FlightOffer:
    """Complete flight offer information"""
    # Core identifiers
    flight_offer_id: str
    provider_offer_id: str
    
    # Pricing
    price_total: float
    base_price: float
    currency: str
    
    # Route information
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    
    # Trip details
    trip_type: str  # one_way_direct, one_way_connecting, round_trip, multi_city
    duration: Optional[str]
    duration_minutes: int
    flight_duration_minutes: int
    total_segments: int
    stops: int
    
    # Airline info
    airline_code: str
    airline_name: str
    airlines: List[str]  # All unique airlines in the journey
    
    # Segments
    segments: List[FlightSegment]
    
    # Baggage
    checked_bags: int
    cabin_bags: int
    
    # Booking constraints
    seats_available: Optional[int]
    instant_ticketing: bool
    last_ticketing_date: Optional[str]
    
    # Provider-specific data for booking
    provider_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FlightSearchResponse:
    """Complete flight search response"""
    success: bool
    flights: List[FlightOffer]
    search_summary: FlightSearchSummary
    search_id: Optional[str] = None
    error_message: Optional[str] = None
    provider_name: Optional[str] = None


@dataclass
class ModelFlightOffer:
    """Simplified flight offer for model consumption"""
    id: str
    price: str  # Formatted price like "$450"
    airline: str
    route: str  # "JFK → LAX"
    departure: str  # Time only like "14:30"
    arrival: str    # Time only like "17:45"
    duration: str   # "5h 15m"
    stops: str      # "Direct" or "1 stop"


@dataclass
class ModelSearchResponse:
    """Simplified search response for model consumption"""
    success: bool
    flights: List[ModelFlightOffer]
    summary: Dict[str, Any]  # Basic summary stats
    search_id: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class PricingResponse:
    """Response for final pricing requests"""
    success: bool
    offer_id: str
    total_amount: float
    base_amount: float
    tax_amount: float
    currency: str
    provider_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


@dataclass
class BookingResponse:
    """Response for booking creation"""
    success: bool
    booking_id: str
    booking_reference: str  # PNR or confirmation code
    total_amount: float
    currency: str
    created_at: str
    provider_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


@dataclass
class CancellationResponse:
    """Response for booking cancellation"""
    success: bool
    cancellation_id: Optional[str]
    refund_amount: float
    refund_currency: str
    cancellation_confirmed_at: Optional[str]
    provider_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


@dataclass
class Passenger:
    """Passenger information for bookings"""
    passenger_type: str  # adult, child, infant
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str
    email: str
    phone: str
    nationality: str
    passport_number: Optional[str] = None
    passport_expiry: Optional[str] = None
    age: Optional[int] = None


# Helper functions for response creation
def create_error_search_response(error_message: str, provider_name: Optional[str] = None) -> FlightSearchResponse:
    """Create an error search response"""
    return FlightSearchResponse(
        success=False,
        flights=[],
        search_summary=FlightSearchSummary(
            total_offers=0,
            price_range_min=0.0,
            price_range_max=0.0,
            currency="USD",
            airlines=[],
            routes_available=0
        ),
        error_message=error_message,
        provider_name=provider_name
    )


def create_error_model_response(error_message: str) -> ModelSearchResponse:
    """Create an error model response"""
    return ModelSearchResponse(
        success=False,
        flights=[],
        summary={},
        error_message=error_message
    )


def create_error_pricing_response(offer_id: str, error_message: str) -> PricingResponse:
    """Create an error pricing response"""
    return PricingResponse(
        success=False,
        offer_id=offer_id,
        total_amount=0.0,
        base_amount=0.0,
        tax_amount=0.0,
        currency="USD",
        error_message=error_message
    )


def create_error_booking_response(error_message: str) -> BookingResponse:
    """Create an error booking response"""
    return BookingResponse(
        success=False,
        booking_id="",
        booking_reference="",
        total_amount=0.0,
        currency="USD",
        created_at="",
        error_message=error_message
    )


def create_error_cancellation_response(error_message: str) -> CancellationResponse:
    """Create an error cancellation response"""
    return CancellationResponse(
        success=False,
        cancellation_id=None,
        refund_amount=0.0,
        refund_currency="USD",
        cancellation_confirmed_at=None,
        error_message=error_message
    )