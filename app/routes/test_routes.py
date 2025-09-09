from flask import Blueprint, jsonify, request
import psycopg2
from psycopg2 import sql, errors
import os
import time

testing_bp = Blueprint("testing", __name__)

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:12345@localhost:5432/rafiki_ai")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "12345")
POSTGRES_DB = os.getenv("POSTGRES_DB", "rafiki_ai")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", 5432)

def get_connection(db_url):
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        return conn
    except psycopg2.OperationalError as e:
        return None

def ensure_database():
    """Create the database and user if they don't exist."""
    try:
        # Connect to default postgres DB to create target DB/user
        conn = psycopg2.connect(
            dbname="postgres",
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
        )
        conn.autocommit = True
        with conn.cursor() as cur:
            # Create user if not exists
            cur.execute(sql.SQL(
                "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname=%s) THEN CREATE USER {} WITH PASSWORD %s; END IF; END $$;"
            ).format(sql.Identifier(POSTGRES_USER)), [POSTGRES_USER, POSTGRES_PASSWORD])

            # Create database if not exists
            cur.execute(sql.SQL(
                "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname=%s) THEN CREATE DATABASE {}; END IF; END $$;"
            ).format(sql.Identifier(POSTGRES_DB)), [POSTGRES_DB])
        conn.close()
    except Exception as e:
        print(f"Failed to ensure database exists: {e}")

def check_table_exists(cur, table_name):
    """Check if a table exists in the database."""
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = %s
        );
    """, (table_name,))
    return cur.fetchone()[0]

@testing_bp.route("/testing/cleanup", methods=["DELETE"])
def cleanup_test_data():
    """
    Deletes test users and their related data.
    
    Query Parameters:
    - phone_number: Delete specific phone number (optional)
    
    Examples:
    DELETE /testing/cleanup                        # Delete all +1555* numbers
    DELETE /testing/cleanup?phone_number=+15551234567  # Delete specific number
    """
    conn = get_connection(DB_URL)

    if not conn:
        # Try to ensure the database exists
        ensure_database()
        conn = get_connection(DB_URL)
        if not conn:
            return jsonify({"error": "Database connection failed after attempting to create DB/user"}), 500

    # Get phone number parameter if provided
    specific_phone = request.args.get('phone_number')
    
    try:
        with conn.cursor() as cur:
            # Check if the users table exists first
            if not check_table_exists(cur, 'users'):
                return jsonify({
                    "status": "success",
                    "message": "Users table doesn't exist yet - nothing to clean up."
                }), 200
            
            # Determine deletion criteria
            if specific_phone:
                # Delete specific phone number
                cur.execute("DELETE FROM users WHERE phone_number = %s;", (specific_phone,))
                message_template = f"Cleaned up user with phone number {specific_phone}"
            else:
                # Delete all test numbers (those starting with +1555)
                cur.execute("DELETE FROM users WHERE phone_number LIKE '+1555%';")
                message_template = "Cleaned up {rows_deleted} test user(s) with +1555* phone numbers"
            
            rows_deleted = cur.rowcount
            conn.commit()
            
        return jsonify({
            "status": "success",
            "message": message_template.format(rows_deleted=rows_deleted) if not specific_phone 
                      else message_template + (f" ({rows_deleted} rows affected)" if rows_deleted > 0 else " (user not found)")
        }), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@testing_bp.route("/testing/cleanup/all", methods=["DELETE"])
def cleanup_all_test_data():
    """
    Nuclear option: Deletes ALL test-related data from multiple tables.
    Use with extreme caution - only for test environments!
    """
    conn = get_connection(DB_URL)

    if not conn:
        ensure_database()
        conn = get_connection(DB_URL)
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500

    tables_to_clean = ['conversations', 'sessions', 'bookings', 'users']  # Add your table names
    results = {}
    
    try:
        with conn.cursor() as cur:
            for table in tables_to_clean:
                if check_table_exists(cur, table):
                    # Only delete test data (phone numbers starting with +1555)
                    if table == 'users':
                        cur.execute(f"DELETE FROM {table} WHERE phone_number LIKE '+1555%';")
                    else:
                        # For related tables, you might need different criteria
                        # This assumes foreign key relationships will handle cascading
                        cur.execute(f"DELETE FROM {table} WHERE user_id IN (SELECT id FROM users WHERE phone_number LIKE '+1555%');")
                    
                    results[table] = cur.rowcount
                else:
                    results[table] = "table not found"
            
            conn.commit()
            
        return jsonify({
            "status": "success",
            "message": "Comprehensive test data cleanup completed",
            "details": results
        }), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e), "details": results}), 500
    finally:
        if conn:
            conn.close()

@testing_bp.route("/testing/users", methods=["GET"])
def list_test_users():
    """
    Lists all test users (phone numbers starting with +1555) for debugging.
    """
    conn = get_connection(DB_URL)
    
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        with conn.cursor() as cur:
            if not check_table_exists(cur, 'users'):
                return jsonify({
                    "status": "success",
                    "users": [],
                    "message": "Users table doesn't exist yet"
                }), 200
            
            cur.execute("""
                SELECT id, phone_number, created_at 
                FROM users 
                WHERE phone_number LIKE '+1555%' 
                ORDER BY created_at DESC;
            """)
            
            users = []
            for row in cur.fetchall():
                users.append({
                    "id": row[0],
                    "phone_number": row[1],
                    "created_at": str(row[2]) if row[2] else None
                })
            
            return jsonify({
                "status": "success",
                "users": users,
                "count": len(users)
            }), 200
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@testing_bp.route("/testing/health", methods=["GET"])
def health_check():
    """
    Simple health check endpoint to verify the testing endpoints are working.
    """
    conn = get_connection(DB_URL)
    
    if not conn:
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "message": "Could not connect to database"
        }), 500
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()
        
        conn.close()
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "message": "Testing endpoints are operational"
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "database": "error",
            "message": str(e)
        }), 500
        
# In-memory storage for testing responses
response_storage = {}

@testing_bp.route("/testing/store-response", methods=["POST"])
def store_response():
    """Store a response for testing purposes"""
    try:
        data = request.get_json()
        
        if not data:
            print("Warning: No JSON data provided to store-response endpoint")
            return jsonify({"error": "No JSON data provided"}), 400
        
        phone_number = data.get('phone_number')
        response_text = data.get('response')
        request_id = data.get('request_id')
        client_timestamp = data.get('timestamp')  # Timestamp from the delivery service
        
        print(f"🧪 Storing response for testing - Phone: {phone_number}, Request ID: {request_id}")
        
        if not phone_number or not response_text:
            print(f"Warning: Missing required data - Phone: {phone_number}, Response: {bool(response_text)}")
            return jsonify({"error": "Missing phone_number or response"}), 400
        
        # Use client timestamp if provided, otherwise generate new millisecond timestamp
        if client_timestamp:
            timestamp_ms = client_timestamp
            print(f"Using client-provided timestamp: {timestamp_ms}")
        else:
            timestamp_ms = int(time.time() * 1000)
            print(f"Generated new timestamp: {timestamp_ms}")
        
        # Store the response with consistent millisecond timestamps
        response_storage[phone_number] = {
            'response': response_text,
            'timestamp': timestamp_ms,  # Now in milliseconds like JavaScript
            'request_id': request_id,
            'stored_at': time.time(),  # Keep server time for debugging
            'response_length': len(response_text)
        }
        
        print(f"✅ Successfully stored response for {phone_number} at timestamp {timestamp_ms} - Length: {len(response_text)} chars")
        
        return jsonify({
            "status": "stored",
            "timestamp": timestamp_ms,
            "phone_number": phone_number
        }), 200
    
    except Exception as e:
        print(f"❌ Error storing response: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@testing_bp.route("/testing/get-response/<phone_number>", methods=["GET"])
def get_response(phone_number):
    """Get the stored response for a phone number"""
    response_data = response_storage.get(phone_number)
    if response_data:
        return jsonify({
            'has_response': True,
            'response': response_data['response'],
            'timestamp': response_data['timestamp']
        }), 200
    
    return jsonify({'has_response': False}), 200

@testing_bp.route("/testing/clear-responses/<phone_number>", methods=["DELETE"])
def clear_responses(phone_number):
    """Clear stored responses for a phone number"""
    if phone_number in response_storage:
        del response_storage[phone_number]
    return jsonify({"status": "cleared"}), 200
