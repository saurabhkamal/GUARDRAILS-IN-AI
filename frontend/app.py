"""
Streamlit Chat Interface - Guardrails in AI
Connect to FastAPI backend with LangChain agent and database tools.
"""
import os
import streamlit as st
import requests
from pathlib import Path

# Load env
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

API_URL = os.getenv("API_URL", "http://localhost:8000")


def chat_api(message: str, chat_history: list, user_role: str) -> dict:
    try:
        r = requests.post(
            f"{API_URL}/chat",
            json={"message": message, "chat_history": chat_history, "user_role": user_role},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": f"Could not reach the API: {str(e)}. Is the backend running?",
            "blocked_at": None,
            "guardrail_details": [],
            "execution_time_seconds": 0.0,
        }


def main():
    st.set_page_config(
        page_title="Guardrails in AI | Database Chat",
        page_icon="🛡️",
        layout="centered",
    )

    st.title("🛡️ Guardrails in AI")
    st.caption("Chat with your Student & Course database. Powered by LangChain + AI.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    def _render_guardrail_details(details: list, exec_time: float = None):
        """Render Guardrail Details expander and execution time."""
        if details:
            with st.expander("📋 Guardrail Details"):
                for d in details:
                    status = "passed" if d.get("passed") else "blocked"
                    symbol = "✅" if d.get("passed") else "❌"
                    st.markdown(f"{symbol} **{d.get('layer', '')}** [{status}] {d.get('detail', '')}")
        if exec_time is not None:
            st.caption(f"⏱️ **Execution time:** {exec_time} seconds")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("blocked_at"):
                st.warning(f"⚠️ Blocked at: {msg['blocked_at']} layer")
            if msg["role"] == "assistant":
                _render_guardrail_details(msg.get("guardrail_details", []), msg.get("execution_time_seconds"))

    if prompt := st.chat_input("Ask about students, courses, or transactions..."):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                history = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages[:-1]
                ]
                result = chat_api(prompt, history, st.session_state.get("user_role", "student"))

            st.markdown(result["message"])
            if result.get("blocked_at"):
                st.warning(f"⚠️ Request blocked at: **{result['blocked_at']}** guardrail layer")
            _render_guardrail_details(result.get("guardrail_details", []), result.get("execution_time_seconds"))

        st.session_state.messages.append({
            "role": "assistant",
            "content": result["message"],
            "blocked_at": result.get("blocked_at"),
            "guardrail_details": result.get("guardrail_details", []),
            "execution_time_seconds": result.get("execution_time_seconds"),
        })

    with st.sidebar:
        st.session_state.user_role = st.selectbox("User Role", ["student", "admin", "viewer"])
        # st.subheader("About")
        st.subheader("Guardrail Layers")
        with st.expander("Policy Layer"):
            st.markdown("**Domain & Data access rules**")
            st.caption("Enforces allowed topics (students, courses, transactions) and blocks harmful intents (SQL injection, schema modification).")
        with st.expander("Input Layer"):
            st.markdown("**Sanitization & Prompt injection protection**")
            st.caption("Validates input length, detects prompt injection patterns, and blocks disallowed content.")
        with st.expander("Instruction Layer"):
            st.markdown("**LLM scope & output constraints**")
            st.caption("System prompt constrains the LLM to database scope only. No invented data, read-only access.")
        with st.expander("Execution Layer"):
            st.markdown("**Tool call validation & parameter checks**")
            st.caption("Validates tool names, limits, and filter parameters before execution. Prevents unauthorized operations.")
        with st.expander("Output Layer"):
            st.markdown("**Response sanitization & leak prevention**")
            st.caption("Checks for sensitive data, leaked internals, hallucination. Sanitizes output before user exposure.")
        with st.expander("Monitoring Layer"):
            st.markdown("**Request lifecycle logging & observability**")
            st.caption("Logs user input, filtration stages, guardrail outcomes, and tool calls to Subabase and JSONL.")
        st.divider()
        st.markdown("**Example questions**")
        st.code("How many active students are there?")
        st.code("List the top 5 courses by price")
        st.code("Show recent enrollment transactions")
        st.divider()
        log_view = st.radio("Log source", ["Local JSONL", "Subabase monitoring_logs"], horizontal=True)
        with st.expander("View Monitoring Logs"):
            try:
                if log_view == "Subabase monitoring_logs":
                    r = requests.get(f"{API_URL}/monitoring-logs", params={"limit": 50}, timeout=10)
                    r.raise_for_status()
                    data = r.json()
                    logs = data.get("logs", [])
                    if logs:
                        import json
                        st.json(logs)
                        st.caption(f"Showing {len(logs)} entries from monitoring_logs table")
                    else:
                        st.info("No monitoring logs yet. Run a chat query first.")
                else:
                    r = requests.get(f"{API_URL}/logs", params={"limit": 50}, timeout=10)
                    r.raise_for_status()
                    st.code(r.text or "(No logs yet)", language="json")
            except Exception as ex:
                st.error(f"Could not fetch logs: {ex}")


if __name__ == "__main__":
    main()
