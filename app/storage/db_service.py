import os
import psycopg2

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
            self.conn.autocommit = True
            print("Database connection established.")
        except Exception as e:
            print(f"Error connecting to database: {e}")
            self.conn = None

