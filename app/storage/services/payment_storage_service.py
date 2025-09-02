# ==============================================================================
# app/storage/services/payment_storage_service.py
# ==============================================================================
from typing import Dict, Any, List, Optional
import json
import secrets
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from app.storage.db_service import StorageService

@dataclass
class PaymentMethod:
    id: str
    user_id: int
    method_type: str
    provider: str
    is_virtual: bool
    is_primary: bool
    is_active: bool
    card_brand: Optional[str]
    card_last_four: Optional[str]
    card_holder_name: Optional[str]
    card_expiry_month: Optional[int]
    card_expiry_year: Optional[int]
    card_country: Optional[str]
    virtual_card_number: Optional[str]
    virtual_cvv: Optional[str]
    virtual_balance: Optional[Decimal]
    virtual_daily_limit: Optional[Decimal]
    mobile_number: Optional[str]
    mobile_provider: Optional[str]
    mobile_account_name: Optional[str]
    bank_name: Optional[str]
    bank_account_last_four: Optional[str]
    stripe_customer_id: Optional[str]
    stripe_payment_method_id: Optional[str]
    created_at: datetime
    updated_at: datetime

@dataclass
class Payment:
    id: str
    booking_id: Optional[str]
    user_id: int
    payment_method_id: Optional[str]
    transaction_id: str
    provider_transaction_id: Optional[str]
    amount: Decimal
    currency: str
    status: str
    transaction_type: str
    description: Optional[str]
    refunded_amount: Decimal
    refund_reason: Optional[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]

class PaymentStorageService:
    """
    Service for managing payment methods and transactions
    
    Responsibilities:
    - Manage user payment methods (virtual and real)
    - Process payments and track transaction lifecycle
    - Handle refunds and partial refunds
    - Support multiple payment providers (Stripe, M-Pesa, etc.)
    - Maintain financial audit trail
    """
    
    def __init__(self, storage: StorageService):
        self.storage = storage
    
    def add_payment_method(self, user_id: int, method_type: str, 
                          provider: str, **method_data) -> Optional[str]:
        """Add a payment method for a user"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                # Build insert data
                insert_data = {
                    'user_id': user_id,
                    'method_type': method_type,
                    'provider': provider,
                    'is_virtual': method_data.get('is_virtual', False),
                    'is_primary': method_data.get('is_primary', False),
                    'is_active': method_data.get('is_active', True)
                }
                
                # Add card-specific fields
                card_fields = [
                    'card_brand', 'card_last_four', 'card_holder_name',
                    'card_expiry_month', 'card_expiry_year', 'card_country'
                ]
                for field in card_fields:
                    if field in method_data:
                        insert_data[field] = method_data[field]
                
                # Add virtual card fields
                virtual_fields = [
                    'virtual_card_number', 'virtual_cvv', 'virtual_balance', 
                    'virtual_daily_limit'
                ]
                for field in virtual_fields:
                    if field in method_data:
                        insert_data[field] = method_data[field]
                
                # Add mobile money fields
                mobile_fields = ['mobile_number', 'mobile_provider', 'mobile_account_name']
                for field in mobile_fields:
                    if field in method_data:
                        insert_data[field] = method_data[field]
                
                # Add bank fields
                bank_fields = ['bank_name', 'bank_account_last_four']
                for field in bank_fields:
                    if field in method_data:
                        insert_data[field] = method_data[field]
                
                # Add external provider fields
                provider_fields = ['stripe_customer_id', 'stripe_payment_method_id']
                for field in provider_fields:
                    if field in method_data:
                        insert_data[field] = method_data[field]
                
                # If this is set as primary, unset other primary methods
                if insert_data.get('is_primary'):
                    cur.execute("""
                        UPDATE payment_methods 
                        SET is_primary = FALSE, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s AND is_primary = TRUE;
                    """, (user_id,))
                
                # Build query
                fields = list(insert_data.keys())
                placeholders = ', '.join(['%s'] * len(fields))
                field_names = ', '.join(fields)
                
                cur.execute(f"""
                    INSERT INTO payment_methods ({field_names})
                    VALUES ({placeholders})
                    RETURNING id;
                """, list(insert_data.values()))
                
                return cur.fetchone()[0] # type: ignore
                
        except Exception as e:
            print(f"Error adding payment method: {e}")
            return None
    
    def get_payment_method(self, method_id: str) -> Optional[PaymentMethod]:
        """Get payment method by ID"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, user_id, method_type, provider, is_virtual, is_primary,
                           is_active, card_brand, card_last_four, card_holder_name,
                           card_expiry_month, card_expiry_year, card_country,
                           virtual_card_number, virtual_cvv, virtual_balance,
                           virtual_daily_limit, mobile_number, mobile_provider,
                           mobile_account_name, bank_name, bank_account_last_four,
                           stripe_customer_id, stripe_payment_method_id,
                           created_at, updated_at
                    FROM payment_methods WHERE id = %s;
                """, (method_id,))
                
                row = cur.fetchone()
                if row:
                    return PaymentMethod(
                        id=row[0], user_id=row[1], method_type=row[2], provider=row[3],
                        is_virtual=row[4], is_primary=row[5], is_active=row[6],
                        card_brand=row[7], card_last_four=row[8], card_holder_name=row[9],
                        card_expiry_month=row[10], card_expiry_year=row[11], card_country=row[12],
                        virtual_card_number=row[13], virtual_cvv=row[14], virtual_balance=row[15],
                        virtual_daily_limit=row[16], mobile_number=row[17], mobile_provider=row[18],
                        mobile_account_name=row[19], bank_name=row[20], bank_account_last_four=row[21],
                        stripe_customer_id=row[22], stripe_payment_method_id=row[23],
                        created_at=row[24], updated_at=row[25]
                    )
                return None
                
        except Exception as e:
            print(f"Error getting payment method: {e}")
            return None
    
    def get_user_payment_methods(self, user_id: int, active_only: bool = True) -> List[PaymentMethod]:
        """Get payment methods for a user"""
        if not self.storage.conn:
            return []
        
        try:
            with self.storage.conn.cursor() as cur:
                query = """
                    SELECT id, user_id, method_type, provider, is_virtual, is_primary,
                           is_active, card_brand, card_last_four, card_holder_name,
                           card_expiry_month, card_expiry_year, card_country,
                           virtual_card_number, virtual_cvv, virtual_balance,
                           virtual_daily_limit, mobile_number, mobile_provider,
                           mobile_account_name, bank_name, bank_account_last_four,
                           stripe_customer_id, stripe_payment_method_id,
                           created_at, updated_at
                    FROM payment_methods WHERE user_id = %s
                """
                
                params = [user_id]
                if active_only:
                    query += " AND is_active = TRUE"
                
                query += " ORDER BY is_primary DESC, created_at DESC;"
                
                cur.execute(query, params)
                
                return [
                    PaymentMethod(
                        id=row[0], user_id=row[1], method_type=row[2], provider=row[3],
                        is_virtual=row[4], is_primary=row[5], is_active=row[6],
                        card_brand=row[7], card_last_four=row[8], card_holder_name=row[9],
                        card_expiry_month=row[10], card_expiry_year=row[11], card_country=row[12],
                        virtual_card_number=row[13], virtual_cvv=row[14], virtual_balance=row[15],
                        virtual_daily_limit=row[16], mobile_number=row[17], mobile_provider=row[18],
                        mobile_account_name=row[19], bank_name=row[20], bank_account_last_four=row[21],
                        stripe_customer_id=row[22], stripe_payment_method_id=row[23],
                        created_at=row[24], updated_at=row[25]
                    )
                    for row in cur.fetchall()
                ]
                
        except Exception as e:
            print(f"Error getting user payment methods: {e}")
            return []
    
    def update_payment_method(self, method_id: str, **update_data) -> bool:
        """Update payment method details"""
        if not self.storage.conn:
            return False
        
        try:
            with self.storage.conn.cursor() as cur:
                # Build update fields dynamically
                update_fields = []
                update_values = []
                
                valid_fields = {
                    'is_primary', 'is_active', 'card_brand', 'card_last_four',
                    'card_holder_name', 'card_expiry_month', 'card_expiry_year',
                    'virtual_balance', 'virtual_daily_limit', 'stripe_customer_id',
                    'stripe_payment_method_id'
                }
                
                for key, value in update_data.items():
                    if key in valid_fields:
                        update_fields.append(f"{key} = %s")
                        update_values.append(value)
                
                if not update_fields:
                    return True
                
                # If setting as primary, unset other primary methods for this user
                if update_data.get('is_primary'):
                    # Get user_id first
                    cur.execute("SELECT user_id FROM payment_methods WHERE id = %s;", (method_id,))
                    user_id = cur.fetchone()[0] # type: ignore
                    
                    cur.execute("""
                        UPDATE payment_methods 
                        SET is_primary = FALSE, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s AND is_primary = TRUE AND id != %s;
                    """, (user_id, method_id))
                
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                
                update_query = f"""
                    UPDATE payment_methods 
                    SET {', '.join(update_fields)}
                    WHERE id = %s;
                """
                
                cur.execute(update_query, update_values + [method_id])
                return cur.rowcount > 0
                
        except Exception as e:
            print(f"Error updating payment method: {e}")
            return False
    
    def deactivate_payment_method(self, method_id: str) -> bool:
        """Deactivate a payment method"""
        return self.update_payment_method(method_id, is_active=False)
    
    def create_payment(self, user_id: int, amount: Decimal, 
                      currency: str = 'USD', **payment_data) -> Optional[str]:
        """Create a new payment transaction"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                # Generate transaction ID if not provided
                transaction_id = payment_data.get('transaction_id', self._generate_transaction_id())
                
                insert_data = {
                    'user_id': user_id,
                    'amount': amount,
                    'currency': currency,
                    'transaction_id': transaction_id,
                    'status': payment_data.get('status', 'pending'),
                    'transaction_type': payment_data.get('transaction_type', 'payment'),
                    'refunded_amount': payment_data.get('refunded_amount', Decimal('0.00'))
                }
                
                # Add optional fields
                optional_fields = [
                    'booking_id', 'payment_method_id', 'provider_transaction_id',
                    'description', 'refund_reason', 'completed_at'
                ]
                for field in optional_fields:
                    if field in payment_data:
                        insert_data[field] = payment_data[field]
                
                # Build query
                fields = list(insert_data.keys())
                placeholders = ', '.join(['%s'] * len(fields))
                field_names = ', '.join(fields)
                
                cur.execute(f"""
                    INSERT INTO payments ({field_names})
                    VALUES ({placeholders})
                    RETURNING id;
                """, list(insert_data.values()))
                
                return cur.fetchone()[0] # type: ignore
                
        except Exception as e:
            print(f"Error creating payment: {e}")
            return None
    
    def get_payment(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, booking_id, user_id, payment_method_id, transaction_id,
                           provider_transaction_id, amount, currency, status,
                           transaction_type, description, refunded_amount, refund_reason,
                           created_at, updated_at, completed_at
                    FROM payments WHERE id = %s;
                """, (payment_id,))
                
                row = cur.fetchone()
                if row:
                    return Payment(
                        id=row[0], booking_id=row[1], user_id=row[2],
                        payment_method_id=row[3], transaction_id=row[4],
                        provider_transaction_id=row[5], amount=row[6], currency=row[7],
                        status=row[8], transaction_type=row[9], description=row[10],
                        refunded_amount=row[11], refund_reason=row[12],
                        created_at=row[13], updated_at=row[14], completed_at=row[15]
                    )
                return None
                
        except Exception as e:
            print(f"Error getting payment: {e}")
            return None
    
    def get_payment_by_transaction_id(self, transaction_id: str) -> Optional[Payment]:
        """Get payment by transaction ID"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, booking_id, user_id, payment_method_id, transaction_id,
                           provider_transaction_id, amount, currency, status,
                           transaction_type, description, refunded_amount, refund_reason,
                           created_at, updated_at, completed_at
                    FROM payments WHERE transaction_id = %s;
                """, (transaction_id,))
                
                row = cur.fetchone()
                if row:
                    return Payment(
                        id=row[0], booking_id=row[1], user_id=row[2],
                        payment_method_id=row[3], transaction_id=row[4],
                        provider_transaction_id=row[5], amount=row[6], currency=row[7],
                        status=row[8], transaction_type=row[9], description=row[10],
                        refunded_amount=row[11], refund_reason=row[12],
                        created_at=row[13], updated_at=row[14], completed_at=row[15]
                    )
                return None
                
        except Exception as e:
            print(f"Error getting payment by transaction ID: {e}")
            return None
    
    def update_payment_status(self, payment_id: str, status: str, 
                            provider_transaction_id: Optional[str] = None) -> bool:
        """Update payment status"""
        if not self.storage.conn:
            return False
        
        try:
            with self.storage.conn.cursor() as cur:
                update_data = {'status': status}
                
                if provider_transaction_id:
                    update_data['provider_transaction_id'] = provider_transaction_id
                
                if status == 'completed':
                    update_data['completed_at'] = datetime.now() # type: ignore
                
                update_fields = []
                update_values = []
                
                for key, value in update_data.items():
                    update_fields.append(f"{key} = %s")
                    update_values.append(value)
                
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                
                update_query = f"""
                    UPDATE payments 
                    SET {', '.join(update_fields)}
                    WHERE id = %s;
                """
                
                cur.execute(update_query, update_values + [payment_id])
                return cur.rowcount > 0
                
        except Exception as e:
            print(f"Error updating payment status: {e}")
            return False
    
    def process_refund(self, payment_id: str, refund_amount: Decimal,
                      refund_reason: str) -> Optional[str]:
        """Process a refund for a payment"""
        if not self.storage.conn:
            return None
        
        try:
            with self.storage.conn.cursor() as cur:
                # Get original payment
                payment = self.get_payment(payment_id)
                if not payment:
                    return None
                
                # Calculate new refunded amount
                new_refunded_amount = payment.refunded_amount + refund_amount
                
                # Determine new status
                if new_refunded_amount >= payment.amount:
                    new_status = 'refunded'
                else:
                    new_status = 'partially_refunded'
                
                # Update original payment
                cur.execute("""
                    UPDATE payments 
                    SET refunded_amount = %s, status = %s, refund_reason = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                """, (new_refunded_amount, new_status, refund_reason, payment_id))
                
                # Create refund transaction
                refund_id = self.create_payment(
                    user_id=payment.user_id,
                    amount=refund_amount,
                    currency=payment.currency,
                    booking_id=payment.booking_id,
                    payment_method_id=payment.payment_method_id,
                    transaction_type='refund',
                    status='completed',
                    description=f'Refund for {payment.transaction_id}',
                    refund_reason=refund_reason,
                    completed_at=datetime.now()
                )
                
                return refund_id
                
        except Exception as e:
            print(f"Error processing refund: {e}")
            return None
    
    def get_user_payments(self, user_id: int, limit: int = 50) -> List[Payment]:
        """Get payments for a user"""
        if not self.storage.conn:
            return []
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, booking_id, user_id, payment_method_id, transaction_id,
                           provider_transaction_id, amount, currency, status,
                           transaction_type, description, refunded_amount, refund_reason,
                           created_at, updated_at, completed_at
                    FROM payments 
                    WHERE user_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s;
                """, (user_id, limit))
                
                return [
                    Payment(
                        id=row[0], booking_id=row[1], user_id=row[2],
                        payment_method_id=row[3], transaction_id=row[4],
                        provider_transaction_id=row[5], amount=row[6], currency=row[7],
                        status=row[8], transaction_type=row[9], description=row[10],
                        refunded_amount=row[11], refund_reason=row[12],
                        created_at=row[13], updated_at=row[14], completed_at=row[15]
                    )
                    for row in cur.fetchall()
                ]
                
        except Exception as e:
            print(f"Error getting user payments: {e}")
            return []
    
    def get_booking_payments(self, booking_id: str) -> List[Payment]:
        """Get all payments for a booking"""
        if not self.storage.conn:
            return []
        
        try:
            with self.storage.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, booking_id, user_id, payment_method_id, transaction_id,
                           provider_transaction_id, amount, currency, status,
                           transaction_type, description, refunded_amount, refund_reason,
                           created_at, updated_at, completed_at
                    FROM payments 
                    WHERE booking_id = %s 
                    ORDER BY created_at ASC;
                """, (booking_id,))
                
                return [
                    Payment(
                        id=row[0], booking_id=row[1], user_id=row[2],
                        payment_method_id=row[3], transaction_id=row[4],
                        provider_transaction_id=row[5], amount=row[6], currency=row[7],
                        status=row[8], transaction_type=row[9], description=row[10],
                        refunded_amount=row[11], refund_reason=row[12],
                        created_at=row[13], updated_at=row[14], completed_at=row[15]
                    )
                    for row in cur.fetchall()
                ]
                
        except Exception as e:
            print(f"Error getting booking payments: {e}")
            return []
    
    def get_payment_statistics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get payment statistics"""
        if not self.storage.conn:
            return {}
        
        try:
            with self.storage.conn.cursor() as cur:
                base_query = """
                    SELECT 
                        COUNT(*) as total_payments,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_payments,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_payments,
                        COUNT(CASE WHEN status IN ('refunded', 'partially_refunded') THEN 1 END) as refunded_payments,
                        SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) as total_completed_amount,
                        SUM(refunded_amount) as total_refunded_amount,
                        AVG(CASE WHEN status = 'completed' THEN amount END) as avg_payment_amount
                    FROM payments
                """
                
                if user_id:
                    cur.execute(base_query + " WHERE user_id = %s;", (user_id,))
                else:
                    cur.execute(base_query + ";")
                
                row = cur.fetchone()
                if row:
                    total_payments = row[0]
                    return {
                        'total_payments': total_payments,
                        'completed_payments': row[1],
                        'failed_payments': row[2],
                        'refunded_payments': row[3],
                        'success_rate': (row[1] / total_payments * 100) if total_payments > 0 else 0,
                        'total_completed_amount': float(row[4]) if row[4] else 0,
                        'total_refunded_amount': float(row[5]) if row[5] else 0,
                        'avg_payment_amount': float(row[6]) if row[6] else 0
                    }
                return {}
                
        except Exception as e:
            print(f"Error getting payment statistics: {e}")
            return {}
    
    def _generate_transaction_id(self) -> str:
        """Generate a unique transaction ID"""
        return f"TXN_{secrets.token_hex(8).upper()}"