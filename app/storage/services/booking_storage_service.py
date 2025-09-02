# ==============================================================================
# app/storage/services/booking_storage_service.py
# ==============================================================================
from typing import Dict, Any, List, Optional, Tuple
import json
from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from app.storage.db_service import StorageService
from app.storage.services.flight_storage_service import FlightStorageService
from app.storage.services.shared_storage import implemented_redis_storage_manager

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
    amadeus_booking_id: Optional[str]
    amadeus_pnr: Optional[str]
    amadeus_response: Dict[str, Any]
    travel_insurance: bool
    special_requests: Optional[str]
    accessibility_requirements: Optional[str]
    confirmation_deadline: Optional[datetime]
    payment_deadline: Optional[datetime]
    checkin_available_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    confirmed_at: Optional[datetime]
    cancelled_at: Optional[datetime]

@dataclass
class BookingPassenger:
    id: str
    booking_id: str
    passenger_profile_id: Optional[str]
    passenger_sequence: int
    passenger_type: str
    is_primary_passenger: bool
    booking_first_name: Optional[str]
    booking_last_name: Optional[str]
    booking_document_number: Optional[str]
    booking_seat_preference: Optional[str]
    booking_meal_preference: Optional[str]
    assigned_seats: Dict[str, Any]
    seat_assignment_status: str
    checked_in_at: Optional[datetime]
    boarding_pass_issued: bool
    boarding_pass_file_id: Optional[str]
    created_at: datetime
    updated_at: datetime

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
    passenger_assignments: Dict[str, Any]
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
    - Handle passenger associations and details
    - Manage flight segments and schedules
    - Track booking status changes and timeline
    - Integration with external booking systems (Amadeus)
    """
    
    def __init__(self, storage: StorageService, flight_storage_service: FlightStorageService):
        self.storage = storage
        self.flight_storage_service = flight_storage_service
    
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
                
                # Build insert query dynamically
                fields = list(booking_data.keys())
                placeholders = ', '.join(['%s'] * len(fields))
                field_names = ', '.join(fields)
                
                cur.execute(f"""
                    INSERT INTO bookings ({field_names})
                    VALUES ({placeholders})
                    RETURNING id;
                """, list(booking_data.values()))
                
                result = cur.fetchone()
                if result:
                    booking_id = result[0]
                else:
                    raise Exception("No booking id found.")
                
                # Add timeline event
                self.add_timeline_event(
                    booking_id=booking_id,
                    event_type='booking_created',
                    event_description='Booking created',
                    triggered_by_user_id=booking_data.get('primary_user_id')
                )
                
                return booking_id
                
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
                           booking_status, payment_status, fulfillment_status, amadeus_booking_id,
                           amadeus_pnr, amadeus_response, travel_insurance, special_requests,
                           accessibility_requirements, confirmation_deadline, payment_deadline,
                           checkin_available_at, created_at, updated_at, confirmed_at, cancelled_at
                    FROM bookings WHERE id = %s;
                """, (booking_id,))
                
                row = cur.fetchone()
                if row:
                    return Booking(
                        id=row[0],
                        booking_reference=row[1],
                        primary_user_id=row[2],
                        group_size=row[3],
                        booking_type=row[4],
                        search_id=row[5],
                        selected_flight_offers=json.loads(row[6]) if row[6] else [],
                        trip_type=row[7],
                        origin_airport=row[8],
                        destination_airport=row[9],
                        departure_date=row[10],
                        return_date=row[11],
                        base_price=row[12],
                        taxes_and_fees=row[13],
                        service_fee=row[14],
                        insurance_fee=row[15],
                        total_amount=row[16],
                        currency=row[17],
                        booking_status=row[18],
                        payment_status=row[19],
                        fulfillment_status=row[20],
                        amadeus_booking_id=row[21],
                        amadeus_pnr=row[22],
                        amadeus_response=json.loads(row[23]) if row[23] else {},
                        travel_insurance=row[24],
                        special_requests=row[25],
                        accessibility_requirements=row[26],
                        confirmation_deadline=row[27],
                        payment_deadline=row[28],
                        checkin_available_at=row[29],
                        created_at=row[30],
                        updated_at=row[31],
                        confirmed_at=row[32],
                        cancelled_at=row[33]
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
                           booking_status, payment_status, fulfillment_status, amadeus_booking_id,
                           amadeus_pnr, amadeus_response, travel_insurance, special_requests,
                           accessibility_requirements, confirmation_deadline, payment_deadline,
                           checkin_available_at, created_at, updated_at, confirmed_at, cancelled_at
                    FROM bookings 
                    WHERE primary_user_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s OFFSET %s;
                """, (user_id, limit, offset))
                
                return [
                    Booking(
                        id=row[0], booking_reference=row[1], primary_user_id=row[2],
                        group_size=row[3], booking_type=row[4], search_id=row[5],
                        selected_flight_offers=json.loads(row[6]) if row[6] else [],
                        trip_type=row[7], origin_airport=row[8], destination_airport=row[9],
                        departure_date=row[10], return_date=row[11], base_price=row[12],
                        taxes_and_fees=row[13], service_fee=row[14], insurance_fee=row[15],
                        total_amount=row[16], currency=row[17], booking_status=row[18],
                        payment_status=row[19], fulfillment_status=row[20],
                        amadeus_booking_id=row[21], amadeus_pnr=row[22],
                        amadeus_response=json.loads(row[23]) if row[23] else {},
                        travel_insurance=row[24], special_requests=row[25],
                        accessibility_requirements=row[26], confirmation_deadline=row[27],
                        payment_deadline=row[28], checkin_available_at=row[29],
                        created_at=row[30], updated_at=row[31], confirmed_at=row[32],
                        cancelled_at=row[33]
                    )
                    for row in cur.fetchall()
                ]
                
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
                    if field in ['amadeus_response', 'selected_flight_offers'] and isinstance(value, dict):
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
                    # Add timeline event
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
    
    def get_booking_details(self, booking_id: str) -> Dict[str, Any]:
        """Get comprehensive booking details"""
        try:
            booking = self.get_booking(booking_id)
            if not booking:
                return {"error": "Booking not found"}
            
            passengers = self.get_booking_passengers(booking_id)
            flight_segments = self.get_booking_flight_segments(booking_id)
            timeline = self.get_booking_timeline(booking_id)
            
            return {
                'success': True,
                'booking_id': booking.id,
                'booking_reference': booking.booking_reference,
                'status': booking.booking_status,
                'payment_status': booking.payment_status,
                'pnr': booking.amadeus_pnr,
                'total_amount': float(booking.total_amount),
                'currency': booking.currency,
                'passengers': [
                    {
                        'passenger_id': p.id,
                        'first_name': p.booking_first_name,
                        'last_name': p.booking_last_name,
                        'passenger_type': p.passenger_type
                    } for p in passengers
                ],
                'flight_segments': [
                    {
                        'flight_number': f"{s.airline_code}{s.flight_number}",
                        'departure_airport': s.departure_airport,
                        'arrival_airport': s.arrival_airport,
                        'departure_time': s.departure_time.isoformat(),
                        'arrival_time': s.arrival_time.isoformat()
                    } for s in flight_segments
                ],
                'timeline': [
                    {
                        'event_type': t.event_type,
                        'description': t.event_description,
                        'timestamp': t.created_at.isoformat()
                    } for t in timeline
                ]
            }
            
        except Exception as e:
            return {"error": f"Get booking details failed: {str(e)}"}
    
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
                        'currency': b.currency
                    } for b in bookings
                ]
            }
            
        except Exception as e:
            return {"error": f"Get user bookings failed: {str(e)}"}
    
    # ====================================================================
    # PASSENGER MANAGEMENT
    # ====================================================================
    
    def add_passenger_to_booking(self, booking_id: str, **passenger_data) -> Optional[str]:
        """Add a passenger to a booking"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                # Get next passenger sequence number
                cur.execute("""
                    SELECT COALESCE(MAX(passenger_sequence), 0) + 1
                    FROM booking_passengers WHERE booking_id = %s;
                """, (booking_id,))
                
                passenger_data['booking_id'] = booking_id
                result = cur.fetchone()
                if result:
                    passenger_data['passenger_sequence'] = result[0]
                else:
                    raise Exception("No passenger sequence found")
                
                # Build insert query
                fields = list(passenger_data.keys())
                placeholders = ', '.join(['%s'] * len(fields))
                field_names = ', '.join(fields)
                
                # Handle JSON fields
                values = []
                for field, value in passenger_data.items():
                    if field == 'assigned_seats' and isinstance(value, dict):
                        values.append(json.dumps(value))
                    else:
                        values.append(value)
                
                cur.execute(f"""
                    INSERT INTO booking_passengers ({field_names})
                    VALUES ({placeholders})
                    RETURNING id;
                """, values)
                
                result = cur.fetchone()
                if result:
                    passenger_id = result[0]
                else:
                    raise Exception("No passenger id found")
                
                # Add timeline event
                self.add_timeline_event(
                    booking_id=booking_id,
                    event_type='passenger_added',
                    event_description='Passenger added to booking',
                    event_data={'passenger_id': passenger_id}
                )
                
                return passenger_id
                
        except Exception as e:
            print(f"Error adding passenger: {e}")
            return None
    
    def get_booking_passengers(self, booking_id: str) -> List[BookingPassenger]:
        """Get all passengers for a booking"""
        if not self.storage.conn:
            return []
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, booking_id, passenger_profile_id, passenger_sequence,
                           passenger_type, is_primary_passenger, booking_first_name,
                           booking_last_name, booking_document_number, booking_seat_preference,
                           booking_meal_preference, assigned_seats, seat_assignment_status,
                           checked_in_at, boarding_pass_issued, boarding_pass_file_id,
                           created_at, updated_at
                    FROM booking_passengers 
                    WHERE booking_id = %s 
                    ORDER BY passenger_sequence;
                """, (booking_id,))
                
                return [
                    BookingPassenger(
                        id=row[0], booking_id=row[1], passenger_profile_id=row[2],
                        passenger_sequence=row[3], passenger_type=row[4],
                        is_primary_passenger=row[5], booking_first_name=row[6],
                        booking_last_name=row[7], booking_document_number=row[8],
                        booking_seat_preference=row[9], booking_meal_preference=row[10],
                        assigned_seats=json.loads(row[11]) if row[11] else {},
                        seat_assignment_status=row[12], checked_in_at=row[13],
                        boarding_pass_issued=row[14], boarding_pass_file_id=row[15],
                        created_at=row[16], updated_at=row[17]
                    )
                    for row in cur.fetchall()
                ]
                
        except Exception as e:
            print(f"Error getting booking passengers: {e}")
            return []
    
    def update_passenger_details(self, booking_id: str, passenger_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update passenger details"""
        if not self.storage.conn:
            return {"error": "Database not available"}
        
        try:
            with self.storage.conn.cursor() as cur:
                # Build update query dynamically
                update_fields = []
                update_values = []
                
                field_mapping = {
                    'first_name': 'booking_first_name',
                    'last_name': 'booking_last_name',
                    'passport_number': 'booking_document_number',
                    'seat_preference': 'booking_seat_preference',
                    'meal_preference': 'booking_meal_preference'
                }
                
                for field, value in update_data.items():
                    if field in field_mapping:
                        update_fields.append(f"{field_mapping[field]} = %s")
                        update_values.append(value)
                
                if not update_fields:
                    return {"error": "No valid fields to update"}
                
                update_values.extend([booking_id, passenger_id])
                
                cur.execute(f"""
                    UPDATE booking_passengers 
                    SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                    WHERE booking_id = %s AND id = %s;
                """, update_values)
                
                if cur.rowcount > 0:
                    return {
                        'success': True,
                        'message': 'Passenger updated successfully'
                    }
                else:
                    return {"error": "Passenger not found or no changes made"}
                    
        except Exception as e:
            return {"error": f"Update passenger failed: {str(e)}"}
    
    def search_passenger_history(self, user_id: int, name_search: str) -> Dict[str, Any]:
        """Search for passengers from user's previous bookings"""
        if not self.storage.conn:
            return {"error": "Database not available"}
        
        try:
            with self.storage.conn.cursor() as cur:
                # Search by name in user's previous bookings
                search_terms = name_search.split()
                if len(search_terms) >= 2:
                    first_name, last_name = search_terms[0], search_terms[-1]
                    cur.execute("""
                        SELECT DISTINCT bp.booking_first_name, bp.booking_last_name, 
                            bp.booking_document_number, bp.passenger_type
                        FROM booking_passengers bp
                        JOIN bookings b ON bp.booking_id = b.id
                        WHERE b.primary_user_id = %s 
                        AND bp.booking_first_name ILIKE %s 
                        AND bp.booking_last_name ILIKE %s
                        ORDER BY bp.created_at DESC
                        LIMIT 10;
                    """, (user_id, f"%{first_name}%", f"%{last_name}%"))
                else:
                    # Single name search
                    cur.execute("""
                        SELECT DISTINCT bp.booking_first_name, bp.booking_last_name,
                            bp.booking_document_number, bp.passenger_type  
                        FROM booking_passengers bp
                        JOIN bookings b ON bp.booking_id = b.id
                        WHERE b.primary_user_id = %s 
                        AND (bp.booking_first_name ILIKE %s OR bp.booking_last_name ILIKE %s)
                        ORDER BY bp.created_at DESC
                        LIMIT 10;
                    """, (user_id, f"%{name_search}%", f"%{name_search}%"))
                
                results = cur.fetchall()
                return {
                    'success': True,
                    'passenger_history': [
                        {
                            'first_name': row[0],
                            'last_name': row[1], 
                            'document_number': row[2],
                            'passenger_type': row[3]
                        } for row in results
                    ]
                }
                
        except Exception as e:
            return {"error": f"Passenger history search failed: {str(e)}"}
    
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
                else:
                    raise Exception("No segment sequence found")
                
                # Build insert query
                fields = list(segment_data.keys())
                placeholders = ', '.join(['%s'] * len(fields))
                field_names = ', '.join(fields)
                
                # Handle JSON fields
                values = []
                for field, value in segment_data.items():
                    if field == 'passenger_assignments' and isinstance(value, dict):
                        values.append(json.dumps(value))
                    else:
                        values.append(value)
                
                cur.execute(f"""
                    INSERT INTO booking_flight_segments ({field_names})
                    VALUES ({placeholders})
                    RETURNING id;
                """, values)
                
                result = cur.fetchone()
                if result:
                    return result[0]
                else:
                    print("Add flight segment returned no result")
                    return None
                
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
                           distance_km, flight_status, passenger_assignments,
                           actual_departure_time, actual_arrival_time, delay_minutes,
                           gate_info, created_at, updated_at
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
                        flight_status=row[17],
                        passenger_assignments=json.loads(row[18]) if row[18] else {},
                        actual_departure_time=row[19], actual_arrival_time=row[20],
                        delay_minutes=row[21], gate_info=row[22], created_at=row[23],
                        updated_at=row[24]
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
                        event_description=row[3],
                        event_data=json.loads(row[4]) if row[4] else {},
                        triggered_by_user_id=row[5], system_event=row[6],
                        created_at=row[7]
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
        elif operation == 'add':
            return self._handle_add_passenger(user_id, **kwargs)
        elif operation == 'update':
            return self._handle_update_passenger(user_id, **kwargs)
        elif operation == 'get':
            return self._handle_get_passengers(user_id, **kwargs)
        elif operation == 'finalize':
            return self._handle_finalize_booking(user_id, **kwargs)
        elif operation == 'cancel':
            return self._handle_cancel_booking(user_id, **kwargs)
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
            
            # Get cached search data
            search_data = implemented_redis_storage_manager.get_data(f"search:{user_id}:{search_id}")
            
            if not search_data:
                return {"error": "Search results expired. Please search again."}
            
            # Create booking with basic info
            booking_data = {
                'primary_user_id': user_id,
                'booking_type': 'flight',
                'search_id': search_id,
                'selected_flight_offers': json.dumps(flight_offer_ids),
                'booking_status': 'draft',
                'payment_status': 'pending',
                'fulfillment_status': 'pending',
                'group_size': kwargs.get('passenger_count', 1),
                'trip_type': search_data.get('trip_type', 'one_way'),
                'origin_airport': search_data.get('origin'),
                'destination_airport': search_data.get('destination'),
                'departure_date': search_data.get('departure_date'),
                'return_date': search_data.get('return_date'),
                'base_price': 0.00,  # Will be updated after Amadeus call
                'taxes_and_fees': 0.00,
                'total_amount': 0.00,
                'currency': 'USD',
                'travel_insurance': False
            }
            
            booking_id = self.create_booking(**booking_data)
            
            if booking_id:
                return {
                    'success': True,
                    'booking_id': booking_id,
                    'status': 'draft',
                    'message': 'Booking created successfully'
                }
            else:
                return {"error": "Failed to create booking"}
                
        except Exception as e:
            return {"error": f"Booking creation failed: {str(e)}"}

    def _handle_add_passenger(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Handle adding passenger from tool"""
        try:
            booking_id = str(kwargs.get('booking_id'))
            
            # Step 1: Create or find passenger profile first
            passenger_profile_id = None
            
            # Check if this passenger already exists for this user
            if kwargs.get('first_name') and kwargs.get('last_name') and kwargs.get('date_of_birth'):
                passenger_profile_id = self._create_or_find_passenger_profile(user_id, kwargs)
            
            # Step 2: Create booking passenger record
            passenger_data = {
                'passenger_type': kwargs.get('passenger_type', 'adult'),
                'passenger_profile_id': passenger_profile_id,  # Link to profile
                'booking_first_name': kwargs.get('first_name'),
                'booking_last_name': kwargs.get('last_name'),
                'booking_document_number': kwargs.get('passport_number'),
                'booking_seat_preference': kwargs.get('seat_preference'),
                'booking_meal_preference': kwargs.get('meal_preference'),
                'is_primary_passenger': kwargs.get('is_primary', False),
                'seat_assignment_status': 'pending',
                'boarding_pass_issued': False,
                'assigned_seats': {}
            }
            
            passenger_id = self.add_passenger_to_booking(booking_id, **passenger_data)
            
            if passenger_id:
                return {
                    'success': True,
                    'passenger_id': passenger_id,
                    'passenger_profile_id': passenger_profile_id,
                    'message': 'Passenger added successfully'
                }
            else:
                return {"error": "Failed to add passenger"}
                
        except Exception as e:
            return {"error": f"Add passenger failed: {str(e)}"}

    def _create_or_find_passenger_profile(self, user_id: int, passenger_data: Dict) -> Optional[str]:
        """Create or find existing passenger profile"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                # Try to find existing passenger profile
                cur.execute("""
                    SELECT pp.id FROM passenger_profiles pp
                    JOIN user_passenger_connections upc ON pp.id = upc.passenger_id
                    WHERE upc.user_id = %s 
                    AND pp.first_name ILIKE %s 
                    AND pp.last_name ILIKE %s
                    AND pp.date_of_birth = %s
                    LIMIT 1;
                """, (user_id, passenger_data.get('first_name', ''), 
                    passenger_data.get('last_name', ''), 
                    passenger_data.get('date_of_birth')))
                
                existing = cur.fetchone()
                if existing:
                    return existing[0]
                
                # Create new passenger profile
                cur.execute("""
                    INSERT INTO passenger_profiles (
                        first_name, last_name, date_of_birth, gender, 
                        email, phone_number, primary_document_type, 
                        primary_document_number, primary_document_expiry,
                        nationality, created_by_user_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (
                    passenger_data.get('first_name'),
                    passenger_data.get('last_name'),
                    passenger_data.get('date_of_birth'),
                    passenger_data.get('gender'),
                    passenger_data.get('email'),
                    passenger_data.get('phone'),
                    'passport',
                    passenger_data.get('passport_number'),
                    passenger_data.get('document_expiry'),
                    passenger_data.get('nationality'),
                    user_id
                ))
                
                profile_id = None
                profile = cur.fetchone()
                if profile:
                    profile_id = profile[0]
                
                # Create user-passenger connection
                cur.execute("""
                    INSERT INTO user_passenger_connections (
                        user_id, passenger_id, relationship, connection_type,
                        can_book_for_passenger, can_modify_passenger_details
                    ) VALUES (%s, %s, %s, %s, %s, %s);
                """, (
                    user_id, profile_id, 
                    'self' if passenger_data.get('is_primary') else 'other',
                    'family', True, True
                ))
                
                return profile_id
                
        except Exception as e:
            print(f"Error creating passenger profile: {e}")
            return None
    
    def _handle_get_passengers(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Handle getting passengers or passenger history"""
        try:
            booking_id = kwargs.get('booking_id')
            name_search = kwargs.get('name_search')
            
            if name_search:
                # Search passenger history
                return self.search_passenger_history(user_id, name_search)
            elif booking_id:
                # Get current booking passengers
                passengers = self.get_booking_passengers(booking_id)
                return {
                    'success': True,
                    'passengers': [
                        {
                            'passenger_id': p.id,
                            'first_name': p.booking_first_name,
                            'last_name': p.booking_last_name,
                            'passenger_type': p.passenger_type,
                            'document_number': p.booking_document_number
                        } for p in passengers
                    ]
                }
            else:
                return {"error": "Either booking_id or name_search required"}
                
        except Exception as e:
            return {"error": f"Get passengers failed: {str(e)}"}

    def _handle_update_passenger(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Handle updating passenger from tool"""
        try:
            booking_id = kwargs.get('booking_id')
            passenger_id = kwargs.get('passenger_id')
            
            if not passenger_id:
                return {"error": "passenger_id required for update"}
            
            # Map tool parameters to database fields
            update_data = {}
            if kwargs.get('first_name'):
                update_data['first_name'] = kwargs['first_name']
            if kwargs.get('last_name'):
                update_data['last_name'] = kwargs['last_name']
            if kwargs.get('passport_number'):
                update_data['passport_number'] = kwargs['passport_number']
            if kwargs.get('seat_preference'):
                update_data['seat_preference'] = kwargs['seat_preference']
            if kwargs.get('meal_preference'):
                update_data['meal_preference'] = kwargs['meal_preference']
            
            result = self.update_passenger_details(str(booking_id), passenger_id, update_data)
            return result
            
        except Exception as e:
            return {"error": f"Update passenger failed: {str(e)}"}

    def _handle_finalize_booking(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Handle booking finalization with Amadeus and Stripe integration"""
        try:
            booking_id = str(kwargs.get('booking_id'))
            
            # Get booking details
            booking_details = self.get_booking_details(booking_id)
            if not booking_details.get('success'):
                return {"error": "Booking not found or incomplete"}
            
            # Get full booking record
            booking = self.get_booking(booking_id)
            if not booking:
                return {"error": "Booking record not found"}
            
            # Get passengers with complete profile data
            passengers = self._get_complete_passenger_data(booking_id)
            if not passengers:
                return {"error": "No passengers found. Add passenger details first."}
            
            # Validate passenger data completeness for Amadeus
            validation_errors = self._validate_passengers_for_amadeus(passengers)
            if validation_errors:
                return {"error": f"Passenger data incomplete: {', '.join(validation_errors)}"}
            
            try:
                # Get the flight search and selected offers
                flight_search = None
                if hasattr(self, 'flight_storage_service'):
                    flight_search = self.flight_storage_service.get_flight_search(str(booking.search_id))
                
                if not flight_search:
                    return {"error": "Original flight search not found"}
                
                # Get selected flight offers with full Amadeus data
                if booking.selected_flight_offers:
                    if isinstance(booking.selected_flight_offers, str):
                        selected_flight_offers = json.loads(booking.selected_flight_offers)
                    else:
                        selected_flight_offers = booking.selected_flight_offers
                else:
                    selected_flight_offers = []

                if not selected_flight_offers:
                    return {"error": "No flight offers selected"}
                
                # Retrieve full flight offer data for pricing
                full_flight_data = []
                offers = self.flight_storage_service.get_search_offers(str(booking.search_id)) if hasattr(self, 'flight_storage_service') else []
                
                for offer_id in selected_flight_offers:
                    # Find the matching offer with full Amadeus data
                    matching_offer = next((o for o in offers if o.flight_offer_id == offer_id), None)
                    if matching_offer and hasattr(matching_offer, 'complete_offer_data'):
                        full_flight_data.append(matching_offer.complete_offer_data)
                
                if not full_flight_data:
                    return {"error": "Flight offer data not available for booking"}
                
                # Initialize Amadeus scraper
                from app.services.api.flights.amadeus_scraper import AmadeusFlightScraper
                amadeus_scraper = AmadeusFlightScraper()
                
                # Step 1: Get confirmed pricing from Amadeus
                print(f"Getting confirmed pricing for booking {booking_id}")
                pricing_response = amadeus_scraper.price_flight_offers(full_flight_data)
                
                if not pricing_response.get('data'):
                    return {"error": "Failed to get confirmed pricing from airline"}
                
                priced_offers = pricing_response['data']['flightOffers']
                confirmed_total = float(pricing_response['data']['flightOffers'][0]['price']['grandTotal'])
                
                # Step 2: Prepare passenger data for Amadeus
                amadeus_passengers = []
                for passenger in passengers:
                    passenger_data = {
                        'first_name': passenger['first_name'],
                        'last_name': passenger['last_name'],
                        'date_of_birth': passenger['date_of_birth'].strftime('%Y-%m-%d') if passenger['date_of_birth'] else '1990-01-01',
                        'gender': passenger.get('gender', 'UNKNOWN').upper(),
                        'email': passenger.get('email', ''),
                        'phone': passenger.get('phone_number', ''),
                        'nationality': passenger.get('nationality', 'US'),
                        'document_number': passenger.get('primary_document_number') or passenger.get('document_number'),
                        'document_expiry': passenger.get('primary_document_expiry').strftime('%Y-%m-%d') if passenger.get('primary_document_expiry') else '2030-12-31', # type: ignore
                        'document_type': passenger.get('primary_document_type', 'PASSPORT').upper()
                    }
                    amadeus_passengers.append(passenger_data)
                
                # Step 3: Create booking with Amadeus
                print(f"Creating Amadeus booking for {booking_id}")
                booking_response = amadeus_scraper.create_flight_booking(
                    priced_offers=priced_offers,
                    passengers_data=amadeus_passengers,
                    booking_reference=booking.booking_reference
                )
                
                if not booking_response.get('data'):
                    return {"error": "Failed to create booking with airline"}
                
                # Extract PNR and booking details
                flight_order = booking_response['data']
                
                # Extract PNR from associatedRecords
                pnr_code = 'NO_PNR'
                associated_records = flight_order.get('associatedRecords', [])
                if associated_records:
                    pnr_code = associated_records[0].get('reference', 'NO_PNR')
                
                # Get pricing details
                flight_offers = flight_order.get('flightOffers', [{}])
                if flight_offers:
                    price_info = flight_offers[0].get('price', {})
                    confirmed_total = float(price_info.get('grandTotal', confirmed_total))
                    base_price = float(price_info.get('base', 0))
                    currency = price_info.get('currency', 'USD')
                else:
                    base_price = confirmed_total * 0.8  # Estimate
                    currency = 'USD'
                
                # Update booking with Amadeus response
                update_success = self.update_booking(booking_id, {
                    'amadeus_pnr': pnr_code,
                    'amadeus_booking_id': flight_order.get('id'),
                    'amadeus_response': booking_response,
                    'total_amount': confirmed_total,
                    'base_price': base_price,
                    'taxes_and_fees': confirmed_total - base_price,
                    'booking_status': 'confirmed_pending_payment',
                    'confirmed_at': datetime.now()
                })
                
                if not update_success:
                    return {"error": "Failed to update booking with PNR information"}
                
                # Mock Stripe payment URL (implement your actual payment integration)
                payment_url = f"https://checkout.stripe.com/pay/session_{booking_id}"
                
                # Add timeline event
                self.add_timeline_event(
                    booking_id=booking_id,
                    event_type='booking_finalized',
                    event_description='Booking confirmed with airline',
                    event_data={
                        'pnr': pnr_code,
                        'amadeus_booking_id': flight_order.get('id'),
                        'confirmed_price': confirmed_total,
                        'currency': currency
                    },
                    triggered_by_user_id=user_id
                )
                
                return {
                    'success': True,
                    'booking_id': booking_id,
                    'pnr': pnr_code,
                    'amadeus_booking_id': flight_order.get('id'),
                    'final_price': confirmed_total,
                    'currency': currency,
                    'payment_url': payment_url,
                    'status': 'confirmed_pending_payment',
                    'message': f'Booking confirmed with airline. PNR: {pnr_code}. Complete payment to finalize.'
                }
                
            except ValueError as ve:
                # Amadeus validation errors
                self.add_timeline_event(
                    booking_id=booking_id,
                    event_type='booking_failed',
                    event_description=f'Booking failed: {str(ve)}',
                    triggered_by_user_id=user_id
                )
                return {"error": f"Booking validation failed: {str(ve)}"}
                
            except ConnectionError as ce:
                # Amadeus API connection errors
                self.add_timeline_event(
                    booking_id=booking_id,
                    event_type='booking_failed',
                    event_description=f'Booking failed: {str(ce)}',
                    triggered_by_user_id=user_id
                )
                return {"error": f"Failed to communicate with airline: {str(ce)}"}
                
        except Exception as e:
            print(f"Booking finalization failed: {e}")
            import traceback
            traceback.print_exc()
            return {"error": f"Booking finalization failed: {str(e)}"}

    def _get_complete_passenger_data(self, booking_id: str) -> List[Dict]:
        """Get complete passenger data including profile information"""
        if not self.storage.conn:
            return []
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        bp.id, bp.booking_first_name, bp.booking_last_name,
                        bp.passenger_type, bp.is_primary_passenger,
                        bp.booking_document_number, bp.booking_seat_preference,
                        bp.booking_meal_preference,
                        -- Profile data (nullable if no profile linked)
                        pp.date_of_birth, pp.gender, pp.email, pp.phone_number,
                        pp.nationality, pp.primary_document_number, 
                        pp.primary_document_expiry, pp.primary_document_type
                    FROM booking_passengers bp
                    LEFT JOIN passenger_profiles pp ON bp.passenger_profile_id = pp.id
                    WHERE bp.booking_id = %s
                    ORDER BY bp.passenger_sequence;
                """, (booking_id,))
                
                passengers = []
                for row in cur.fetchall():
                    passenger = {
                        'passenger_id': row[0],
                        'first_name': row[1],
                        'last_name': row[2],
                        'passenger_type': row[3],
                        'is_primary': row[4],
                        'document_number': row[5] or row[13], # booking document or profile document
                        'seat_preference': row[6],
                        'meal_preference': row[7],
                        # Profile data (from passenger_profiles table)
                        'date_of_birth': row[8],
                        'gender': row[9],
                        'email': row[10],
                        'phone_number': row[11],
                        'nationality': row[12],
                        'primary_document_number': row[13],
                        'primary_document_expiry': row[14],
                        'primary_document_type': row[15]
                    }
                    passengers.append(passenger)
                
                return passengers
                
        except Exception as e:
            print(f"Error getting complete passenger data: {e}")
            return []

    def _validate_passengers_for_amadeus(self, passengers: List[Dict]) -> List[str]:
        """Validate passenger data required for Amadeus booking"""
        errors = []
        
        for i, passenger in enumerate(passengers, 1):
            passenger_ref = f"Passenger {i} ({passenger.get('first_name', 'Unknown')})"
            
            # Required fields for Amadeus
            if not passenger.get('first_name'):
                errors.append(f"{passenger_ref}: Missing first name")
            if not passenger.get('last_name'):
                errors.append(f"{passenger_ref}: Missing last name")
            if not passenger.get('date_of_birth'):
                errors.append(f"{passenger_ref}: Missing date of birth")
            
            # Document validation
            document_number = passenger.get('primary_document_number') or passenger.get('document_number')
            if not document_number:
                errors.append(f"{passenger_ref}: Missing passport/document number")
            
            # Optional but recommended fields
            if not passenger.get('nationality'):
                errors.append(f"{passenger_ref}: Missing nationality (recommended)")
            
            # Validate date format if provided
            if passenger.get('date_of_birth') and not isinstance(passenger['date_of_birth'], (str, type(None))):
                try:
                    # If it's a date object, it's valid
                    if hasattr(passenger['date_of_birth'], 'strftime'):
                        pass  # Valid date object
                    else:
                        errors.append(f"{passenger_ref}: Invalid date of birth format")
                except:
                    errors.append(f"{passenger_ref}: Invalid date of birth format")
        
        return errors

    def _handle_cancel_booking(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Handle booking cancellation"""
        try:
            booking_id = str(kwargs.get('booking_id'))
            reason = kwargs.get('reason', 'No reason provided')
            
            # Get booking details first
            booking = self.get_booking(booking_id)
            if not booking:
                return {"error": "Booking not found"}
            
            # Check if booking belongs to user
            if booking.primary_user_id != user_id:
                return {"error": "Access denied to this booking"}
            
            cancellation_steps = []
            
            # Mock Amadeus cancellation (if PNR exists)
            if booking.amadeus_pnr:
                # TODO: Integrate with actual Amadeus cancellation API
                cancellation_steps.append({
                    "step": "amadeus_cancellation",
                    "success": True,
                    "details": {"pnr": booking.amadeus_pnr, "status": "cancelled"}
                })
            
            # Mock Stripe refund (if payment was completed)
            if booking.payment_status == 'paid':
                # TODO: Integrate with actual Stripe refund API
                cancellation_steps.append({
                    "step": "stripe_refund",
                    "success": True,
                    "details": {"amount": float(booking.total_amount), "currency": booking.currency}
                })
            
            # Update booking status
            update_success = self.update_booking(booking_id, {
                'booking_status': 'cancelled',
                'cancelled_at': datetime.now()
            })
            
            if not update_success:
                return {"error": "Failed to update booking status"}
            
            # Add timeline event
            self.add_timeline_event(
                booking_id=booking_id,
                event_type='booking_cancelled',
                event_description=f'Booking cancelled: {reason}',
                event_data={'reason': reason, 'cancelled_by_user': user_id},
                triggered_by_user_id=user_id
            )
            
            return {
                'success': True,
                'booking_id': booking_id,
                'cancellation_steps': cancellation_steps,
                'status': 'cancelled',
                'message': 'Booking cancelled successfully'
            }
            
        except Exception as e:
            return {"error": f"Cancellation failed: {str(e)}"}
    
    # ====================================================================
    # UTILITY METHODS
    # ====================================================================
    
    def _generate_booking_reference(self) -> str:
        """Generate a unique booking reference"""
        import random
        import string
        
        # Generate format: ABC123DE (3 letters + 3 numbers + 2 letters)
        letters = ''.join(random.choices(string.ascii_uppercase, k=3))
        numbers = ''.join(random.choices(string.digits, k=3))
        suffix = ''.join(random.choices(string.ascii_uppercase, k=2))
        
        return f"{letters}{numbers}{suffix}"