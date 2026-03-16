"""
Create tables and seed data in Subabase.
Uses direct PostgreSQL connection (psycopg2) for DDL, then seed via Supabase client.
Run: python setup_database.py

Requires DATABASE_URL in .env, e.g.:
  postgresql://postgres:[YOUR-PASSWORD]@db.PROJECT_REF.supabase.co:5432/postgres
Or SUPABASE_DB_PASSWORD (we construct URL from SUPABASE_URL).
"""
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD")


def get_database_url() -> str:
    if DATABASE_URL and "YOUR" not in DATABASE_URL.upper() and "PASSWORD" not in DATABASE_URL:
        return DATABASE_URL
    if SUPABASE_DB_PASSWORD and SUPABASE_DB_PASSWORD.strip() and SUPABASE_URL:
        # Extract project ref from https://xxx.supabase.co
        m = re.search(r"https://([a-z0-9]+)\.supabase\.co", SUPABASE_URL)
        if m:
            ref = m.group(1)
            return f"postgresql://postgres:{SUPABASE_DB_PASSWORD}@db.{ref}.supabase.co:5432/postgres"
    raise SystemExit(
        "Set DATABASE_URL or SUPABASE_DB_PASSWORD in .env.\n"
        "Get it from Supabase Dashboard → Project Settings → Database → Connection string"
    )


def run_schema():
    import psycopg2

    url = get_database_url()
    schema_path = Path(__file__).parent / "database" / "schema.sql"
    sql = schema_path.read_text(encoding="utf-8")
    print("Applying schema...")
    conn = psycopg2.connect(url)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        print("  Schema applied.")
    finally:
        conn.close()


def run_seed():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise SystemExit("SUPABASE_URL and SUPABASE_KEY required for seeding.")
    print("Seeding data...")
    # Run seed script
    import subprocess
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "database" / "seed.py")],
        cwd=str(Path(__file__).parent),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr or result.stdout)
        raise SystemExit(f"Seed failed: {result.returncode}")
    print(result.stdout)


def main():
    print("=== Setup Database ===\n")
    run_schema()
    run_seed()
    print("\nDone. Run python test_subabase.py to verify.")


if __name__ == "__main__":
    main()
