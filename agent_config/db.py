import sqlite3
from pathlib import Path
from agno.db.sqlite import SqliteDb
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_DIR = PROJECT_ROOT / "database"
DB_DIR.mkdir(parents=True, exist_ok=True)
APP_DB_PATH = DB_DIR / "app.db"

db = SqliteDb(
    db_file=str(APP_DB_PATH)
)

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(APP_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

