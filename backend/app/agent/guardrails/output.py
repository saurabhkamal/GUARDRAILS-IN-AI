"""
Output Layer Guardrail
Validates and filters LLM/agent output before returning to the user.
- PII masking (optional) or output sanitization
- Output length limits
- Block leakage of system prompts, tool internals, or unauthorized data
- Ensure response stays on-topic and safe
"""
import re
from typing import Tuple

# Patterns that indicate leaked internal content
LEAK_PATTERNS = [
    r"system\s*:\s*you\s+are",
    r"<\|[a-z_]+\|>",
    r"\[INST\]",
    r"\[/INST\]",
    r"tool_input\s*:",
    r"agent_scratchpad",
    r"internal\s+error\s+message",
    r"traceback\s*:",
    r"file\s*\"[^\"]+\"",
    r"langchain\.|langgraph\.|openai\.",
]

# Max characters in final output
MAX_OUTPUT_LENGTH = 10000


class OutputGuardrail:
    """Output layer: validate and sanitize agent output before user exposure."""

    def check(self, output: str, context: dict | None = None) -> Tuple[bool, str]:
        """
        Validate agent output before returning to user.
        Returns (allowed, sanitized_or_error_message).
        context: optional { "original_query": str } for relevance checks
        """
        if output is None:
            output = ""

        text = str(output).strip()

        # Empty output is allowed (e.g. tool-only response)
        if not text:
            return True, text

        # Length limit
        if len(text) > MAX_OUTPUT_LENGTH:
            text = text[:MAX_OUTPUT_LENGTH] + "\n\n[Output truncated due to length limit.]"

        # Check for leaked internal content
        lower = text.lower()
        for pattern in LEAK_PATTERNS:
            if re.search(pattern, lower):
                return False, "Output contains content that cannot be displayed."

        # Block raw SQL or code blocks that look like injection
        if re.search(r"delete\s+from|drop\s+table|truncate\s+table", lower):
            return False, "Output rejected: contains disallowed content."

        return True, text
