"""
Instruction Layer Guardrail
Constrains the LLM system prompt and instructions.
- Scope: only answer questions about students, courses, transactions
- Output format constraints
- Refuse to perform unauthorized actions
"""
from typing import List

SYSTEM_INSTRUCTION = """You are an AI assistant with access to an educational database.
You can query information about students, courses, and transactions.

RULES:
- Only answer questions related to students, courses, enrollments, payments, and transactions.
- Use the provided tools to fetch data. Do NOT make up data.
- If a query cannot be answered with the database, say so clearly.
- Never attempt to modify, delete, or alter data. You have read-only access.
- Format numbers as currency (e.g., $1,234.56) when showing prices or amounts.
- Be concise and accurate. If data is not found, say "No matching records found."
"""


class InstructionGuardrail:
    """Instruction layer: system prompt and output constraints."""

    def get_system_prompt(self, user_role: str = "student") -> str:
        """Return the constrained system prompt for the LLM."""
        if user_role == "admin":
            return SYSTEM_INSTRUCTION + "\nYou are an administrator and have permission to view schema details."
        return SYSTEM_INSTRUCTION

    def get_output_constraints(self) -> List[str]:
        """Return rules for the LLM output format."""
        return [
            "Respond only in the context of the educational database.",
            "Do not invent student names, course codes, or transaction IDs.",
            "When showing tables, use clear formatting.",
        ]
