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
        self.schema_dependencies = {
            'users': UserSchema(),
            'passenger_profiles': PassengerSchema(),  # References users
            'flight_searches': FlightSchema(),        # References users
            'stored_files': DocumentSchema(),         # References users, bookings, passenger_profiles
            'bookings': BookingSchema(),              # References users, flight_searches
            'conversations': ConversationSchema(),    # References users, bookings, flight_searches, stored_files
            'payments': PaymentSchema(),              # References users, bookings
            'personalization': PersonalizationSchema() # References users, passenger_profiles
        }
        
        # Define the dependency graph (table -> list of tables it depends on)
        self.dependencies = {
            'users': [],
            'passenger_profiles': ['users'],
            'flight_searches': ['users'],
            'stored_files': ['users', 'bookings', 'passenger_profiles'],  # Will be created after bookings
            'bookings': ['users', 'flight_searches'],
            'conversations': ['users', 'bookings', 'flight_searches', 'stored_files'],
            'payments': ['users', 'bookings'],
            'personalization': ['users', 'passenger_profiles']
        }
    
    def _get_creation_order(self) -> List[str]:
        """
        Calculate the correct order for table creation using topological sort
        """
        # Topological sort to handle dependencies
        visited = set()
        temp_visited = set()
        result = []
        
        def visit(table):
            if table in temp_visited:
                raise ValueError(f"Circular dependency detected involving {table}")
            if table in visited:
                return
            
            temp_visited.add(table)
            
            # Visit all dependencies first
            for dependency in self.dependencies.get(table, []):
                visit(dependency)
            
            temp_visited.remove(table)
            visited.add(table)
            result.append(table)
        
        # Visit all tables
        for table in self.dependencies.keys():
            visit(table)
        
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
            print(f"📋 Creating tables in dependency order: {' -> '.join(creation_order)}")
            
            with self.storage.conn.cursor() as cur:
                # First pass: Create tables in dependency order
                for table_name in creation_order:
                    schema = self.schema_dependencies[table_name]
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
                            return False
                
                # Second pass: Create indexes (after all tables exist)
                print("\n📊 Creating indexes...")
                for table_name in creation_order:
                    schema = self.schema_dependencies[table_name]
                    
                    for index_sql in schema.get_indexes():
                        try:
                            cur.execute(index_sql)
                        except Exception as e:
                            print(f"  ⚠️  Index creation warning in {schema.__class__.__name__}: {e}")
                            # Don't fail on index errors as they might already exist
                
                print("\n✅ All database schemas created successfully")
                return True
                
        except Exception as e:
            print(f"❌ Schema creation failed: {e}")
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
                for table_name in drop_order:
                    # Get all actual table names from each schema
                    schema = self.schema_dependencies[table_name]
                    for table_sql in schema.get_table_definitions():
                        if "CREATE TABLE IF NOT EXISTS" in table_sql:
                            actual_table = table_sql.split("CREATE TABLE IF NOT EXISTS")[1].split("(")[0].strip()
                            cur.execute(f"DROP TABLE IF EXISTS {actual_table} CASCADE;")
                            print(f"🗑️  Dropped table: {actual_table}")
                
                return True
                
        except Exception as e:
            print(f"❌ Error dropping tables: {e}")
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
                
                for table_name, schema in self.schema_dependencies.items():
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