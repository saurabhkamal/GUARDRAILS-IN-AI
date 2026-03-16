"""
Run migration 001: Add columns to students and courses, create indexes.
Tries direct DB connection first; if that fails, prints instructions to run in SQL Editor.

Run: python run_migration.py
"""
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD")


def run_migration_via_db():
    """Run migration SQL via direct PostgreSQL connection."""
    import psycopg2
    import re

    url = None
    if DATABASE_URL and "YOUR" not in (DATABASE_URL or "").upper():
        url = DATABASE_URL
    elif SUPABASE_DB_PASSWORD and SUPABASE_URL:
        m = re.search(r"https://([a-z0-9]+)\.supabase\.co", SUPABASE_URL)
        if m:
            ref = m.group(1)
            region = os.getenv("SUPABASE_POOLER_REGION", "us-east-1")
            url = f"postgresql://postgres.{ref}:{SUPABASE_DB_PASSWORD}@aws-0-{region}.pooler.supabase.com:5432/postgres"

    if not url:
        return False

    try:
        migration_path = Path(__file__).parent / "database" / "migrations" / "001_add_students_courses_columns.sql"
        sql = migration_path.read_text(encoding="utf-8")
        conn = psycopg2.connect(url)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.close()
        return True
    except Exception as e:
        print(f"DB connection failed: {e}")
        return False


def main():
    print("=== Migration 001: Add students/courses columns and indexes ===\n")

    if run_migration_via_db():
        print("Migration applied successfully.\n")
    else:
        print("Could not connect to database. Run the migration manually:")
        print("1. Open: Supabase Dashboard > SQL Editor")
        print("2. Copy/paste: database/migrations/001_add_students_courses_columns.sql")
        print("3. Run the query\n")
        print("Then run: python database/update_new_columns.py\n")
        sys.exit(1)

    print("Populating new columns with data...")
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "database" / "update_new_columns.py")],
        cwd=str(Path(__file__).parent),
        capture_output=False,
    )
    if result.returncode != 0:
        sys.exit(result.returncode)

    print("\nDone. Run python test_subabase.py to verify.")


if __name__ == "__main__":
    main()
