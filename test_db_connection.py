# test_db_connection.py
from database import get_db_connection

def test_connection():
    try:
        with get_db_connection() as conn:
            result = conn.execute("SELECT 1")
            print("Database connection successful!")
            return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()