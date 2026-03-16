"""
Test Subabase connection and verify data.
Run from project root: python test_subabase.py
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env")
    exit(1)

print("Connecting to Subabase...")
try:
    from supabase import create_client
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Connection OK.\n")
except Exception as e:
    print(f"ERROR: Connection failed - {e}")
    exit(1)

# Test each table
for table, label in [
    ("students", "Students"),
    ("courses", "Courses"),
    ("transactions", "Transactions"),
]:
    try:
        result = sb.table(table).select("*", count="exact").limit(5).execute()
        count = result.count if hasattr(result, "count") and result.count is not None else len(result.data)
        print(f"=== {label} (showing up to 5 rows, total: {count}) ===")
        if result.data:
            for i, row in enumerate(result.data[:5], 1):
                print(f"  {i}. {row}")
        else:
            print("  (no rows)")
        print()
    except Exception as e:
        print(f"ERROR querying {table}: {e}\n")

# Get exact counts
print("=== Summary ===")
for table in ["students", "courses", "transactions"]:
    try:
        result = sb.table(table).select("id", count="exact").limit(1).execute()
        n = result.count if hasattr(result, "count") and result.count is not None else "?"
        print(f"  {table}: {n} rows")
    except Exception as e:
        print(f"  {table}: error - {e}")

print("\nSubabase connection test complete.")
