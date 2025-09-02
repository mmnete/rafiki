# ==============================================================================
# app/database/schemas/conversation_schema.py - Conversation and message schema
# ==============================================================================
from typing import List
from .base_schema import BaseSchema

class ConversationSchema(BaseSchema):
    """
    Conversation history with 5-year TTL and rich context storage
    
    Design considerations:
    - 5-year message retention for regulatory compliance
    - Rich context linking conversations to bookings/searches
    - AI performance tracking and optimization data
    - User feedback and satisfaction tracking
    - Conversation threading for complex multi-turn interactions
    """
    
    def get_table_definitions(self) -> List[str]:
        return [
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                
                -- Message Content
                user_message TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                user_message_hash VARCHAR(64),
                response_truncated BOOLEAN DEFAULT FALSE,
                
                -- Message Classification
                message_type VARCHAR(30) DEFAULT 'chat',
                intent_classification VARCHAR(50),
                sentiment_score DECIMAL(3,2),
                language_detected VARCHAR(10),
                
                -- Media and Attachments
                has_media BOOLEAN DEFAULT FALSE,
                media_file_ids JSONB DEFAULT '[]',
                media_descriptions JSONB DEFAULT '[]',
                
                -- AI Processing Context
                tools_used JSONB DEFAULT '[]',
                tool_execution_results JSONB DEFAULT '{}',
                processing_time_ms INT,
                model_used VARCHAR(50),
                model_version VARCHAR(20),
                prompt_tokens INT,
                response_tokens INT,
                total_cost_usd DECIMAL(8,4) DEFAULT 0.0000,
                
                -- Conversation Threading
                conversation_thread_id UUID,
                message_sequence INT DEFAULT 1,
                parent_message_id UUID REFERENCES conversations(id),
                is_thread_starter BOOLEAN DEFAULT FALSE,
                thread_context_summary TEXT,
                
                -- Business Context and Journey
                related_booking_id UUID REFERENCES bookings(id),
                related_search_id UUID REFERENCES flight_searches(id),
                booking_stage VARCHAR(50),
                user_journey_stage VARCHAR(50),
                conversion_event VARCHAR(50),
                
                -- Quality and Performance Metrics
                user_satisfaction_rating INT CHECK (user_satisfaction_rating BETWEEN 1 AND 5),
                response_quality_score DECIMAL(3,2),
                task_completion_status VARCHAR(30),
                user_effort_score INT CHECK (user_effort_score BETWEEN 1 AND 10),
                
                -- User Feedback and Interaction
                feedback_provided TEXT,
                was_helpful BOOLEAN,
                thumbs_up_down VARCHAR(10),
                follow_up_needed BOOLEAN DEFAULT FALSE,
                escalated_to_human BOOLEAN DEFAULT FALSE,
                
                -- Error and Issue Tracking
                had_errors BOOLEAN DEFAULT FALSE,
                error_details JSONB DEFAULT '[]',
                retry_attempts INT DEFAULT 0,
                
                -- Channel and Context
                message_channel VARCHAR(20) DEFAULT 'sms',
                device_type VARCHAR(20),
                user_location_context VARCHAR(100),
                session_id UUID,
                
                -- Metadata with TTL Management
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '5 years'),
                archived_at TIMESTAMP,
                last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INT DEFAULT 0,
                
                -- Constraints
                CONSTRAINT valid_message_type CHECK (message_type IN (
                    'chat', 'onboarding', 'search_request', 'booking_request', 'payment_request', 
                    'support_request', 'cancellation_request', 'system_message', 'follow_up',
                    'clarification', 'confirmation', 'error_recovery'
                )),
                CONSTRAINT valid_channel CHECK (message_channel IN (
                    'sms', 'whatsapp', 'web_chat', 'mobile_app', 'api', 'webhook'
                )),
                CONSTRAINT valid_task_completion CHECK (task_completion_status IN (
                    'completed', 'partially_completed', 'failed', 'abandoned', 'redirected', 'ongoing'
                )),
                CONSTRAINT valid_thumbs CHECK (thumbs_up_down IS NULL OR thumbs_up_down IN ('up', 'down'))
            );
            """,
            
            """
            CREATE TABLE IF NOT EXISTS conversation_summaries (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                
                -- Summary Period
                summary_period_start TIMESTAMP NOT NULL,
                summary_period_end TIMESTAMP NOT NULL,
                message_count INT NOT NULL,
                total_characters INT,
                
                -- AI-Generated Summary
                summary_text TEXT NOT NULL,
                key_topics JSONB DEFAULT '[]',
                action_items JSONB DEFAULT '[]',
                unresolved_issues JSONB DEFAULT '[]',
                important_decisions JSONB DEFAULT '[]',
                
                -- Context Preservation
                mentioned_bookings JSONB DEFAULT '[]',
                mentioned_passengers JSONB DEFAULT '[]',
                preference_changes JSONB DEFAULT '[]',
                
                -- Summary Quality
                summary_confidence_score DECIMAL(3,2) DEFAULT 0.00,
                human_reviewed BOOLEAN DEFAULT FALSE,
                human_reviewer_notes TEXT,
                
                -- Metadata
                summary_generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                summary_model_used VARCHAR(50),
                summary_model_version VARCHAR(20),
                expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '7 years'),
                
                -- Constraints
                UNIQUE(user_id, summary_period_start, summary_period_end)
            );
            """,
            
            """
            CREATE TABLE IF NOT EXISTS message_media (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                
                -- Media Details
                media_type VARCHAR(50) NOT NULL,
                original_url TEXT,
                stored_file_id UUID REFERENCES stored_files(id),
                
                -- Content Analysis
                ai_description TEXT,
                extracted_text TEXT,
                contains_document_info BOOLEAN DEFAULT FALSE,
                document_data_extracted JSONB DEFAULT '{}',
                
                -- Processing Status
                processing_status VARCHAR(30) DEFAULT 'pending',
                processing_error TEXT,
                
                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                
                -- Constraints
                CONSTRAINT valid_media_type CHECK (media_type IN (
                    'image', 'document', 'audio', 'video', 'pdf', 'id_document', 'receipt'
                )),
                CONSTRAINT valid_processing_status CHECK (processing_status IN (
                    'pending', 'processing', 'completed', 'failed', 'skipped'
                ))
            );
            """,
            
            """
            CREATE TABLE IF NOT EXISTS conversation_context (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                
                -- Context Type and Data
                context_type VARCHAR(50) NOT NULL,
                context_data JSONB NOT NULL DEFAULT '{}',
                
                -- Context Relevance
                relevance_score DECIMAL(3,2) DEFAULT 1.00,
                is_active BOOLEAN DEFAULT TRUE,
                
                -- Context Lifecycle
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                
                -- Constraints
                CONSTRAINT valid_context_type CHECK (context_type IN (
                    'booking_in_progress', 'search_preferences', 'passenger_collection', 
                    'payment_processing', 'error_recovery', 'onboarding_state', 
                    'user_preferences', 'flight_selection', 'seat_selection'
                ))
            );
            """,
            
            """
            CREATE TABLE IF NOT EXISTS conversation_analytics (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                
                -- Time Period
                analytics_date DATE NOT NULL,
                user_id INT REFERENCES users(id) ON DELETE CASCADE,
                
                -- Conversation Metrics
                total_conversations INT DEFAULT 0,
                total_messages INT DEFAULT 0,
                average_response_time_ms INT,
                total_tokens_used INT DEFAULT 0,
                total_cost_usd DECIMAL(8,4) DEFAULT 0.0000,
                
                -- User Behavior Metrics
                sessions_started INT DEFAULT 0,
                sessions_completed INT DEFAULT 0,
                sessions_abandoned INT DEFAULT 0,
                average_session_length_minutes DECIMAL(6,2),
                
                -- Business Metrics
                searches_performed INT DEFAULT 0,
                bookings_started INT DEFAULT 0,
                bookings_completed INT DEFAULT 0,
                conversion_rate DECIMAL(5,4) DEFAULT 0.0000,
                
                -- AI Performance Metrics
                tool_calls_made INT DEFAULT 0,
                tool_success_rate DECIMAL(5,4) DEFAULT 0.0000,
                error_rate DECIMAL(5,4) DEFAULT 0.0000,
                average_satisfaction_score DECIMAL(3,2),
                
                -- Content Analysis
                top_intents JSONB DEFAULT '[]',
                common_topics JSONB DEFAULT '[]',
                frequent_errors JSONB DEFAULT '[]',
                
                -- Metadata
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Constraints
                UNIQUE(analytics_date, user_id)
            );
            """
        ]
    
    def get_indexes(self) -> List[str]:
        return [
            # Core conversation indexes
            "CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_conversations_created ON conversations(created_at DESC);",
            "CREATE INDEX IF NOT EXISTS idx_conversations_expires ON conversations(expires_at);",
            "CREATE INDEX IF NOT EXISTS idx_conversations_thread ON conversations(conversation_thread_id);",
            "CREATE INDEX IF NOT EXISTS idx_conversations_sequence ON conversations(conversation_thread_id, message_sequence);",
            "CREATE INDEX IF NOT EXISTS idx_conversations_parent ON conversations(parent_message_id);",
            
            # Business context indexes
            "CREATE INDEX IF NOT EXISTS idx_conversations_booking ON conversations(related_booking_id);",
            "CREATE INDEX IF NOT EXISTS idx_conversations_search ON conversations(related_search_id);",
            "CREATE INDEX IF NOT EXISTS idx_conversations_stage ON conversations(booking_stage);",
            "CREATE INDEX IF NOT EXISTS idx_conversations_journey ON conversations(user_journey_stage);",
            
            # Message classification indexes
            "CREATE INDEX IF NOT EXISTS idx_conversations_type ON conversations(message_type);",
            "CREATE INDEX IF NOT EXISTS idx_conversations_intent ON conversations(intent_classification);",
            "CREATE INDEX IF NOT EXISTS idx_conversations_channel ON conversations(message_channel);",
            "CREATE INDEX IF NOT EXISTS idx_conversations_has_media ON conversations(has_media);",
            
            # Quality and feedback indexes
            "CREATE INDEX IF NOT EXISTS idx_conversations_satisfaction ON conversations(user_satisfaction_rating);",
            "CREATE INDEX IF NOT EXISTS idx_conversations_helpful ON conversations(was_helpful);",
            "CREATE INDEX IF NOT EXISTS idx_conversations_thumbs ON conversations(thumbs_up_down);",
            "CREATE INDEX IF NOT EXISTS idx_conversations_errors ON conversations(had_errors);",
            
            # AI performance indexes
            "CREATE INDEX IF NOT EXISTS idx_conversations_model ON conversations(model_used);",
            "CREATE INDEX IF NOT EXISTS idx_conversations_processing_time ON conversations(processing_time_ms);",
            "CREATE INDEX IF NOT EXISTS idx_conversations_cost ON conversations(total_cost_usd);",
            
            # Summary indexes
            "CREATE INDEX IF NOT EXISTS idx_conversation_summaries_user ON conversation_summaries(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_summaries_period ON conversation_summaries(summary_period_start, summary_period_end);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_summaries_generated ON conversation_summaries(summary_generated_at);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_summaries_expires ON conversation_summaries(expires_at);",
            
            # Media indexes
            "CREATE INDEX IF NOT EXISTS idx_message_media_conversation ON message_media(conversation_id);",
            "CREATE INDEX IF NOT EXISTS idx_message_media_type ON message_media(media_type);",
            "CREATE INDEX IF NOT EXISTS idx_message_media_status ON message_media(processing_status);",
            "CREATE INDEX IF NOT EXISTS idx_message_media_file ON message_media(stored_file_id);",
            
            # Context indexes
            "CREATE INDEX IF NOT EXISTS idx_conversation_context_conversation ON conversation_context(conversation_id);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_context_type ON conversation_context(context_type);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_context_active ON conversation_context(is_active);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_context_expires ON conversation_context(expires_at);",
            
            # Analytics indexes
            "CREATE INDEX IF NOT EXISTS idx_conversation_analytics_date ON conversation_analytics(analytics_date);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_analytics_user ON conversation_analytics(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_analytics_calculated ON conversation_analytics(calculated_at);",
        ]
    
    def get_migrations(self) -> List[str]:
        """Future migrations for conversation schema"""
        return [
            # Example migration for adding new columns
            """
            ALTER TABLE conversations 
            ADD COLUMN IF NOT EXISTS conversation_mood VARCHAR(20);
            """,
            
            """
            ALTER TABLE conversations 
            ADD COLUMN IF NOT EXISTS ai_confidence_score DECIMAL(3,2) DEFAULT 0.00;
            """,
            
            # Example migration for new constraints
            """
            ALTER TABLE conversations 
            ADD CONSTRAINT valid_mood CHECK (conversation_mood IS NULL OR conversation_mood IN (
                'positive', 'neutral', 'negative', 'frustrated', 'excited', 'confused'
            ));
            """
        ]
