-- =============================================
-- GUARDRAILS IN AI - Subabase Schema
-- Tables: students, courses, transactions
-- =============================================

-- Enable UUID extension if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================
-- STUDENTS TABLE
-- =============================================
CREATE TABLE IF NOT EXISTS students (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE,
    enrollment_date TIMESTAMPTZ DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'graduated')),
    major TEXT,
    gpa NUMERIC(3, 2) DEFAULT 0.00,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for common queries
CREATE INDEX IF NOT EXISTS idx_students_email ON students(email);
CREATE INDEX IF NOT EXISTS idx_students_status ON students(status);
CREATE INDEX IF NOT EXISTS idx_students_enrollment_date ON students(enrollment_date);
CREATE INDEX IF NOT EXISTS idx_students_major ON students(major);

-- =============================================
-- COURSES TABLE
-- =============================================
CREATE TABLE IF NOT EXISTS courses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    credits INTEGER NOT NULL CHECK (credits > 0),
    price_usd DECIMAL(10, 2) NOT NULL CHECK (price_usd >= 0),
    duration_weeks INTEGER CHECK (duration_weeks > 0),
    category VARCHAR(50),
    department TEXT NOT NULL DEFAULT 'General',
    max_enrollment INTEGER DEFAULT 50,
    current_enrollment INTEGER DEFAULT 0,
    instructor TEXT,
    semester TEXT NOT NULL DEFAULT 'Fall 2024',
    fee NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_courses_code ON courses(code);
CREATE INDEX IF NOT EXISTS idx_courses_category ON courses(category);
CREATE INDEX IF NOT EXISTS idx_courses_is_active ON courses(is_active);
CREATE INDEX IF NOT EXISTS idx_courses_dept ON courses(department);

-- =============================================
-- TRANSACTIONS TABLE
-- =============================================
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    amount_usd DECIMAL(10, 2) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('enrollment', 'refund', 'payment', 'scholarship')),
    status VARCHAR(20) DEFAULT 'completed' CHECK (status IN ('pending', 'completed', 'failed', 'refunded')),
    payment_method VARCHAR(50),
    transaction_date TIMESTAMPTZ DEFAULT NOW(),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_student_id ON transactions(student_id);
CREATE INDEX IF NOT EXISTS idx_transactions_course_id ON transactions(course_id);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_students_updated_at BEFORE UPDATE ON students
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_courses_updated_at BEFORE UPDATE ON courses
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_transactions_updated_at BEFORE UPDATE ON transactions
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

-- =============================================
-- MONITORING TABLE
-- Logs each and every piece of information for observability
-- =============================================
CREATE TABLE IF NOT EXISTS monitoring_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    event VARCHAR(50) NOT NULL,
    -- User input
    user_input_raw TEXT,
    user_input_length INTEGER,
    chat_history_length INTEGER,
    -- Filtration
    stage VARCHAR(50),
    filtration_type VARCHAR(100),
    original_preview TEXT,
    filtered_preview TEXT,
    -- Guardrails
    guardrail VARCHAR(50),
    passed BOOLEAN,
    blocked BOOLEAN,
    guardrail_message TEXT,
    -- Tools
    tool_name VARCHAR(100),
    tool_input JSONB,
    tool_allowed BOOLEAN,
    tool_blocked_reason TEXT,
    result_preview TEXT,
    success BOOLEAN,
    -- Request outcome
    request_success BOOLEAN,
    blocked_at VARCHAR(50),
    output_preview TEXT,
    tool_calls_count INTEGER,
    summary JSONB,
    -- Hallucination prevention
    hallucination_prevented BOOLEAN,
    hallucination_details TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_monitoring_request_id ON monitoring_logs(request_id);
CREATE INDEX IF NOT EXISTS idx_monitoring_timestamp ON monitoring_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_monitoring_event ON monitoring_logs(event);
CREATE INDEX IF NOT EXISTS idx_monitoring_guardrail ON monitoring_logs(guardrail);
