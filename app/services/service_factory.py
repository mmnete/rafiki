# app/services/service_factory.py
import os
from typing import Dict, Any
from app.storage.db_service import StorageService
from app.services.api.flights.flight_service import FlightService
from app.services.modelling.model_service import ModelService
from app.services.modelling.response_parser import ResponseParser
from app.services.modelling.tool_executor_service import ToolExecutorService
from app.services.messaging.conversation_orchestrator import ConversationOrchestrator

from app.storage.services.conversation_storage_service import ConversationStorageService
from app.storage.services.flight_storage_service import FlightStorageService
from app.storage.services.flight_details_service import FlightDetailsService
from app.storage.services.booking_storage_service import BookingStorageService
from app.storage.services.user_storage_service import UserStorageService
from app.storage.services.shared_storage import shared_storage_service

from app.controllers.localization_manager import LocalizationManager

from app.storage.schema_manager import SchemaManager


class ServiceFactory:
    """Factory for creating and managing services"""
    
    @staticmethod
    def create_services(use_real_payments: bool = False) -> Dict[str, Any]:
        """Create all services with appropriate implementations"""
        
        
        base_storage_service = StorageService()
        schema_manager = SchemaManager(base_storage_service)
    
        # Create tables if they don't exist
        print("🔧 Initializing database schemas...")
        if schema_manager.create_all_tables():
            print("✅ Database schemas initialized successfully")
        else:
            print("❌ Failed to initialize database schemas")
            # You can choose to raise an exception here if you want the app to fail
            # raise RuntimeError("Database schema initialization failed")
        
        # Verify tables exist (optional check)
        if not schema_manager.verify_tables_exist():
            print("⚠️  Warning: Some required tables may be missing")
        
        
        flight_storage_service = FlightStorageService(base_storage_service) 
        booking_storage_service = BookingStorageService(base_storage_service, shared_storage_service)
        user_storage_service = UserStorageService(base_storage_service)
        conversation_storage_service = ConversationStorageService(base_storage_service)
        
        localization_manager = LocalizationManager()
        flight_service = FlightService(flight_storage_service, booking_storage_service, user_storage_service)
        flight_details_service = FlightDetailsService(flight_storage_service)
        
        payment_api_key = os.getenv("PAYMENT_API_KEY")
        if not payment_api_key:
            raise ValueError("PAYMENT_API_KEY environment variable is not set")
        
        # Model services (clean architecture)
        model_service = ModelService(use_openai=True)  # Configure as needed
        response_parser = ResponseParser()
        tool_executor = ToolExecutorService(max_workers=5)
        conversation_orchestrator = ConversationOrchestrator(
            model_service=model_service,
            response_parser=response_parser,
            tool_executor=tool_executor,
            max_iterations=5
        )
        
        return {
            "shared_storage_service": shared_storage_service,
            # storage services
            "base_storage_service": base_storage_service,
            "user_storage_service": user_storage_service,
            "flight_storage_service": flight_storage_service,
            "flight_details_service": flight_details_service,
            "booking_storage_service": booking_storage_service,
            "conversation_storage_service": conversation_storage_service,
            
            # services
            "flight_service": flight_service,
            "localization_manager": localization_manager,
            
            # Model services
            "conversation_orchestrator": conversation_orchestrator,  # Main interface
            "model_backend": model_service,      # Direct model access
            "response_parser": response_parser,  # For testing
            "tool_executor": tool_executor       # For testing
        }
