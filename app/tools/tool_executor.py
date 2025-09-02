from typing import Any, Dict


class ToolExecutor:
    """
    Executes tools by delegating to appropriate services.
    Pure execution logic - no configuration or prompt generation.
    """
    
    def __init__(self, services: Dict[str, Any]):
        self.services = services
    
    def execute_tool(self, tool_name: str, user_id: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a tool by name with parameters
        """
        try:
            # User Management Tools
            if tool_name == "get_user_details":
                return self._get_user_details(user_id)
            elif tool_name == "update_user_profile":
                return self._update_user_profile(user_id, **kwargs)
            
            # Flight Tools
            elif tool_name == "search_flights":
                return self._search_flights(user_id, **kwargs)
            
            # Booking Tools  
            elif tool_name == "create_flight_booking":
                return self._create_flight_booking(user_id, **kwargs)
            elif tool_name == "add_passenger_to_booking":
                return self._add_passenger_to_booking(user_id, **kwargs)
            elif tool_name == "get_user_bookings":
                return self._get_user_bookings(user_id, **kwargs)
            
            # Payment Tools
            elif tool_name == "process_booking_payment":
                return self._process_booking_payment(user_id, **kwargs)
            elif tool_name == "cancel_booking_with_refund":
                return self._cancel_booking_with_refund(user_id, **kwargs)
            
            # Admin Tools
            elif tool_name == "get_user_balance":
                return self._get_user_balance(user_id)
            
            else:
                return {"error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}
    
    # User Management Implementations
    def _get_user_details(self, user_id: str) -> Dict[str, Any]:
        """Get user details"""
        user = self.services["user"].get_user_by_id(user_id)
        if not user:
            return {"error": "User not found"}
        
        return {
            "user_id": user.id,
            "first_name": getattr(user, 'first_name', None),
            "last_name": getattr(user, 'last_name', None),
            "location": getattr(user, 'location', None),
            "preferred_language": getattr(user, 'preferred_language', None),
            "email": getattr(user, 'email', None),
            "phone_number": getattr(user, 'phone_number', None),
            "status": getattr(user, 'status', 'unknown'),
            "is_trusted_tester": getattr(user, 'is_trusted_tester', False),
        }
    
    def _update_user_profile(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """Update user profile"""
        # Filter out None values
        updates = {k: v for k, v in kwargs.items() if v is not None}
        
        updated_user = self.services["user"].update_user_by_id(user_id, **updates)
        if updated_user:
            return {"success": True, "message": "Profile updated successfully", "updated_fields": list(updates.keys())}
        return {"error": "Failed to update profile"}
    
    # Flight Tool Implementations
    def _search_flights(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """Search flights"""
        flight_service = self.services["flight"]
        
        # Call flight search
        search_results = flight_service.search_flights(**kwargs)
        
        # Handle dual return format if your flight service returns (summary, full)
        if isinstance(search_results, tuple) and len(search_results) == 2:
            summary_results, full_results = search_results
            return summary_results
        
        return search_results  # type: ignore
    
    # Booking Tool Implementations
    def _create_flight_booking(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """Create flight booking"""
        return self.services["booking"].create_booking(user_id, **kwargs)
    
    def _add_passenger_to_booking(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """Add passenger to booking"""
        booking_id = kwargs.pop('booking_id')
        return self.services["booking"].add_passenger_to_booking(booking_id, **kwargs)
    
    def _get_user_bookings(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """Get user bookings"""
        return self.services["booking"].get_user_bookings(user_id, **kwargs)
    
    # Payment Tool Implementations
    def _process_booking_payment(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """Process booking payment"""
        return self.services["payment"].process_booking_payment(user_id, **kwargs)
    
    def _cancel_booking_with_refund(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """Cancel booking with refund"""
        booking_id = kwargs.get('booking_id')
        reason = kwargs.get('cancellation_reason')
        return self.services["booking"].cancel_booking_with_refund(booking_id, reason)
    
    # Admin Tool Implementations
    def _get_user_balance(self, user_id: str) -> Dict[str, Any]:
        """Get user balance"""
        return self.services["payment"].get_user_balance(user_id)

