from typing import List
from .base_schema import BaseSchema

class PaymentSchema(BaseSchema):
    """
    Comprehensive payment system supporting virtual testing and real Stripe payments
    
    Design considerations:
    - Supports both virtual (testing) and real payment methods
    - Tracks complete transaction lifecycle
    - Handles refunds, partial refunds, and adjustments
    - Maintains audit trail for financial reconciliation
    - Supports multiple currencies and payment providers
    """
    
    def __init__(self):
        super().__init__()
        self.table_name = "payments"
    
    def get_table_definitions(self) -> List[str]:
        return [
            """
            CREATE TABLE IF NOT EXISTS payment_methods (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                
                -- Payment Method Classification
                method_type VARCHAR(30) NOT NULL,
                provider VARCHAR(50) NOT NULL,
                is_virtual BOOLEAN DEFAULT FALSE,
                is_primary BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                
                -- Card Information (for virtual and real cards)
                card_brand VARCHAR(20),
                card_last_four VARCHAR(4),
                card_holder_name VARCHAR(255),
                card_expiry_month INT,
                card_expiry_year INT,
                card_country VARCHAR(3),
                
                -- Virtual Card Details (for testing)
                virtual_card_number VARCHAR(20),
                virtual_cvv VARCHAR(4),
                virtual_balance DECIMAL(12,2) DEFAULT 1000000.00,
                virtual_daily_limit DECIMAL(10,2) DEFAULT 50000.00,
                
                -- Mobile Money (M-Pesa, etc.)
                mobile_number VARCHAR(20),
                mobile_provider VARCHAR(50),
                mobile_account_name VARCHAR(255),
                
                -- Bank Account Details
                bank_name VARCHAR(100),
                bank_account_last_four VARCHAR(4),
                
                -- External Identifiers
                stripe_customer_id VARCHAR(255),
                stripe_payment_method_id VARCHAR(255),
                
                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Constraints
                CONSTRAINT valid_method_type CHECK (method_type IN ('card', 'mobile_money', 'bank_transfer', 'virtual'))
            );
            """,
            
            """
            CREATE TABLE IF NOT EXISTS payments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                booking_id UUID REFERENCES bookings(id) ON DELETE SET NULL,
                user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                payment_method_id UUID REFERENCES payment_methods(id),
                
                -- Transaction Details
                transaction_id VARCHAR(255) UNIQUE NOT NULL,
                provider_transaction_id VARCHAR(255),
                amount DECIMAL(10,2) NOT NULL,
                currency VARCHAR(3) DEFAULT 'USD',
                status VARCHAR(30) NOT NULL DEFAULT 'pending',
                
                -- Transaction Context
                transaction_type VARCHAR(20) NOT NULL DEFAULT 'payment',
                description TEXT,
                
                -- Refund and Adjustments
                refunded_amount DECIMAL(10,2) DEFAULT 0.00,
                refund_reason TEXT,
                
                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                
                -- Constraints
                CONSTRAINT valid_payment_status CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'refunded', 'partially_refunded', 'authorized', 'captured')),
                CONSTRAINT valid_transaction_type CHECK (transaction_type IN ('payment', 'refund', 'chargeback', 'adjustment'))
            );
            """
        ]
    
    def get_indexes(self) -> List[str]:
        return [
            "CREATE INDEX IF NOT EXISTS idx_payment_methods_user ON payment_methods(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_payment_methods_active ON payment_methods(is_active);",
            "CREATE INDEX IF NOT EXISTS idx_payments_booking ON payments(booking_id);",
            "CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_payments_transaction ON payments(transaction_id);",
            "CREATE INDEX IF NOT EXISTS idx_payments_provider_id ON payments(provider_transaction_id);",
            "CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);",
        ]
