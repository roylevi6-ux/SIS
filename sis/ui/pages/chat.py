"""Conversational Interface — LLM-powered queries over pipeline data per PRD P0-13, P0-14.

Uses the query service to send natural language questions to the LLM with
full pipeline context. Supports follow-up questions via conversation history.
"""

from __future__ import annotations

import streamlit as st

from sis.services.query_service import query as llm_query
from sis.services.usage_tracking_service import track_event
from sis.services.user_action_log_service import log_action, ACTION_CHAT_QUERY
from sis.ui.components.layout import page_header


def render():
    page_header("Chat", "Ask questions about your pipeline, deals, and forecasts")

    # Initialize chat history
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # Display chat history
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask about your pipeline..."):
        track_event("chat_query")
        log_action(ACTION_CHAT_QUERY, action_detail=prompt[:200], page_name="Chat")
        with st.chat_message("user"):
            st.markdown(prompt)

        # Query LLM with history BEFORE appending current message (avoid duplicate)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = _process_query(prompt)
                st.markdown(response)

        # Append both to history AFTER the query
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        st.session_state.chat_messages.append({"role": "assistant", "content": response})

    # Suggested queries (3-col layout instead of 5-col)
    if not st.session_state.chat_messages:
        st.markdown("**Suggested queries:**")
        suggestions = [
            "Which deals are at risk?",
            "Show me the pipeline overview",
            "Which deals have divergent forecasts?",
            "Tell me about the highest health deal",
            "What's the team rollup?",
        ]
        row1 = st.columns(3)
        for i in range(3):
            with row1[i]:
                if st.button(suggestions[i], key=f"suggest_{i}", use_container_width=True):
                    with st.spinner("Thinking..."):
                        response = _process_query(suggestions[i])
                    st.session_state.chat_messages.append({"role": "user", "content": suggestions[i]})
                    st.session_state.chat_messages.append({"role": "assistant", "content": response})
                    st.rerun()
        row2 = st.columns(3)
        for i in range(3, 5):
            with row2[i - 3]:
                if st.button(suggestions[i], key=f"suggest_{i}", use_container_width=True):
                    with st.spinner("Thinking..."):
                        response = _process_query(suggestions[i])
                    st.session_state.chat_messages.append({"role": "user", "content": suggestions[i]})
                    st.session_state.chat_messages.append({"role": "assistant", "content": response})
                    st.rerun()


def _process_query(prompt: str) -> str:
    """Send query to LLM-powered query service with conversation history."""
    history = st.session_state.get("chat_messages", [])
    return llm_query(prompt, history=history)
