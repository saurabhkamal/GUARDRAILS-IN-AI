"""
Seed script for Subabase - Students, Courses, Transactions
Generates 1000+ records for development and testing.
Run: python database/seed.py
"""
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Set SUPABASE_URL and SUPABASE_KEY in .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Sample data
FIRST_NAMES = [
    "Emma", "Liam", "Olivia", "Noah", "Ava", "Ethan", "Sophia", "Mason",
    "Isabella", "William", "Mia", "James", "Charlotte", "Benjamin", "Amelia",
    "Lucas", "Harper", "Henry", "Evelyn", "Alexander", "Abigail", "Sebastian",
    "Emily", "Jack", "Elizabeth", "Aiden", "Sofia", "Owen", "Avery", "Samuel"
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"
]
COURSE_PREFIXES = ["CS", "MATH", "ENG", "BIO", "PHYS", "ECON", "HIST", "ART"]
COURSE_NAMES = [
    "Introduction to Programming", "Data Structures", "Machine Learning",
    "Calculus I", "Linear Algebra", "Statistics", "English Composition",
    "Biology 101", "Physics I", "Microeconomics", "World History",
    "Digital Art", "Web Development", "Database Systems", "Algorithms"
]
CATEGORIES = ["STEM", "Humanities", "Arts", "Business", "Science"]
PAYMENT_METHODS = ["credit_card", "debit_card", "bank_transfer", "scholarship", "financial_aid"]


def random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


def main():
    print("Seeding database...")

    # 1. Insert Courses (50 courses)
    courses = []
    for i in range(50):
        prefix = random.choice(COURSE_PREFIXES)
        name = random.choice(COURSE_NAMES)
        courses.append({
            "code": f"{prefix}{100 + i}",
            "name": f"{name} - Section {i % 5 + 1}",
            "description": f"Comprehensive course covering {name}",
            "credits": random.choice([3, 4]),
            "price_usd": round(random.uniform(99, 899), 2),
            "duration_weeks": random.choice([8, 10, 12, 16]),
            "category": random.choice(CATEGORIES),
            "is_active": random.random() > 0.1
        })
    courses_result = supabase.table("courses").insert(courses).execute()
    courses_data = courses_result.data
    print(f"  Inserted {len(courses_data)} courses")

    # 2. Insert Students (150 students)
    students = []
    for i in range(150):
        fn = random.choice(FIRST_NAMES)
        ln = random.choice(LAST_NAMES)
        students.append({
            "email": f"{fn.lower()}.{ln.lower()}{i}@university.edu",
            "first_name": fn,
            "last_name": ln,
            "date_of_birth": (datetime.now() - timedelta(days=random.randint(365*18, 365*35))).date().isoformat(),
            "enrollment_date": random_date(datetime(2020, 1, 1), datetime(2024, 6, 1)).isoformat(),
            "status": random.choices(["active", "inactive", "graduated"], weights=[0.7, 0.2, 0.1])[0]
        })
    students_result = supabase.table("students").insert(students).execute()
    students_data = students_result.data
    print(f"  Inserted {len(students_data)} students")

    # 3. Use inserted IDs for FK references

    # 4. Insert Transactions (1000+ records)
    tx_types = ["enrollment", "payment", "refund", "scholarship"]
    tx_statuses = ["pending", "completed", "failed", "refunded"]
    transactions = []
    for _ in range(1050):
        student = random.choice(students_data)
        course = random.choice(courses_data)
        tx_type = random.choices(tx_types, weights=[0.5, 0.35, 0.05, 0.1])[0]
        if tx_type == "refund":
            amount = -round(random.uniform(50, course["price_usd"] * 0.5), 2)
        elif tx_type == "scholarship":
            amount = -round(random.uniform(100, 500), 2)
        else:
            amount = round(random.uniform(course["price_usd"] * 0.2, course["price_usd"]), 2)
        status = random.choices(tx_statuses, weights=[0.05, 0.85, 0.05, 0.05])[0]
        transactions.append({
            "student_id": student["id"],
            "course_id": course["id"],
            "amount_usd": amount,
            "type": tx_type,
            "status": status,
            "payment_method": random.choice(PAYMENT_METHODS),
            "transaction_date": random_date(datetime(2022, 1, 1), datetime.now()).isoformat(),
            "notes": random.choice(["", "Early bird discount", "Semester bundle", ""]) or None
        })

    # Batch insert transactions (Supabase has limits, insert in batches of 100)
    batch_size = 100
    for i in range(0, len(transactions), batch_size):
        batch = transactions[i:i + batch_size]
        supabase.table("transactions").insert(batch).execute()
    print(f"  Inserted {len(transactions)} transactions")

    print("Seeding complete!")


if __name__ == "__main__":
    main()
