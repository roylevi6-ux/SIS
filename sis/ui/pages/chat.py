"""Conversational Interface — LLM-powered queries over pipeline data per PRD P0-13, P0-14.

Uses the query service to send natural language questions to the LLM with
full pipeline context. Supports follow-up questions via conversation history.
"""

import streamlit as st

from sis.services.query_service import query as llm_query


def render():
    st.title("Chat — Pipeline Intelligence")
    st.caption("Ask questions about your pipeline, deals, and forecasts")

    # Initialize chat history
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # Display chat history
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask about your pipeline..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Process query via LLM
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = _process_query(prompt)
                st.markdown(response)
                st.session_state.chat_messages.append({"role": "assistant", "content": response})

    # Suggested queries
    if not st.session_state.chat_messages:
        st.markdown("**Suggested queries:**")
        suggestions = [
            "Which deals are at risk?",
            "Show me the pipeline overview",
            "Which deals have divergent forecasts?",
            "Tell me about the highest health deal",
            "What's the team rollup?",
        ]
        cols = st.columns(len(suggestions))
        for i, suggestion in enumerate(suggestions):
            with cols[i]:
                if st.button(suggestion, key=f"suggest_{i}", use_container_width=True):
                    response = _process_query(suggestion)
                    st.session_state.chat_messages.append({"role": "user", "content": suggestion})
                    st.session_state.chat_messages.append({"role": "assistant", "content": response})
                    st.rerun()


def _process_query(prompt: str) -> str:
    """Send query to LLM-powered query service with conversation history."""
    history = st.session_state.get("chat_messages", [])
    return llm_query(prompt, history=history)
