"""
Monitoring Layer Guardrail
Logs each and every piece of information through the request lifecycle to:
1. monitoring_logs table (Subabase) - persistent, queryable
2. JSONL file - local backup

Logs:
- Raw user input
- Filtration applied at each stage
- Guardrails invoked and their outcomes
- Tool calls allowed vs blocked
- Hallucination prevention
- Request outcome
"""
import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Thread-local storage
_lock = threading.Lock()
_LOG_DIR = Path(__file__).resolve().parent.parent.parent.parent / "logs"
_LOG_FILE = _LOG_DIR / "guardrail_monitor.jsonl"


def _ensure_log_dir():
    _LOG_DIR.mkdir(parents=True, exist_ok=True)


def _write_jsonl(entry: dict):
    """Append JSON line to local file backup."""
    _ensure_log_dir()
    with _lock:
        try:
            with open(_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str, ensure_ascii=False) + "\n")
        except Exception:
            pass


def _get_supabase():
    """Lazy import to avoid circular deps."""
    from app.db.subabase_client import get_supabase
    return get_supabase()


def _insert_monitoring_log(row: dict) -> bool:
    """Insert a row into monitoring_logs. Returns True on success."""
    try:
        sb = _get_supabase()
        sb.table("monitoring_logs").insert(row).execute()
        return True
    except Exception:
        return False


class MonitoringGuardrail:
    """
    Monitoring layer: comprehensive logging to Subabase monitoring_logs table.
    Logs user input, filtration, guardrails, tools allowed/blocked, hallucination prevention.
    """

    def __init__(self):
        self._log_file = _LOG_FILE
        self._use_db = True

    def _row(self, request_id: str, event: str, **kwargs) -> dict:
        """Build a row for monitoring_logs, excluding None values."""
        base = {
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": event,
        }
        for k, v in kwargs.items():
            if v is not None:
                base[k] = v
        return base

    def _log(self, row: dict):
        """Persist to DB and file."""
        if self._use_db:
            _insert_monitoring_log(row)
        _write_jsonl(row)

    def log_request_start(self, request_id: str, user_input: str, chat_history_len: int = 0):
        """Log the start of a request with raw user input."""
        row = self._row(
            request_id, "request_start",
            user_input_raw=user_input,
            user_input_length=len(user_input or ""),
            chat_history_length=chat_history_len,
        )
        self._log(row)

    def log_filtration(
        self,
        request_id: str,
        stage: str,
        filtration_type: str,
        original: Any = None,
        filtered: Any = None,
    ):
        """
        Log what filtration/sanitization was applied.
        stage: input | output | policy
        filtration_type: sanitized | blocked_validation | blocked_violation | truncated_or_sanitized
        """
        row = self._row(
            request_id, "filtration",
            stage=stage,
            filtration_type=filtration_type,
            original_preview=str(original)[:500] if original is not None else None,
            filtered_preview=str(filtered)[:500] if filtered is not None else None,
        )
        self._log(row)

    def log_guardrail_invoked(
        self,
        request_id: str,
        guardrail: str,
        passed: bool,
        message: Optional[str] = None,
        blocked: bool = False,
    ):
        """
        Log that a guardrail was invoked.
        guardrail: policy | input | instruction | execution | output | monitoring
        """
        row = self._row(
            request_id, "guardrail_invoked",
            guardrail=guardrail,
            passed=passed,
            blocked=blocked,
            guardrail_message=message,
        )
        self._log(row)

    def log_tool_call(
        self,
        request_id: str,
        tool_name: str,
        tool_input: dict,
        success: bool,
        allowed: bool = True,
        blocked_reason: Optional[str] = None,
        result_preview: Optional[str] = None,
    ):
        """
        Log a tool call - whether allowed or blocked.
        success: tool executed successfully
        allowed: tool was permitted by execution guardrail
        blocked_reason: if blocked, why
        """
        row = self._row(
            request_id, "tool_call",
            tool_name=tool_name,
            tool_input=tool_input,
            tool_allowed=allowed,
            tool_blocked_reason=blocked_reason,
            success=success,
            result_preview=(result_preview or "")[:500] if result_preview else None,
        )
        self._log(row)

    def log_tool_blocked(
        self,
        request_id: str,
        tool_name: str,
        tool_input: dict,
        reason: str,
    ):
        """Log when a tool was blocked by execution guardrail."""
        self.log_tool_call(
            request_id=request_id,
            tool_name=tool_name,
            tool_input=tool_input,
            success=False,
            allowed=False,
            blocked_reason=reason,
        )

    def log_hallucination_prevention(
        self,
        request_id: str,
        prevented: bool,
        details: Optional[str] = None,
        output_preview: Optional[str] = None,
    ):
        """Log when output guardrail prevented hallucination or unsafe content."""
        row = self._row(
            request_id, "hallucination_prevention",
            hallucination_prevented=prevented,
            hallucination_details=details,
            output_preview=(output_preview or "")[:500] if output_preview else None,
        )
        self._log(row)

    def log_request_end(
        self,
        request_id: str,
        success: bool,
        blocked_at: Optional[str] = None,
        output_preview: Optional[str] = None,
        tool_calls_count: int = 0,
        summary: Optional[dict] = None,
    ):
        """Log the end of a request with outcome summary."""
        row = self._row(
            request_id, "request_end",
            request_success=success,
            blocked_at=blocked_at,
            output_preview=(output_preview or "")[:500] if output_preview else None,
            tool_calls_count=tool_calls_count,
            summary=summary or {},
        )
        self._log(row)

    def get_log_path(self) -> Path:
        """Return path to the local JSONL log file."""
        return _LOG_FILE
