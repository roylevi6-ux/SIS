"""Analysis service — run pipeline, persist results per Technical Architecture Section 6.1."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sis.db.session import get_session
from sis.db.models import AnalysisRun, AgentAnalysis, DealAssessment
from sis.orchestrator.pipeline import AnalysisPipeline, PipelineResult
from sis.services.transcript_service import get_active_transcript_texts, get_active_transcript_ids

logger = logging.getLogger(__name__)

# Agent ID to human name mapping
AGENT_NAMES = {
    "agent_1": "Stage & Progress",
    "agent_2": "Relationship & Power Map",
    "agent_3": "Commercial & Risk",
    "agent_4": "Momentum & Engagement",
    "agent_5": "Technical Validation",
    "agent_6": "Economic Buyer",
    "agent_7": "MSP & Next Steps",
    "agent_8": "Competitive Displacement",
    "agent_9": "Open Discovery",
    "agent_10": "Synthesis",
}


def analyze_account(
    account_id: str,
    progress_callback=None,
) -> dict:
    """Run the full 10-agent pipeline for one account.

    Returns:
        dict with run_id, status, deal_assessment summary, cost
    """
    # Get transcript texts
    transcript_texts = get_active_transcript_texts(account_id)
    if not transcript_texts:
        raise ValueError(f"No active transcripts for account {account_id}")

    # Run pipeline
    pipeline = AnalysisPipeline(progress_callback=progress_callback)
    result = pipeline.run(account_id, transcript_texts)

    # Persist to DB
    transcript_ids = get_active_transcript_ids(account_id)
    run_id = _persist_pipeline_result(account_id, result, transcript_texts, transcript_ids)
    result.run_id = run_id

    return {
        "run_id": run_id,
        "status": result.status,
        "wall_clock_seconds": round(result.wall_clock_seconds, 1),
        "total_cost_usd": round(result.cost_summary.total_cost_usd, 4),
        "agents_completed": len(result.agent_outputs),
        "agents_total": 10,
        "errors": result.errors,
        "validation_warnings": result.validation_warnings,
    }


async def analyze_account_async(
    account_id: str,
    progress_callback=None,
) -> dict:
    """Async version of analyze_account."""
    transcript_texts = get_active_transcript_texts(account_id)
    if not transcript_texts:
        raise ValueError(f"No active transcripts for account {account_id}")

    pipeline = AnalysisPipeline(progress_callback=progress_callback)
    result = await pipeline.run_async(account_id, transcript_texts)

    transcript_ids = get_active_transcript_ids(account_id)
    run_id = _persist_pipeline_result(account_id, result, transcript_texts, transcript_ids)
    result.run_id = run_id

    return {
        "run_id": run_id,
        "status": result.status,
        "wall_clock_seconds": round(result.wall_clock_seconds, 1),
        "total_cost_usd": round(result.cost_summary.total_cost_usd, 4),
        "agents_completed": len(result.agent_outputs),
        "agents_total": 10,
        "errors": result.errors,
        "validation_warnings": result.validation_warnings,
    }


def _persist_pipeline_result(
    account_id: str,
    result: PipelineResult,
    transcript_texts: list[str],
    transcript_ids: list[str] | None = None,
) -> str:
    """Persist pipeline results to DB. Returns run_id."""
    with get_session() as session:
        # Create analysis run record
        run = AnalysisRun(
            account_id=account_id,
            started_at=result.started_at,
            completed_at=result.completed_at,
            status=result.status,
            transcript_ids=json.dumps(transcript_ids) if transcript_ids else None,
            total_input_tokens=result.cost_summary.total_input_tokens,
            total_output_tokens=result.cost_summary.total_output_tokens,
            total_cost_usd=result.cost_summary.total_cost_usd,
            model_versions=json.dumps({
                agent_id: meta.get("model", "unknown")
                for agent_id, meta in result.agent_metadata.items()
            }),
            error_log=json.dumps(result.errors) if result.errors else None,
        )
        session.add(run)
        session.flush()

        # Persist individual agent analyses (agents 1-9)
        for agent_id, output_dict in result.agent_outputs.items():
            meta = result.agent_metadata.get(agent_id, {})
            agent_analysis = AgentAnalysis(
                analysis_run_id=run.id,
                account_id=account_id,
                agent_id=agent_id,
                agent_name=AGENT_NAMES.get(agent_id, agent_id),
                transcript_count_analyzed=output_dict.get("transcript_count_analyzed"),
                narrative=output_dict.get("narrative", ""),
                findings=json.dumps(output_dict.get("findings", {})),
                evidence=json.dumps(output_dict.get("evidence", [])),
                confidence_overall=output_dict.get("confidence", {}).get("overall"),
                confidence_rationale=output_dict.get("confidence", {}).get("rationale"),
                data_gaps=json.dumps(output_dict.get("confidence", {}).get("data_gaps", [])),
                sparse_data_flag=1 if output_dict.get("sparse_data_flag") else 0,
                input_tokens=meta.get("input_tokens"),
                output_tokens=meta.get("output_tokens"),
                cost_usd=None,  # calculated from cost_summary
                model_used=meta.get("model"),
                retries=meta.get("attempts", 1) - 1,
            )
            session.add(agent_analysis)

        # Persist synthesis as DealAssessment
        if result.synthesis_output:
            syn = result.synthesis_output
            assessment = DealAssessment(
                analysis_run_id=run.id,
                account_id=account_id,
                deal_memo=syn.get("deal_memo", ""),
                contradiction_map=json.dumps(syn.get("contradiction_map", [])),
                inferred_stage=syn.get("inferred_stage", 0),
                stage_name=syn.get("inferred_stage_name", ""),
                stage_confidence=syn.get("inferred_stage_confidence", 0.0),
                health_score=syn.get("health_score", 0),
                health_breakdown=json.dumps(syn.get("health_score_breakdown", [])),
                overall_confidence=syn.get("confidence_interval", {}).get("overall_confidence", 0.0),
                confidence_rationale=syn.get("confidence_interval", {}).get("rationale"),
                key_unknowns=json.dumps(syn.get("confidence_interval", {}).get("key_unknowns", [])),
                momentum_direction=syn.get("momentum_direction", "Unknown"),
                momentum_trend=syn.get("momentum_trend"),
                ai_forecast_category=syn.get("forecast_category", "Pipeline"),
                forecast_confidence=None,
                forecast_rationale=syn.get("forecast_rationale"),
                top_positive_signals=json.dumps(syn.get("top_positive_signals", [])),
                top_risks=json.dumps(syn.get("top_risks", [])),
                recommended_actions=json.dumps(syn.get("recommended_actions", [])),
            )
            session.add(assessment)

        session.flush()
        return run.id


def get_carry_forward_actions(account_id: str) -> list[dict]:
    """Compare recommended actions across the two most recent runs.

    Returns actions from the previous run that were NOT addressed in the
    current run (i.e. no similar action appears in the latest assessment).
    Each returned dict has the original action fields plus a 'status' of
    'unfollowed'.
    """
    with get_session() as session:
        assessments = (
            session.query(DealAssessment)
            .filter_by(account_id=account_id)
            .order_by(DealAssessment.created_at.desc())
            .limit(2)
            .all()
        )
        if len(assessments) < 2:
            return []

        current_actions = json.loads(assessments[0].recommended_actions or "[]")
        previous_actions = json.loads(assessments[1].recommended_actions or "[]")

    if not previous_actions:
        return []

    # Build set of current action texts (lowered) for fuzzy matching
    current_texts = {
        a.get("action", "").lower().strip()
        for a in current_actions
        if isinstance(a, dict)
    }

    unfollowed = []
    for prev in previous_actions:
        if not isinstance(prev, dict):
            continue
        prev_text = prev.get("action", "").lower().strip()
        # Check if a similar action exists in the current run
        if not any(_action_similar(prev_text, ct) for ct in current_texts):
            unfollowed.append({**prev, "status": "unfollowed"})

    return unfollowed


def _action_similar(a: str, b: str) -> bool:
    """Simple similarity check — shared significant words."""
    if not a or not b:
        return False
    words_a = set(a.split()) - {"the", "a", "an", "to", "and", "or", "of", "for", "with"}
    words_b = set(b.split()) - {"the", "a", "an", "to", "and", "or", "of", "for", "with"}
    if not words_a or not words_b:
        return False
    overlap = len(words_a & words_b)
    return overlap / min(len(words_a), len(words_b)) >= 0.5


def get_analysis_history(account_id: str) -> list[dict]:
    """Get all analysis runs for an account, most recent first."""
    with get_session() as session:
        runs = (
            session.query(AnalysisRun)
            .filter_by(account_id=account_id)
            .order_by(AnalysisRun.started_at.desc())
            .all()
        )
        return [
            {
                "run_id": r.id,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
                "status": r.status,
                "total_cost_usd": r.total_cost_usd,
                "total_input_tokens": r.total_input_tokens,
                "total_output_tokens": r.total_output_tokens,
            }
            for r in runs
        ]


def get_latest_run_id(account_id: str) -> str | None:
    """Get the latest analysis run ID for an account."""
    with get_session() as session:
        latest = (
            session.query(DealAssessment)
            .filter_by(account_id=account_id)
            .order_by(DealAssessment.created_at.desc())
            .first()
        )
        return latest.analysis_run_id if latest else None


def get_agent_analyses(run_id: str) -> list[dict]:
    """Get all agent analyses for a specific run."""
    with get_session() as session:
        analyses = (
            session.query(AgentAnalysis)
            .filter_by(analysis_run_id=run_id)
            .order_by(AgentAnalysis.agent_id)
            .all()
        )
        return [
            {
                "agent_id": a.agent_id,
                "agent_name": a.agent_name,
                "narrative": a.narrative,
                "findings": json.loads(a.findings) if a.findings else {},
                "evidence": json.loads(a.evidence) if a.evidence else [],
                "confidence_overall": a.confidence_overall,
                "confidence_rationale": a.confidence_rationale,
                "data_gaps": json.loads(a.data_gaps) if a.data_gaps else [],
                "sparse_data_flag": bool(a.sparse_data_flag),
                "model_used": a.model_used,
                "input_tokens": a.input_tokens,
                "output_tokens": a.output_tokens,
                "status": a.status,
            }
            for a in analyses
        ]


def rerun_agent(run_id: str, agent_id: str) -> dict:
    """Re-run a single agent for an existing analysis run.

    Retrieves the original transcripts and stage context, re-executes the
    specified agent, and updates the stored AgentAnalysis row.

    Per Technical Architecture Section 6.1 — supports selective re-execution
    without re-running the full pipeline.

    Returns:
        dict with updated agent analysis data
    """
    import asyncio
    import time
    from sis.agents.runner import run_agent_async
    from sis.validation import validate_agent_output

    # Agent ID to builder mapping (lazy imports)
    AGENT_BUILDERS = {
        "agent_1": ("sis.agents.stage_classifier", "build_call"),
        "agent_2": ("sis.agents.relationship", "build_call"),
        "agent_3": ("sis.agents.commercial", "build_call"),
        "agent_4": ("sis.agents.momentum", "build_call"),
        "agent_5": ("sis.agents.technical", "build_call"),
        "agent_6": ("sis.agents.economic_buyer", "build_call"),
        "agent_7": ("sis.agents.msp_next_steps", "build_call"),
        "agent_8": ("sis.agents.competitive", "build_call"),
    }

    if agent_id not in AGENT_BUILDERS:
        raise ValueError(f"Cannot rerun {agent_id}. Only agents 1-8 can be individually rerun.")

    # Load the original run context
    with get_session() as session:
        run = session.query(AnalysisRun).filter_by(id=run_id).one_or_none()
        if not run:
            raise ValueError(f"Analysis run not found: {run_id}")
        account_id = run.account_id

    # Get current transcript texts
    transcript_texts = get_active_transcript_texts(account_id)
    if not transcript_texts:
        raise ValueError(f"No active transcripts for account {account_id}")

    # Get the stage context from Agent 1's existing output
    with get_session() as session:
        agent1 = (
            session.query(AgentAnalysis)
            .filter_by(analysis_run_id=run_id, agent_id="agent_1")
            .first()
        )
        if not agent1:
            raise ValueError("Agent 1 output not found — cannot rerun without stage context")
        findings = json.loads(agent1.findings) if agent1.findings else {}
        stage_context = {
            "inferred_stage": findings.get("inferred_stage"),
            "stage_name": findings.get("stage_name"),
            "confidence": agent1.confidence_overall,
            "reasoning": findings.get("reasoning"),
        }

    # Build and run the agent
    import importlib
    module_path, func_name = AGENT_BUILDERS[agent_id]
    mod = importlib.import_module(module_path)
    builder = getattr(mod, func_name)

    if agent_id == "agent_1":
        call_kwargs = builder(transcript_texts, None)
    else:
        call_kwargs = builder(transcript_texts, stage_context, None)
        call_kwargs.setdefault("transcript_count", len(transcript_texts))

    agent_result = asyncio.run(run_agent_async(**call_kwargs))
    output_dict = agent_result.output.model_dump()

    # Validate
    warnings = validate_agent_output(output_dict)

    # Update the stored analysis
    with get_session() as session:
        existing = (
            session.query(AgentAnalysis)
            .filter_by(analysis_run_id=run_id, agent_id=agent_id)
            .first()
        )
        if existing:
            existing.narrative = output_dict.get("narrative", "")
            existing.findings = json.dumps(output_dict.get("findings", {}))
            existing.evidence = json.dumps(output_dict.get("evidence", []))
            existing.confidence_overall = output_dict.get("confidence", {}).get("overall")
            existing.confidence_rationale = output_dict.get("confidence", {}).get("rationale")
            existing.data_gaps = json.dumps(output_dict.get("confidence", {}).get("data_gaps", []))
            existing.sparse_data_flag = 1 if output_dict.get("sparse_data_flag") else 0
            existing.input_tokens = agent_result.input_tokens
            existing.output_tokens = agent_result.output_tokens
            existing.model_used = agent_result.model
            existing.retries = agent_result.attempts - 1
            existing.status = "completed"
        session.flush()

    return {
        "agent_id": agent_id,
        "status": "completed",
        "warnings": warnings,
        "input_tokens": agent_result.input_tokens,
        "output_tokens": agent_result.output_tokens,
    }


def resynthesize(run_id: str) -> dict:
    """Re-run Agent 10 (Synthesis) using the current agent outputs for an existing run.

    Per Technical Architecture Section 6.1 — allows re-synthesis after individual
    agent reruns without re-running the entire pipeline.

    Returns:
        dict with updated deal assessment data
    """
    import asyncio
    from sis.agents.synthesis import build_call as synthesis_build_call
    from sis.agents.runner import run_agent_async

    # Load all agent outputs from the run
    with get_session() as session:
        run = session.query(AnalysisRun).filter_by(id=run_id).one_or_none()
        if not run:
            raise ValueError(f"Analysis run not found: {run_id}")
        account_id = run.account_id

        agent_rows = (
            session.query(AgentAnalysis)
            .filter_by(analysis_run_id=run_id)
            .order_by(AgentAnalysis.agent_id)
            .all()
        )

        agent_outputs = {}
        stage_context = None
        for a in agent_rows:
            output = {
                "narrative": a.narrative,
                "findings": json.loads(a.findings) if a.findings else {},
                "evidence": json.loads(a.evidence) if a.evidence else [],
                "confidence": {
                    "overall": a.confidence_overall,
                    "rationale": a.confidence_rationale,
                    "data_gaps": json.loads(a.data_gaps) if a.data_gaps else [],
                },
                "sparse_data_flag": bool(a.sparse_data_flag),
            }
            agent_outputs[a.agent_id] = output

            if a.agent_id == "agent_1":
                findings = json.loads(a.findings) if a.findings else {}
                stage_context = {
                    "inferred_stage": findings.get("inferred_stage"),
                    "stage_name": findings.get("stage_name"),
                    "confidence": a.confidence_overall,
                    "reasoning": findings.get("reasoning"),
                }

    if not stage_context:
        raise ValueError("Agent 1 output not found — cannot resynthesize")

    # Run synthesis
    call_kwargs = synthesis_build_call(agent_outputs, stage_context)
    agent10_result = asyncio.run(run_agent_async(**call_kwargs))
    syn = agent10_result.output.model_dump()

    # Update the DealAssessment
    with get_session() as session:
        existing = (
            session.query(DealAssessment)
            .filter_by(analysis_run_id=run_id)
            .first()
        )
        if existing:
            existing.deal_memo = syn.get("deal_memo", "")
            existing.contradiction_map = json.dumps(syn.get("contradiction_map", []))
            existing.inferred_stage = syn.get("inferred_stage", 0)
            existing.stage_name = syn.get("inferred_stage_name", "")
            existing.stage_confidence = syn.get("inferred_stage_confidence", 0.0)
            existing.health_score = syn.get("health_score", 0)
            existing.health_breakdown = json.dumps(syn.get("health_score_breakdown", []))
            existing.overall_confidence = syn.get("confidence_interval", {}).get("overall_confidence", 0.0)
            existing.confidence_rationale = syn.get("confidence_interval", {}).get("rationale")
            existing.key_unknowns = json.dumps(syn.get("confidence_interval", {}).get("key_unknowns", []))
            existing.momentum_direction = syn.get("momentum_direction", "Unknown")
            existing.momentum_trend = syn.get("momentum_trend")
            existing.ai_forecast_category = syn.get("forecast_category", "Pipeline")
            existing.forecast_rationale = syn.get("forecast_rationale")
            existing.top_positive_signals = json.dumps(syn.get("top_positive_signals", []))
            existing.top_risks = json.dumps(syn.get("top_risks", []))
            existing.recommended_actions = json.dumps(syn.get("recommended_actions", []))
        session.flush()

    return {
        "status": "completed",
        "health_score": syn.get("health_score"),
        "forecast_category": syn.get("forecast_category"),
        "input_tokens": agent10_result.input_tokens,
        "output_tokens": agent10_result.output_tokens,
    }
