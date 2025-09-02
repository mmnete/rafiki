# test_tool_call_manager.py - Updated for constructor changes
import pytest
from unittest.mock import Mock, MagicMock
from app.tools.tool_call_manager import ToolCallManager, ToolParameter, ToolConfig

class TestToolCallManager:
    
    @pytest.fixture
    def mock_services(self):
        """Create mock services for testing"""
        return {
            'user_storage_service': Mock(),
            'flight_service': Mock(),
            'flight_details_service': Mock(),
            'booking_storage_service': Mock(),
            'shared_storage_service': Mock()  # Added this required service
        }
    
    @pytest.fixture
    def tool_manager(self, mock_services):
        """Create ToolCallManager instance for testing"""
        return ToolCallManager(mock_services)  # Removed shared_storage parameter
    
    @pytest.fixture
    def mock_user_onboarded(self):
        """Mock user with complete onboarding"""
        user = Mock()
        user.id = 'user123'
        user.first_name = 'John'
        user.last_name = 'Doe'
        user.location = 'New York, USA'
        user.preferred_language = 'en'
        return user
    
    @pytest.fixture
    def mock_user_incomplete(self):
        """Mock user with incomplete onboarding"""
        user = Mock()
        user.id = 'user456'
        user.first_name = 'Jane'
        user.last_name = None
        user.location = None
        user.preferred_language = 'en'
        return user

    def test_initialization_with_valid_services(self, mock_services):
        """Test successful initialization with all required services"""
        manager = ToolCallManager(mock_services)
        assert manager.services == mock_services
        assert len(manager.tools) > 0

    def test_initialization_missing_service_raises_error(self):
        """Test initialization fails when required service is missing"""
        incomplete_services = {
            'user_storage_service': Mock(),
            'flight_service': Mock(),
            # Missing other required services
        }
        
        with pytest.raises(ValueError, match="Required service not provided"):
            ToolCallManager(incomplete_services)

    def test_initialization_missing_shared_storage_service(self):
        """Test initialization fails when shared_storage_service is missing"""
        incomplete_services = {
            'user_storage_service': Mock(),
            'flight_service': Mock(),
            'flight_details_service': Mock(),
            'booking_storage_service': Mock(),
            # Missing shared_storage_service
        }
        
        with pytest.raises(ValueError, match="Required service not provided: shared_storage_service"):
            ToolCallManager(incomplete_services)

    def test_all_required_services_validated(self):
        """Test that all required services are properly validated"""
        required_services = [
            'user_storage_service', 'flight_service', 'flight_details_service',
            'booking_storage_service', 'shared_storage_service'
        ]
        
        for missing_service in required_services:
            incomplete_services = {service: Mock() for service in required_services}
            del incomplete_services[missing_service]
            
            with pytest.raises(ValueError, match=f"Required service not provided: {missing_service}"):
                ToolCallManager(incomplete_services)

    def test_user_onboarding_status_check(self, tool_manager):
        """Test user onboarding status detection"""
        # Complete user
        complete_user = Mock()
        complete_user.first_name = 'John'
        complete_user.last_name = 'Doe'
        complete_user.location = 'NYC, USA'
        complete_user.preferred_language = 'en'
        
        assert tool_manager._is_user_onboarded(complete_user) == True
        
        # Incomplete user
        incomplete_user = Mock()
        incomplete_user.first_name = 'Jane'
        incomplete_user.last_name = None
        incomplete_user.location = 'LA, USA'
        incomplete_user.preferred_language = 'en'
        
        assert tool_manager._is_user_onboarded(incomplete_user) == False
        
        # None user
        assert tool_manager._is_user_onboarded(None) == False

    def test_available_tools_for_incomplete_user(self, tool_manager, mock_user_incomplete):
        """Test that incomplete user only gets onboarding tools"""
        available_tools = tool_manager.get_available_tools_for_user(mock_user_incomplete)
        
        # Should only have onboarding tools
        expected_tools = ['get_user_details', 'update_user_profile']
        assert all(tool in available_tools for tool in expected_tools)
        
        # Should not have flight search tools
        flight_tools = ['search_flights', 'create_flight_booking']
        assert not any(tool in available_tools for tool in flight_tools)

    def test_available_tools_for_complete_user(self, tool_manager, mock_user_onboarded):
        """Test that complete user gets flight search tools"""
        available_tools = tool_manager.get_available_tools_for_user(mock_user_onboarded)
        
        # Should have onboarding tools
        onboarding_tools = ['get_user_details', 'update_user_profile']
        assert all(tool in available_tools for tool in onboarding_tools)
        
        # Should have flight search tools
        flight_tools = ['search_flights', 'get_flight_details', 'create_flight_booking']
        assert all(tool in available_tools for tool in flight_tools)

    def test_tool_access_control(self, tool_manager, mock_user_incomplete, mock_user_onboarded):
        """Test tool access control based on user status"""
        # Incomplete user cannot access flight tools
        assert not tool_manager.can_user_access_tool(mock_user_incomplete, 'search_flights')
        assert tool_manager.can_user_access_tool(mock_user_incomplete, 'get_user_details')
        
        # Complete user can access flight tools
        assert tool_manager.can_user_access_tool(mock_user_onboarded, 'search_flights')
        assert tool_manager.can_user_access_tool(mock_user_onboarded, 'get_user_details')

    def test_get_tool_function(self, tool_manager):
        """Test retrieving tool execution functions"""
        # Valid tool
        func = tool_manager.get_tool_function('get_user_details')
        assert func is not None
        assert callable(func)
        
        # Invalid tool
        func = tool_manager.get_tool_function('nonexistent_tool')
        assert func is None

    def test_tool_execution_with_access_denied(self, tool_manager, mock_user_incomplete):
        """Test tool execution fails when user lacks access"""
        result = tool_manager.execute_tool_for_user(
            mock_user_incomplete, 'search_flights', 
            origin='SFO', destination='LAX', departure_date='2025-01-01'
        )
        
        assert 'error' in result
        assert 'Access denied' in result['error']

    def test_tool_execution_success(self, tool_manager, mock_user_onboarded):
        """Test successful tool execution"""
        # Mock the service response
        mock_user_data = {'id': 'user123', 'first_name': 'John'}
        tool_manager.services['user_storage_service'].get_or_create_user.return_value = mock_user_data
        
        result = tool_manager.execute_tool_for_user(mock_user_onboarded, 'get_user_details')
        
        assert result == mock_user_data
        tool_manager.services['user_storage_service'].get_or_create_user.assert_called_once_with('user123')

    def test_tool_execution_with_service_error(self, tool_manager, mock_user_onboarded):
        """Test tool execution handles service errors gracefully"""
        # Mock service to raise exception
        tool_manager.services['user_storage_service'].get_or_create_user.side_effect = Exception("Database error")
        
        result = tool_manager.execute_tool_for_user(mock_user_onboarded, 'get_user_details')
        
        assert 'error' in result
        assert 'Tool execution failed' in result['error']

    def test_flight_search_delegation(self, tool_manager, mock_user_onboarded):
        """Test flight search delegation to flight service"""
        # Mock flight service response
        mock_flights = [{'flight_id': 'test123', 'price': 299.99}]
        tool_manager.services['flight_service'].search_flights.return_value = mock_flights
        
        # Mock shared storage cache response
        tool_manager.services['shared_storage_service'].cache_search_results.return_value = 'search_123'
        
        result = tool_manager.execute_tool_for_user(
            mock_user_onboarded, 'search_flights',
            origin='SFO', destination='LAX', departure_date='2025-09-15'
        )
        
        assert 'search_id' in result
        assert 'flights' in result
        assert result['flights'] == mock_flights
        
        # Verify service calls
        tool_manager.services['flight_service'].search_flights.assert_called_once()
        tool_manager.services['shared_storage_service'].cache_search_results.assert_called_once()

    def test_booking_operation_handlers(self, tool_manager, mock_user_onboarded):
        """Test booking operation handlers"""
        # Mock booking service response
        mock_booking_response = {
            'success': True,
            'booking_id': 'BK123'
        }
        tool_manager.services['booking_storage_service'].handle_booking_operation.return_value = mock_booking_response
        
        # Test create booking operation through tool execution
        result = tool_manager.execute_tool_for_user(
            mock_user_onboarded, 'create_flight_booking',
            search_id='search_123', flight_offer_ids=['offer_456']
        )
        
        assert result['success'] == True
        assert 'booking_id' in result
        tool_manager.services['booking_storage_service'].handle_booking_operation.assert_called_once()

    def test_passenger_management_operations(self, tool_manager, mock_user_onboarded):
        """Test passenger management operations"""
        # Mock booking service response for passenger operations
        mock_passenger_response = {
            'success': True,
            'passenger_id': 'P123'
        }
        tool_manager.services['booking_storage_service'].handle_booking_operation.return_value = mock_passenger_response
        
        result = tool_manager.execute_tool_for_user(
            mock_user_onboarded, 'manage_booking_passengers',
            booking_id='BK123', action='add', passenger_type='adult',
            first_name='John', last_name='Doe', date_of_birth='1990-01-01'
        )
        
        assert result['success'] == True
        assert 'passenger_id' in result

    def test_booking_finalization_workflow(self, tool_manager, mock_user_onboarded):
        """Test booking finalization with payment URL generation"""
        # Mock finalization response
        mock_finalization_response = {
            'success': True,
            'pnr': 'ABC123',
            'payment_url': 'https://checkout.stripe.com/pay/test_session',
            'final_price': 299.99
        }
        tool_manager.services['booking_storage_service'].handle_booking_operation.return_value = mock_finalization_response
        
        result = tool_manager.execute_tool_for_user(
            mock_user_onboarded, 'finalize_booking',
            booking_id='BK123'
        )
        
        assert result['success'] == True
        assert 'pnr' in result
        assert 'payment_url' in result
        assert 'final_price' in result

    def test_booking_details_retrieval(self, tool_manager, mock_user_onboarded):
        """Test booking details retrieval"""
        mock_booking_details = {
            'success': True,
            'booking_id': 'BK123',
            'status': 'confirmed',
            'passengers': [{'first_name': 'John', 'last_name': 'Doe'}]
        }
        tool_manager.services['booking_storage_service'].handle_booking_operation.return_value = mock_booking_details
        
        result = tool_manager.execute_tool_for_user(
            mock_user_onboarded, 'get_booking_details',
            booking_id='BK123'
        )
        
        assert result['success'] == True
        assert result['booking_id'] == 'BK123'
        assert 'passengers' in result

    def test_booking_cancellation(self, tool_manager, mock_user_onboarded):
        """Test booking cancellation workflow"""
        mock_cancellation_response = {
            'success': True,
            'cancellation_steps': [
                {'step': 'amadeus_cancellation', 'success': True},
                {'step': 'stripe_refund', 'success': True}
            ],
            'status': 'cancelled'
        }
        tool_manager.services['booking_storage_service'].handle_booking_operation.return_value = mock_cancellation_response
        
        result = tool_manager.execute_tool_for_user(
            mock_user_onboarded, 'cancel_booking',
            booking_id='BK123', reason='Change of plans'
        )
        
        assert result['success'] == True
        assert result['status'] == 'cancelled'
        assert 'cancellation_steps' in result

    def test_error_handling_in_service_calls(self, tool_manager, mock_user_onboarded):
        """Test error handling in service operations"""
        # Mock service error
        tool_manager.services['booking_storage_service'].handle_booking_operation.side_effect = Exception("Service error")

        result = tool_manager.execute_tool_for_user(
            mock_user_onboarded, 'create_flight_booking',
            search_id='search_123', flight_offer_ids=['offer_456']
        )

        assert 'error' in result
        assert 'Service error' in result['error']  # Check for the actual error message

    def test_tool_instructions_generation(self, tool_manager, mock_user_onboarded):
        """Test tool instructions are generated correctly for user"""
        instructions = tool_manager.get_tool_instructions_for_user(mock_user_onboarded)
        
        assert 'Available Tools' in instructions
        assert 'get_user_details' in instructions
        assert 'search_flights' in instructions
        assert '**Parameters:**' in instructions

    def test_user_phase_determination(self, tool_manager):
        """Test correct user phase identification"""
        # Incomplete user
        incomplete_user = Mock()
        incomplete_user.first_name = None
        assert tool_manager._get_user_phase(incomplete_user) == "Onboarding"
        
        # Complete user
        complete_user = Mock()
        complete_user.first_name = 'John'
        complete_user.last_name = 'Doe'
        complete_user.location = 'NYC'
        complete_user.preferred_language = 'en'
        assert tool_manager._get_user_phase(complete_user) == "Flight Search"

    def test_tool_parameter_validation(self, tool_manager):
        """Test tool parameter configuration is correct"""
        search_tool = tool_manager.tools['search_flights']
        
        # Check required parameters exist
        param_names = [p.name for p in search_tool.parameters]
        assert 'origin' in param_names
        assert 'destination' in param_names
        assert 'departure_date' in param_names
        
        # Check parameter types and requirements
        origin_param = next(p for p in search_tool.parameters if p.name == 'origin')
        assert origin_param.required == True
        assert origin_param.param_type == 'string'

    def test_tool_registration(self, tool_manager):
        """Test tool registration process"""
        # Create a test tool config
        test_tool = ToolConfig(
            name="test_tool",
            description="Test tool",
            parameters=[],
            instructions="Test instructions",
            examples=["test"],
            execute_function=lambda x: x
        )
        
        # Register tool
        tool_manager.register_tool(test_tool)
        
        # Verify registration
        assert 'test_tool' in tool_manager.tools
        assert tool_manager.tools['test_tool'] == test_tool
