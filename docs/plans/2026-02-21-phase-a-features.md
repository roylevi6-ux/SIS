# Phase A Features Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make SIS usable by TLs and VP — LLM-powered chat, IC forecast entry, meeting prep, deal briefs.

**Architecture:** Each feature is a service function + FastAPI route + Next.js UI page. The query service uses the Anthropic client (via `sis/agents/runner.py:get_client()`) to translate natural language into structured DB queries, format the results, and return them. No new agents — these features layer on top of existing pipeline data.

**Tech Stack:** Anthropic Claude (via proxy), Next.js (frontend), FastAPI (API), SQLAlchemy, Pydantic, existing service layer.

> [!NOTE]
> Code samples below were written for the original Streamlit POC. The actual implementation uses Next.js + FastAPI. Service layer code (`sis/services/`) remains the same; only the UI layer has changed.

---

### Task 1: Query Service — LLM-Powered Chat Backend

**Files:**
- Create: `sis/services/query_service.py`
- Modify: `sis/ui/pages/chat.py`
- Modify: `sis/services/__init__.py`

**Context:** The current chat page (`chat.py`) uses keyword matching (`if "at risk" in query_lower`). The spec requires LLM-powered natural language queries (P0-13, P0-14, Section 6.5). The query service should:
1. Gather all pipeline data (accounts, assessments, rollups) into a context string
2. Send context + user query + conversation history to the LLM
3. Return the LLM's formatted answer

This is a structured query layer over stored data — NOT re-running the pipeline per query.

**Step 1: Create `sis/services/query_service.py`**

```python
"""Query service — LLM-powered conversational interface per Section 6.5."""

import json
import anthropic
from sis.config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, MODEL_CHAT
from sis.services.account_service import list_accounts, get_account_detail
from sis.services.dashboard_service import get_pipeline_overview, get_divergence_report, get_team_rollup

SYSTEM_PROMPT = """You are the SIS (Sales Intelligence System) assistant for Riskified's sales team.
You answer questions about deal health, pipeline status, forecasts, and team performance.

You have access to structured pipeline data provided below. Answer based ONLY on this data.
If the data does not contain the answer, say so — never hallucinate.

Rules:
- Be concise and specific. Use bullet points for lists.
- Reference deal names, scores, and categories exactly as shown in the data.
- When comparing deals, cite specific health scores and momentum directions.
- If asked about a specific deal, include: health score, stage, momentum, forecast, top risks.
- For pipeline questions, summarize by health tier (Healthy 70+, At Risk 45-69, Critical <45).
- When asked about forecast divergence, explain both AI and IC categories and the delta.
"""

def _build_context() -> str:
    """Build a context string with all pipeline data for the LLM."""
    # accounts with assessments
    accounts = list_accounts()
    overview = get_pipeline_overview()
    divergences = get_divergence_report()
    rollup = get_team_rollup()

    sections = []
    sections.append("## Pipeline Summary")
    s = overview["summary"]
    sections.append(f"Total: {overview['total_deals']} deals | "
                    f"Healthy: {s['healthy_count']} (${s['total_mrr_healthy']:,.0f}) | "
                    f"At Risk: {s['at_risk_count']} (${s['total_mrr_at_risk']:,.0f}) | "
                    f"Critical: {s['critical_count']} (${s['total_mrr_critical']:,.0f})")

    sections.append("\n## All Deals")
    for a in accounts:
        hs = a.get('health_score', 'N/A')
        mom = a.get('momentum_direction', 'N/A')
        ai_fc = a.get('ai_forecast_category', 'N/A')
        ic_fc = a.get('ic_forecast_category', 'Not set')
        stage = f"{a.get('inferred_stage', '?')} ({a.get('stage_name', 'N/A')})"
        mrr = f"${a['mrr_estimate']:,.0f}" if a.get('mrr_estimate') else 'N/A'
        div = " [DIVERGENT]" if a.get('divergence_flag') else ""
        sections.append(
            f"- {a['account_name']}: Health={hs}, Momentum={mom}, "
            f"Stage={stage}, AI={ai_fc}, IC={ic_fc}, MRR={mrr}, "
            f"TL={a.get('team_lead','N/A')}{div}"
        )

    if divergences:
        sections.append("\n## Divergent Forecasts")
        for d in divergences:
            sections.append(
                f"- {d['account_name']}: AI={d['ai_forecast_category']}, "
                f"IC={d['ic_forecast_category']}, MRR=${d.get('mrr_estimate',0):,.0f}"
            )

    if rollup:
        sections.append("\n## Team Rollup")
        for t in rollup:
            avg = f"{t['avg_health_score']:.0f}" if t.get('avg_health_score') else "N/A"
            sections.append(
                f"- {t['team_name']}: {t['total_deals']} deals, "
                f"Avg Health={avg}, MRR=${t['total_mrr']:,.0f}, "
                f"Divergent={t.get('divergent_count', 0)}"
            )

    return "\n".join(sections)


def query(user_message: str, history: list[dict] | None = None) -> str:
    """Process a natural language query about the pipeline.

    Args:
        user_message: The user's question.
        history: Previous messages as [{"role": "user"|"assistant", "content": str}].

    Returns:
        The LLM's answer as a string.
    """
    context = _build_context()

    messages = []
    # Include conversation history for follow-ups (P0-14)
    if history:
        # Keep last 10 messages to stay within context limits
        for msg in history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

    # Current query with injected context
    messages.append({
        "role": "user",
        "content": f"<pipeline_data>\n{context}\n</pipeline_data>\n\n{user_message}",
    })

    client = anthropic.Anthropic(
        api_key=ANTHROPIC_API_KEY,
        base_url=ANTHROPIC_BASE_URL,
        timeout=60.0,
        max_retries=1,
    )

    response = client.messages.create(
        model=MODEL_CHAT,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=messages,
    )

    return response.content[0].text
```

**Step 2: Update `sis/services/__init__.py`**

Add `from . import query_service` to the imports.

**Step 3: Update `sis/ui/pages/chat.py`**

Replace `_process_query()` with a call to `query_service.query()`, passing conversation history for follow-up context:

```python
from sis.services.query_service import query as llm_query

def _process_query(prompt: str) -> str:
    """Send query to LLM-powered query service with conversation history."""
    # Pass prior messages for follow-up context (P0-14)
    history = st.session_state.get("chat_messages", [])
    return llm_query(prompt, history=history)
```

Remove all the keyword-matching logic (`if any(kw in query_lower...)`).

**Step 4: Verify**

Run: `python3 -c "from sis.services.query_service import query; print('Query service imports OK')"`

**Step 5: Commit**

```bash
git add sis/services/query_service.py sis/services/__init__.py sis/ui/pages/chat.py
git commit -m "feat: LLM-powered query service replaces keyword chat (P0-13, P0-14)"
```

---

### Task 2: IC Forecast Entry UI

**Files:**
- Modify: `sis/ui/pages/pipeline_overview.py`
- Modify: `sis/ui/app.py` (add new page to nav)

**Context:** `account_service.set_ic_forecast()` already exists and computes divergence. We just need a UI for TLs/VP to enter IC forecasts per deal. Per spec P0-8c, this is entered SEPARATELY from the scoring pipeline.

**Step 1: Add IC forecast entry to pipeline overview page**

Add an expandable section below each deal in `pipeline_overview.py` that lets the user set the IC forecast category via a selectbox:

```python
# Inside the deal rendering loop, after column c6:
with st.expander("Set IC Forecast", expanded=False):
    categories = ["", "Commit", "Best Case", "Pipeline", "Upside", "At Risk", "No Decision Risk"]
    current_ic = deal.get("ic_forecast_category") or ""
    current_idx = categories.index(current_ic) if current_ic in categories else 0
    new_ic = st.selectbox(
        "IC Forecast",
        categories,
        index=current_idx,
        key=f"ic_{deal['account_id']}",
        label_visibility="collapsed",
    )
    if new_ic and new_ic != current_ic:
        if st.button("Save", key=f"save_ic_{deal['account_id']}"):
            from sis.services.account_service import set_ic_forecast
            result = set_ic_forecast(deal["account_id"], new_ic)
            if result["divergence_flag"]:
                st.warning(f"Divergence detected: {result['explanation'][:100]}")
            else:
                st.success("IC forecast saved. Matches AI forecast.")
            st.rerun()
```

**Step 2: Verify**

Import check: `python3 -c "from sis.ui.pages.pipeline_overview import render; print('OK')"`

**Step 3: Commit**

```bash
git add sis/ui/pages/pipeline_overview.py
git commit -m "feat: IC forecast entry UI on pipeline overview (P0-8c)"
```

---

### Task 3: Meeting Prep Mode Page

**Files:**
- Create: `sis/ui/pages/meeting_prep.py`
- Modify: `sis/ui/app.py` (add to nav)

**Context:** Per P0-24, this is a pre-call brief that pulls from the latest deal assessment: key topics to raise, questions to ask (from risk flags), risks to probe, unresolved items. Distinct from deal brief (P0-19).

**Step 1: Create `sis/ui/pages/meeting_prep.py`**

```python
"""Meeting Prep Mode — pre-call brief per PRD P0-24.

Generates a preparation guide for upcoming prospect calls using
the latest deal assessment: topics, questions, risks, unresolved items.
"""

import json
import streamlit as st

from sis.services.account_service import list_accounts, get_account_detail


def render():
    st.title("Meeting Prep")
    st.caption("Pre-call brief for upcoming prospect meetings")

    accounts = list_accounts()
    if not accounts:
        st.info("No accounts yet. Create one in Upload Transcript.")
        return

    # Account selector
    scored = [a for a in accounts if a.get("health_score") is not None]
    if not scored:
        st.info("No scored accounts. Run analysis first.")
        return

    names = [a["account_name"] for a in scored]
    selected = st.selectbox("Select Account", names)
    account = scored[names.index(selected)]
    detail = get_account_detail(account["id"])
    assessment = detail.get("assessment")

    if not assessment:
        st.warning(f"No assessment for {account['account_name']}.")
        return

    st.divider()

    # Header
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Health Score", f"{assessment['health_score']}/100")
    with col2:
        st.metric("Stage", f"{assessment['inferred_stage']} — {assessment['stage_name']}")
    with col3:
        st.metric("Momentum", assessment["momentum_direction"])

    st.divider()

    # 1. Key Topics to Raise (from risks and low-scoring components)
    st.subheader("Key Topics to Raise")
    breakdown = assessment.get("health_breakdown", [])
    if isinstance(breakdown, list):
        weak = [c for c in breakdown if isinstance(c, dict) and c.get("score", 100) < c.get("max_score", 20) * 0.5]
        if weak:
            for comp in weak:
                st.markdown(f"- **{comp.get('component', 'Unknown')}** "
                           f"({comp.get('score', 0)}/{comp.get('max_score', 20)}): "
                           f"{comp.get('rationale', '')}")
        else:
            st.markdown("No weak components identified.")

    # 2. Questions to Ask (from key unknowns + risk flags)
    st.subheader("Questions to Ask")
    unknowns = assessment.get("key_unknowns", [])
    risks = assessment.get("top_risks", [])
    questions = []
    for u in unknowns:
        questions.append(f"Clarify: {u}")
    for r in risks[:3]:
        if isinstance(r, dict):
            questions.append(f"Probe risk: {r.get('risk', str(r))}")
        else:
            questions.append(f"Probe: {r}")

    if questions:
        for q in questions:
            st.markdown(f"- {q}")
    else:
        st.markdown("No specific questions identified from the analysis.")

    # 3. Risks to Watch
    st.subheader("Risks to Watch During Call")
    if risks:
        for r in risks:
            if isinstance(r, dict):
                sev = r.get("severity", "")
                risk_text = r.get("risk", str(r))
                st.markdown(f"- **[{sev}]** {risk_text}")
            else:
                st.markdown(f"- {r}")
    else:
        st.markdown("No significant risks flagged.")

    # 4. Recommended Actions (from synthesis)
    st.subheader("Actions to Follow Up On")
    actions = assessment.get("recommended_actions", [])
    if actions:
        for a in actions:
            if isinstance(a, dict):
                st.markdown(f"- **{a.get('owner', 'TBD')}**: {a.get('action', str(a))}")
            else:
                st.markdown(f"- {a}")
    else:
        st.markdown("No pending actions.")

    # 5. Positive signals to leverage
    st.subheader("Positive Signals to Leverage")
    signals = assessment.get("top_positive_signals", [])
    if signals:
        for s in signals[:3]:
            if isinstance(s, dict):
                st.markdown(f"- {s.get('signal', str(s))}")
            else:
                st.markdown(f"- {s}")
    else:
        st.markdown("No strong positive signals detected.")
```

**Step 2: Add to `sis/ui/app.py`**

Add `"Meeting Prep"` to the PAGES list (after "Run Analysis"), and add the routing:

```python
elif page == "Meeting Prep":
    from sis.ui.pages.meeting_prep import render
    render()
```

**Step 3: Verify**

`python3 -c "from sis.ui.pages.meeting_prep import render; print('OK')"`

**Step 4: Commit**

```bash
git add sis/ui/pages/meeting_prep.py sis/ui/app.py
git commit -m "feat: meeting prep mode — pre-call brief page (P0-24)"
```

---

### Task 4: Deal Brief Page with 3-Format Selector

**Files:**
- Create: `sis/ui/pages/deal_brief.py`
- Modify: `sis/ui/app.py` (add to nav)

**Context:** Export service already has `export_deal_brief()` with 3 formats (structured, narrative, inspection). We need a UI page that lets users select an account, choose a format, view the brief, and copy/download.

**Step 1: Create `sis/ui/pages/deal_brief.py`**

```python
"""Deal Brief — 3-format deal brief per PRD P0-19.

Generates exportable deal briefs in three styles:
1. Structured one-pager (fixed template)
2. Narrative memo (3-5 paragraphs + structured fields)
3. Inspection questions (3-5 questions with evidence)
"""

import streamlit as st

from sis.services.account_service import list_accounts
from sis.services.export_service import export_deal_brief


def render():
    st.title("Deal Brief")
    st.caption("One-page deal brief for pipeline review prep — 3 formats")

    accounts = list_accounts()
    scored = [a for a in accounts if a.get("health_score") is not None]

    if not scored:
        st.info("No scored accounts. Run analysis first.")
        return

    col1, col2 = st.columns([2, 1])
    with col1:
        names = [a["account_name"] for a in scored]
        selected = st.selectbox("Select Account", names)
        account = scored[names.index(selected)]

    with col2:
        format_labels = {
            "structured": "Structured One-Pager",
            "narrative": "Narrative Memo",
            "inspection": "Inspection Questions",
        }
        chosen_format = st.radio(
            "Brief Format",
            list(format_labels.keys()),
            format_func=lambda x: format_labels[x],
        )

    st.divider()

    # Generate brief
    brief = export_deal_brief(account["id"], format=chosen_format)

    # Display
    st.markdown(brief)

    # Download button
    st.divider()
    st.download_button(
        label="Download as Markdown",
        data=brief,
        file_name=f"deal-brief-{account['account_name'].lower().replace(' ', '-')}.md",
        mime="text/markdown",
    )
```

**Step 2: Add to `sis/ui/app.py`**

Add `"Deal Brief"` to PAGES (after "Deal Detail") and add routing:

```python
elif page == "Deal Brief":
    from sis.ui.pages.deal_brief import render
    render()
```

**Step 3: Verify**

`python3 -c "from sis.ui.pages.deal_brief import render; print('OK')"`

**Step 4: Commit**

```bash
git add sis/ui/pages/deal_brief.py sis/ui/app.py
git commit -m "feat: deal brief page with 3-format selector (P0-19)"
```

---

### Task 5: Final Integration — Update App Navigation

**Files:**
- Modify: `sis/ui/app.py`

**Context:** All 4 features need to be reflected in the sidebar navigation with logical grouping.

**Step 1: Update PAGES list and routing in `app.py`**

Final PAGES list should be:

```python
PAGES = [
    "Pipeline Overview",
    "Deal Detail",
    "Deal Brief",
    "Divergence View",
    "Team Rollup",
    "Meeting Prep",
    "Upload Transcript",
    "Run Analysis",
    "Chat",
    "Feedback Dashboard",
    "Cost Monitor",
]
```

**Step 2: Verify all imports**

```bash
python3 -c "
from sis.services.query_service import query
from sis.services.export_service import export_deal_brief, export_forecast_report
from sis.ui.pages.meeting_prep import render as mp_render
from sis.ui.pages.deal_brief import render as db_render
print('All Phase A imports OK')
"
```

**Step 3: Final commit**

```bash
git add sis/ui/app.py
git commit -m "feat: Phase A complete — navigation updated with all new pages"
```

---

## Execution Summary

| Task | Feature | PRD Req | Files | Est. Time |
|------|---------|---------|-------|-----------|
| 1 | LLM-powered query service | P0-13, P0-14 | query_service.py, chat.py | 5 min |
| 2 | IC forecast entry UI | P0-8c | pipeline_overview.py | 3 min |
| 3 | Meeting prep mode | P0-24 | meeting_prep.py, app.py | 3 min |
| 4 | Deal brief 3 formats | P0-19 | deal_brief.py, app.py | 3 min |
| 5 | Navigation integration | — | app.py | 2 min |
