"""FastAPI backend for Guardrails in AI chat."""
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from app.agent.agent import GuardedAgent
from app.agent.guardrails.monitoring import MonitoringGuardrail

app = FastAPI(
    title="Guardrails in AI",
    description="Chat API with LangChain agent and database tools",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = GuardedAgent()


class ChatRequest(BaseModel):
    message: str
    chat_history: list = []
    user_role: str = "student"


class ChatResponse(BaseModel):
    success: bool
    message: str
    blocked_at: str | None = None
    guardrail_details: list = []
    execution_time_seconds: float = 0.0


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    result = agent.chat(req.message, req.chat_history, user_role=req.user_role)
    return ChatResponse(
        success=result["success"],
        message=result["message"],
        blocked_at=result.get("blocked_at"),
        guardrail_details=result.get("guardrail_details", []),
        execution_time_seconds=result.get("execution_time_seconds", 0.0),
    )


_monitor = MonitoringGuardrail()


@app.get("/logs", response_class=PlainTextResponse)
def get_logs(limit: int = 100):
    """Return recent monitoring log entries (JSONL from local file)."""
    log_path = _monitor.get_log_path()
    if not log_path.exists():
        return ""
    try:
        lines = log_path.read_text(encoding="utf-8").strip().split("\n")
        return "\n".join(lines[-limit:]) if lines else ""
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/monitoring-logs")
def get_monitoring_logs(limit: int = 100, request_id: str | None = None, event: str | None = None):
    """Fetch monitoring logs from Subabase monitoring_logs table."""
    try:
        from app.db.subabase_client import get_supabase
        sb = get_supabase()
        q = sb.table("monitoring_logs").select("*").order("created_at", desc=True).limit(limit)
        if request_id:
            q = q.eq("request_id", request_id)
        if event:
            q = q.eq("event", event)
        result = q.execute()
        return {"logs": result.data, "count": len(result.data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
