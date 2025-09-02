# ==============================================================================
# tests/storage/services/test_payment_storage_service.py
# ==============================================================================
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from decimal import Decimal
from app.storage.services.payment_storage_service import (
    PaymentStorageService, PaymentMethod, Payment
)

class TestPaymentStorageService:
    
    @pytest.fixture
    def mock_storage(self):
        """Mock storage service"""
        storage = Mock()
        storage.conn = MagicMock()
        return storage
    
    @pytest.fixture
    def payment_service(self, mock_storage):
        """Create payment service with mocked storage"""
        return PaymentStorageService(mock_storage)
    
    def test_add_payment_method_card_success(self, payment_service, mock_storage):
        """Test adding a card payment method"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ['method-uuid-123']
        
        method_data = {
            'card_brand': 'visa',
            'card_last_four': '1234',
            'card_holder_name': 'John Doe',
            'card_expiry_month': 12,
            'card_expiry_year': 2030,
            'stripe_payment_method_id': 'pm_123456789',
            'is_primary': True
        }
        
        # Act
        result = payment_service.add_payment_method(
            user_id=123,
            method_type='card',
            provider='stripe',
            **method_data
        )
        
        # Assert
        assert result == 'method-uuid-123'
        assert mock_cursor.execute.call_count == 2  # UPDATE primary + INSERT method
        
        # Verify primary method update
        first_call = mock_cursor.execute.call_args_list[0][0]
        assert "UPDATE payment_methods" in first_call[0]
        assert "is_primary = FALSE" in first_call[0]
    
    def test_add_payment_method_virtual_card(self, payment_service, mock_storage):
        """Test adding a virtual payment method"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ['virtual-method-123']
        
        method_data = {
            'is_virtual': True,
            'virtual_card_number': '4111111111111111',
            'virtual_cvv': '123',
            'virtual_balance': Decimal('10000.00'),
            'virtual_daily_limit': Decimal('5000.00')
        }
        
        # Act
        result = payment_service.add_payment_method(
            user_id=123,
            method_type='virtual',
            provider='test',
            **method_data
        )
        
        # Assert
        assert result == 'virtual-method-123'
        mock_cursor.execute.assert_called()
        
        execute_call = mock_cursor.execute.call_args[0]
        assert "INSERT INTO payment_methods" in execute_call[0]
    
    def test_add_payment_method_mobile_money(self, payment_service, mock_storage):
        """Test adding mobile money payment method"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ['mobile-method-123']
        
        method_data = {
            'mobile_number': '+254712345678',
            'mobile_provider': 'M-Pesa',
            'mobile_account_name': 'John Doe'
        }
        
        # Act
        result = payment_service.add_payment_method(
            user_id=123,
            method_type='mobile_money',
            provider='safaricom',
            **method_data
        )
        
        # Assert
        assert result == 'mobile-method-123'
    
    def test_get_payment_method_success(self, payment_service, mock_storage):
        """Test successful payment method retrieval"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        method_row = [
            'method-123', 456, 'card', 'stripe', False, True, True,
            'visa', '1234', 'John Doe', 12, 2030, 'US',
            None, None, None, None, None, None, None,
            'Chase Bank', '5678', 'cus_123', 'pm_456',
            datetime.now(), datetime.now()
        ]
        mock_cursor.fetchone.return_value = method_row
        
        # Act
        result = payment_service.get_payment_method('method-123')
        
        # Assert
        assert result is not None
        assert isinstance(result, PaymentMethod)
        assert result.id == 'method-123'
        assert result.method_type == 'card'
        assert result.card_brand == 'visa'
        assert result.is_primary is True
    
    def test_get_user_payment_methods(self, payment_service, mock_storage):
        """Test getting user payment methods"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        method_rows = [
            [
                'method-1', 123, 'card', 'stripe', False, True, True,
                'visa', '1234', 'John Doe', 12, 2030, 'US',
                None, None, None, None, None, None, None,
                None, None, 'cus_123', 'pm_456',
                datetime.now(), datetime.now()],
            [
                'method-2', 123, 'mobile_money', 'safaricom', False, False, True,
                None, None, None, None, None, None,
                None, None, None, None, '+254712345678', 'M-Pesa', 'Jane Doe',
                None, None, None, None,
                datetime.now(), datetime.now()
            ]
        ]
        mock_cursor.fetchall.return_value = method_rows
        
        # Act
        result = payment_service.get_user_payment_methods(123)
        
        # Assert
        assert len(result) == 2
        assert result[0].is_primary is True  # Should be ordered by primary first
        assert result[1].method_type == 'mobile_money'
        
        # Verify active filter and ordering
        execute_call = mock_cursor.execute.call_args[0]
        assert "AND is_active = TRUE" in execute_call[0]
        assert "ORDER BY is_primary DESC, created_at DESC" in execute_call[0]
    
    def test_update_payment_method_set_primary(self, payment_service, mock_storage):
        """Test updating payment method to primary"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = [123]  # user_id lookup
        mock_cursor.rowcount = 1
        
        # Act
        result = payment_service.update_payment_method('method-123', is_primary=True)
        
        # Assert
        assert result is True
        assert mock_cursor.execute.call_count == 3  # SELECT user_id + UPDATE others + UPDATE target
    
    def test_create_payment_success(self, payment_service, mock_storage):
        """Test successful payment creation"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ['payment-uuid-123']
        
        payment_data = {
            'booking_id': 'booking-456',
            'payment_method_id': 'method-789',
            'description': 'Flight booking payment',
            'provider_transaction_id': 'stripe_pi_123'
        }
        
        # Act
        result = payment_service.create_payment(
            user_id=123,
            amount=Decimal('299.99'),
            currency='USD',
            **payment_data
        )
        
        # Assert
        assert result == 'payment-uuid-123'
        mock_cursor.execute.assert_called_once()
        
        execute_call = mock_cursor.execute.call_args[0]
        assert "INSERT INTO payments" in execute_call[0]
        assert "RETURNING id" in execute_call[0]
    
    def test_create_payment_generates_transaction_id(self, payment_service, mock_storage):
        """Test that transaction ID is generated if not provided"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ['payment-123']
        
        # Act
        result = payment_service.create_payment(
            user_id=123,
            amount=Decimal('100.00')
        )
        
        # Assert
        assert result == 'payment-123'
        
        # Verify transaction_id was generated
        execute_call = mock_cursor.execute.call_args[0]
        params = execute_call[1]
        # Find transaction_id in parameters (should start with TXN_)
        transaction_id = None
        for param in params:
            if isinstance(param, str) and param.startswith('TXN_'):
                transaction_id = param
                break
        assert transaction_id is not None
        assert len(transaction_id) == 20  # TXN_ + 16 hex chars
    
    def test_get_payment_success(self, payment_service, mock_storage):
        """Test successful payment retrieval"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        payment_row = [
            'payment-123', 'booking-456', 789, 'method-101',
            'TXN_ABC123DEF456', 'stripe_pi_789', Decimal('299.99'), 'USD',
            'completed', 'payment', 'Flight booking payment',
            Decimal('0.00'), None, datetime.now(), datetime.now(), datetime.now()
        ]
        mock_cursor.fetchone.return_value = payment_row
        
        # Act
        result = payment_service.get_payment('payment-123')
        
        # Assert
        assert result is not None
        assert isinstance(result, Payment)
        assert result.id == 'payment-123'
        assert result.amount == Decimal('299.99')
        assert result.status == 'completed'
        assert result.refunded_amount == Decimal('0.00')
    
    def test_get_payment_by_transaction_id_success(self, payment_service, mock_storage):
        """Test getting payment by transaction ID"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        payment_row = [
            'payment-456', None, 123, None, 'TXN_CUSTOM123',
            None, Decimal('50.00'), 'USD', 'pending', 'payment',
            None, Decimal('0.00'), None, datetime.now(), datetime.now(), None
        ]
        mock_cursor.fetchone.return_value = payment_row
        
        # Act
        result = payment_service.get_payment_by_transaction_id('TXN_CUSTOM123')
        
        # Assert
        assert result is not None
        assert result.transaction_id == 'TXN_CUSTOM123'
        assert result.status == 'pending'
    
    def test_update_payment_status_success(self, payment_service, mock_storage):
        """Test updating payment status"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 1
        
        # Act
        result = payment_service.update_payment_status(
            'payment-123', 
            'completed', 
            provider_transaction_id='stripe_pi_789'
        )
        
        # Assert
        assert result is True
        mock_cursor.execute.assert_called_once()
        
        execute_call = mock_cursor.execute.call_args[0]
        assert "UPDATE payments" in execute_call[0]
        assert "status = %s" in execute_call[0]
        assert "completed_at = %s" in execute_call[0]  # Should set completion time
    
    def test_process_refund_success(self, payment_service, mock_storage):
        """Test processing a refund"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [
            ['refund-payment-123']  # Return from create_payment call
        ]
        
        # Mock the get_payment call
        original_payment = Payment(
            id='payment-123', booking_id='booking-456', user_id=789,
            payment_method_id='method-101', transaction_id='TXN_ORIGINAL',
            provider_transaction_id='stripe_pi_original', amount=Decimal('299.99'),
            currency='USD', status='completed', transaction_type='payment',
            description='Original payment', refunded_amount=Decimal('0.00'),
            refund_reason=None, created_at=datetime.now(), updated_at=datetime.now(),
            completed_at=datetime.now()
        )
        payment_service.get_payment = Mock(return_value=original_payment)
        payment_service.create_payment = Mock(return_value='refund-payment-123')
        
        # Act
        result = payment_service.process_refund(
            'payment-123',
            Decimal('100.00'),
            'Customer requested refund'
        )
        
        # Assert
        assert result == 'refund-payment-123'
        
        # Verify original payment was updated
        mock_cursor.execute.assert_called()
        execute_call = mock_cursor.execute.call_args[0]
        assert "UPDATE payments" in execute_call[0]
        assert "refunded_amount = %s" in execute_call[0]
        assert "status = %s" in execute_call[0]
        
        # Verify refund transaction was created
        payment_service.create_payment.assert_called_once()
        create_call_kwargs = payment_service.create_payment.call_args[1]
        assert create_call_kwargs['transaction_type'] == 'refund'
        assert create_call_kwargs['status'] == 'completed'
    
    def test_process_full_refund_status(self, payment_service, mock_storage):
        """Test that full refund sets status to 'refunded'"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        original_payment = Payment(
            id='payment-123', booking_id=None, user_id=123,
            payment_method_id=None, transaction_id='TXN_123',
            provider_transaction_id=None, amount=Decimal('100.00'),
            currency='USD', status='completed', transaction_type='payment',
            description=None, refunded_amount=Decimal('0.00'),
            refund_reason=None, created_at=datetime.now(), updated_at=datetime.now(),
            completed_at=datetime.now()
        )
        payment_service.get_payment = Mock(return_value=original_payment)
        payment_service.create_payment = Mock(return_value='refund-123')
        
        # Act
        payment_service.process_refund('payment-123', Decimal('100.00'), 'Full refund')
        
        # Assert - check that status is set to 'refunded' for full refund
        update_call = mock_cursor.execute.call_args[0]
        params = update_call[1]
        assert 'refunded' in params  # Should be 'refunded', not 'partially_refunded'
    
    def test_get_user_payments(self, payment_service, mock_storage):
        """Test getting user payments"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        payment_rows = [
            [
                'payment-1', 'booking-1', 123, 'method-1', 'TXN_001',
                'provider_001', Decimal('199.99'), 'USD', 'completed', 'payment',
                'Flight payment', Decimal('0.00'), None,
                datetime.now(), datetime.now(), datetime.now()
            ],
            [
                'payment-2', None, 123, 'method-2', 'TXN_002',
                None, Decimal('50.00'), 'USD', 'failed', 'payment',
                'Service fee', Decimal('0.00'), None,
                datetime.now(), datetime.now(), None
            ]
        ]
        mock_cursor.fetchall.return_value = payment_rows
        
        # Act
        result = payment_service.get_user_payments(123, limit=10)
        
        # Assert
        assert len(result) == 2
        assert result[0].status == 'completed'
        assert result[1].status == 'failed'
        
        # Verify query parameters
        execute_call = mock_cursor.execute.call_args[0]
        assert "WHERE user_id = %s" in execute_call[0]
        assert "ORDER BY created_at DESC" in execute_call[0]
        assert "LIMIT %s" in execute_call[0]
    
    def test_get_booking_payments(self, payment_service, mock_storage):
        """Test getting payments for a booking"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        payment_rows = [
            [
                'payment-1', 'booking-123', 456, 'method-1', 'TXN_BOOKING_001',
                'stripe_pi_001', Decimal('299.99'), 'USD', 'completed', 'payment',
                'Initial payment', Decimal('0.00'), None,
                datetime.now(), datetime.now(), datetime.now()
            ]
        ]
        mock_cursor.fetchall.return_value = payment_rows
        
        # Act
        result = payment_service.get_booking_payments('booking-123')
        
        # Assert
        assert len(result) == 1
        assert result[0].booking_id == 'booking-123'
        
        # Verify chronological ordering for booking payments
        execute_call = mock_cursor.execute.call_args[0]
        assert "ORDER BY created_at ASC" in execute_call[0]
    
    def test_get_payment_statistics_success(self, payment_service, mock_storage):
        """Test getting payment statistics"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        stats_row = [100, 80, 10, 5, Decimal('15000.00'), Decimal('500.00'), Decimal('187.50')]
        mock_cursor.fetchone.return_value = stats_row
        
        # Act
        result = payment_service.get_payment_statistics()
        
        # Assert
        assert result['total_payments'] == 100
        assert result['completed_payments'] == 80
        assert result['failed_payments'] == 10
        assert result['refunded_payments'] == 5
        assert result['success_rate'] == 80.0  # 80/100 * 100
        assert result['total_completed_amount'] == 15000.0
        assert result['total_refunded_amount'] == 500.0
        assert result['avg_payment_amount'] == 187.5
    
    def test_get_payment_statistics_for_user(self, payment_service, mock_storage):
        """Test getting payment statistics for specific user"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        stats_row = [5, 4, 1, 0, Decimal('800.00'), Decimal('0.00'), Decimal('200.00')]
        mock_cursor.fetchone.return_value = stats_row
        
        # Act
        result = payment_service.get_payment_statistics(user_id=123)
        
        # Assert
        assert result['total_payments'] == 5
        assert result['success_rate'] == 80.0
        
        # Verify user filter in query
        execute_call = mock_cursor.execute.call_args[0]
        assert "WHERE user_id = %s" in execute_call[0]
    
    def test_deactivate_payment_method(self, payment_service, mock_storage):
        """Test deactivating payment method"""
        # Arrange
        payment_service.update_payment_method = Mock(return_value=True)
        
        # Act
        result = payment_service.deactivate_payment_method('method-123')
        
        # Assert
        assert result is True
        payment_service.update_payment_method.assert_called_once_with(
            'method-123', is_active=False
        )
    
    def test_exception_handling(self, payment_service, mock_storage):
        """Test exception handling in various methods"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Database error")
        
        # Act & Assert
        assert payment_service.add_payment_method(123, 'card', 'stripe') is None
        assert payment_service.get_payment_method('method-123') is None
        assert payment_service.get_user_payment_methods(123) == []
        assert payment_service.update_payment_method('method-123', is_active=False) is False
        assert payment_service.create_payment(123, Decimal('100.00')) is None
        assert payment_service.get_payment('payment-123') is None
        assert payment_service.get_payment_by_transaction_id('TXN_123') is None
        assert payment_service.update_payment_status('payment-123', 'completed') is False
        assert payment_service.process_refund('payment-123', Decimal('50.00'), 'test') is None
        assert payment_service.get_user_payments(123) == []
        assert payment_service.get_booking_payments('booking-123') == []
        assert payment_service.get_payment_statistics() == {}
    
    def test_no_connection_handling(self, payment_service):
        """Test handling when no database connection"""
        # Arrange
        payment_service.storage.conn = None
        
        # Act & Assert
        assert payment_service.add_payment_method(123, 'card', 'stripe') is None
        assert payment_service.get_payment_method('method-123') is None
        assert payment_service.get_user_payment_methods(123) == []
        assert payment_service.update_payment_method('method-123') is False
        assert payment_service.create_payment(123, Decimal('100.00')) is None
        assert payment_service.get_payment('payment-123') is None
        assert payment_service.get_payment_by_transaction_id('TXN_123') is None
        assert payment_service.update_payment_status('payment-123', 'completed') is False
        assert payment_service.process_refund('payment-123', Decimal('50.00'), 'test') is None
        assert payment_service.get_user_payments(123) == []
        assert payment_service.get_booking_payments('booking-123') == []
        assert payment_service.get_payment_statistics() == {}
    
    def test_transaction_id_generation_format(self, payment_service):
        """Test transaction ID generation format"""
        # Act
        transaction_id = payment_service._generate_transaction_id()
        
        # Assert
        assert transaction_id.startswith('TXN_')
        assert len(transaction_id) == 20  # TXN_ + 16 hex characters
        assert transaction_id[4:].isupper()  # Hex part should be uppercase
    
    def test_zero_division_in_statistics(self, payment_service, mock_storage):
        """Test statistics calculation with zero payments"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        stats_row = [0, 0, 0, 0, None, None, None]  # No payments
        mock_cursor.fetchone.return_value = stats_row
        
        # Act
        result = payment_service.get_payment_statistics()
        
        # Assert
        assert result['success_rate'] == 0  # Should handle division by zero
        assert result['total_completed_amount'] == 0
        assert result['avg_payment_amount'] == 0
    
    def test_partial_refund_status(self, payment_service, mock_storage):
        """Test that partial refund sets correct status"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        original_payment = Payment(
            id='payment-123', booking_id=None, user_id=123,
            payment_method_id=None, transaction_id='TXN_123',
            provider_transaction_id=None, amount=Decimal('200.00'),
            currency='USD', status='completed', transaction_type='payment',
            description=None, refunded_amount=Decimal('0.00'),
            refund_reason=None, created_at=datetime.now(), updated_at=datetime.now(),
            completed_at=datetime.now()
        )
        payment_service.get_payment = Mock(return_value=original_payment)
        payment_service.create_payment = Mock(return_value='refund-123')
        
        # Act
        payment_service.process_refund('payment-123', Decimal('50.00'), 'Partial refund')
        
        # Assert - check that status is set to 'partially_refunded'
        update_call = mock_cursor.execute.call_args[0]
        params = update_call[1]
        assert 'partially_refunded' in params  # Should be partial, not full refund
    
    def test_get_user_payment_methods_include_inactive(self, payment_service, mock_storage):
        """Test getting user payment methods including inactive ones"""
        # Arrange
        mock_cursor = MagicMock()
        mock_storage.conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        
        # Act
        payment_service.get_user_payment_methods(123, active_only=False)
        
        # Assert
        execute_call = mock_cursor.execute.call_args[0]
        assert "AND is_active = TRUE" not in execute_call[0]