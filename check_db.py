import psycopg2
from app.core.config import settings

db_url = settings.database_url.replace("postgresql+psycopg2://", "postgresql://")
conn = psycopg2.connect(db_url)
cur = conn.cursor()
try:
    cur.execute("SELECT version_num FROM alembic_version;")
    print("Alembic version table:", cur.fetchall())
except Exception as e:
    print("Alembic version error:", e)
    conn.rollback()

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
tables = [t[0] for t in cur.fetchall()]
print("Tables:", tables)

for table in tables:
    cur.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name='{table}';")
    print(f"Table {table}:", cur.fetchall())

conn.close()
