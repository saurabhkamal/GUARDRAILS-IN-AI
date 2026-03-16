"""
Input Layer Guardrail
Validates and sanitizes user input before passing to the LLM.
- Length limits
- Prompt injection detection
- PII detection (optional alert)
- Profanity / harmful content
"""
import re
from typing import Tuple


class InputGuardrail:
    """Input layer: sanitize and validate user input."""

    MAX_INPUT_LENGTH = 2000
    PROMPT_INJECTION_PATTERNS = [
        r"ignore\s+(previous|above|all)\s+instructions",
        r"disregard\s+(all|your)\s+instructions",
        r"you\s+are\s+now\s+",
        r"pretend\s+you\s+are",
        r"act\s+as\s+if\s+you\s+have",
        r"<\|[a-z_]+\|>",  # Special tokens
        r"system\s*:\s*",
        r"assistant\s*:\s*",
        r"\[INST\]",
        r"\[/INST\]",
    ]
    PROFANITY_BLOCKLIST = {"hack", "exploit", "bypass", "circumvent"}  # Extend as needed

    def check(self, user_input: str) -> Tuple[bool, str]:
        """
        Validate and sanitize input.
        Returns (allowed, sanitized_or_error_message).
        """
        if not user_input:
            return False, "Input cannot be empty."

        text = user_input.strip()

        # Length limit
        if len(text) > self.MAX_INPUT_LENGTH:
            return False, f"Input exceeds maximum length of {self.MAX_INPUT_LENGTH} characters."

        # Prompt injection detection
        lower = text.lower()
        for pattern in self.PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, lower):
                return False, "Input contains patterns that are not allowed."

        # Block explicitly harmful intent words in context
        words = set(re.findall(r"\w+", lower))
        if words & self.PROFANITY_BLOCKLIST and any(w in lower for w in ["system", "guardrail", "bypass"]):
            return False, "Input rejected by safety policy."

        return True, text
