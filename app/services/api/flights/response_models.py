from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
from datetime import datetime
from decimal import Decimal
from enum import Enum


# --- Enums for Type Safety & Clarity ---
class CabinClass(Enum):
    ECONOMY = "Economy"
    PREMIUM_ECONOMY = "Premium Economy"
    BUSINESS = "Business"
    FIRST = "First"

class TripType(Enum):
    ONE_WAY_DIRECT = "one_way_direct"
    ONE_WAY_CONNECTING = "one_way_connecting"
    ROUND_TRIP = "round_trip"
    MULTI_CITY = "multi_city"

class PassengerType(Enum):
    ADULT = "adult"
    CHILD = "child"
    INFANT = "infant"


# --- Core Data Models ---
@dataclass
class FlightSearchSummary:
    """Summary statistics for flight search results"""
    total_offers: int
    price_range_min: Decimal
    price_range_max: Decimal
    currency: str
    routes_available: int
    airlines: List[str] = field(default_factory=list)


@dataclass
class FlightSegment:
    """Individual flight segment information"""
    # Required fields (no defaults)
    airline_code: str
    airline_name: str
    flight_number: str
    departure_iata: str
    arrival_iata: str
    departure_time: datetime
    arrival_time: datetime
    duration_minutes: int
    stops: int
    cabin_class: CabinClass
    
    # Optional fields (with defaults)
    departure_terminal: Optional[str] = None
    arrival_terminal: Optional[str] = None
    aircraft_code: Optional[str] = None
    aircraft_name: Optional[str] = None
    operating_carrier: Optional[str] = None
    segment_id: Optional[str] = None
    seat_configuration: Optional[str] = None
    meal_service: Optional[str] = None
    layover_duration_minutes: Optional[int] = None
    connection_airport_name: Optional[str] = None
    minimum_connection_time: Optional[int] = None
    terminal_change_required: Optional[bool] = None
    wifi_available: bool = False
    power_outlets: bool = False
    entertainment: bool = False
    meal_options: List[str] = field(default_factory=list)


@dataclass
class Pricing:
    """Pricing details for a flight offer"""
    # Required fields (no defaults)
    price_total: Decimal
    base_price: Decimal
    currency: str
    
    # Optional fields (with defaults)
    checked_bag_fee: Optional[Decimal] = None
    change_fee: Optional[Decimal] = None
    cancellation_fee: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None


@dataclass
class Baggage:
    """Baggage policy details"""
    checked_bags_included: int = 0
    cabin_bags_included: int = 0
    carry_on_included: bool = False
    carry_on_weight_limit: Optional[str] = None
    carry_on_size_limit: Optional[str] = None
    checked_bag_weight_limit: Optional[str] = None
    baggage_policy: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FareDetails:
    """Details about the fare class and rules"""
    # Required fields (no defaults)
    fare_class: str
    refundable: bool
    changeable: bool


@dataclass
class AncillaryServices:
    """Optional add-on services"""
    seat_selection_available: bool = False
    meal_upgrade_available: bool = False
    priority_boarding_available: bool = False
    lounge_access: bool = False
    seat_selection_fee_range: Optional[str] = None
    wifi_cost: Optional[str] = None
    seat_types_available: List[str] = field(default_factory=list)


@dataclass
class FlightOffer:
    """Complete flight offer information"""
    # Required fields (no defaults)
    offer_id: str
    provider_offer_id: str
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    duration_minutes: int
    trip_type: TripType
    total_segments: int
    stops: int
    airline_code: str
    pricing: Pricing
    baggage: Baggage
    fare_details: FareDetails
    ancillary_services: AncillaryServices
    
    # Optional fields (with defaults)
    seats_available: Optional[int] = None
    last_ticketing_date: Optional[datetime] = None
    instant_ticketing: bool = True
    segments: List[FlightSegment] = field(default_factory=list)
    provider_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FlightSearchResponse:
    """Complete flight search response"""
    # Required fields (no defaults)
    success: bool
    search_summary: FlightSearchSummary
    
    # Optional fields (with defaults)
    search_id: Optional[str] = None
    error_message: Optional[str] = None
    provider_name: Optional[str] = None
    flights: List[FlightOffer] = field(default_factory=list)


@dataclass
class SimplifiedFlightOffer:
    """Simplified flight offer for model consumption"""
    id: str
    price: str
    airline: str
    route: str
    departure: str
    arrival: str
    duration: str
    stops: str


@dataclass
class SimplifiedSearchResponse:
    """Simplified search response for model consumption"""
    # Required fields (no defaults)
    success: bool
    summary: Dict[str, Any]
    
    # Optional fields (with defaults)
    search_id: Optional[str] = None
    search_params: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    flights: List[SimplifiedFlightOffer] = field(default_factory=list)


@dataclass
class Passenger:
    """Passenger information for bookings"""
    # Required fields (no defaults)
    passenger_type: PassengerType
    first_name: str
    last_name: str
    date_of_birth: datetime
    gender: str
    email: str
    phone: str
    nationality: str
    
    # Optional fields (with defaults)
    passport_number: Optional[str] = None
    passport_expiry: Optional[datetime] = None
    age: Optional[int] = None


@dataclass
class ErrorResponse:
    """Unified error response class"""
    error_message: str
    success: bool = field(init=False, default=False)

    def __post_init__(self):
        self.success = False


# --- Response Classes (keeping original structure for compatibility) ---
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
    booking_reference: str
    total_amount: float
    currency: str
    created_at: str
    provider_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


@dataclass
class CancellationResponse:
    """Response for booking cancellation"""
    success: bool
    refund_amount: float
    refund_currency: str
    cancellation_id: Optional[str] = None
    cancellation_confirmed_at: Optional[str] = None
    provider_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


# --- Helper Functions ---
def create_error_search_response(error_message: str, provider_name: Optional[str] = None) -> FlightSearchResponse:
    """Create an error search response"""
    return FlightSearchResponse(
        success=False,
        search_summary=FlightSearchSummary(
            total_offers=0,
            price_range_min=Decimal("0.00"),
            price_range_max=Decimal("0.00"),
            currency="USD",
            routes_available=0
        ),
        error_message=error_message,
        provider_name=provider_name
    )


def create_error_model_response(error_message: str) -> SimplifiedSearchResponse:
    """Create an error model response"""
    return SimplifiedSearchResponse(
        success=False,
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
        refund_amount=0.0,
        refund_currency="USD",
        cancellation_id=None,
        cancellation_confirmed_at=None,
        error_message=error_message
    )
