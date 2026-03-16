"""
Create tables and seed data in Subabase.
Run: python bootstrap_db.py
      python bootstrap_db.py --db-password YOUR_DB_PASSWORD
      (or set SUPABASE_DB_PASSWORD in .env)

Requires DATABASE_URL or SUPABASE_DB_PASSWORD for schema (DDL).
Uses SUPABASE_URL + SUPABASE_KEY for seeding.
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD")


def get_database_url(db_password: str | None = None) -> str:
    pw = db_password or (SUPABASE_DB_PASSWORD and SUPABASE_DB_PASSWORD.strip())
    # Prefer full DATABASE_URL from Supabase dashboard (most reliable)
    if DATABASE_URL and "YOUR" not in (DATABASE_URL or "").upper():
        return DATABASE_URL
    if pw and SUPABASE_URL:
        m = re.search(r"https://([a-z0-9]+)\.supabase\.co", SUPABASE_URL)
        if m:
            ref = m.group(1)
            region = os.getenv("SUPABASE_POOLER_REGION", "us-east-1")
            return f"postgresql://postgres.{ref}:{pw}@aws-0-{region}.pooler.supabase.com:5432/postgres"
    raise SystemExit(
        "Set DATABASE_URL in .env (from Dashboard > Project Settings > Database > Connect)\n"
        "Or set SUPABASE_DB_PASSWORD (database password, NOT the API key)"
    )


def run_schema(db_password: str | None = None):
    import psycopg2

    url = get_database_url(db_password)
    schema_path = Path(__file__).parent / "database" / "schema.sql"
    sql = schema_path.read_text(encoding="utf-8")
    print("Applying schema (creating tables)...")
    try:
        conn = psycopg2.connect(url)
    except Exception as e:
        err = str(e)
        print(f"\n  Connection failed: {err}\n")
        if "Tenant or user not found" in err:
            print("  'Tenant or user not found' usually means SUPABASE_DB_PASSWORD is wrong.")
            print("  Use the DATABASE password from Project Settings > Database (not the API key).")
        print("\n  MANUAL WORKAROUND:")
        print("  1. Open: Supabase Dashboard > SQL Editor")
        print("  2. Copy/paste the contents of database/schema.sql")
        print("  3. Run the query")
        print("  4. Then run: python database/seed.py")
        raise SystemExit(1)
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
    parser = argparse.ArgumentParser(description="Create Subabase tables and seed data")
    parser.add_argument("--db-password", help="Database password (or set SUPABASE_DB_PASSWORD)")
    args = parser.parse_args()

    print("=== Bootstrap Database ===\n")
    run_schema(args.db_password)
    run_seed()
    print("\nDone. Run: python test_subabase.py")


if __name__ == "__main__":
    main()
