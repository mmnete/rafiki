# ==============================================================================
# tests/storage/services/test_flight_storage_service.py
# ==============================================================================
import pytest
import json
from unittest.mock import Mock, MagicMock
from datetime import datetime, date, timedelta
from decimal import Decimal
from app.storage.services.flight_storage_service import (
    FlightStorageService, FlightSearch, FlightOffer, FlightStatusUpdate
)

class TestFlightStorageService:
    
    @pytest.fixture
    def mock_storage(self):
        """Mock storage service"""
        storage = Mock()
        storage.conn = MagicMock()
        return storage
    
    @pytest.fixture
    def flight_service(self, mock_storage):
        """Create flight service with mocked storage"""
        return FlightStorageService(mock_storage)
    
    def test_create_flight_search_success(self, flight_service, mock_storage):
        """Test successful flight search creation"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ['search-uuid-123']
        
        with mock_cursor:
            # Mock get_search_by_custom_id to return None (no existing search)
            flight_service.get_search_by_custom_id = Mock(return_value=None)
            
            search_params = {
                'origin': 'NYC',
                'destination': 'LAX',
                'departure_date': '2024-06-15',
                'passengers': 2
            }
            
            # Act
            result = flight_service.create_flight_search(
                user_id=123,
                custom_search_id='search_123_456',
                search_type='one_way',
                search_params=search_params,
                result_count=25,
                apis_used=['amadeus', 'skyscanner']
            )
            
            # Assert
            assert result == 'search-uuid-123'
            mock_cursor.execute.assert_called()
            
            # Verify INSERT query
            execute_call = mock_cursor.execute.call_args[0]
            assert "INSERT INTO flight_searches" in execute_call[0]
            assert "RETURNING id" in execute_call[0]
    
    def test_create_flight_search_existing_custom_id(self, flight_service, mock_storage):
        """Test creating search with existing custom_search_id returns existing"""
        # Arrange
        existing_search = FlightSearch(
            id='existing-search-123',
            user_id=123,
            custom_search_id='search_123_456',
            search_type='one_way',
            search_params={},
            raw_results=[],
            processed_results=[],
            result_count=0,
            apis_used=[],
            search_duration_ms=None,
            cache_hit=False,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=7),
            accessed_at=datetime.now(),
            access_count=1
        )
        
        flight_service.get_search_by_custom_id = Mock(return_value=existing_search)
        flight_service.update_search_access = Mock(return_value=True)
        
        # Act
        result = flight_service.create_flight_search(
            user_id=123,
            custom_search_id='search_123_456',
            search_type='one_way',
            search_params={}
        )
        
        # Assert
        assert result == 'existing-search-123'
        flight_service.update_search_access.assert_called_once_with('existing-search-123')
    
    def test_get_flight_search_success(self, flight_service, mock_storage):
        """Test successful flight search retrieval"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        search_row = [
            'search-123', 123, 'custom_search_456', 'round_trip',
            '{"origin": "NYC", "destination": "LAX"}',
            '[]', '[]', 25, '["amadeus"]', 1500, False,
            datetime.now(), datetime.now() + timedelta(days=7),
            datetime.now(), 3
        ]
        mock_cursor.fetchone.return_value = search_row
        
        # Act
        result = flight_service.get_flight_search('search-123')
        
        # Assert
        assert result is not None
        assert isinstance(result, FlightSearch)
        assert result.id == 'search-123'
        assert result.user_id == 123
        assert result.search_type == 'round_trip'
        assert result.result_count == 25
        assert result.apis_used == ['amadeus']
    
    def test_get_search_by_custom_id_success(self, flight_service, mock_storage):
        """Test getting search by custom ID"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        search_row = [
            'search-123', 123, 'custom_search_456', 'one_way',
            '{"origin": "NYC"}', '[]', '[]', 10, '[]',
            800, True, datetime.now(), datetime.now() + timedelta(days=7),
            datetime.now(), 1
        ]
        mock_cursor.fetchone.return_value = search_row
        
        # Act
        result = flight_service.get_search_by_custom_id('custom_search_456')
        
        # Assert
        assert result is not None
        assert result.custom_search_id == 'custom_search_456'
        assert result.cache_hit is True
        
        # Verify expiration check in query
        execute_call = mock_cursor.execute.call_args[0]
        assert "expires_at > CURRENT_TIMESTAMP" in execute_call[0]
    
    def test_update_search_access_success(self, flight_service, mock_storage):
        """Test updating search access"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 1
        
        # Act
        result = flight_service.update_search_access('search-123')
        
        # Assert
        assert result is True
        mock_cursor.execute.assert_called_once()
        
        execute_call = mock_cursor.execute.call_args[0]
        assert "UPDATE flight_searches" in execute_call[0]
        assert "accessed_at = CURRENT_TIMESTAMP" in execute_call[0]
        assert "access_count = access_count + 1" in execute_call[0]
    
    def test_get_user_searches(self, flight_service, mock_storage):
        """Test getting user searches"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        search_rows = [
            [
                'search-1', 123, 'search_1', 'one_way', '{}',
                '[]', '[]', 5, '[]', None, False,
                datetime.now(), datetime.now() + timedelta(days=7),
                datetime.now(), 1
            ],
            [
                'search-2', 123, 'search_2', 'round_trip', '{}',
                '[]', '[]', 8, '[]', None, False,
                datetime.now(), datetime.now() + timedelta(days=7),
                datetime.now(), 1
            ]
        ]
        mock_cursor.fetchall.return_value = search_rows
        
        # Act
        result = flight_service.get_user_searches(123, limit=10)
        
        # Assert
        assert len(result) == 2
        assert all(isinstance(search, FlightSearch) for search in result)
        assert result[0].user_id == 123
        
        # Verify query
        execute_call = mock_cursor.execute.call_args[0]
        assert "WHERE user_id = %s" in execute_call[0]
        assert "ORDER BY created_at DESC" in execute_call[0]
        assert "LIMIT %s" in execute_call[0]
    
    def test_add_flight_offer_success(self, flight_service, mock_storage):
        """Test adding flight offer"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ['offer-uuid-123']
        
        # Act
        result = flight_service.add_flight_offer(
            search_id='search-123',
            flight_offer_id='AA1234_2024-06-15',
            base_price=Decimal('199.99'),
            total_price=Decimal('249.99'),
            taxes_and_fees=Decimal('50.00'),
            airline_codes=['AA'],
            route_summary='NYC -> LAX',
            total_duration_minutes=360,
            stops_count=0,
            complete_offer_data={'segments': [{'flight': 'AA1234'}]}
        )
        
        # Assert
        assert result == 'offer-uuid-123'
        mock_cursor.execute.assert_called_once()
        
        execute_call = mock_cursor.execute.call_args[0]
        assert "INSERT INTO flight_offers" in execute_call[0]
        assert "RETURNING id" in execute_call[0]
    
    def test_get_search_offers_with_sorting(self, flight_service, mock_storage):
        """Test getting search offers with different sorting options"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        offer_rows = [
            [
                'offer-1', 'search-123', 'AA1234', 'amadeus-offer-1',
                Decimal('199.99'), Decimal('50.00'), Decimal('249.99'), 'USD',
                '["AA"]', 'NYC -> LAX', 360, 0, None, 5,
                '{}', '{}', datetime.now()
            ]
        ]
        mock_cursor.fetchall.return_value = offer_rows
        
        # Act
        result = flight_service.get_search_offers('search-123', sort_by='price')
        
        # Assert
        assert len(result) == 1
        assert isinstance(result[0], FlightOffer)
        assert result[0].total_price == Decimal('249.99')
        assert result[0].airline_codes == ['AA']
        
        # Verify sort order in query
        execute_call = mock_cursor.execute.call_args[0]
        assert "ORDER BY total_price ASC" in execute_call[0]
    
    def test_get_search_offers_duration_sort(self, flight_service, mock_storage):
        """Test getting offers sorted by duration"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        
        # Act
        flight_service.get_search_offers('search-123', sort_by='duration')
        
        # Assert
        execute_call = mock_cursor.execute.call_args[0]
        assert "ORDER BY total_duration_minutes ASC" in execute_call[0]
    
    def test_get_flight_offer_success(self, flight_service, mock_storage):
        """Test getting specific flight offer"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        offer_row = [
            'offer-123', 'search-456', 'UA5678', None,
            Decimal('299.99'), Decimal('75.00'), Decimal('374.99'), 'USD',
            '["UA", "LH"]', 'NYC -> FRA -> LAX', 720, 1,
            datetime.now() + timedelta(hours=2), 3,
            '{"refundable": false}', '{"segments": []}', datetime.now()
        ]
        mock_cursor.fetchone.return_value = offer_row
        
        # Act
        result = flight_service.get_flight_offer('offer-123')
        
        # Assert
        assert result is not None
        assert isinstance(result, FlightOffer)
        assert result.id == 'offer-123'
        assert result.flight_offer_id == 'UA5678'
        assert result.stops_count == 1
        assert result.airline_codes == ['UA', 'LH']
    
    def test_add_flight_status_update_success(self, flight_service, mock_storage):
        """Test adding flight status update"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = [1]
        
        # Act
        result = flight_service.add_flight_status_update(
            airline_code='AA',
            flight_number='1234',
            scheduled_departure_date=date(2024, 6, 15),
            current_status='delayed',
            delay_minutes=30,
            new_departure_time=datetime(2024, 6, 15, 9, 30),
            gate='A12',
            status_message='Delayed due to weather'
        )
        
        # Assert
        assert result == 1
        mock_cursor.execute.assert_called_once()
        
        execute_call = mock_cursor.execute.call_args[0]
        assert "INSERT INTO flight_status_updates" in execute_call[0]
    
    def test_get_flight_status_success(self, flight_service, mock_storage):
        """Test getting flight status"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        status_row = [
            1, 'AA', '1234', date(2024, 6, 15), 'delayed', 30,
            datetime(2024, 6, 15, 9, 30), datetime(2024, 6, 15, 12, 30),
            'A12', 'T1', 'Weather delay', 'airline_api', datetime.now()
        ]
        mock_cursor.fetchone.return_value = status_row
        
        # Act
        result = flight_service.get_flight_status('AA', '1234', date(2024, 6, 15))
        
        # Assert
        assert result is not None
        assert isinstance(result, FlightStatusUpdate)
        assert result.airline_code == 'AA'
        assert result.flight_number == '1234'
        assert result.current_status == 'delayed'
        assert result.delay_minutes == 30
        
        # Verify query gets latest status
        execute_call = mock_cursor.execute.call_args[0]
        assert "ORDER BY created_at DESC" in execute_call[0]
        assert "LIMIT 1" in execute_call[0]
    
    def test_cleanup_expired_searches_success(self, flight_service, mock_storage):
        """Test cleaning up expired searches"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 5  # 5 records deleted
        
        # Act
        result = flight_service.cleanup_expired_searches(days_old=7)
        
        # Assert
        assert result == 5
        mock_cursor.execute.assert_called_once()
        
        execute_call = mock_cursor.execute.call_args[0]
        assert "DELETE FROM flight_searches" in execute_call[0]
        assert "expires_at <" in execute_call[0]
        assert "created_at <" in execute_call[0]
    
    def test_get_search_statistics_with_user(self, flight_service, mock_storage):
        """Test getting search statistics for specific user"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        stats_row = [50, 15, 1200.5, 12.8, 30, 20]  # total, cache_hits, avg_duration, avg_results, one_way, round_trip
        mock_cursor.fetchone.return_value = stats_row
        
        # Act
        result = flight_service.get_search_statistics(user_id=123)
        
        # Assert
        assert result['total_searches'] == 50
        assert result['cache_hits'] == 15
        assert result['cache_hit_rate'] == 30.0  # 15/50 * 100
        assert result['avg_duration_ms'] == 1200.5
        assert result['avg_results'] == 12.8
        assert result['one_way_searches'] == 30
        assert result['round_trip_searches'] == 20
        
        # Verify user filter in query
        execute_call = mock_cursor.execute.call_args[0]
        assert "WHERE user_id = %s" in execute_call[0]
    
    def test_get_search_statistics_global(self, flight_service, mock_storage):
        """Test getting global search statistics"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        stats_row = [100, 25, 800.0, 15.2, 60, 40]
        mock_cursor.fetchone.return_value = stats_row
        
        # Act
        result = flight_service.get_search_statistics()
        
        # Assert
        assert result['total_searches'] == 100
        assert result['cache_hit_rate'] == 25.0
        
        # Verify no user filter
        execute_call = mock_cursor.execute.call_args[0]
        assert "WHERE user_id" not in execute_call[0]
    
    def test_json_field_handling(self, flight_service, mock_storage):
        """Test proper JSON field serialization"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ['search-123']
        
        flight_service.get_search_by_custom_id = Mock(return_value=None)
        
        search_params = {'origin': 'NYC', 'destination': 'LAX'}
        apis_used = ['amadeus', 'skyscanner']
        
        # Act
        flight_service.create_flight_search(
            user_id=123,
            custom_search_id='test_search',
            search_type='one_way',
            search_params=search_params,
            apis_used=apis_used
        )
        
        # Assert
        execute_call = mock_cursor.execute.call_args[0]
        execute_params = mock_cursor.execute.call_args[0][1]
        
        # Verify JSON serialization
        assert json.dumps(search_params) in execute_params
        assert json.dumps(apis_used) in execute_params
    
    def test_exception_handling(self, flight_service, mock_storage):
        """Test exception handling in various methods"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Database error")
        
        # Act & Assert
        assert flight_service.create_flight_search(123, 'test', 'one_way', {}) is None
        assert flight_service.get_flight_search('search-123') is None
        assert flight_service.get_search_by_custom_id('custom-123') is None
        assert flight_service.update_search_access('search-123') is False
        assert flight_service.get_user_searches(123) == []
        assert flight_service.add_flight_offer('search-123', 'offer-123', Decimal('100'), Decimal('100')) is None
        assert flight_service.get_search_offers('search-123') == []
        assert flight_service.get_flight_offer('offer-123') is None
        assert flight_service.add_flight_status_update('AA', '1234', date.today(), 'on_time') is None
        assert flight_service.get_flight_status('AA', '1234', date.today()) is None
        assert flight_service.cleanup_expired_searches() == 0
        assert flight_service.get_search_statistics() == {}
    
    def test_no_connection_handling(self, flight_service):
        """Test handling when no database connection"""
        # Arrange
        flight_service.storage.conn = None
        
        # Act & Assert
        assert flight_service.create_flight_search(123, 'test', 'one_way', {}) is None
        assert flight_service.get_flight_search('search-123') is None
        assert flight_service.get_search_by_custom_id('custom-123') is None
        assert flight_service.update_search_access('search-123') is False
        assert flight_service.get_user_searches(123) == []
        assert flight_service.add_flight_offer('search-123', 'offer-123', Decimal('100'), Decimal('100')) is None
        assert flight_service.get_search_offers('search-123') == []
        assert flight_service.get_flight_offer('offer-123') is None
        assert flight_service.add_flight_status_update('AA', '1234', date.today(), 'on_time') is None
        assert flight_service.get_flight_status('AA', '1234', date.today()) is None
        assert flight_service.cleanup_expired_searches() == 0
        assert flight_service.get_search_statistics() == {}
    
    def test_offer_sort_options(self, flight_service, mock_storage):
        """Test different sorting options for offers"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        
        # Test different sort options
        sort_tests = [
            ('price', 'total_price ASC'),
            ('duration', 'total_duration_minutes ASC'), 
            ('stops', 'stops_count ASC, total_price ASC'),
            ('departure', 'created_at DESC'),
            ('invalid', 'total_price ASC')  # Should default to price
        ]
        
        for sort_by, expected_order in sort_tests:
            # Act
            flight_service.get_search_offers('search-123', sort_by=sort_by)
            
            # Assert
            execute_call = mock_cursor.execute.call_args[0]
            assert expected_order in execute_call[0]
    
    def test_flight_search_not_found(self, flight_service, mock_storage):
        """Test getting non-existent flight search"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        
        # Act
        result = flight_service.get_flight_search('nonexistent-search')
        
        # Assert
        assert result is None
    
    def test_flight_offer_not_found(self, flight_service, mock_storage):
        """Test getting non-existent flight offer"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        
        # Act
        result = flight_service.get_flight_offer('nonexistent-offer')
        
        # Assert
        assert result is None
    
    def test_flight_status_not_found(self, flight_service, mock_storage):
        """Test getting non-existent flight status"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        
        # Act
        result = flight_service.get_flight_status('XX', '0000', date.today())
        
        # Assert
        assert result is None
    
    def test_zero_division_in_statistics(self, flight_service, mock_storage):
        """Test statistics calculation with zero searches"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        stats_row = [0, 0, None, None, 0, 0]  # Zero searches
        mock_cursor.fetchone.return_value = stats_row
        
        # Act
        result = flight_service.get_search_statistics()
        
        # Assert
        assert result['cache_hit_rate'] == 0  # Should handle division by zero
        assert result['avg_duration_ms'] == 0
        assert result['avg_results'] == 0