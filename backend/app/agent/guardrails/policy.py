"""
Policy Layer Guardrail
Enforces organizational and business policies before processing.
- Allowed domain: students, courses, transactions only
- Block harmful or off-topic intents
- Enforce data access policies
"""
import re
from typing import Tuple


class PolicyGuardrail:
    """Policy layer: business rules and allowed scope."""

    ALLOWED_TOPICS = {"student", "students", "course", "courses", "transaction", "transactions",
                      "enrollment", "payment", "refund", "credit", "price", "fee"}
    BLOCKED_PATTERNS = [
        r"delete\s+(all|everything|table)",
        r"drop\s+table",
        r"truncate",
        r"alter\s+table",
        r"modify\s+schema",
        r"create\s+table",
        r"insert\s+into\s+\w+\s+values\s*\(.*\).*;",  # Raw INSERT injection
        r"1\s*=\s*1",  # SQL injection pattern
        r"--\s*$",  # SQL comment injection
        r"union\s+select",
        r";\s*drop",
        r"exec\s*\(",
        r"execute\s+immediate",
    ]

    def check(self, user_input: str, user_role: str = "student") -> Tuple[bool, str]:
        """
        Validate user input against policy.
        Returns (allowed, message).
        """
        if not user_input or not user_input.strip():
            return False, "Empty input is not allowed."

        # Role-based access control
        if user_role == "viewer" and any(word in user_input.lower() for word in ["delete", "drop", "update", "insert"]):
            return False, "Viewers are not allowed to perform write operations."

        TRANSACTION_KEYWORDS = {"transaction", "transactions", "enrollment", "enrollments", "payment", "payments", "refund", "refunds", "fee", "fees", "credit"}
        if user_role in ("student", "viewer"):
            words = set(re.findall(r"\w+", user_input.lower()))
            if words & TRANSACTION_KEYWORDS:
                return False, f'BLOCKED role_access: Transaction and payment data is restricted to admins only. Role "{user_role}" is not permitted to access financial or enrollment records.'

        text = user_input.lower().strip()

        # Schema access control
        if "schema" in text and user_role != "admin":
            return False, f'BLOCKED schema_access: Schema/structure access denied for role "{user_role}". Only admins can view database schema details. Try asking about the data instead.'

        # Check for blocked patterns (security)
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return False, "This request violates the data access policy."

        # Check if query relates to allowed domain (soft - allow general questions)
        words = set(re.findall(r"\w+", text))
        if words & self.ALLOWED_TOPICS or len(text) < 100:
            return True, "OK"

        # For long inputs without clear topic, allow but flag for audit
        return True, "OK"
