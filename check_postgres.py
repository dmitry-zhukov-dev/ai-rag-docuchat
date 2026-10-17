import sys
from sqlalchemy import text
from app.db.session import engine

def main():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            value = result.scalar()
            if value == 1:
                print("PostgreSQL connection successful: SELECT 1 returned 1")
                sys.exit(0)
            else:
                print(f"PostgreSQL connection returned unexpected value: {value}")
                sys.exit(1)
    except Exception as e:
        print(f"PostgreSQL connection failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
