-- =============================================
-- Migration 001: Add columns to students and courses
-- Run in Supabase SQL Editor
-- =============================================

-- STUDENTS: Add major, gpa, is_active
ALTER TABLE students ADD COLUMN IF NOT EXISTS major TEXT;
ALTER TABLE students ADD COLUMN IF NOT EXISTS gpa NUMERIC(3, 2) DEFAULT 0.00;
ALTER TABLE students ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- COURSES: Add department, max_enrollment, current_enrollment, instructor, semester, fee
ALTER TABLE courses ADD COLUMN IF NOT EXISTS department TEXT;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS max_enrollment INTEGER DEFAULT 50;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS current_enrollment INTEGER DEFAULT 0;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS instructor TEXT;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS semester TEXT;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS fee NUMERIC(10, 2) DEFAULT 0.00;

-- Backfill NOT NULL columns for existing rows
UPDATE courses SET department = COALESCE(department, 'General') WHERE department IS NULL;
UPDATE courses SET semester = COALESCE(semester, 'Fall 2024') WHERE semester IS NULL;
UPDATE courses SET fee = COALESCE(fee, 0.00) WHERE fee IS NULL;

ALTER TABLE courses ALTER COLUMN department SET NOT NULL;
ALTER TABLE courses ALTER COLUMN semester SET NOT NULL;
ALTER TABLE courses ALTER COLUMN fee SET NOT NULL;

-- Indexes (IF NOT EXISTS - skip if already created)
CREATE INDEX IF NOT EXISTS idx_students_email ON students(email);
CREATE INDEX IF NOT EXISTS idx_students_major ON students(major);
CREATE INDEX IF NOT EXISTS idx_courses_code ON courses(code);
CREATE INDEX IF NOT EXISTS idx_courses_dept ON courses(department);
CREATE INDEX IF NOT EXISTS idx_transactions_student ON transactions(student_id);
CREATE INDEX IF NOT EXISTS idx_transactions_course ON transactions(course_id);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);

-- monitoring_logs = guardrail_logs equivalent (schema uses monitoring_logs)
-- session_id -> request_id, guardrail_layer -> guardrail
CREATE INDEX IF NOT EXISTS idx_guardrail_logs_session ON monitoring_logs(request_id);
CREATE INDEX IF NOT EXISTS idx_guardrail_logs_layer ON monitoring_logs(guardrail);
CREATE INDEX IF NOT EXISTS idx_guardrail_logs_ts ON monitoring_logs(timestamp);
