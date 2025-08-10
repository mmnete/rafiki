import os
import psycopg2
from psycopg2 import sql
from psycopg2.extras import DictCursor

class User:
    def __init__(self, id: str, phone_number: str, first_name: str = None, middle_name: str = None, last_name: str = None, location: str = None, status: str = "new"):
        self.id = id
        self.phone_number = phone_number
        self.first_name = first_name
        self.middle_name = middle_name
        self.last_name = last_name
        self.location = location
        self.status = status
        
    def to_dict(self):
        return {
            "id": self.id,
            "phone_number": self.phone_number,
            "first_name": self.first_name,
            "middle_name": self.middle_name,
            "last_name": self.last_name,
            "location": self.location,
            "status": self.status
        }
        
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get("id"),
            phone_number=data.get("phone_number"),
            first_name=data.get("first_name"),
            middle_name=data.get("middle_name"),
            last_name=data.get("last_name"),
            location=data.get("location"),
            status=data.get("status", "new")  # default to "new" if not present
        )
        
    def __repr__(self):
        return f"User(phone_number={self.phone_number}, status={self.status})"

class Conversation:
    def __init__(self, user_id: int, request: str, response: str, created_at=None, id=None):
        self.id = id
        self.user_id = user_id
        self.request = request
        self.response = response
        self.created_at = created_at

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "request": self.request,
            "response": self.response,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get("id"),
            user_id=data["user_id"],
            request=data["request"],
            response=data["response"],
            created_at=data.get("created_at")
        )

    def __repr__(self):
        return f"Conversation(user_id={self.user_id}, request={self.request!r}, response={self.response!r})"


class StorageService:
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        self.conn = None
        self._connect_db()

    def _connect_db(self):
        """Establishes a connection to the PostgreSQL database."""
        if not self.db_url:
            print("ERROR: DATABASE_URL is not set. Database operations will fail.")
            return

        try:
            self.conn = psycopg2.connect(self.db_url)
            self.conn.autocommit = True  # Auto-commit changes for simplicity
            print("Database connection established.")
            self._create_tables()
        except Exception as e:
            print(f"Error connecting to database: {e}")
            self.conn = None

    def _create_tables(self):
        """Creates the 'users' and 'conversations' tables if they don't exist."""
        if not self.conn:
            print("Cannot create tables: No database connection.")
            return

        try:
            with self.conn.cursor() as cur:
                # Modified users table to include new fields based on your User class
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        phone_number VARCHAR(50) UNIQUE NOT NULL,
                        first_name VARCHAR(255),
                        middle_name VARCHAR(255),
                        last_name VARCHAR(255),
                        location VARCHAR(255),
                        status VARCHAR(50) DEFAULT 'new'
                    );
                """)
                # Create conversations table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id SERIAL PRIMARY KEY,
                        user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        request TEXT NOT NULL,
                        response TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                # Create index for efficient querying
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_created_at
                    ON conversations(user_id, created_at DESC);
                """)
            print("Database tables checked/created successfully.")
        except Exception as e:
            print(f"Error creating tables: {e}")

    def get_or_create_user(self, phone_number, first_name=None, middle_name=None, last_name=None, location=None, status="onboarding_greet"):
        """
        Retrieves a user's ID and details by phone number, or creates a new user if not found.
        When creating, it uses provided details or defaults.
        Returns a tuple (user_id, user_data_dict).
        `user_data_dict` contains all fields: id, phone_number, first_name, etc.
        """
        if not self.conn:
            print("No database connection to get or create user.")
            return None, {}

        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                # Try to fetch existing user
                cur.execute("""
                    SELECT id, phone_number, first_name, middle_name, last_name, location, status
                    FROM users WHERE phone_number = %s;
                """, (phone_number,))
                user_data = cur.fetchone()
                if user_data:
                    return User.from_dict(dict(user_data))
                else:
                    # Insert new user with provided details or defaults
                    cur.execute("""
                        INSERT INTO users (phone_number, first_name, middle_name, last_name, location, status)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id, phone_number, first_name, middle_name, last_name, location, status;
                    """, (phone_number, first_name, middle_name, last_name, location, status))
                    new_user_data = cur.fetchone()
                    if new_user_data:
                        return User.from_dict(dict(new_user_data))
        except Exception as e:
            print(f"Error getting or creating user {phone_number}: {e}")
            return None, {}

    def load_user_conversation_history(self, user_id, limit=None):
        """
        Loads the entire conversation history for a given user ID, ordered by creation time.
        Returns a list of dictionaries, each representing a conversation turn.
        """
        if not self.conn:
            print("No database connection to load conversation history.")
            return []

        try:
            # Use DictCursor to get results as dictionaries for easier access
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                query = """
                    SELECT id, user_id, request, response, created_at
                    FROM conversations
                    WHERE user_id = %s
                    ORDER BY created_at ASC
                """
                if limit:
                    query += " LIMIT %s"
                    cur.execute(query, (user_id, limit))
                else:
                    cur.execute(query, (user_id,))
                
                return [Conversation.from_dict(dict(row)) for row in cur.fetchall()]
        except Exception as e:
            print(f"Error loading conversation history for user ID {user_id}: {e}")
            return []

    def save_conversation_entry(self, user_id, request_text, response_text):
        if not self.conn:
            print("No database connection to save conversation entry.")
            return None

        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("""
                    INSERT INTO conversations (user_id, request, response)
                    VALUES (%s, %s, %s)
                    RETURNING id, user_id, request, response, created_at;
                """, (user_id, request_text, response_text))
                row = cur.fetchone()
                return Conversation.from_dict(dict(row))
        except Exception as e:
            print(f"Error saving conversation entry for user ID {user_id}: {e}")
        return None


    def delete_user_data(self, user_id):
        """Deletes a user and all their associated conversation data."""
        if not self.conn:
            print("No database connection to delete user data.")
            return False

        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM users WHERE id = %s;", (user_id,))
            print(f"User with ID {user_id} and all associated conversations deleted.")
            return True
        except Exception as e:
            print(f"Error deleting user with ID {user_id}: {e}")
            return False

    def close_connection(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            print("Database connection closed.")

    def update_user_profile(self, user_id, first_name=None, middle_name=None, last_name=None, location=None, status=None):
        """
        Updates specific profile fields for an existing user.
        Only non-None arguments will be updated.
        """
        if not self.conn:
            print("No database connection to update user profile.")
            return False

        update_fields = []
        update_values = []

        if first_name is not None:
            update_fields.append("first_name = %s")
            update_values.append(first_name)
        if middle_name is not None:
            update_fields.append("middle_name = %s")
            update_values.append(middle_name)
        if last_name is not None:
            update_fields.append("last_name = %s")
            update_values.append(last_name)
        if location is not None:
            update_fields.append("location = %s")
            update_values.append(location)
        if status is not None:
            update_fields.append("status = %s")
            update_values.append(status)

        if not update_fields:
            print("No fields to update for user profile.")
            return False

        try:
            with self.conn.cursor() as cur:
                # Using sql.SQL for safe query construction with dynamic fields
                query = sql.SQL("UPDATE users SET {} WHERE id = %s;").format(
                    sql.SQL(", ").join(map(sql.SQL, update_fields))
                )
                cur.execute(query, update_values + [user_id])
                if cur.rowcount > 0:
                    print(f"User profile for ID {user_id} updated successfully.")
                    return True
                else:
                    print(f"User with ID {user_id} not found for update.")
                    return False
        except Exception as e:
            print(f"Error updating user profile for ID {user_id}: {e}")
            return False

    def get_user_details(self, user_id):
        """
        Retrieves all profile details for a specific user ID.
        Returns a dictionary of user data or None if not found.
        """
        if not self.conn:
            print("No database connection to get user details.")
            return None

        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("""
                    SELECT id, phone_number, first_name, middle_name, last_name, location, status
                    FROM users WHERE id = %s;
                """, (user_id,))
                user_data = cur.fetchone()
                if user_data:
                    return dict(user_data)
                else:
                    return None
        except Exception as e:
            print(f"Error getting user details for ID {user_id}: {e}")
            return None


    def delete_all_users(self):
        """
        Deletes all users and their associated conversation data.
        WARNING: This action is irreversible.
        """
        if not self.conn:
            print("No database connection to delete all users.")
            return False

        try:
            with self.conn.cursor() as cur:
                # Use TRUNCATE for faster deletion and to reset IDs
                cur.execute("TRUNCATE TABLE users RESTART IDENTITY CASCADE;")
            print("All users and their conversations deleted successfully.")
            return True
        except Exception as e:
            print(f"Error deleting all users: {e}")
            return False


