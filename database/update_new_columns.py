"""
Populate new columns (major, gpa, is_active for students;
department, max_enrollment, instructor, semester, fee for courses).
Run after applying 001_add_students_courses_columns.sql

Run: python database/update_new_columns.py
"""
import os
import random
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Set SUPABASE_URL and SUPABASE_KEY in .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

MAJORS = [
    "Computer Science", "Biology", "Mathematics", "English", "Psychology",
    "Business Administration", "Economics", "History", "Physics", "Chemistry",
    "Engineering", "Art", "Political Science", "Sociology", "Nursing"
]
INSTRUCTORS = [
    "Dr. Sarah Johnson", "Prof. Michael Chen", "Dr. Emily Davis", "Prof. James Wilson",
    "Dr. Maria Garcia", "Prof. Robert Brown", "Dr. Lisa Anderson", "Prof. David Lee",
    "Dr. Jennifer Taylor", "Prof. Christopher Moore", "Dr. Amanda Martinez"
]
SEMESTERS = ["Fall 2024", "Spring 2024", "Fall 2023", "Spring 2023", "Summer 2024"]
DEPARTMENTS = ["Computer Science", "Mathematics", "English", "Biology", "Physics", "Economics", "History", "Art"]


def main():
    print("Updating students with major, gpa, is_active...")
    students = supabase.table("students").select("id").execute().data
    for s in students:
        supabase.table("students").update({
            "major": random.choice(MAJORS),
            "gpa": round(random.uniform(2.0, 4.0), 2),
            "is_active": random.random() > 0.15
        }).eq("id", s["id"]).execute()
    print(f"  Updated {len(students)} students")

    print("Updating courses with department, max_enrollment, current_enrollment, instructor, semester, fee...")
    courses = supabase.table("courses").select("id, price_usd").execute().data
    for c in courses:
        max_enroll = random.choice([30, 50, 75, 100])
        supabase.table("courses").update({
            "department": random.choice(DEPARTMENTS),
            "max_enrollment": max_enroll,
            "current_enrollment": random.randint(0, min(max_enroll, 45)),
            "instructor": random.choice(INSTRUCTORS),
            "semester": random.choice(SEMESTERS),
            "fee": c.get("price_usd", 0) or round(random.uniform(99, 899), 2)
        }).eq("id", c["id"]).execute()
    print(f"  Updated {len(courses)} courses")

    print("Done.")


if __name__ == "__main__":
    main()
