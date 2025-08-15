import sqlite3
import os

db_path = 'farmlink.db'
try:
    # Remove the database file if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing {db_path}")

    # Connect to the database (will create a new one)
    with sqlite3.connect(db_path) as conn:
        print("Connected to database successfully!")
        c = conn.cursor()
        # Create a test table
        c.execute('''
            CREATE TABLE IF NOT EXISTS test (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL
            )
        ''')
        conn.commit()
        print("Test table created successfully!")
        # Verify SQLite version
        c.execute('SELECT sqlite_version();')
        version = c.fetchone()
        print(f"SQLite version: {version[0]}")
except sqlite3.DatabaseError as e:
    print(f"Database error: {e}")
except Exception as e:
    print(f"Error: {e}")