"""Database tools for the LangChain agent."""
from contextvars import ContextVar
from typing import Any, Optional

from langchain_core.tools import tool

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.subabase_client import get_supabase
from app.agent.guardrails.execution import ExecutionGuardrail
from app.agent.guardrails.monitoring import MonitoringGuardrail

_exec_guardrail = ExecutionGuardrail()
_monitor = MonitoringGuardrail()

# Context var for request_id (set by agent before invoking tools)
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_role_ctx: ContextVar[Optional[str]] = ContextVar("user_role", default="student")


def _validate_tool_call(tool_name: str, kwargs: dict) -> Optional[str]:
    user_role = user_role_ctx.get()
    ok, msg = _exec_guardrail.check_tool_call(tool_name, kwargs, user_role=user_role)
    if not ok:
        rid = request_id_ctx.get()
        if rid:
            _monitor.log_tool_blocked(rid, tool_name, kwargs, msg)
        return msg
    return None


@tool
def query_students(limit: int = 10, status: Optional[str] = None, email_search: Optional[str] = None) -> str:
    """
    Query students from the database.
    Args:
        limit: Max number of results (1-100). Default 10.
        status: Filter by status: 'active', 'inactive', or 'graduated'.
        email_search: Partial email search (case-insensitive).
    Returns:
        JSON string of matching students.
    """
    err = _validate_tool_call("query_students", {"limit": limit, "filters": {"status": status}})
    if err:
        return err
    try:
        sb = get_supabase()
        q = sb.table("students").select("*").limit(min(limit, 100))
        if status:
            q = q.eq("status", status)
        if email_search:
            q = q.ilike("email", f"%{email_search}%")
        result = q.execute()
        return str(result.data)
    except Exception as e:
        return f"Error querying students: {str(e)}"


@tool
def query_courses(limit: int = 10, category: Optional[str] = None, is_active: Optional[bool] = None) -> str:
    """
    Query courses from the database.
    Args:
        limit: Max number of results (1-100). Default 10.
        category: Filter by category (e.g., STEM, Humanities).
        is_active: Filter by active status (True/False).
    Returns:
        JSON string of matching courses.
    """
    err = _validate_tool_call("query_courses", {"limit": limit, "filters": {"category": category}})
    if err:
        return err
    try:
        sb = get_supabase()
        q = sb.table("courses").select("*").limit(min(limit, 100))
        if category:
            q = q.eq("category", category)
        if is_active is not None:
            q = q.eq("is_active", is_active)
        result = q.execute()
        return str(result.data)
    except Exception as e:
        return f"Error querying courses: {str(e)}"


@tool
def query_transactions(
    limit: int = 10,
    type_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    student_id: Optional[str] = None,
) -> str:
    """
    Query transactions from the database.
    Args:
        limit: Max number of results (1-100). Default 10.
        type_filter: enrollment, payment, refund, or scholarship.
        status_filter: pending, completed, failed, or refunded.
        student_id: Filter by student UUID.
    Returns:
        JSON string of matching transactions.
    """
    err = _validate_tool_call(
        "query_transactions",
        {"limit": limit, "filters": {"type": type_filter, "status": status_filter}},
    )
    if err:
        return err
    try:
        sb = get_supabase()
        q = sb.table("transactions").select("id, student_id, course_id, amount_usd, type, status, transaction_date").limit(min(limit, 100))
        if type_filter:
            q = q.eq("type", type_filter)
        if status_filter:
            q = q.eq("status", status_filter)
        if student_id:
            q = q.eq("student_id", student_id)
        result = q.execute()
        return str(result.data)
    except Exception as e:
        return f"Error querying transactions: {str(e)}"


@tool
def get_student_summary(student_email: Optional[str] = None, student_id: Optional[str] = None) -> str:
    """
    Get a summary for a student: enrollments, transaction counts, total spent.
    Provide either student_email or student_id.
    """
    err = _validate_tool_call("get_student_summary", {"filters": {"email": student_email}})
    if err:
        return err
    if not student_email and not student_id:
        return "Provide either student_email or student_id."
    try:
        sb = get_supabase()
        if student_email:
            s = sb.table("students").select("*").ilike("email", f"%{student_email}%").limit(1).execute()
        else:
            s = sb.table("students").select("*").eq("id", student_id).limit(1).execute()
        if not s.data:
            return "Student not found."
        stu = s.data[0]
        tx = sb.table("transactions").select("amount_usd, type, status").eq("student_id", stu["id"]).execute()
        total = sum(float(t["amount_usd"]) for t in tx.data if t["status"] == "completed")
        return f"Student: {stu['first_name']} {stu['last_name']} ({stu['email']}). Total transactions: {len(tx.data)}. Total spent (completed): ${total:,.2f}"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def get_database_schema() -> str:
    """
    Get the database schema details. Only accessible by admins.
    """
    err = _validate_tool_call("get_database_schema", {})
    if err:
        return err
    try:
        sb = get_supabase()
        # Simple schema info from Supabase
        return "Tables: students (id, first_name, last_name, email, status), courses (id, code, name, category, is_active), transactions (id, student_id, course_id, amount_usd, type, status, transaction_date)"
    except Exception as e:
        return f"Error: {str(e)}"


def get_all_tools():
    return [query_students, query_courses, query_transactions, get_student_summary, get_database_schema]
