"""LangChain agent with Euron Euri AI (OpenAI-compatible) and guardrails."""
import os
import time
import uuid
from contextvars import ContextVar
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.runnables import RunnablePassthrough

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

load_dotenv(Path(__file__).resolve().parent.parent.parent.parent / ".env")

from app.agent.tools import get_all_tools, request_id_ctx, user_role_ctx
from app.agent.guardrails import (
    PolicyGuardrail,
    InputGuardrail,
    InstructionGuardrail,
    ExecutionGuardrail,
    OutputGuardrail,
    MonitoringGuardrail,
)


def get_llm():
    """Initialize LLM using Euron Euri API (OpenAI-compatible)."""
    api_key = os.getenv("EURON_API_KEY") or os.getenv("EURIAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("EURON_BASE_URL", "https://api.euron.one/api/v1/euri")
    model = os.getenv("LLM_MODEL", "gpt-4.1-nano")
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=0,
        max_tokens=8192,
    )


def create_agent(user_role: str = "student"):
    llm = get_llm()
    tools = get_all_tools()
    inst = InstructionGuardrail()

    prompt = ChatPromptTemplate.from_messages([
        ("system", inst.get_system_prompt(user_role=user_role)),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=5,
        handle_parsing_errors=True,
        return_intermediate_steps=True,
    )


class GuardedAgent:
    """Agent wrapped with all six guardrail layers and monitoring."""

    def __init__(self, user_role: str = "student"):
        self.policy = PolicyGuardrail()
        self.input_guard = InputGuardrail()
        self.instruction = InstructionGuardrail()
        self.execution = ExecutionGuardrail()
        self.output_guard = OutputGuardrail()
        self.monitoring = MonitoringGuardrail()
        self.agent_executor = create_agent(user_role=user_role)

    def _guardrail_detail(self, layer: str, passed: bool, detail: str) -> dict:
        return {"layer": layer, "passed": passed, "detail": detail}

    def chat(self, user_input: str, chat_history: list = None, request_id: str | None = None, user_role: str = "student") -> dict:
        """
        Process user input through guardrails and agent.
        Returns { "success": bool, "message": str, "blocked_at": str | None, "guardrail_details": list, "execution_time_seconds": float }
        """
        # Re-initialize agent if role changes (simplified for now)
        self.agent_executor = create_agent(user_role=user_role)

        start_time = time.perf_counter()
        rid = request_id or str(uuid.uuid4())
        chat_history = chat_history or []
        details: list = []

        # Set context for tool guardrails
        user_role_ctx.set(user_role)

        def elapsed() -> float:
            return round(time.perf_counter() - start_time, 3)

        # Monitoring: request start
        self.monitoring.log_request_start(rid, user_input, len(chat_history))

        # 1. Policy Layer
        ok, msg = self.policy.check(user_input, user_role=user_role)
        self.monitoring.log_guardrail_invoked(rid, "policy", ok, msg, blocked=not ok)
        if not ok:
            details.append(self._guardrail_detail("policy", False, f"domain_check: {msg}"))
            details.extend([
                self._guardrail_detail("input", False, "skipped (blocked at policy)"),
                self._guardrail_detail("instruction", False, "skipped (blocked at policy)"),
                self._guardrail_detail("execution", False, "skipped (blocked at policy)"),
                self._guardrail_detail("output", False, "skipped (blocked at policy)"),
                self._guardrail_detail("monitoring", False, "skipped (blocked at policy)"),
            ])
            self.monitoring.log_filtration(rid, "policy", "blocked_violation", user_input, None)
            self.monitoring.log_request_end(rid, False, "policy", msg, 0, {"reason": msg})
            return {"success": False, "message": msg, "blocked_at": "policy", "guardrail_details": details, "execution_time_seconds": elapsed(), "request_id": rid}

        details.append(self._guardrail_detail("policy", True, "domain_check: Request within allowed domain (students, courses, transactions)."))

        # 2. Input Layer (filtration)
        ok, result = self.input_guard.check(user_input)
        self.monitoring.log_guardrail_invoked(rid, "input", ok, result if not ok else None, blocked=not ok)
        if not ok:
            details.append(self._guardrail_detail("input", False, f"sanitization: {result}"))
            details.extend([
                self._guardrail_detail("instruction", False, "skipped (blocked at input)"),
                self._guardrail_detail("execution", False, "skipped (blocked at input)"),
                self._guardrail_detail("output", False, "skipped (blocked at input)"),
                self._guardrail_detail("monitoring", False, "skipped (blocked at input)"),
            ])
            self.monitoring.log_filtration(rid, "input", "blocked_validation", user_input, None)
            self.monitoring.log_request_end(rid, False, "input", result, 0, {"reason": result})
            return {"success": False, "message": result, "blocked_at": "input", "guardrail_details": details, "execution_time_seconds": elapsed(), "request_id": rid}

        details.append(self._guardrail_detail("input", True, "sanitization: No prompt injection patterns detected. Input within length limits."))
        sanitized_input = result
        self.monitoring.log_filtration(rid, "input", "sanitized", user_input, sanitized_input)

        # 3. Instruction layer is applied via system prompt in agent
        self.monitoring.log_guardrail_invoked(rid, "instruction", True, "applied via system prompt")
        details.append(self._guardrail_detail("instruction", True, "scope_constraints: System prompt applied - LLM constrained to database scope."))

        # 4. Execution layer is applied inside each tool
        try:
            request_id_ctx.set(rid)
            response = self.agent_executor.invoke({
                "input": sanitized_input,
                "chat_history": chat_history,
            })
            raw_output = response.get("output", "")
            steps = response.get("intermediate_steps", [])

            # Log tool calls (allowed & executed)
            for s in steps:
                action = s[0] if len(s) > 0 else None
                tool_name = getattr(action, "tool", None) or getattr(action, "name", "unknown")
                tool_input = getattr(action, "tool_input", None) or getattr(action, "input", {}) or {}
                if not isinstance(tool_input, dict):
                    tool_input = {"input": str(tool_input)[:200]}
                result_preview = str(s[1])[:500] if len(s) > 1 else None
                self.monitoring.log_tool_call(rid, str(tool_name), tool_input, True, allowed=True, result_preview=result_preview)

            details.append(self._guardrail_detail("execution", True, "tool_validation: All tool calls validated. No unauthorized tools or parameters."))

            # 5. Output Layer
            ok, filtered_output = self.output_guard.check(raw_output, {"original_query": sanitized_input})
            self.monitoring.log_guardrail_invoked(rid, "output", ok, None, blocked=not ok)
            if not ok:
                details.append(self._guardrail_detail("output", False, "sensitive_data: Output blocked - contains disallowed content or leaked internal patterns."))
                details.append(self._guardrail_detail("monitoring", False, "skipped (blocked at output)"))
                self.monitoring.log_filtration(rid, "output", "blocked_unsafe_content", raw_output[:200], None)
                self.monitoring.log_hallucination_prevention(
                    rid, prevented=True,
                    details="Output contained leaked/internal content or disallowed patterns - blocked",
                    output_preview=raw_output[:200],
                )
                self.monitoring.log_request_end(rid, False, "output", filtered_output, len(steps), {"reason": "Output rejected"})
                return {"success": False, "message": filtered_output, "blocked_at": "output", "guardrail_details": details, "execution_time_seconds": elapsed(), "request_id": rid}

            details.append(self._guardrail_detail("output", True, "sensitive_data: No sensitive data patterns detected in output."))
            details.append(self._guardrail_detail("output", True, "hallucination_detection: No hallucination indicators found."))
            if raw_output != filtered_output:
                self.monitoring.log_filtration(rid, "output", "truncated_or_sanitized", raw_output[:200], filtered_output[:200])
                self.monitoring.log_hallucination_prevention(rid, prevented=True, details="Output truncated/sanitized due to length or safety")

            # 6. Monitoring (invoked throughout; log completion)
            self.monitoring.log_guardrail_invoked(rid, "monitoring", True, "logged full lifecycle")
            details.append(self._guardrail_detail("monitoring", True, "lifecycle_logging: Full request lifecycle logged to monitoring layer."))

            self.monitoring.log_request_end(
                rid,
                True,
                None,
                filtered_output,
                len(steps),
                {"guardrails_passed": ["policy", "input", "instruction", "execution", "output", "monitoring"]},
            )
            return {
                "success": True,
                "message": filtered_output,
                "blocked_at": None,
                "guardrail_details": details,
                "execution_time_seconds": elapsed(),
                "request_id": rid,
            }
        except Exception as e:
            details.append(self._guardrail_detail("execution", False, f"tool_validation: {str(e)[:200]}"))
            details.extend([
                self._guardrail_detail("output", False, "skipped (blocked at execution)"),
                self._guardrail_detail("monitoring", False, "skipped (blocked at execution)"),
            ])
            self.monitoring.log_guardrail_invoked(rid, "execution", False, str(e), blocked=True)
            self.monitoring.log_request_end(rid, False, "execution", str(e), 0, {"error": str(e)})
            return {
                "success": False,
                "message": f"An error occurred: {str(e)}",
                "blocked_at": "execution",
                "guardrail_details": details,
                "execution_time_seconds": elapsed(),
                "request_id": rid,
            }
