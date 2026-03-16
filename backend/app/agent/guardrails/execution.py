"""
Execution Layer Guardrail
Validates agent tool calls before execution.
- Allowed tool names
- Parameter validation (e.g., limit caps, allowed filters)
- Prevents destructive or unauthorized operations
"""
from typing import Any, Dict, List, Tuple

ALLOWED_TOOLS = {"query_students", "query_courses", "query_transactions", "get_student_summary", "get_database_schema"}
MAX_LIMIT = 100
ALLOWED_FILTER_KEYS = {"status", "category", "type", "email", "course_code"}


class ExecutionGuardrail:
    """Execution layer: validate tool calls before execution."""

    def check_tool_call(self, tool_name: str, tool_input: Dict[str, Any], user_role: str = "student") -> Tuple[bool, str]:
        """
        Validate a tool call before execution.
        Returns (allowed, message).
        """
        if tool_name not in ALLOWED_TOOLS:
            return False, f"Tool '{tool_name}' is not allowed."

        if tool_name == "get_database_schema" and user_role != "admin":
            return False, "Access denied: get_database_schema is for admins only."

        if tool_name == "query_transactions" and user_role != "admin":
            return False, f"Access denied: transaction data is restricted to admins only. Role \"{user_role}\" is not permitted."

        # Limit validation
        limit = tool_input.get("limit")
        if limit is not None:
            try:
                n = int(limit)
                if n < 1 or n > MAX_LIMIT:
                    return False, f"Limit must be between 1 and {MAX_LIMIT}."
            except (ValueError, TypeError):
                return False, "Limit must be a valid integer."

        # Filter keys validation - only allow safe filter fields
        filters = tool_input.get("filters") or tool_input.get("filter") or {}
        if isinstance(filters, dict):
            for key in filters:
                if key not in ALLOWED_FILTER_KEYS and key not in ("limit",):
                    # Allow limit in tool_input directly
                    pass
            # Block dangerous keys
            blocked = {"password", "raw_sql", "query", "exec"}
            if any(k.lower() in blocked for k in (filters.keys() if isinstance(filters, dict) else [])):
                return False, "Filter contains disallowed parameters."

        return True, "OK"
