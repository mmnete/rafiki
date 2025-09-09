# app/storage/schema_manager.py
from typing import List, Dict, Set
import psycopg2
from app.storage.db_service import StorageService

# Import all your schema classes
from app.storage.schemas.user_schema import UserSchema
from app.storage.schemas.booking_schema import BookingSchema
from app.storage.schemas.conversation_schema import ConversationSchema
from app.storage.schemas.document_schema import DocumentSchema
from app.storage.schemas.flight_schema import FlightSchema
from app.storage.schemas.passenger_schema import PassengerSchema
from app.storage.schemas.payment_schema import PaymentSchema
from app.storage.schemas.personalization_schema import PersonalizationSchema

class SchemaManager:
    """
    Manages database schema creation and migrations with proper dependency ordering
    """
    
    def __init__(self, storage: StorageService):
        self.storage = storage
        
        # Define schemas with their dependencies (what they reference)
        # IMPORTANT: PassengerSchema should NOT contain booking_passengers table anymore
        # booking_passengers is now in BookingSchema to fix dependency issues
        self.schema_dependencies = {
            'users': UserSchema(),                    # Base user authentication tables
            'passenger_profiles': PassengerSchema(),  # Contains passenger_profiles, user_sessions, user_frequent_passengers (NOT booking_passengers)
            'flight_searches': FlightSchema(),        # References users 
            'bookings': BookingSchema(),              # References users, passenger_profiles, contains booking_passengers
            'stored_files': DocumentSchema(),         # References users, bookings, passenger_profiles
            'conversations': ConversationSchema(),    # References users, bookings, flight_searches, stored_files
            'payments': PaymentSchema(),              # References users, bookings
            'personalization': PersonalizationSchema() # References users, passenger_profiles
        }
        
        # Define the dependency graph (schema -> list of schemas it depends on)
        self.dependencies = {
            'users': [],                              # Base tables, no dependencies
            'passenger_profiles': ['users'],          # References users
            'flight_searches': ['users'],             # References users
            'bookings': ['users', 'passenger_profiles'], # References users, passenger_profiles, AND contains booking_passengers
            'stored_files': ['users', 'bookings', 'passenger_profiles'], # References users, bookings, passenger_profiles
            'conversations': ['users', 'bookings', 'flight_searches', 'stored_files'],
            'payments': ['users', 'bookings'],        # References users, bookings
            'personalization': ['users', 'passenger_profiles'] # References users, passenger_profiles
        }
    
    def _get_creation_order(self) -> List[str]:
        """
        Calculate the correct order for table creation using topological sort
        """
        # Topological sort to handle dependencies
        visited = set()
        temp_visited = set()
        result = []
        
        def visit(schema_name):
            if schema_name in temp_visited:
                raise ValueError(f"Circular dependency detected involving {schema_name}")
            if schema_name in visited:
                return
            
            temp_visited.add(schema_name)
            
            # Visit all dependencies first
            for dependency in self.dependencies.get(schema_name, []):
                visit(dependency)
            
            temp_visited.remove(schema_name)
            visited.add(schema_name)
            result.append(schema_name)
        
        # Visit all schemas
        for schema_name in self.dependencies.keys():
            visit(schema_name)
        
        return result
    
    def create_all_tables(self) -> bool:
        """
        Create all tables and indexes in the correct dependency order
        """
        if not self.storage.conn:
            print("❌ No database connection available")
            return False
        
        try:
            creation_order = self._get_creation_order()
            print(f"📋 Creating schemas in dependency order: {' -> '.join(creation_order)}")
            
            with self.storage.conn.cursor() as cur:
                # First pass: Create tables in dependency order
                for schema_name in creation_order:
                    schema = self.schema_dependencies[schema_name]
                    print(f"📋 Creating tables for {schema.__class__.__name__}...")
                    
                    # Create tables
                    for table_sql in schema.get_table_definitions():
                        try:
                            cur.execute(table_sql)
                            # Extract table name from SQL for better logging
                            if "CREATE TABLE IF NOT EXISTS" in table_sql:
                                actual_table = table_sql.split("CREATE TABLE IF NOT EXISTS")[1].split("(")[0].strip()
                                print(f"  ✅ Created table: {actual_table}")
                        except Exception as e:
                            print(f"  ❌ Error creating table in {schema.__class__.__name__}: {e}")
                            print(f"  SQL: {table_sql[:200]}...")  # Print first 200 chars for debugging
                            return False
                
                # Commit after all tables are created
                self.storage.conn.commit()
                
                # Second pass: Create indexes (after all tables exist)
                print("\n📊 Creating indexes...")
                for schema_name in creation_order:
                    schema = self.schema_dependencies[schema_name]
                    
                    for index_sql in schema.get_indexes():
                        try:
                            cur.execute(index_sql)
                        except Exception as e:
                            print(f"  ⚠️  Index creation warning in {schema.__class__.__name__}: {e}")
                            # Don't fail on index errors as they might already exist
                
                # Commit after indexes
                self.storage.conn.commit()
                
                print("\n✅ All database schemas created successfully")
                return True
                
        except Exception as e:
            print(f"❌ Schema creation failed: {e}")
            if self.storage.conn:
                self.storage.conn.rollback()
            return False
    
    def drop_all_tables(self) -> bool:
        """
        Drop all tables in reverse dependency order
        """
        if not self.storage.conn:
            return False
        
        try:
            creation_order = self._get_creation_order()
            # Reverse order for dropping
            drop_order = list(reversed(creation_order))
            
            with self.storage.conn.cursor() as cur:
                for schema_name in drop_order:
                    # Get all actual table names from each schema
                    schema = self.schema_dependencies[schema_name]
                    for table_sql in schema.get_table_definitions():
                        if "CREATE TABLE IF NOT EXISTS" in table_sql:
                            actual_table = table_sql.split("CREATE TABLE IF NOT EXISTS")[1].split("(")[0].strip()
                            cur.execute(f"DROP TABLE IF EXISTS {actual_table} CASCADE;")
                            print(f"🗑️  Dropped table: {actual_table}")
                
                self.storage.conn.commit()
                return True
                
        except Exception as e:
            print(f"❌ Error dropping tables: {e}")
            if self.storage.conn:
                self.storage.conn.rollback()
            return False
    
    def verify_tables_exist(self) -> bool:
        """
        Verify all required tables exist
        """
        if not self.storage.conn:
            return False
        
        try:
            with self.storage.conn.cursor() as cur:
                all_tables_exist = True
                
                for schema_name, schema in self.schema_dependencies.items():
                    for table_sql in schema.get_table_definitions():
                        if "CREATE TABLE IF NOT EXISTS" in table_sql:
                            actual_table = table_sql.split("CREATE TABLE IF NOT EXISTS")[1].split("(")[0].strip()
                            
                            cur.execute("""
                                SELECT EXISTS (
                                    SELECT FROM information_schema.tables 
                                    WHERE table_schema = 'public' 
                                    AND table_name = %s
                                );
                            """, (actual_table,))
                            
                            exists = cur.fetchone()[0] # type: ignore
                            if not exists:
                                print(f"❌ Table {actual_table} does not exist")
                                all_tables_exist = False
                            else:
                                print(f"✅ Table {actual_table} exists")
                
                return all_tables_exist
                
        except Exception as e:
            print(f"❌ Error verifying tables: {e}")
            return False
    
    def get_dependency_info(self) -> Dict:
        """
        Get information about table dependencies for debugging
        """
        creation_order = self._get_creation_order()
        return {
            'creation_order': creation_order,
            'dependencies': self.dependencies,
            'total_schemas': len(self.schema_dependencies)
        }
