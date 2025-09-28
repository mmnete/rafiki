# ==============================================================================
# app/storage/services/booking_storage_service.py
# ==============================================================================
from typing import Dict, Any, List, Optional, Tuple
import json
import random
import string
from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from app.storage.db_service import StorageService
from app.storage.services.shared_storage import SharedStorageService
from app.services.api.flights.response_models import Passenger, PassengerType
from app.services.api.flights.flight_service import FlightService
from app.storage.services.passenger_storage_service import PassengerProfile

@dataclass
class Booking:
    id: str
    booking_reference: str
    primary_user_id: int
    group_size: int
    booking_type: str
    search_id: Optional[str]
    selected_flight_offers: List[Dict[str, Any]]
    trip_type: str
    origin_airport: Optional[str]
    destination_airport: Optional[str]
    departure_date: Optional[date]
    return_date: Optional[date]
    base_price: Decimal
    taxes_and_fees: Decimal
    service_fee: Decimal
    insurance_fee: Decimal
    total_amount: Decimal
    currency: str
    booking_status: str
    payment_status: str
    fulfillment_status: str
    provider_name: Optional[str]
    provider_booking_id: Optional[str]
    provider_pnr: Optional[str]
    provider_response: Dict[str, Any]
    travel_insurance: bool
    special_requests: Optional[str]
    accessibility_requirements: Optional[str]
    emergency_contact_name: Optional[str]
    emergency_contact_phone: Optional[str]
    emergency_contact_relationship: Optional[str]
    emergency_contact_email: Optional[str]
    confirmation_deadline: Optional[datetime]
    payment_deadline: Optional[datetime]
    checkin_available_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    confirmed_at: Optional[datetime]
    cancelled_at: Optional[datetime]

@dataclass
class BookingFlightSegment:
    id: str
    booking_id: str
    flight_offer_id: str
    segment_sequence: int
    segment_type: str
    airline_code: str
    airline_name: Optional[str]
    flight_number: str
    aircraft_type: Optional[str]
    departure_airport: str
    departure_terminal: Optional[str]
    departure_time: datetime
    arrival_airport: str
    arrival_terminal: Optional[str]
    arrival_time: datetime
    duration_minutes: Optional[int]
    distance_km: Optional[int]
    flight_status: str
    actual_departure_time: Optional[datetime]
    actual_arrival_time: Optional[datetime]
    delay_minutes: int
    gate_info: Optional[str]
    created_at: datetime
    updated_at: datetime

@dataclass
class BookingTimelineEvent:
    id: int
    booking_id: str
    event_type: str
    event_description: Optional[str]
    event_data: Dict[str, Any]
    triggered_by_user_id: Optional[int]
    system_event: bool
    created_at: datetime

class BookingStorageService:
    """
    Service for managing flight bookings and related data
    
    Responsibilities:
    - Create and manage flight bookings
    - Handle booking status changes and timeline
    - Integration with external booking providers
    - Provide booking context for model decisions
    """
    
    def __init__(self, storage: StorageService, shared_storage: Optional[SharedStorageService]=None):
        self.storage = storage
        self.shared_storage = shared_storage
    
    # ====================================================================
    # CORE BOOKING CRUD OPERATIONS
    # ====================================================================
    
    def create_booking(self, **booking_data) -> Optional[str]:
        """Create a new booking and return booking ID"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                # Generate booking reference if not provided
                if 'booking_reference' not in booking_data:
                    booking_data['booking_reference'] = self._generate_booking_reference()
                
                # Handle JSON fields
                if 'selected_flight_offers' in booking_data:
                    if isinstance(booking_data['selected_flight_offers'], (list, dict)):
                        booking_data['selected_flight_offers'] = json.dumps(booking_data['selected_flight_offers'])
                
                if 'provider_response' in booking_data:
                    if isinstance(booking_data['provider_response'], dict):
                        booking_data['provider_response'] = json.dumps(booking_data['provider_response'])
                
                # Build insert query dynamically
                fields = list(booking_data.keys())
                placeholders = ', '.join(['%s'] * len(fields))
                field_names = ', '.join(fields)
                
                insert_query = f"""
                    INSERT INTO bookings ({field_names})
                    VALUES ({placeholders})
                    RETURNING id;
                """
                
                cur.execute(insert_query, list(booking_data.values()))
                result = cur.fetchone()
                
                if result:
                    booking_id = result[0]
                    
                    # Add timeline event
                    self.add_timeline_event(
                        booking_id=booking_id,
                        event_type='booking_created',
                        event_description='Booking created',
                        triggered_by_user_id=booking_data.get('primary_user_id')
                    )
                    
                    return booking_id
                else:
                    return None
                
        except Exception as e:
            print(f"Error creating booking: {e}")
            return None
    
    def get_booking(self, booking_id: str) -> Optional[Booking]:
        """Get booking by ID"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, booking_reference, primary_user_id, group_size, booking_type,
                        search_id, selected_flight_offers, trip_type, origin_airport,
                        destination_airport, departure_date, return_date, base_price,
                        taxes_and_fees, service_fee, insurance_fee, total_amount, currency,
                        booking_status, payment_status, fulfillment_status, 
                        provider_name, provider_booking_id, provider_pnr, provider_response,
                        travel_insurance, special_requests, accessibility_requirements,
                        emergency_contact_name, emergency_contact_phone, 
                        emergency_contact_relationship, emergency_contact_email,
                        confirmation_deadline, payment_deadline, checkin_available_at,
                        created_at, updated_at, confirmed_at, cancelled_at
                    FROM bookings WHERE id = %s;
                """, (booking_id,))
                
                row = cur.fetchone()
                if row:
                    return Booking(
                        id=row[0], booking_reference=row[1], primary_user_id=row[2],
                        group_size=row[3], booking_type=row[4], search_id=row[5],
                        selected_flight_offers=self._safe_json_parse(row[6], []), # type: ignore
                        trip_type=row[7], origin_airport=row[8], destination_airport=row[9],
                        departure_date=row[10], return_date=row[11], base_price=row[12],
                        taxes_and_fees=row[13], service_fee=row[14], insurance_fee=row[15],
                        total_amount=row[16], currency=row[17], booking_status=row[18],
                        payment_status=row[19], fulfillment_status=row[20],
                        provider_name=row[21], provider_booking_id=row[22], 
                        provider_pnr=row[23], provider_response=self._safe_json_parse(row[24], {}), # type: ignore
                        travel_insurance=row[25], special_requests=row[26],
                        accessibility_requirements=row[27], emergency_contact_name=row[28],
                        emergency_contact_phone=row[29], emergency_contact_relationship=row[30],
                        emergency_contact_email=row[31], confirmation_deadline=row[32],
                        payment_deadline=row[33], checkin_available_at=row[34],
                        created_at=row[35], updated_at=row[36], confirmed_at=row[37],
                        cancelled_at=row[38]
                    )
                return None
                
        except Exception as e:
            print(f"Error getting booking: {e}")
            return None
    
    def get_bookings_for_user(self, user_id: int, limit: int = 50, offset: int = 0) -> List[Booking]:
        """Get bookings for a specific user"""
        if not self.storage.conn:
            return []
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, booking_reference, primary_user_id, group_size, booking_type,
                        search_id, selected_flight_offers, trip_type, origin_airport,
                        destination_airport, departure_date, return_date, base_price,
                        taxes_and_fees, service_fee, insurance_fee, total_amount, currency,
                        booking_status, payment_status, fulfillment_status,
                        provider_name, provider_booking_id, provider_pnr, provider_response,
                        travel_insurance, special_requests, accessibility_requirements,
                        emergency_contact_name, emergency_contact_phone,
                        emergency_contact_relationship, emergency_contact_email,
                        confirmation_deadline, payment_deadline, checkin_available_at,
                        created_at, updated_at, confirmed_at, cancelled_at
                    FROM bookings 
                    WHERE primary_user_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s OFFSET %s;
                """, (user_id, limit, offset))
                
                return [self._row_to_booking(row) for row in cur.fetchall()]
                
        except Exception as e:
            print(f"Error getting user bookings: {e}")
            return []
    
    def update_booking(self, booking_id: str, update_data: Dict[str, Any]) -> bool:
        """Update booking with arbitrary fields"""
        if not self.storage.conn:
            return False
        
        try:
            with self.storage.conn.cursor() as cur:
                # Build update query dynamically
                update_fields = []
                update_values = []
                
                for field, value in update_data.items():
                    if field in ['provider_response', 'selected_flight_offers'] and isinstance(value, dict):
                        update_fields.append(f"{field} = %s")
                        update_values.append(json.dumps(value))
                    else:
                        update_fields.append(f"{field} = %s")
                        update_values.append(value)
                
                if not update_fields:
                    return False
                
                update_values.append(booking_id)
                
                cur.execute(f"""
                    UPDATE bookings 
                    SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                """, update_values)
                
                return cur.rowcount > 0
                
        except Exception as e:
            print(f"Error updating booking: {e}")
            return False
    
    def update_booking_status(self, booking_id: str, status: str, 
                            triggered_by_user_id: Optional[int] = None) -> bool:
        """Update booking status and add timeline event"""
        if not self.storage.conn:
            return False
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    UPDATE bookings 
                    SET booking_status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                """, (status, booking_id))
                
                if cur.rowcount > 0:
                    self.add_timeline_event(
                        booking_id=booking_id,
                        event_type='booking_status_updated',
                        event_description=f'Status changed to {status}',
                        event_data={'new_status': status},
                        triggered_by_user_id=triggered_by_user_id
                    )
                    return True
                return False
                
        except Exception as e:
            print(f"Error updating booking status: {e}")
            return False
    
    def get_booking_context(self, booking_id: str) -> Dict[str, Any]:
        """Get essential booking context for model decision-making"""
        try:
            booking = self.get_booking(booking_id)
            if not booking:
                return {"error": "Booking not found"}
            
            # Get passenger count from booking_passengers table
            current_passengers = 0
            if self.storage.conn:
                with self.storage.conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM booking_passengers WHERE booking_id = %s", (booking_id,))
                    result = cur.fetchone()
                    if result:
                        current_passengers = result[0]
            
            # Calculate completion status
            passengers_complete = current_passengers >= booking.group_size
            emergency_contact_complete = bool(booking.emergency_contact_name and booking.emergency_contact_phone)
            
            # Determine next actions needed
            next_actions = []
            if current_passengers < booking.group_size:
                next_actions.append(f"Add {booking.group_size - current_passengers} more passenger(s)")
            if not emergency_contact_complete:
                next_actions.append("Add emergency contact information")
            if passengers_complete and emergency_contact_complete and booking.booking_status == 'draft':
                next_actions.append("Ready for finalization")
            
            return {
                "booking_id": booking.id,
                "booking_reference": booking.booking_reference,
                "status": booking.booking_status,
                "payment_status": booking.payment_status,
                "booking_type": booking.booking_type,
                "trip_type": booking.trip_type,
                "route": f"{booking.origin_airport} → {booking.destination_airport}" if booking.origin_airport else None,
                "departure_date": booking.departure_date.isoformat() if booking.departure_date else None,
                "return_date": booking.return_date.isoformat() if booking.return_date else None,
                "passenger_info": {
                    "required_count": booking.group_size,
                    "current_count": current_passengers,
                    "passengers_complete": passengers_complete,
                    "missing_passengers": max(0, booking.group_size - current_passengers)
                },
                "emergency_contact": {
                    "name": booking.emergency_contact_name,
                    "phone": booking.emergency_contact_phone,
                    "relationship": booking.emergency_contact_relationship,
                    "email": booking.emergency_contact_email,
                    "complete": emergency_contact_complete
                },
                "pricing": {
                    "total_amount": float(booking.total_amount),
                    "currency": booking.currency,
                    "service_fee": float(booking.service_fee)
                },
                "provider_info": {
                    "provider_name": booking.provider_name,
                    "pnr": booking.provider_pnr
                },
                "special_requests": booking.special_requests,
                "accessibility_requirements": booking.accessibility_requirements,
                "next_actions": next_actions,
                "can_finalize": passengers_complete and emergency_contact_complete,
                "created_at": booking.created_at.isoformat(),
                "updated_at": booking.updated_at.isoformat()
            }
            
        except Exception as e:
            return {"error": f"Get booking context failed: {str(e)}"}
    
    def get_user_bookings(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Get user's bookings with optional filtering"""
        try:
            status_filter = kwargs.get('status')
            include_past = kwargs.get('include_past', False)
            
            bookings = self.get_bookings_for_user(user_id, limit=50)
            
            # Apply filters
            if status_filter:
                bookings = [b for b in bookings if b.booking_status == status_filter]
            
            if not include_past:
                current_time = datetime.now()
                bookings = [b for b in bookings if b.departure_date and b.departure_date >= current_time.date()]
            
            return {
                'success': True,
                'bookings': [
                    {
                        'booking_id': b.id,
                        'booking_reference': b.booking_reference,
                        'status': b.booking_status,
                        'origin': b.origin_airport,
                        'destination': b.destination_airport,
                        'departure_date': b.departure_date.isoformat() if b.departure_date else None,
                        'total_amount': float(b.total_amount),
                        'currency': b.currency,
                        'pnr': b.provider_pnr
                    } for b in bookings
                ]
            }
            
        except Exception as e:
            return {"error": f"Get user bookings failed: {str(e)}"}
    
    # ====================================================================
    # FLIGHT SEGMENT MANAGEMENT
    # ====================================================================
    
    def add_flight_segment(self, booking_id: str, **segment_data) -> Optional[str]:
        """Add a flight segment to a booking"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                # Get next segment sequence number
                cur.execute("""
                    SELECT COALESCE(MAX(segment_sequence), 0) + 1
                    FROM booking_flight_segments WHERE booking_id = %s;
                """, (booking_id,))
                
                segment_data['booking_id'] = booking_id
                result = cur.fetchone()
                if result:
                    segment_data['segment_sequence'] = result[0]
                
                # Build insert query
                fields = list(segment_data.keys())
                placeholders = ', '.join(['%s'] * len(fields))
                field_names = ', '.join(fields)
                
                cur.execute(f"""
                    INSERT INTO booking_flight_segments ({field_names})
                    VALUES ({placeholders})
                    RETURNING id;
                """, list(segment_data.values()))
                
                result = cur.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            print(f"Error adding flight segment: {e}")
            return None
    
    def get_booking_flight_segments(self, booking_id: str) -> List[BookingFlightSegment]:
        """Get all flight segments for a booking"""
        if not self.storage.conn:
            return []
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, booking_id, flight_offer_id, segment_sequence, segment_type,
                           airline_code, airline_name, flight_number, aircraft_type,
                           departure_airport, departure_terminal, departure_time,
                           arrival_airport, arrival_terminal, arrival_time, duration_minutes,
                           distance_km, flight_status, actual_departure_time, 
                           actual_arrival_time, delay_minutes, gate_info, created_at, updated_at
                    FROM booking_flight_segments 
                    WHERE booking_id = %s 
                    ORDER BY segment_sequence;
                """, (booking_id,))
                
                return [
                    BookingFlightSegment(
                        id=row[0], booking_id=row[1], flight_offer_id=row[2],
                        segment_sequence=row[3], segment_type=row[4], airline_code=row[5],
                        airline_name=row[6], flight_number=row[7], aircraft_type=row[8],
                        departure_airport=row[9], departure_terminal=row[10],
                        departure_time=row[11], arrival_airport=row[12],
                        arrival_terminal=row[13], arrival_time=row[14],
                        duration_minutes=row[15], distance_km=row[16],
                        flight_status=row[17], actual_departure_time=row[18],
                        actual_arrival_time=row[19], delay_minutes=row[20],
                        gate_info=row[21], created_at=row[22], updated_at=row[23]
                    )
                    for row in cur.fetchall()
                ]
                
        except Exception as e:
            print(f"Error getting flight segments: {e}")
            return []
    
    # ====================================================================
    # TIMELINE EVENT MANAGEMENT
    # ====================================================================
    
    def add_timeline_event(self, booking_id: str, event_type: str, 
                          event_description: Optional[str] = None,
                          event_data: Optional[Dict[str, Any]] = None,
                          triggered_by_user_id: Optional[int] = None,
                          system_event: bool = False) -> bool:
        """Add an event to the booking timeline"""
        if not self.storage.conn:
            return False
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO booking_timeline (
                        booking_id, event_type, event_description, event_data,
                        triggered_by_user_id, system_event
                    ) VALUES (%s, %s, %s, %s, %s, %s);
                """, (
                    booking_id, event_type, event_description,
                    json.dumps(event_data or {}), triggered_by_user_id, system_event
                ))
                
                return True
                
        except Exception as e:
            print(f"Error adding timeline event: {e}")
            return False
    
    def get_booking_timeline(self, booking_id: str) -> List[BookingTimelineEvent]:
        """Get timeline events for a booking"""
        if not self.storage.conn:
            return []
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, booking_id, event_type, event_description, event_data,
                           triggered_by_user_id, system_event, created_at
                    FROM booking_timeline 
                    WHERE booking_id = %s 
                    ORDER BY created_at DESC;
                """, (booking_id,))
                
                return [
                    BookingTimelineEvent(
                        id=row[0], booking_id=row[1], event_type=row[2],
                        event_description=row[3], event_data=self._safe_json_parse(row[4], {}), # type: ignore
                        triggered_by_user_id=row[5], system_event=row[6], created_at=row[7]
                    )
                    for row in cur.fetchall()
                ]
                
        except Exception as e:
            print(f"Error getting timeline: {e}")
            return []
    
    # ====================================================================
    # MAIN TOOL OPERATION HANDLER
    # ====================================================================
    
    def handle_booking_operation(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Main handler for all booking operations from tools"""
        operation = kwargs.get('action', 'create')
        
        if operation == 'create':
            return self._handle_create_booking(user_id, **kwargs)
        elif operation == 'get':
            return self._handle_get_booking_context(user_id, **kwargs)
        elif operation == 'update_booking':
            return self._handle_update_booking(user_id, **kwargs)
        elif operation == 'add_emergency_contact':
            return self._handle_add_emergency_contact(user_id, **kwargs)
        elif operation == 'finalize':
            return self._handle_finalize_booking(user_id, **kwargs)
        else:
            return {"error": f"Unknown operation: {operation}"}
    
    # ====================================================================
    # PRIVATE OPERATION HANDLERS
    # ====================================================================

    def _handle_create_booking(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Handle booking creation from tool"""
        try:
            search_id = kwargs.get('search_id')
            flight_offer_ids = kwargs.get('flight_offer_ids', [])
            
            if not search_id:
                return {"error": "Search ID required for booking creation"}
            
            # Get cached search data if shared_storage is available
            search_data = None
            if self.shared_storage:
                search_data = self.shared_storage.get_cached_search(user_id, search_id)
                if not search_data:
                    return {"error": "Search results expired. Please search again."}
            
            # Create booking with basic info
            booking_data = {
                'primary_user_id': user_id,
                'booking_type': kwargs.get('booking_type', 'individual'),
                'search_id': search_id,
                'selected_flight_offers': flight_offer_ids,
                'booking_status': 'draft',
                'payment_status': 'pending',
                'fulfillment_status': 'pending',
                'group_size': kwargs.get('passenger_count', 1),
                'provider_name': 'amadeus',  # Default provider
                'base_price': 0.00,
                'taxes_and_fees': 0.00,
                'service_fee': 5.00,
                'insurance_fee': 0.00,
                'total_amount': 5.00,
                'currency': 'USD',
                'travel_insurance': False
            }
            
            # Add search data if available
            if search_data:
                booking_data.update({
                    'trip_type': search_data.get('trip_type', 'one_way'),
                    'origin_airport': search_data.get('origin'),
                    'destination_airport': search_data.get('destination'),
                    'departure_date': search_data.get('departure_date'),
                    'return_date': search_data.get('return_date')
                })
            
            booking_id = self.create_booking(**booking_data)
            
            if booking_id:
                return {
                    'success': True,
                    'search_id': search_id,
                    'booking_id': booking_id,
                    'status': 'draft',
                    'message': 'Booking draft created successfully'
                }
            else:
                return {"error": "Failed to create booking"}
                
        except Exception as e:
            print(f"Booking creation error: {e}")
            return {"error": f"Booking creation failed: {str(e)}"}
    
    def _handle_get_booking_context(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Handle getting booking context"""
        try:
            booking_id = kwargs.get('booking_id')
            if not booking_id:
                return {"error": "booking_id required"}
            
            # Verify booking belongs to user
            booking = self.get_booking(str(booking_id))
            if not booking:
                return {"error": "Booking not found"}
            
            if booking.primary_user_id != user_id:
                return {"error": "Access denied to this booking"}
            
            return self.get_booking_context(str(booking_id))
            
        except Exception as e:
            return {"error": f"Get booking context failed: {str(e)}"}
    
    def _handle_update_booking(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Handle booking-level updates"""
        try:
            booking_id = str(kwargs.get('booking_id'))
            
            # Verify booking exists and belongs to user
            booking = self.get_booking(booking_id)
            if not booking:
                return {"error": "Booking not found"}
            
            if booking.primary_user_id != user_id:
                return {"error": "Access denied to this booking"}
            
            # Build update data
            update_data = {}
            updated_fields = []
            
            # Update fields
            for field in ['group_size', 'booking_type', 'special_requests', 'accessibility_requirements']:
                if field in kwargs:
                    update_data[field] = kwargs[field]
                    updated_fields.append(field)
            
            if not update_data:
                return {"error": "No changes detected"}
            
            # Perform the update
            success = self.update_booking(booking_id, update_data)
            
            if success:
                self.add_timeline_event(
                    booking_id=booking_id,
                    event_type='booking_updated',
                    event_description=f'Booking details updated: {", ".join(updated_fields)}',
                    event_data={'updated_fields': updated_fields, 'changes': update_data},
                    triggered_by_user_id=user_id
                )
                
                return {
                    'success': True,
                    'booking_id': booking_id,
                    'updated_fields': updated_fields,
                    'message': f'Booking updated successfully'
                }
            else:
                return {"error": "Failed to update booking"}
                
        except Exception as e:
            return {"error": f"Update booking failed: {str(e)}"}
    
    def _handle_add_emergency_contact(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Handle adding emergency contact information"""
        try:
            booking_id = str(kwargs.get('booking_id'))
            
            # Verify booking exists and belongs to user
            booking = self.get_booking(booking_id)
            if not booking:
                return {"error": "Booking not found"}
            
            if booking.primary_user_id != user_id:
                return {"error": "Access denied to this booking"}
            
            # Build emergency contact data
            emergency_data = {}
            for field in ['emergency_contact_name', 'emergency_contact_phone', 
                         'emergency_contact_relationship', 'emergency_contact_email']:
                if field in kwargs:
                    emergency_data[field] = kwargs[field]
            
            if not emergency_data:
                return {"error": "No emergency contact information provided"}
            
            # Update booking with emergency contact
            success = self.update_booking(booking_id, emergency_data)
            
            if success:
                self.add_timeline_event(
                    booking_id=booking_id,
                    event_type='emergency_contact_added',
                    event_description='Emergency contact information added',
                    event_data=emergency_data,
                    triggered_by_user_id=user_id
                )
                
                return {
                    'success': True,
                    'booking_id': booking_id,
                    'message': 'Emergency contact information added successfully'
                }
            else:
                return {"error": "Failed to add emergency contact information"}
                
        except Exception as e:
            return {"error": f"Add emergency contact failed: {str(e)}"}
    
    def _handle_finalize_booking(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Handle booking finalization with provider integration"""
        try:
            booking_id = str(kwargs.get('booking_id'))
            
            # Verify booking exists and belongs to user
            booking = self.get_booking(booking_id)
            if not booking:
                return {"error": "Booking not found"}
            
            if booking.primary_user_id != user_id:
                return {"error": "Access denied to this booking"}
            
            # Check if booking is ready for finalization
            booking_context = self.get_booking_context(booking_id)
            if 'error' in booking_context:
                return {"error": f"Cannot get booking status: {booking_context['error']}"}
            
            if not booking_context.get('can_finalize', False):
                missing_actions = booking_context.get('next_actions', [])
                missing_desc = [action for action in missing_actions if action != "Ready for finalization"]
                return {
                    "error": f"Booking not ready for finalization. Missing: {', '.join(missing_desc)}"
                }
            
            # Get flight service instance
            flight_service = self._get_flight_service()
            if not flight_service:
                return {"error": "Flight service not available"}
            
            # Extract flight offer information from booking
            selected_offers = booking.selected_flight_offers
            if not selected_offers:
                return {"error": "No flight offers selected in booking"}

            # Get provider name (default to duffel)
            provider_name = booking.provider_name or "duffel"

            # Extract offer ID - handle different formats
            offer_id = None
            if isinstance(selected_offers, list) and len(selected_offers) > 0:
                # Could be a list of strings or list of dicts
                first_offer = selected_offers[0]
                if isinstance(first_offer, str):
                    offer_id = first_offer
                elif isinstance(first_offer, dict):
                    # If it's a dict, look for common ID fields
                    offer_id = first_offer.get('id') or first_offer.get('offer_id') or first_offer.get('flight_offer_id')
                else:
                    return {"error": f"Unexpected offer format: {type(first_offer)}"}
            elif isinstance(selected_offers, str):
                offer_id = selected_offers
            else:
                return {"error": f"Invalid flight offer format in booking: {type(selected_offers)}"}

            if not offer_id:
                return {"error": "Could not extract offer ID from selected offers"}

            # Clean up offer ID to get provider offer ID
            if isinstance(offer_id, str) and offer_id.startswith(f"{provider_name}_"):
                clean_offer_id = offer_id.replace(f"{provider_name}_", "")
            else:
                clean_offer_id = str(offer_id)  # Ensure it's a string
            
            # Get final pricing from provider
            pricing_response = flight_service.get_final_price(clean_offer_id, provider_name)
            if not pricing_response.success:
                return {"error": f"Failed to get final pricing: {pricing_response.error_message}"}
            
            # Get passenger data for booking
            passengers = self._get_passengers_for_booking(booking_id)
            if not passengers:
                return {"error": "No passengers found for booking"}
            
            # Generate booking reference if not exists
            if not booking.booking_reference:
                booking_reference = self._generate_booking_reference()
                self.update_booking(booking_id, {"booking_reference": booking_reference})
            else:
                booking_reference = booking.booking_reference
            
            # Create booking with provider
            booking_response = flight_service.create_booking(
                offer_id=clean_offer_id,
                passengers=passengers,
                booking_reference=booking_reference,
                provider=provider_name
            )
            
            if not booking_response.success:
                return {"error": f"Failed to create provider booking: {booking_response.error_message}"}
            
            # Update booking with provider response
            final_amount = pricing_response.final_price
            update_data = {
                'provider_booking_id': booking_response.booking_id,
                'provider_pnr': booking_response.booking_reference,
                'provider_response': booking_response.provider_data,
                'booking_status': 'confirmed_pending_payment',
                'total_amount': final_amount,
                'base_price': pricing_response.base_price,
                'taxes_and_fees': pricing_response.tax_amount,
                'currency': pricing_response.currency
            }
            
            success = self.update_booking(booking_id, update_data)
            
            if not success:
                return {"error": "Failed to update booking with provider information"}
            
            # Add timeline event
            self.add_timeline_event(
                booking_id=booking_id,
                event_type='booking_finalized',
                event_description='Booking finalized with airline, awaiting payment',
                event_data={
                    'provider': provider_name,
                    'pnr': booking_response.booking_reference,
                    'final_amount': final_amount,
                    'currency': pricing_response.currency
                },
                triggered_by_user_id=user_id
            )
            
            return {
                'success': True,
                'booking_id': booking_id,
                'pnr': booking_response.booking_reference,
                'final_price': final_amount,
                'currency': pricing_response.currency,
                'provider': provider_name,
                'booking_reference': booking.booking_reference,
                'status': 'confirmed_pending_payment',
                'message': 'Booking finalized successfully. Payment required to complete.'
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": f"Finalization failed: {str(e)}"}

    def _get_flight_service(self) -> Optional[FlightService]:
        """Get flight service instance - to be injected via constructor"""
        # This should be injected in the constructor
        # For now, we'll assume it's available in shared_storage or similar
        return getattr(self, 'flight_service', None)

    def _get_passengers_for_booking(self, booking_id: str) -> List:
        """Get passengers formatted for provider APIs"""
        if not self.storage.conn:
            return []
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT first_name, last_name, date_of_birth, gender, nationality,
                        passport_number, document_expiry, seat_preference, meal_preference
                    FROM booking_passengers 
                    WHERE booking_id = %s 
                    ORDER BY created_at;
                """, (booking_id,))
                
                passengers = []
                for row in cur.fetchall():
                    # Convert date strings to datetime objects
                    date_of_birth = row[2] if isinstance(row[2], datetime) else datetime.fromisoformat(row[2]) if row[2] else datetime(1990, 1, 1)
                    passport_expiry = None
                    if row[6]:
                        passport_expiry = row[6] if isinstance(row[6], datetime) else datetime.fromisoformat(row[6])
                    
                    passenger = Passenger(
                        passenger_type=PassengerType.ADULT,  # Default, could be enhanced
                        first_name=row[0] or "",
                        last_name=row[1] or "",
                        date_of_birth=date_of_birth,
                        gender=row[3] or "M",
                        email="",  # Would need to be stored separately
                        phone="",  # Would need to be stored separately
                        nationality=row[4] or "US",
                        passport_number=row[5],
                        passport_expiry=passport_expiry
                    )
                    passengers.append(passenger)
                
                return passengers
                
        except Exception as e:
            print(f"Error getting passengers for booking: {e}")
            return []
    
    # ====================================================================
    # UTILITY METHODS
    # ====================================================================
    
    def _safe_json_parse(self, value, default=None):
        """Safely parse JSON data that might already be parsed"""
        if value is None:
            return default if default is not None else {}
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                print(f"Warning: Failed to parse JSON: {value}")
                return default if default is not None else {}
        return default if default is not None else {}
    
    def _row_to_booking(self, row) -> Booking:
        """Convert database row to Booking object"""
        return Booking(
            id=row[0], booking_reference=row[1], primary_user_id=row[2],
            group_size=row[3], booking_type=row[4], search_id=row[5],
            selected_flight_offers=self._safe_json_parse(row[6], []), # type: ignore
            trip_type=row[7], origin_airport=row[8], destination_airport=row[9],
            departure_date=row[10], return_date=row[11], base_price=row[12],
            taxes_and_fees=row[13], service_fee=row[14], insurance_fee=row[15],
            total_amount=row[16], currency=row[17], booking_status=row[18],
            payment_status=row[19], fulfillment_status=row[20],
            provider_name=row[21], provider_booking_id=row[22], 
            provider_pnr=row[23], provider_response=self._safe_json_parse(row[24], {}), # type: ignore
            travel_insurance=row[25], special_requests=row[26],
            accessibility_requirements=row[27], emergency_contact_name=row[28],
            emergency_contact_phone=row[29], emergency_contact_relationship=row[30],
            emergency_contact_email=row[31], confirmation_deadline=row[32],
            payment_deadline=row[33], checkin_available_at=row[34],
            created_at=row[35], updated_at=row[36], confirmed_at=row[37],
            cancelled_at=row[38]
        )
    
    def _generate_booking_reference(self) -> str:
        """Generate a unique booking reference"""

        # Generate format: ABC123DE (3 letters + 3 numbers + 2 letters)
        letters = ''.join(random.choices(string.ascii_uppercase, k=3))
        numbers = ''.join(random.choices(string.digits, k=3))
        suffix = ''.join(random.choices(string.ascii_uppercase, k=2))
        
        return f"{letters}{numbers}{suffix}"
        
    def _generate_booking_summary(self, booking, current_passengers, completion_status, next_actions) -> str:
        """Generate a human-readable summary for the model"""
        summary_parts = []
        
        # Basic booking info
        summary_parts.append(f"Booking {booking.booking_reference} ({booking.booking_type})")
        summary_parts.append(f"Status: {booking.booking_status}")
        
        # Route info
        if booking.origin_airport:
            route = f"{booking.origin_airport} → {booking.destination_airport}"
            if booking.departure_date:
                route += f" on {booking.departure_date.strftime('%Y-%m-%d')}"
            summary_parts.append(route)
        
        # Progress summary
        progress_parts = []
        if completion_status["passengers_added"]:
            progress_parts.append(f"✓ {current_passengers}/{booking.group_size} passengers")
        else:
            progress_parts.append(f"⚠ {current_passengers}/{booking.group_size} passengers")
        
        if completion_status["passenger_details_complete"]:
            progress_parts.append("✓ Details complete")
        else:
            progress_parts.append("⚠ Details incomplete")
        
        if completion_status["emergency_contact_complete"]:
            progress_parts.append("✓ Emergency contact")
        else:
            progress_parts.append("⚠ Emergency contact needed")
        
        summary_parts.append("Progress: " + ", ".join(progress_parts))
        
        # Next actions
        if next_actions:
            action_descriptions = [action["description"] for action in next_actions[:2]]  # Show first 2
            summary_parts.append("Next: " + "; ".join(action_descriptions))
        
        return "Booking Summary: \n".join(summary_parts)

        
    def extract_booking_operation_context(self, result: Dict[str, Any], operation: str, **kwargs) -> str:
        """Unified context extraction for all booking operations"""
        booking_id = result.get('booking_id', kwargs.get('booking_id', ''))
        
        # Generate tool call representation based on operation
        tool_call = self._generate_tool_call_string(operation, result, **kwargs)
        
        # Start with tool call
        context = f"{tool_call}\n"
        
        # Handle errors first
        if 'error' in result:
            context += f"Error: {result['error']}"
            return context
        
        # Add operation-specific context
        if operation == 'create':
            search_id = result.get('search_id', '')
            total_amount = result.get('total_amount', 0)
            context += f"SUCCESS: Booking created\n"
            context += f"Booking ID: {booking_id}\n"
            context += f"Amount: ${total_amount}\n"
            context += f"Status: Draft - needs passengers\n"
            
        elif operation == 'add_passenger':
            first_name = result.get('first_name', '')
            last_name = result.get('last_name', '')
            total = result.get('total_passengers', 0)
            required = result.get('required_passengers', 1)
            
            context += f"SUCCESS: Passenger added\n"
            context += f"Added: {first_name} {last_name}\n"
            context += f"Progress: {total}/{required} passengers\n"
            
        elif operation == 'update_passenger':
            context += f"SUCCESS: Passenger details updated\n"
            
        elif operation == 'update_booking':
            updated_fields = result.get('updated_fields', [])
            context += f"SUCCESS: Booking updated\n"
            if updated_fields:
                context += f"Updated: {', '.join(updated_fields)}\n"
                
        elif operation == 'add_emergency_contact':
            context += f"SUCCESS: Emergency contact added\n"
            
        elif operation == 'finalize':
            pnr = result.get('pnr', '')
            final_price = result.get('final_price', 0)
            payment_url = result.get('payment_url', '')
            
            context += f"SUCCESS: Booking finalized\n"
            if pnr:
                context += f"PNR: {pnr}\n"
            
            try:
                price_str = f"${float(final_price):.0f}" if final_price else "$0"
            except (ValueError, TypeError):
                price_str = "Price TBD"
            
            context += f"Final price: {price_str}\n"
            if payment_url:
                context += "Payment link generated - user must pay to complete\n"
                
        # Add comprehensive booking status if we have a booking_id
        if booking_id:
            context += "\n" + "="*50 + "\n"
            context += "CURRENT BOOKING STATUS:\n"
            
            booking_context = self.get_booking_context(booking_id)
            if 'error' not in booking_context:
                # Add booking summary
                summary = booking_context.get('summary', '')
                if summary:
                    context += f"{summary}\n\n"
                
                # Add detailed next actions
                next_actions = booking_context.get('next_actions', [])
                if next_actions:
                    context += "NEXT ACTIONS NEEDED:\n"
                    for i, action in enumerate(next_actions[:3], 1):  # Show top 3 actions
                        context += f"{i}. {action['description']}\n"
                        context += f"   Call: {action['tool_call']}\n"
                        if 'missing_fields' in action:
                            context += f"   Missing: {', '.join(action['missing_fields'])}\n"
                    
                    if len(next_actions) > 3:
                        context += f"   ... and {len(next_actions) - 3} more actions\n"
                else:
                    # Check if ready for finalization
                    if booking_context.get('completion_status', {}).get('ready_for_finalization'):
                        context += "READY FOR FINALIZATION!\n"
                        context += f"Call: finalize_booking(booking_id='{booking_id}')\n"
                    else:
                        context += "Booking in progress...\n"
                
                # Add passenger details summary
                passengers = booking_context.get('passengers', {})
                if passengers.get('list'):
                    context += f"\nPASSENGERS ({passengers['current_count']}/{passengers['required_count']}):\n"
                    for p in passengers['list']:
                        name = f"{p.get('first_name', '')} {p.get('last_name', '')}"
                        details = []
                        if not p.get('date_of_birth'):
                            details.append('DOB missing')
                        if not p.get('nationality'):
                            details.append('nationality missing')
                        if not p.get('document_number'):
                            details.append('passport missing')
                        if not p.get('seat_preference'):
                            details.append('seat pref missing')
                        if not p.get('meal_preference'):
                            details.append('meal pref missing')
                        
                        status = " ⚠ " + ", ".join(details) if details else " ✓"
                        context += f"• {name}{status}\n"
                
                # Add emergency contact status
                emergency = booking_context.get('emergency_contact', {})
                if emergency.get('complete'):
                    context += f"\nEMERGENCY CONTACT: ✓ {emergency.get('name')} ({emergency.get('relationship')})\n"
                else:
                    context += f"\nEMERGENCY CONTACT: ⚠ Not provided\n"
            else:
                context += f"Could not retrieve booking status: {booking_context['error']}\n"
        
        return context
    
    def _generate_tool_call_string(self, operation: str, result: Dict[str, Any], **kwargs) -> str:
        """Generate the tool call string representation"""
        booking_id = result.get('booking_id', kwargs.get('booking_id', ''))
        
        if operation == 'create':
            search_id = result.get('search_id', kwargs.get('search_id', ''))
            flight_offer_ids = kwargs.get('flight_offer_ids', [])
            return f"<call>create_flight_booking(search_id='{search_id}', flight_offer_ids={flight_offer_ids})</call>"
            
        elif operation == 'add_passenger':
            first_name = result.get('first_name', kwargs.get('first_name', ''))
            last_name = result.get('last_name', kwargs.get('last_name', ''))
            return f"<call>manage_booking_passengers(booking_id='{booking_id}', action='add', first_name='{first_name}', last_name='{last_name}', ...)</call>"
            
        elif operation == 'update_passenger':
            passenger_id = result.get('passenger_id', kwargs.get('passenger_id', ''))
            return f"<call>manage_booking_passengers(booking_id='{booking_id}', action='update', passenger_id='{passenger_id}', ...)</call>"
            
        elif operation == 'update_booking':
            return f"<call>manage_booking_passengers(booking_id='{booking_id}', action='update_booking', ...)</call>"
            
        elif operation == 'get':
            return f"<call>manage_booking_passengers(booking_id='{booking_id}', action='get')</call>"
            
        elif operation == 'add_emergency_contact':
            return f"<call>manage_booking_passengers(booking_id='{booking_id}', action='add_emergency_contact', ...)</call>"
            
        elif operation == 'finalize':
            return f"<call>finalize_booking(booking_id='{booking_id}')</call>"
            
        else:
            return f"<call>booking_operation(action='{operation}', booking_id='{booking_id}')</call>"
    
    def handle_passenger_lookup(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """
        Look up passenger details from user's booking history and connections
        
        Args:
            user_id: The user performing the lookup
            booking_id: Optional - limit search to specific booking
            first_name: Optional - search by first name (partial match supported)
            last_name: Optional - search by last name (partial match supported)
            partial_match: Bool - whether to allow partial name matching (default True)
            include_connections: Bool - whether to include connected passengers (default True)
            limit: Int - maximum number of results to return (default 20)
        
        Returns:
            Dict with success status and passenger list or error message
        """
        try:
            if not self.storage.conn:
                return {"error": "Database connection not available"}
            
            booking_id = kwargs.get("booking_id")
            first_name = kwargs.get("first_name", "").strip()
            last_name = kwargs.get("last_name", "").strip()
            partial_match = kwargs.get("partial_match", True)
            include_connections = kwargs.get("include_connections", True)
            limit = kwargs.get("limit", 20)
            
            passengers = []
            
            with self.storage.conn.cursor() as cur:
                # Build the main query to search through passenger profiles
                base_query = """
                    SELECT DISTINCT
                        pp.id,
                        pp.first_name,
                        pp.middle_name,
                        pp.last_name,
                        pp.date_of_birth,
                        pp.gender,
                        pp.title,
                        pp.email,
                        pp.phone_number,
                        pp.primary_document_type,
                        pp.primary_document_number,
                        pp.primary_document_expiry,
                        pp.primary_document_country,
                        pp.nationality,
                        pp.seat_preference,
                        pp.meal_preference,
                        pp.special_assistance,
                        pp.medical_conditions,
                        pp.dietary_restrictions,
                        pp.airline_loyalties,
                        pp.tsa_precheck_number,
                        pp.global_entry_number,
                        pp.created_by_user_id,
                        pp.is_verified,
                        pp.verification_method,
                        pp.created_at,
                        pp.updated_at,
                        pp.last_traveled_at,
                        upc.relationship,
                        upc.connection_type,
                        upc.trust_level,
                        upc.can_book_for_passenger,
                        upc.can_modify_passenger_details,
                        upc.can_view_passenger_history,
                        COUNT(bp.id) as booking_count,
                        MAX(b.created_at) as last_booking_date
                    FROM passenger_profiles pp
                    LEFT JOIN user_passenger_connections upc ON pp.id = upc.passenger_id AND upc.user_id = %s
                    LEFT JOIN booking_passengers bp ON pp.id = bp.passenger_profile_id
                    LEFT JOIN bookings b ON bp.booking_id = b.id AND b.primary_user_id = %s
                    WHERE (
                        pp.created_by_user_id = %s
                        OR upc.user_id = %s
                    )
                """
                
                query_params = [user_id, user_id, user_id, user_id]
                conditions = []
                
                # Add booking ID filter if specified
                if booking_id:
                    conditions.append("b.id = %s")
                    query_params.append(booking_id)
                
                # Add name filters
                if first_name:
                    if partial_match:
                        conditions.append("pp.first_name ILIKE %s")
                        query_params.append(f"%{first_name}%") # type: ignore
                    else:
                        conditions.append("pp.first_name ILIKE %s")
                        query_params.append(first_name)
                
                if last_name:
                    if partial_match:
                        conditions.append("pp.last_name ILIKE %s")
                        query_params.append(f"%{last_name}%") # type: ignore
                    else:
                        conditions.append("pp.last_name ILIKE %s")
                        query_params.append(last_name)
                
                # If we don't want connections, only include profiles created by this user
                if not include_connections:
                    conditions.append("pp.created_by_user_id = %s")
                    query_params.append(user_id)
                
                # Add conditions to query
                if conditions:
                    base_query += " AND " + " AND ".join(conditions)
                
                # Add grouping, ordering and limit
                base_query += """
                    GROUP BY pp.id, upc.relationship, upc.connection_type, upc.trust_level,
                            upc.can_book_for_passenger, upc.can_modify_passenger_details, 
                            upc.can_view_passenger_history
                    ORDER BY 
                        CASE 
                            WHEN pp.created_by_user_id = %s THEN 1  -- Own profiles first
                            WHEN upc.relationship = 'self' THEN 2  -- Self connections next
                            WHEN upc.relationship IN ('spouse', 'partner', 'child', 'parent') THEN 3  -- Family next
                            WHEN upc.trust_level = 'high' THEN 4  -- High trust connections
                            ELSE 5
                        END,
                        booking_count DESC NULLS LAST,  -- Most frequently booked
                        pp.last_traveled_at DESC NULLS LAST,  -- Most recently traveled
                        last_booking_date DESC NULLS LAST  -- Most recent booking
                    LIMIT %s
                """
                query_params.extend([user_id, limit])
                
                # Execute the query
                cur.execute(base_query, query_params)
                rows = cur.fetchall()
                
                # Convert rows to PassengerProfile objects
                for row in rows:
                    # Parse airline_loyalties JSON
                    airline_loyalties = {}
                    if row[19]:  # airline_loyalties field
                        try:
                            airline_loyalties = json.loads(row[19]) if isinstance(row[19], str) else row[19]
                        except (json.JSONDecodeError, TypeError):
                            airline_loyalties = {}
                    
                    # Create PassengerProfile object
                    profile = PassengerProfile(
                        id=row[0],
                        first_name=row[1] or "",
                        middle_name=row[2],
                        last_name=row[3] or "",
                        date_of_birth=row[4],
                        gender=row[5],
                        title=row[6],
                        email=row[7],
                        phone_number=row[8],
                        primary_document_type=row[9],
                        primary_document_number=row[10],
                        primary_document_expiry=row[11],
                        primary_document_country=row[12],
                        nationality=row[13],
                        seat_preference=row[14] or "any",
                        meal_preference=row[15],
                        special_assistance=row[16],
                        medical_conditions=row[17],
                        dietary_restrictions=row[18],
                        airline_loyalties=airline_loyalties,
                        tsa_precheck_number=row[20],
                        global_entry_number=row[21],
                        created_by_user_id=row[22],
                        is_verified=bool(row[23]),
                        verification_method=row[24],
                        created_at=row[25],
                        updated_at=row[26],
                        last_traveled_at=row[27]
                    )
                    
                    # Add connection metadata
                    connection_info = {
                        "relationship": row[28],
                        "connection_type": row[29],
                        "trust_level": row[30],
                        "can_book_for_passenger": bool(row[31]) if row[31] is not None else False,
                        "can_modify_passenger_details": bool(row[32]) if row[32] is not None else False,
                        "can_view_passenger_history": bool(row[33]) if row[33] is not None else False,
                        "booking_count": row[34] or 0,
                        "last_booking_date": row[35].isoformat() if row[35] else None
                    }
                    
                    # Calculate completeness score
                    required_fields = [
                        profile.first_name, profile.last_name, profile.date_of_birth, 
                        profile.nationality, profile.primary_document_number
                    ]
                    optional_fields = [
                        profile.seat_preference and profile.seat_preference != "any",
                        profile.meal_preference,
                        profile.primary_document_expiry,
                        profile.email,
                        profile.phone_number
                    ]
                    
                    completeness_score = sum(2 for field in required_fields if field) + \
                                    sum(1 for field in optional_fields if field)
                    
                    passenger_data = {
                        "profile": profile,
                        "connection_info": connection_info,
                        "completeness_score": completeness_score,
                        "is_complete": completeness_score >= 8  # At least required fields + some optional
                    }
                    
                    passengers.append(passenger_data)
            
            # Prepare response with PassengerProfile objects
            response = {
                "success": True,
                "passengers": passengers,
                "total_found": len(passengers),
                "search_criteria": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "booking_id": booking_id,
                    "partial_match": partial_match,
                    "include_connections": include_connections
                }
            }
            
            # Add helpful context if no results
            if not passengers:
                if first_name or last_name:
                    response["message"] = f"No passengers found matching '{first_name} {last_name}' in your connections"
                elif booking_id:
                    response["message"] = f"No passengers found for booking {booking_id}"
                else:
                    response["message"] = "No passenger profiles found in your connections"
            else:
                # Add summary message
                complete_count = sum(1 for p in passengers if p["is_complete"])
                response["message"] = f"Found {len(passengers)} passenger(s), {complete_count} with complete details"
            
            return response
            
        except Exception as e:
            print(f"Error in handle_passenger_lookup: {e}")
            import traceback
            traceback.print_exc()
            return {"error": f"Passenger lookup failed: {str(e)}"}


    def get_passenger_autocomplete_suggestions(self, user_id: int, partial_name: str, limit: int = 5) -> Dict[str, Any]:
        """
        Get passenger name suggestions for autocomplete based on partial input
        
        Args:
            user_id: The user requesting suggestions
            partial_name: Partial name to match against
            limit: Maximum number of suggestions to return
        
        Returns:
            Dict with success status and suggestion list containing PassengerProfile objects
        """
        try:
            if not self.storage.conn:
                return {"error": "Database connection not available"}
            
            if not partial_name or len(partial_name) < 2:
                return {"success": True, "suggestions": [], "message": "Need at least 2 characters"}
            
            suggestions = []
            
            with self.storage.conn.cursor() as cur:
                # Search for passengers in user's connections
                cur.execute("""
                    SELECT 
                        pp.id,
                        pp.first_name,
                        pp.middle_name,
                        pp.last_name,
                        pp.date_of_birth,
                        pp.gender,
                        pp.title,
                        pp.email,
                        pp.phone_number,
                        pp.primary_document_type,
                        pp.primary_document_number,
                        pp.primary_document_expiry,
                        pp.primary_document_country,
                        pp.nationality,
                        pp.seat_preference,
                        pp.meal_preference,
                        pp.special_assistance,
                        pp.medical_conditions,
                        pp.dietary_restrictions,
                        pp.airline_loyalties,
                        pp.tsa_precheck_number,
                        pp.global_entry_number,
                        pp.created_by_user_id,
                        pp.is_verified,
                        pp.verification_method,
                        pp.created_at,
                        pp.updated_at,
                        pp.last_traveled_at,
                        upc.relationship,
                        COUNT(b.id) as booking_count,
                        MAX(b.created_at) as last_booking
                    FROM passenger_profiles pp
                    LEFT JOIN user_passenger_connections upc ON pp.id = upc.passenger_id AND upc.user_id = %s
                    LEFT JOIN booking_passengers bp ON pp.id = bp.passenger_profile_id
                    LEFT JOIN bookings b ON bp.booking_id = b.id AND b.primary_user_id = %s
                    WHERE (
                        pp.created_by_user_id = %s 
                        OR upc.user_id = %s
                    ) AND (
                        pp.first_name ILIKE %s
                        OR pp.last_name ILIKE %s
                        OR CONCAT(pp.first_name, ' ', pp.last_name) ILIKE %s
                    )
                    GROUP BY pp.id, upc.relationship
                    ORDER BY booking_count DESC, last_booking DESC
                    LIMIT %s
                """, (
                    user_id, user_id, user_id, user_id,
                    f"%{partial_name}%", f"%{partial_name}%", f"%{partial_name}%",
                    limit
                ))
                
                for row in cur.fetchall():
                    # Parse airline_loyalties JSON
                    airline_loyalties = {}
                    if row[19]:  # airline_loyalties field
                        try:
                            airline_loyalties = json.loads(row[19]) if isinstance(row[19], str) else row[19]
                        except (json.JSONDecodeError, TypeError):
                            airline_loyalties = {}
                    
                    # Create PassengerProfile object
                    profile = PassengerProfile(
                        id=row[0],
                        first_name=row[1] or "",
                        middle_name=row[2],
                        last_name=row[3] or "",
                        date_of_birth=row[4],
                        gender=row[5],
                        title=row[6],
                        email=row[7],
                        phone_number=row[8],
                        primary_document_type=row[9],
                        primary_document_number=row[10],
                        primary_document_expiry=row[11],
                        primary_document_country=row[12],
                        nationality=row[13],
                        seat_preference=row[14] or "any",
                        meal_preference=row[15],
                        special_assistance=row[16],
                        medical_conditions=row[17],
                        dietary_restrictions=row[18],
                        airline_loyalties=airline_loyalties,
                        tsa_precheck_number=row[20],
                        global_entry_number=row[21],
                        created_by_user_id=row[22],
                        is_verified=bool(row[23]),
                        verification_method=row[24],
                        created_at=row[25],
                        updated_at=row[26],
                        last_traveled_at=row[27]
                    )
                    
                    suggestion = {
                        "profile": profile,
                        "display_name": f"{profile.first_name} {profile.last_name}",
                        "relationship": row[28] or "previous passenger",
                        "booking_count": row[29] or 0,
                        "last_used": row[30].isoformat() if row[30] else None
                    }
                    
                    suggestions.append(suggestion)
            
            return {
                "success": True,
                "suggestions": suggestions,
                "query": partial_name,
                "total_found": len(suggestions)
            }
            
        except Exception as e:
            print(f"Error in get_passenger_autocomplete_suggestions: {e}")
            return {"error": f"Autocomplete suggestions failed: {str(e)}"}


    def get_passenger_usage_stats(self, user_id: int, passenger_id: str) -> Dict[str, Any]:
        """
        Get usage statistics for a specific passenger profile
        
        Args:
            user_id: The user requesting stats
            passenger_id: The passenger profile ID to analyze
        
        Returns:
            Dict with usage statistics and PassengerProfile object
        """
        try:
            if not self.storage.conn:
                return {"error": "Database connection not available"}
            
            with self.storage.conn.cursor() as cur:
                # First verify user has access to this passenger
                cur.execute("""
                    SELECT pp.*, upc.relationship, upc.connection_type, upc.trust_level
                    FROM passenger_profiles pp
                    LEFT JOIN user_passenger_connections upc ON pp.id = upc.passenger_id AND upc.user_id = %s
                    WHERE pp.id = %s AND (
                        pp.created_by_user_id = %s 
                        OR upc.user_id = %s
                    )
                """, (user_id, passenger_id, user_id, user_id))
                
                passenger_row = cur.fetchone()
                if not passenger_row:
                    return {"error": "Passenger not found or access denied"}
                
                # Get booking history for this passenger
                cur.execute("""
                    SELECT 
                        COUNT(DISTINCT b.id) as total_bookings,
                        MIN(b.created_at) as first_booking,
                        MAX(b.created_at) as last_booking,
                        AVG(b.total_amount) as avg_booking_value,
                        COUNT(DISTINCT b.origin_airport) as unique_origins,
                        COUNT(DISTINCT b.destination_airport) as unique_destinations,
                        STRING_AGG(DISTINCT b.origin_airport || '-' || b.destination_airport, ', ') as common_routes
                    FROM passenger_profiles pp
                    JOIN booking_passengers bp ON pp.id = bp.passenger_profile_id
                    JOIN bookings b ON bp.booking_id = b.id
                    WHERE pp.id = %s AND b.primary_user_id = %s
                """, (passenger_id, user_id))
                
                stats_row = cur.fetchone()
                
                # Parse airline_loyalties JSON
                airline_loyalties = {}
                if passenger_row[19]:  # airline_loyalties field
                    try:
                        airline_loyalties = json.loads(passenger_row[19]) if isinstance(passenger_row[19], str) else passenger_row[19]
                    except (json.JSONDecodeError, TypeError):
                        airline_loyalties = {}
                
                # Create PassengerProfile object
                profile = PassengerProfile(
                    id=passenger_row[0],
                    first_name=passenger_row[1] or "",
                    middle_name=passenger_row[2],
                    last_name=passenger_row[3] or "",
                    date_of_birth=passenger_row[4],
                    gender=passenger_row[5],
                    title=passenger_row[6],
                    email=passenger_row[7],
                    phone_number=passenger_row[8],
                    primary_document_type=passenger_row[9],
                    primary_document_number=passenger_row[10],
                    primary_document_expiry=passenger_row[11],
                    primary_document_country=passenger_row[12],
                    nationality=passenger_row[13],
                    seat_preference=passenger_row[14] or "any",
                    meal_preference=passenger_row[15],
                    special_assistance=passenger_row[16],
                    medical_conditions=passenger_row[17],
                    dietary_restrictions=passenger_row[18],
                    airline_loyalties=airline_loyalties,
                    tsa_precheck_number=passenger_row[20],
                    global_entry_number=passenger_row[21],
                    created_by_user_id=passenger_row[22],
                    is_verified=bool(passenger_row[23]),
                    verification_method=passenger_row[24],
                    created_at=passenger_row[25],
                    updated_at=passenger_row[26],
                    last_traveled_at=passenger_row[27]
                )
                
                if not stats_row or not stats_row[0]:
                    stats = {
                        "total_bookings": 0,
                        "message": "No booking history found for this passenger"
                    }
                else:
                    stats = {
                        "total_bookings": stats_row[0],
                        "first_booking": stats_row[1].isoformat() if stats_row[1] else None,
                        "last_booking": stats_row[2].isoformat() if stats_row[2] else None,
                        "average_booking_value": float(stats_row[3]) if stats_row[3] else 0,
                        "unique_origins": stats_row[4] or 0,
                        "unique_destinations": stats_row[5] or 0,
                        "common_routes": stats_row[6] or ""
                    }
                
                # Add connection info
                connection_info = {
                    "relationship": passenger_row[28],
                    "connection_type": passenger_row[29],
                    "trust_level": passenger_row[30]
                }
                
                return {
                    "success": True,
                    "passenger_profile": profile,
                    "connection_info": connection_info,
                    "stats": stats
                }
                
        except Exception as e:
            print(f"Error in get_passenger_usage_stats: {e}")
            return {"error": f"Stats retrieval failed: {str(e)}"}
