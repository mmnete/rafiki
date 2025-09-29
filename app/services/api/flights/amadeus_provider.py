from typing import List, Optional, Tuple, Dict, Any
import requests
import json
import re
import time
import hashlib
from datetime import datetime
from decimal import Decimal
from .base_provider import FlightProvider
from .response_models import (
    FlightSearchResponse, SimplifiedSearchResponse, PricingResponse, 
    BookingResponse, CancellationResponse, Passenger,
    FlightOffer, FlightSegment, FlightSearchSummary, SimplifiedFlightOffer,
    Pricing, Baggage, FareDetails, AncillaryServices, CabinClass, TripType, PassengerType, EmergencyContact, 
    create_error_search_response, create_error_model_response,
    create_error_pricing_response, create_error_booking_response,
    create_error_cancellation_response
)
import logging

logger = logging.getLogger(__name__)

class AmadeusProvider(FlightProvider):
    """Enhanced Amadeus implementation with comprehensive flight details extraction"""
    
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        try:
            self.client_id = client_id or self._get_env_var("AMADEUS_CLIENT_ID")
            self.client_secret = client_secret or self._get_env_var("AMADEUS_CLIENT_SECRET")
            
            if not self.client_id or not self.client_secret:
                raise ValueError("Amadeus credentials are required")
            
            self.base_url = "https://test.api.amadeus.com"  # Use test environment
            self.token = None
            self.headers = {}
            
            # Initialize authentication
            self._authenticate()
            
        except Exception as e:
            raise ValueError(f"Failed to initialize Amadeus client: {e}")
    
    def _get_env_var(self, key: str) -> str:
        from os import getenv
        return getenv(key) or ""
    
    def _authenticate(self) -> None:
        """Authenticate with Amadeus API"""
        url = f"{self.base_url}/v1/security/oauth2/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            response = requests.post(url, data=data)
            response.raise_for_status()
            token_data = response.json()
            self.token = token_data["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Amadeus authentication failed: {e}")

    def search_flights(self, origin: str, destination: str, departure_date: str,
                    return_date: Optional[str] = None, passengers: List[Passenger] = [],
                    travel_class: str = "ECONOMY") -> Tuple[SimplifiedSearchResponse, FlightSearchResponse]:
        """Search flights using Amadeus API with enhanced details extraction"""
        try:
            if not passengers:
                passengers = [Passenger(
                    passenger_type=PassengerType.ADULT,
                    first_name="",
                    last_name="",
                    date_of_birth=datetime(1990, 1, 1),
                    gender="",
                    email="",
                    phone="",
                    nationality=""
                )]

            adults = sum(1 for p in passengers if p.passenger_type == PassengerType.ADULT)
            children = sum(1 for p in passengers if p.passenger_type == PassengerType.CHILD)
            infants = sum(1 for p in passengers if p.passenger_type == PassengerType.INFANT)

            url = f"{self.base_url}/v2/shopping/flight-offers"
            params = {
                "originLocationCode": origin.upper(),
                "destinationLocationCode": destination.upper(),
                "departureDate": departure_date,
                "adults": adults,
                "children": children,
                "infants": infants,
                "travelClass": travel_class,
                "currencyCode": "USD",
                "max": 5,
            }

            if return_date:
                params["returnDate"] = return_date

            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()

            api_response = response.json()
            return self._transform_amadeus_response(api_response)

        except requests.exceptions.RequestException as e:
            error_msg = f"Amadeus search failed: {str(e)}"
            logger.error(error_msg, exc_info=True)  # log with traceback
            return (
                create_error_model_response(error_msg),
                create_error_search_response(error_msg, "amadeus")
            )
        except Exception as e:
            error_msg = f"Amadeus search error: {str(e)}"
            logger.exception(error_msg)  # automatically includes stack trace
            return (
                create_error_model_response(error_msg),
                create_error_search_response(error_msg, "amadeus")
            )
    
    def get_final_price(self, offer_id: str, 
                   additional_baggage: Optional[Dict] = None,
                   selected_seats: Optional[Dict] = None) -> PricingResponse:
        """Get final confirmed pricing with optional ancillary services"""
        try:
            # TODO: Load offer from cache right now.
            if offer_id not in []:
                return create_error_pricing_response(
                    offer_id, 
                    "Offer not found in cache. Please search again."
                )
            
            stored_offer_data = {} 
            original_offer = stored_offer_data.get("full_offer")
            
            if not original_offer:
                return create_error_pricing_response(
                    offer_id,
                    "Original offer data not available"
                )
            
            # Clone the offer to avoid modifying the original
            modified_offer = json.loads(json.dumps(original_offer))
            
            # Add ancillary services if requested
            if additional_baggage or selected_seats:
                modified_offer = self._add_ancillary_services(
                    modified_offer, additional_baggage, selected_seats
                )
            
            # Prepare the pricing request body
            pricing_request = {
                "data": {
                    "type": "flight-offers-pricing",
                    "flightOffers": [modified_offer]
                }
            }
            
            # Build URL with include parameters for ancillaries
            url = f"{self.base_url}/v1/shopping/flight-offers/pricing"
            include_params = []
            
            if additional_baggage:
                include_params.append("bags")
            if selected_seats:
                include_params.append("other-services")
            
            if include_params:
                url += f"?include={','.join(include_params)}"
            
            # CRITICAL: Add the required header
            pricing_headers = self.headers.copy()
            pricing_headers["X-HTTP-Method-Override"] = "GET"
            pricing_headers["Content-Type"] = "application/json"
            
            response = requests.post(
                url, 
                headers=pricing_headers, 
                json=pricing_request
            )
            response.raise_for_status()
            
            # Process the pricing response
            pricing_data = response.json()
            return self._process_pricing_response(pricing_data, offer_id)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Amadeus pricing request failed: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg += f" - {error_detail}"
                except:
                    error_msg += f" - Status: {e.response.status_code}"
            return create_error_pricing_response(offer_id, error_msg)
        except Exception as e:
            return create_error_pricing_response(offer_id, f"Amadeus pricing error: {str(e)}")

    def create_booking(self, offer_id: str, passengers: List[Passenger], 
                    booking_reference: str, 
                    emergency_contact: Optional[EmergencyContact] = None) -> BookingResponse:
        """Create actual booking using Amadeus Flight Create Orders API"""
        try:
            # Extract ancillary services from passengers
            additional_baggage = {}
            selected_seats = {}
            
            # Process each passenger's selections
            for passenger_idx, passenger in enumerate(passengers):
                # Process baggage options
                if passenger.baggage_options:
                    for baggage in passenger.baggage_options:
                        segment_key = baggage.segment_id
                        if segment_key not in additional_baggage:
                            additional_baggage[segment_key] = {}
                        
                        if baggage.type == "EXTRA_BAG" or baggage.type == "CHECKED_BAG":
                            if baggage.weight:
                                additional_baggage[segment_key] = {
                                    "weight": baggage.weight,
                                    "weightUnit": "KG"
                                }
                            else:
                                additional_baggage[segment_key] = {
                                    "quantity": baggage.pieces
                                }
                
                # Process seat selections
                if passenger.seat_selection:
                    seat_key = f"traveler_{passenger_idx}_{passenger.seat_selection.segment_id}"
                    selected_seats[seat_key] = {
                        "seatNumber": passenger.seat_selection.seat_number
                    }
            
            # Get the confirmed pricing with ancillaries
            pricing_response = self.get_final_price(
                offer_id, 
                additional_baggage if additional_baggage else None,
                selected_seats if selected_seats else None
            )
            
            if not pricing_response.success:
                return create_error_booking_response(
                    f"Failed to confirm pricing: {pricing_response.error_message}"
                )
            
            # Get the priced offer from pricing response
            if not hasattr(pricing_response, 'priced_offer') or not pricing_response.priced_offer:
                return create_error_booking_response(
                    "No priced offer available for booking"
                )
            
            # Transform passengers to Amadeus format
            amadeus_travelers = self._transform_passengers_to_amadeus(passengers)
            
            # Build remarks list
            general_remarks = [{
                "subType": "GENERAL_MISCELLANEOUS",
                "text": f"Booking ref: {booking_reference}"
            }]
            
            # Add emergency contact as remark if provided
            if emergency_contact:
                emergency_text = f"EMRG CONTACT {emergency_contact.name} {emergency_contact.relationship} {emergency_contact.phone}"
                if emergency_contact.email:
                    emergency_text += f" {emergency_contact.email}"
                
                general_remarks.append({
                    "subType": "GENERAL_MISCELLANEOUS",
                    "text": emergency_text
                })
            
            # Add meal requests to remarks
            for passenger_idx, passenger in enumerate(passengers):
                if passenger.meal_option:
                    meal_text = f"MEAL P{passenger_idx + 1} S{passenger.meal_option.segment_id} {passenger.meal_option.meal_code}"
                    general_remarks.append({
                        "subType": "GENERAL_MISCELLANEOUS", 
                        "text": meal_text
                    })
            
            # Prepare booking request
            booking_request = {
                "data": {
                    "type": "flight-order",
                    "flightOffers": [pricing_response.priced_offer],
                    "travelers": amadeus_travelers,
                    "remarks": {
                        "general": general_remarks
                    },
                    "ticketingAgreement": {
                        "option": "DELAY_TO_CANCEL",
                        "delay": "6D"
                    },
                    "contacts": self._create_contact_info()
                }
            }
            
            # Make the booking request
            url = f"{self.base_url}/v1/booking/flight-orders"
            
            booking_headers = self.headers.copy()
            booking_headers["Content-Type"] = "application/json"
            
            response = requests.post(
                url,
                headers=booking_headers,
                json=booking_request
            )
            response.raise_for_status()
            
            # Process booking response
            booking_data = response.json()
            return self._process_booking_response(booking_data, booking_reference)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Amadeus booking request failed: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg += f" - {error_detail}"
                except:
                    error_msg += f" - Status: {e.response.status_code}"
            return create_error_booking_response(error_msg)
        except Exception as e:
            return create_error_booking_response(f"Amadeus booking error: {str(e)}")

    def cancel_booking(self, booking_reference: str) -> CancellationResponse:
        """Cancel booking with Amadeus"""
        return create_error_cancellation_response(
            "Amadeus cancellation requires custom implementation per airline"
        )
    
    def get_provider_name(self) -> str:
        return "amadeus"

    def _process_booking_response(self, booking_data: Dict, booking_reference: str) -> BookingResponse:
        """Process the Flight Create Orders API response"""
        try:
            # Extract booking confirmation data
            booking_info = booking_data.get("data", {})
            booking_id = booking_info.get("id")
            
            # Extract PNR from associated records
            pnr = None
            associated_records = booking_info.get("associatedRecords", [])
            for record in associated_records:
                if record.get("reference"):
                    pnr = record.get("reference")
                    break
            
            if not pnr:
                # Sometimes PNR is in different location
                pnr = booking_info.get("associatedRecords", [{}])[0].get("reference", booking_reference)
            
            # Extract flight offers from booking
            flight_offers = booking_info.get("flightOffers", [])
            
            # Extract total amount and currency from flight offers
            total_amount = Decimal("0")
            currency = "USD"
            
            if flight_offers:
                first_offer = flight_offers[0]
                price_info = first_offer.get("price", {})
                total_amount = Decimal(str(price_info.get("grandTotal", 0)))
                currency = price_info.get("currency", "USD")
            
            # Extract creation date or use current time
            creation_date_str = booking_info.get("creationDate")
            if creation_date_str:
                try:
                    # Parse ISO format: "2024-12-01T14:30:00.000"
                    created_at = datetime.fromisoformat(creation_date_str.replace('Z', '+00:00'))
                except:
                    created_at = datetime.now()
            else:
                created_at = datetime.now()
            
            # Extract ticketing information
            ticketing_agreement = booking_info.get("ticketingAgreement", {})
            last_ticketing_date = ticketing_agreement.get("dateTime")
            
            # Extract traveler information
            travelers = booking_info.get("travelers", [])
            
            # Extract contact information
            contacts = booking_info.get("contacts", [])
            
            # Determine booking status
            status = "CONFIRMED"
            if booking_info.get("queuingOfficeId"):
                status = "QUEUED_FOR_TICKETING"
            
            return BookingResponse(
                success=True,
                booking_reference=booking_reference,
                pnr=pnr,
                booking_id=booking_id,
                confirmation_number=pnr,
                status=status,
                total_amount=total_amount,
                currency=currency,
                created_at=created_at,
                provider_data={
                    "full_response": booking_data,
                    "amadeus_booking_id": booking_id,
                    "creation_date": booking_info.get("creationDate"),
                    "last_ticketing_date": last_ticketing_date,
                    "flight_offers": flight_offers,
                    "travelers": travelers,
                    "contacts": contacts,
                    "ticketing_agreement": ticketing_agreement,
                    "queuing_office_id": booking_info.get("queuingOfficeId")
                }
            )
            
        except Exception as e:
            return create_error_booking_response(
                f"Failed to process booking response: {str(e)}"
            )
    
    def _process_pricing_response(self, pricing_data: Dict, offer_id: str) -> PricingResponse:
        """Process the Flight Offers Price API response"""
        try:
            # Check for warnings (price changes)
            warnings = pricing_data.get("warnings", [])
            price_changed = False
            price_change_info = None
            
            for warning in warnings:
                if warning.get("code") == "8009":  # Price change warning
                    price_changed = True
                    price_change_info = warning.get("title", "Price has changed")
                
            # Extract the priced offer
            flight_offers = pricing_data.get("data", {}).get("flightOffers", [])
            if not flight_offers:
                return create_error_pricing_response(
                    offer_id,
                    "No flight offers returned from pricing API"
                )
            
            priced_offer = flight_offers[0]
            
            # Extract final pricing information
            price_info = priced_offer.get("price", {})
            final_total = Decimal(str(price_info.get("grandTotal", 0)))
            final_base = Decimal(str(price_info.get("base", 0)))
            currency = price_info.get("currency", "USD")
            final_tax = final_total - final_base
            
            # Check if booking is still available
            bookable_seats = priced_offer.get("numberOfBookableSeats", 0)
            is_available = bookable_seats > 0
            
            # Extract additional pricing details
            additional_services = price_info.get("additionalServices", [])
            baggage_fees = []
            for service in additional_services:
                if service.get("type") == "CHECKED_BAGS":
                    baggage_fees.append({
                        "amount": service.get("amount"),
                        "currency": service.get("currency", currency)
                    })
            
            return PricingResponse(
                success=True,
                offer_id=offer_id,
                final_price=final_total,
                base_price=final_base,
                tax_amount=final_tax,
                currency=currency,
                price_changed=price_changed,
                price_change_info=price_change_info,
                is_available=is_available,
                seats_available=bookable_seats,
                priced_offer=priced_offer,  # Store for booking
                provider_data={
                    "full_response": pricing_data,
                    "last_ticketing_date": priced_offer.get("lastTicketingDate"),
                    "instant_ticketing": priced_offer.get("instantTicketingRequired", True),
                    "baggage_fees": baggage_fees,
                    "warnings": warnings,
                    "validating_airline_codes": priced_offer.get("validatingAirlineCodes", []),
                    "traveler_pricings": priced_offer.get("travelerPricings", [])
                }
            )
            
        except Exception as e:
            return create_error_pricing_response(
                offer_id, 
                f"Failed to process pricing response: {str(e)}"
            )
    
    def _add_ancillary_services(self, offer: Dict, additional_baggage: Optional[Dict], 
                           selected_seats: Optional[Dict]) -> Dict:
        """Add ancillary services to flight offer for pricing"""
        try:
            traveler_pricings = offer.get("travelerPricings", [])
            
            for traveler_idx, traveler_pricing in enumerate(traveler_pricings):
                fare_details = traveler_pricing.get("fareDetailsBySegment", [])
                
                for segment_idx, fare_detail in enumerate(fare_details):
                    segment_id = fare_detail.get("segmentId")
                    
                    # Initialize additionalServices if not present
                    if "additionalServices" not in fare_detail:
                        fare_detail["additionalServices"] = {}
                    
                    # Add baggage
                    if additional_baggage:
                        # Check for segment-specific baggage or use all_segments default
                        baggage_for_segment = additional_baggage.get(segment_id, 
                                                                additional_baggage.get('all_segments', {}))
                        if baggage_for_segment:
                            if "quantity" in baggage_for_segment:
                                fare_detail["additionalServices"]["chargeableCheckedBags"] = {
                                    "quantity": baggage_for_segment["quantity"]
                                }
                            elif "weight" in baggage_for_segment:
                                fare_detail["additionalServices"]["chargeableCheckedBags"] = {
                                    "weight": baggage_for_segment["weight"],
                                    "weightUnit": baggage_for_segment.get("weightUnit", "KG")
                                }
                    
                    # Add seat selection
                    if selected_seats:
                        seat_key = f"traveler_{traveler_idx}_{segment_id}"
                        seat_for_segment = selected_seats.get(seat_key)
                        if seat_for_segment:
                            fare_detail["additionalServices"]["chargeableSeatNumber"] = seat_for_segment["seatNumber"]
                    
                    # Add other ancillary services if needed
                    # You can extend this for meals, priority boarding, etc.
            
            return offer
            
        except Exception as e:
            print(f"Error adding ancillary services: {e}")
            return offer  # Return original offer if modification fails
    
    # Enhanced helper methods
    def _transform_passengers_to_amadeus(self, passengers: List[Passenger]) -> List[Dict]:
        """Transform passengers to Amadeus format with full details"""
        amadeus_travelers = []
        
        for idx, passenger in enumerate(passengers):
            date_str = passenger.date_of_birth.strftime("%Y-%m-%d")
            
            traveler = {
                "id": str(idx + 1),
                "dateOfBirth": date_str,
                "name": {
                    "firstName": passenger.first_name,
                    "lastName": passenger.last_name
                },
                "gender": passenger.gender.upper() if passenger.gender else "UNKNOWN",
                "contact": {
                    "emailAddress": passenger.email,
                    "phones": []
                }
            }
            
            # Add phone if available
            if passenger.phone:
                traveler["contact"]["phones"] = [{
                    "deviceType": "MOBILE",
                    "countryCallingCode": "1",
                    "number": passenger.phone
                }]
            
            # Add documents if available
            if passenger.passport_number:
                expiry_str = passenger.passport_expiry.strftime("%Y-%m-%d") if passenger.passport_expiry else "2030-12-31"
                traveler["documents"] = [{
                    "documentType": "PASSPORT",
                    "number": passenger.passport_number,
                    "expiryDate": expiry_str,
                    "issuanceCountry": passenger.nationality or "US",
                    "validityCountry": passenger.nationality or "US",
                    "nationality": passenger.nationality or "US",
                    "holder": True
                }]
            
            amadeus_travelers.append(traveler)
        
        return amadeus_travelers
    
    def _transform_amadeus_response(self, api_response: Dict) -> Tuple[SimplifiedSearchResponse, FlightSearchResponse]:
        """Transform Amadeus response to our standard format with enhanced details"""
        try:
            offers = api_response.get("data", [])
            
            if not offers:
                error_msg = "No flights found for your search criteria"
                return (
                    create_error_model_response(error_msg),
                    create_error_search_response(error_msg, "amadeus")
                )
            
            # Get dictionaries for lookups
            dictionaries = api_response.get("dictionaries", {})
            airline_dict = dictionaries.get("carriers", {})
            aircraft_dict = dictionaries.get("aircraft", {})
            
            # Process offers with enhanced detail extraction
            flight_offers = []
            model_offers = []
            
            for idx, offer in enumerate(offers):
                try:
                    flight_offer = self._process_amadeus_offer_enhanced(offer, idx, airline_dict, aircraft_dict)
                    model_offer = self._create_model_offer(flight_offer)
                    
                    flight_offers.append(flight_offer)
                    model_offers.append(model_offer)
                except Exception as e:
                    print(f"Error processing Amadeus offer: {e}")
                    continue
            
            # Create enhanced summary
            if flight_offers:
                prices = [flight_offer.pricing.price_total for flight_offer in flight_offers]
                airlines = list(set([flight_offer.airline_code for flight_offer in flight_offers]))
                
                search_summary = FlightSearchSummary(
                    total_offers=len(flight_offers),
                    price_range_min=min(prices),
                    price_range_max=max(prices),
                    currency=flight_offers[0].pricing.currency,
                    routes_available=1,
                    airlines=airlines
                )
            else:
                search_summary = FlightSearchSummary(
                    total_offers=0,
                    price_range_min=Decimal("0"),
                    price_range_max=Decimal("0"),
                    currency="USD",
                    routes_available=0,
                    airlines=[]
                )
            
            # Create responses
            full_response = FlightSearchResponse(
                success=True,
                search_summary=search_summary,
                flights=flight_offers,
                provider_name="amadeus"
            )
            
            model_response = SimplifiedSearchResponse(
                success=True,
                summary={
                    "total_found": len(flight_offers),
                    "price_range": f"${float(search_summary.price_range_min):.0f}-${float(search_summary.price_range_max):.0f}",
                    "airlines": airlines[:3],
                    "direct_flights": len([f for f in flight_offers if f.stops == 0]),
                    "connecting_flights": len([f for f in flight_offers if f.stops > 0])
                },
                flights=model_offers
            )
            
            return model_response, full_response
            
        except Exception as e:
            error_msg = f"Amadeus response transformation error: {str(e)}"
            return (
                create_error_model_response(error_msg),
                create_error_search_response(error_msg, "amadeus")
            )
    
    def _process_amadeus_offer_enhanced(self, offer: Dict, offer_idx: int, 
                                  airline_dict: Dict, aircraft_dict: Dict) -> FlightOffer:
        """Process a single Amadeus offer with comprehensive detail extraction"""
        
        # Generate offer ID
        offer_id = offer.get("id") or f"amadeus_{offer_idx}_{int(time.time())}"
        
        # Enhanced pricing extraction
        price_info = offer.get("price", {})
        total_amount = float(price_info.get("grandTotal", 0))
        base_amount = float(price_info.get("base", 0))
        currency = price_info.get("currency", "USD")
        
        # Extract tax information
        tax_amount = total_amount - base_amount
        
        # Check for additional services (like baggage fees)
        additional_services = price_info.get("additionalServices", [])
        checked_bag_fee = None
        for service in additional_services:
            if service.get("type") == "CHECKED_BAGS":
                checked_bag_fee = Decimal(str(service.get("amount", 0)))
        
        # Enhanced pricing object
        pricing = Pricing(
            price_total=Decimal(str(total_amount)),
            base_price=Decimal(str(base_amount)),
            currency=currency,
            tax_amount=Decimal(str(tax_amount)),
            checked_bag_fee=checked_bag_fee
        )
        
        # Enhanced baggage extraction from traveler pricings
        baggage = self._extract_baggage_details(offer)
        
        # Enhanced fare details extraction
        fare_details = self._extract_fare_details(offer)
        
        # Enhanced ancillary services extraction
        ancillary_services = self._extract_ancillary_services(offer)
        
        # Get the main itinerary (first one for one-way, multiple for round-trip)
        itineraries = offer.get("itineraries", [])
        main_itinerary = itineraries[0] if itineraries else {}
        
        # Get overall departure and arrival times from the main itinerary
        departure_time, arrival_time = self._get_itinerary_times(main_itinerary)
        
        # Process all segments across all itineraries
        all_segments = []
        airlines = set()
        total_stops = 0
        
        for itinerary in itineraries:
            for segment in itinerary.get("segments", []):
                flight_segment = self._process_amadeus_segment_enhanced(segment, airline_dict, aircraft_dict, offer)
                all_segments.append(flight_segment)
                airlines.add(flight_segment.airline_code)
                total_stops += segment.get("numberOfStops", 0)
        
        # Get main itinerary segments (processed FlightSegment objects)
        main_segment_ids = [s.get("id") for s in main_itinerary.get("segments", [])]
        main_segments = [seg for seg in all_segments if seg.segment_id in main_segment_ids]
        
        # Get route info from processed segments
        first_segment = main_segments[0] if main_segments else None
        last_segment = main_segments[-1] if main_segments else None
        
        # Determine trip type
        num_itineraries = len(itineraries)
        if num_itineraries > 1:
            trip_type = TripType.ROUND_TRIP
        elif len(main_segments) > 1:
            trip_type = TripType.ONE_WAY_CONNECTING
        else:
            trip_type = TripType.ONE_WAY_DIRECT
        
        # Calculate duration from the main itinerary
        duration = main_itinerary.get("duration", "")
        duration_minutes = self._parse_duration_to_minutes(duration)
        
        return FlightOffer(
            offer_id=f"amadeus_{offer_id}",
            provider_offer_id=offer_id,
            origin=first_segment.departure_iata if first_segment else "",
            destination=last_segment.arrival_iata if last_segment else "",
            departure_time=departure_time,
            arrival_time=arrival_time,
            duration_minutes=duration_minutes or 0,
            trip_type=trip_type,
            total_segments=len(main_segments),
            stops=len(main_segments) - 1 if main_segments else 0,
            airline_code=first_segment.airline_code if first_segment else "",
            pricing=pricing,
            baggage=baggage,
            fare_details=fare_details,
            ancillary_services=ancillary_services,
            segments=all_segments,
            seats_available=offer.get("numberOfBookableSeats"),
            instant_ticketing=offer.get("instantTicketingRequired", True),
            last_ticketing_date=self._parse_datetime(offer.get("lastTicketingDate")) if offer.get("lastTicketingDate") else None, # type: ignore
            provider_data={"full_offer": offer}
        )
    
    def _extract_baggage_details(self, offer: Dict) -> Baggage:
        """Extract comprehensive baggage information from Amadeus offer"""
        traveler_pricings = offer.get("travelerPricings", [])
        
        # Default values
        checked_bags_included = 0
        cabin_bags_included = 0
        carry_on_included = False
        carry_on_weight_limit = None
        baggage_policy = {}
        
        if traveler_pricings:
            first_traveler = traveler_pricings[0]
            fare_details = first_traveler.get("fareDetailsBySegment", [])
            
            if fare_details:
                first_fare = fare_details[0]
                
                # Extract checked bags
                checked_bags = first_fare.get("includedCheckedBags", {})
                checked_bags_included = checked_bags.get("quantity", 0)
                
                # Extract cabin bags
                cabin_bags = first_fare.get("includedCabinBags", {})
                cabin_bags_included = cabin_bags.get("quantity", 0)
                carry_on_included = cabin_bags_included > 0
                
                # Extract amenities for baggage info
                amenities = first_fare.get("amenities", [])
                baggage_amenities = []
                for amenity in amenities:
                    if amenity.get("amenityType") == "BAGGAGE":
                        baggage_amenities.append({
                            "description": amenity.get("description"),
                            "chargeable": amenity.get("isChargeable", False)
                        })
                
                baggage_policy = {
                    "checked_bags_included": checked_bags_included,
                    "cabin_bags_included": cabin_bags_included,
                    "baggage_amenities": baggage_amenities
                }
        
        return Baggage(
            checked_bags_included=checked_bags_included,
            cabin_bags_included=cabin_bags_included,
            carry_on_included=carry_on_included,
            carry_on_weight_limit=carry_on_weight_limit,
            baggage_policy=baggage_policy
        )
    
    def _extract_fare_details(self, offer: Dict) -> FareDetails:
        """Extract fare class and rules from Amadeus offer"""
        traveler_pricings = offer.get("travelerPricings", [])
        
        # Default values
        fare_class = "Economy"
        refundable = False
        changeable = True
        
        if traveler_pricings:
            first_traveler = traveler_pricings[0]
            fare_details = first_traveler.get("fareDetailsBySegment", [])
            
            if fare_details:
                first_fare = fare_details[0]
                
                # Extract cabin class
                cabin = first_fare.get("cabin", "ECONOMY")
                fare_class = cabin.title()
                
                # Extract branded fare info
                branded_fare_label = first_fare.get("brandedFareLabel", "")
                if branded_fare_label:
                    fare_class = f"{fare_class} ({branded_fare_label})"
                
                # Determine refundability and changeability from fare basis
                fare_basis = first_fare.get("fareBasis", "")
                
                # Basic rules (these would be enhanced with actual fare rules data)
                if "BASIC" in branded_fare_label.upper():
                    refundable = False
                    changeable = False
                elif "SAVER" in branded_fare_label.upper():
                    refundable = False
                    changeable = True
        
        return FareDetails(
            fare_class=fare_class,
            refundable=refundable,
            changeable=changeable
        )
    
    def _extract_ancillary_services(self, offer: Dict) -> AncillaryServices:
        """Extract ancillary services from Amadeus offer"""
        traveler_pricings = offer.get("travelerPricings", [])
        
        # Default values
        seat_selection_available = False
        meal_upgrade_available = False
        priority_boarding_available = False
        lounge_access = False
        seat_types_available = []
        wifi_cost = None
        
        if traveler_pricings:
            first_traveler = traveler_pricings[0]
            fare_details = first_traveler.get("fareDetailsBySegment", [])
            
            if fare_details:
                first_fare = fare_details[0]
                amenities = first_fare.get("amenities", [])
                
                for amenity in amenities:
                    amenity_type = amenity.get("amenityType", "")
                    description = amenity.get("description", "").upper()
                    is_chargeable = amenity.get("isChargeable", False)
                    
                    if amenity_type == "PRE_RESERVED_SEAT":
                        seat_selection_available = True
                        if "EXTRA LEGROOM" in description:
                            seat_types_available.append("Extra Legroom")
                        elif "ADVANCE SEAT" in description:
                            seat_types_available.append("Standard Seat Selection")
                    
                    elif amenity_type == "MEAL":
                        if "MEAL" in description and is_chargeable:
                            meal_upgrade_available = True
                    
                    elif amenity_type == "TRAVEL_SERVICES":
                        if "PRIORITY BOARDING" in description:
                            priority_boarding_available = True
                    
                    elif amenity_type == "ENTERTAINMENT":
                        if "WIFI" in description or "INTERNET" in description:
                            if is_chargeable:
                                wifi_cost = "Available for purchase"
                            else:
                                wifi_cost = "Complimentary"
        
        return AncillaryServices(
            seat_selection_available=seat_selection_available,
            meal_upgrade_available=meal_upgrade_available,
            priority_boarding_available=priority_boarding_available,
            lounge_access=lounge_access,
            seat_types_available=seat_types_available,
            wifi_cost=wifi_cost
        )
    
    def _process_amadeus_segment_enhanced(self, segment: Dict, airline_dict: Dict, 
                                        aircraft_dict: Dict, offer: Dict) -> FlightSegment:
        """Process a single Amadeus segment with enhanced details"""
        airline_code = segment.get("carrierCode", "")
        aircraft_code = segment.get("aircraft", {}).get("code")
        duration_minutes = self._parse_duration_to_minutes(segment.get("duration"))
        
        # Parse datetime strings
        departure_info = segment.get("departure", {})
        arrival_info = segment.get("arrival", {})
        
        departure_time = self._parse_datetime(departure_info.get("at", ""))
        arrival_time = self._parse_datetime(arrival_info.get("at", ""))
        
        # Extract cabin class from traveler pricing
        cabin_class = CabinClass.ECONOMY  # Default
        traveler_pricings = offer.get("travelerPricings", [])
        if traveler_pricings:
            fare_details = traveler_pricings[0].get("fareDetailsBySegment", [])
            for fare_detail in fare_details:
                if fare_detail.get("segmentId") == segment.get("id"):
                    cabin = fare_detail.get("cabin", "ECONOMY")
                    cabin_class = self._map_cabin_class(cabin)
                    break
        
        # Extract meal and entertainment options
        meal_options = []
        wifi_available = False
        power_outlets = False
        entertainment = False
        
        # Get amenities for this segment
        if traveler_pricings:
            fare_details = traveler_pricings[0].get("fareDetailsBySegment", [])
            for fare_detail in fare_details:
                if fare_detail.get("segmentId") == segment.get("id"):
                    amenities = fare_detail.get("amenities", [])
                    for amenity in amenities:
                        description = amenity.get("description", "").upper()
                        amenity_type = amenity.get("amenityType", "")
                        
                        if amenity_type == "MEAL":
                            if not amenity.get("isChargeable", False):
                                if "SNACK" in description:
                                    meal_options.append("Complimentary Snack")
                                elif "MEAL" in description:
                                    meal_options.append("Complimentary Meal")
                                elif "DRINK" in description:
                                    meal_options.append("Complimentary Beverages")
                        
                        elif amenity_type == "ENTERTAINMENT":
                            if "POWER" in description or "USB" in description:
                                power_outlets = True
                            if "WIFI" in description or "INTERNET" in description:
                                wifi_available = True
                            entertainment = True
                    break
        
        return FlightSegment(
            airline_code=airline_code,
            airline_name=airline_dict.get(airline_code, "Unknown"),
            flight_number=segment.get("number", ""),
            departure_iata=departure_info.get("iataCode", ""),
            arrival_iata=arrival_info.get("iataCode", ""),
            departure_time=departure_time,
            arrival_time=arrival_time,
            duration_minutes=duration_minutes or 0,
            stops=segment.get("numberOfStops", 0),
            cabin_class=cabin_class,
            departure_terminal=departure_info.get("terminal"),
            arrival_terminal=arrival_info.get("terminal"),
            aircraft_code=aircraft_code,
            aircraft_name=aircraft_dict.get(aircraft_code, "Unknown") if aircraft_code else "Unknown",
            operating_carrier=segment.get("operating", {}).get("carrierCode", airline_code),
            segment_id=segment.get("id"),
            wifi_available=wifi_available,
            power_outlets=power_outlets,
            entertainment=entertainment,
            meal_options=meal_options
        )
    
    def _map_cabin_class(self, amadeus_cabin: str) -> CabinClass:
        """Map Amadeus cabin class to our enum"""
        mapping = {
            "ECONOMY": CabinClass.ECONOMY,
            "PREMIUM_ECONOMY": CabinClass.PREMIUM_ECONOMY,
            "BUSINESS": CabinClass.BUSINESS,
            "FIRST": CabinClass.FIRST
        }
        return mapping.get(amadeus_cabin.upper(), CabinClass.ECONOMY)
    
    def _parse_datetime(self, datetime_str: str) -> datetime:
        """Parse Amadeus datetime string to datetime object"""
        if not datetime_str:
            return datetime.now()
        try:
            # Amadeus format: "2025-10-18T20:29:00" (already in correct ISO format)
            return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        except Exception as e:
            logger.warning(f"Failed to parse datetime '{datetime_str}': {e}")
            return datetime.now()
    
    def _get_itinerary_times(self, itinerary: Dict) -> Tuple[datetime, datetime]:
        """Get the actual departure and arrival times for an itinerary"""
        segments = itinerary.get("segments", [])
        if not segments:
            return datetime.now(), datetime.now()
        
        # First segment departure time
        first_segment = segments[0]
        departure_time = self._parse_datetime(
            first_segment.get("departure", {}).get("at", "")
        )
        
        # Last segment arrival time  
        last_segment = segments[-1]
        arrival_time = self._parse_datetime(
            last_segment.get("arrival", {}).get("at", "")
        )
        
        return departure_time, arrival_time
    
    def _create_model_offer(self, flight_offer: FlightOffer) -> SimplifiedFlightOffer:
        """Create simplified model offer from full flight offer with enhanced info"""
        # Format duration from minutes
        duration_str = self._format_duration_minutes(flight_offer.duration_minutes)
        
        # Enhanced stops text with connection info
        if flight_offer.stops == 0:
            stops_text = "Direct"
        else:
            stops_text = f"{flight_offer.stops} stop{'s' if flight_offer.stops > 1 else ''}"
            # Add connection airports if available
            main_segments = [seg for seg in flight_offer.segments if seg.segment_id in [s.get("id") for s in flight_offer.provider_data["full_offer"].get("itineraries", [{}])[0].get("segments", [])]]
            if len(main_segments) > 1:
                connection_airports = []
                for i in range(len(main_segments) - 1):
                    connection_airports.append(main_segments[i].arrival_iata)
                if connection_airports:
                    stops_text += f" ({', '.join(connection_airports)})"
        
        # Extract time from datetime objects - format in local time
        departure_time = flight_offer.departure_time.strftime("%H:%M")
        arrival_time = flight_offer.arrival_time.strftime("%H:%M")
        
        # Add date if arrival is next day
        if flight_offer.arrival_time.date() > flight_offer.departure_time.date():
            arrival_time += "+1"
        
        # Get airline name from first segment
        airline_name = flight_offer.segments[0].airline_name if flight_offer.segments else "Unknown"
        
        return SimplifiedFlightOffer(
            id=flight_offer.offer_id,
            price=f"${float(flight_offer.pricing.price_total):.0f}",
            airline=airline_name,
            route=f"{flight_offer.origin} → {flight_offer.destination}",
            departure=departure_time,
            arrival=arrival_time,
            duration=duration_str,
            stops=stops_text
        )
        
    def _parse_duration_to_minutes(self, duration_str: Optional[str]) -> Optional[int]:
        """Parse ISO 8601 duration to minutes (PT1H55M -> 115)"""
        if not duration_str:
            return None
            
        # Parse PT1H55M format
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?'
        match = re.match(pattern, duration_str)
        if not match:
            return None
            
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        return hours * 60 + minutes
    
    def _format_duration_minutes(self, duration_minutes: int) -> str:
        """Format duration minutes to display string"""
        if not duration_minutes:
            return ""
            
        hours = duration_minutes // 60
        minutes = duration_minutes % 60
        
        if hours and minutes:
            return f"{hours}h {minutes}m"
        elif hours:
            return f"{hours}h"
        elif minutes:
            return f"{minutes}m"
        else:
            return ""