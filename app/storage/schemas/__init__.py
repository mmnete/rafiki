from typing import Dict, List
from .base_schema import BaseSchema
from .user_schema import UserSchema
from .passenger_schema import PassengerSchema
from .booking_schema import BookingSchema
from .payment_schema import PaymentSchema
from .conversation_schema import ConversationSchema
from .flight_schema import FlightSchema
from .document_schema import DocumentSchema
from .personalization_schema import PersonalizationSchema

class SchemaRegistry:
    """Registry for all database schemas with dependency management"""
    
    def __init__(self):
        self.schemas = {
            'user': UserSchema(),
            'passenger': PassengerSchema(),
            'personalization': PersonalizationSchema(),
            'flight': FlightSchema(),
            'booking': BookingSchema(),
            'payment': PaymentSchema(),
            'document': DocumentSchema(),
            'conversation': ConversationSchema(),
        }
    
    def get_creation_order(self) -> List[str]:
        """Get schemas in dependency order for creation"""
        return [
            'user',           # Core user accounts
            'passenger',      # Passenger profiles (can exist before bookings)
            'personalization', # User preferences and connections
            'flight',         # Flight searches and data
            'booking',        # Bookings (depends on users, passengers, flights)
            'payment',        # Payment methods and transactions
            'document',       # Files and documents
            'conversation',   # Conversation history
        ]
    
    def get_all_schemas(self) -> Dict[str, BaseSchema]:
        """Get all schemas"""
        return self.schemas