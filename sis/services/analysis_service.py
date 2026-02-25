"""Analysis service — run pipeline, persist results per Technical Architecture Section 6.1."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sis.db.session import get_session
from sis.db.models import Account, AnalysisRun, AgentAnalysis, DealAssessment
from sis.orchestrator.pipeline import AnalysisPipeline, PipelineResult
from sis.services.transcript_service import get_active_transcript_texts, get_active_transcript_ids
from sis.constants import is_expansion_deal, normalize_deal_type

logger = logging.getLogger(__name__)

# Agent ID to human name mapping
AGENT_NAMES = {
    "agent_0e": "Account Health & Sentiment",
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


def create_analysis_run(account_id: str) -> str:
    """Create an AnalysisRun row immediately and return its ID.

    This is called before the pipeline starts so the frontend can
    connect to SSE with a real run_id right away.
    """
    from datetime import datetime, timezone as tz
    transcript_ids = get_active_transcript_ids(account_id)
    with get_session() as session:
        run = AnalysisRun(
            account_id=account_id,
            started_at=datetime.now(tz.utc).isoformat(),
            status="running",
            transcript_ids=json.dumps(transcript_ids) if transcript_ids else None,
        )
        session.add(run)
        session.flush()
        return run.id


def analyze_account(
    account_id: str,
    progress_callback=None,
    run_id: str | None = None,
) -> dict:
    """Run the agent pipeline for one account.

    Args:
        account_id: Account to analyze.
        progress_callback: Optional legacy callback.
        run_id: Pre-created run ID for progress tracking. If None, one is
                created after the pipeline finishes (legacy behavior).

    Returns:
        dict with run_id, status, deal_assessment summary, cost
    """
    transcript_texts = get_active_transcript_texts(account_id)
    if not transcript_texts:
        raise ValueError(f"No active transcripts for account {account_id}")

    # Fetch deal context from account + transcript age
    with get_session() as session:
        account = session.query(Account).filter_by(id=account_id).one_or_none()
        if not account:
            raise ValueError(f"Account not found: {account_id}")
        from sis.constants import normalize_deal_type
        deal_type = normalize_deal_type(account.deal_type)
        prior_contract_value = account.prior_contract_value

        # Read SF indication fields for gap analysis (Agent 10 Step 5 only)
        sf_data = None
        if any([account.sf_stage, account.sf_forecast_category, account.sf_close_quarter, account.cp_estimate]):
            sf_data = {
                "sf_stage": account.sf_stage,
                "sf_forecast_category": account.sf_forecast_category,
                "sf_close_quarter": account.sf_close_quarter,
                "cp_estimate": account.cp_estimate,
            }

        # Compute days since most recent transcript for confidence penalties
        from sis.db.models import Transcript
        from sqlalchemy import func
        latest_date_str = (
            session.query(func.max(Transcript.call_date))
            .filter_by(account_id=account_id, is_active=1)
            .scalar()
        )
        transcript_age_days = None
        if latest_date_str:
            from datetime import date
            try:
                latest_date = date.fromisoformat(latest_date_str)
                transcript_age_days = (date.today() - latest_date).days
            except (ValueError, TypeError):
                pass

    deal_context = {
        "deal_type": deal_type,
        "prior_contract_value": prior_contract_value,
        "most_recent_transcript_age_days": transcript_age_days,
    }

    pipeline = AnalysisPipeline(progress_callback=progress_callback, run_id=run_id)
    result = pipeline.run(account_id, transcript_texts, deal_context=deal_context, sf_data=sf_data)

    transcript_ids = get_active_transcript_ids(account_id)
    persisted_run_id = _persist_pipeline_result(
        account_id, result, transcript_texts, transcript_ids, existing_run_id=run_id,
    )
    result.run_id = persisted_run_id

    expected_agents = 11 if is_expansion_deal(deal_type) else 10
    return {
        "run_id": persisted_run_id,
        "status": result.status,
        "wall_clock_seconds": round(result.wall_clock_seconds, 1),
        "total_cost_usd": round(result.cost_summary.total_cost_usd, 4),
        "agents_completed": len(result.agent_outputs),
        "agents_total": expected_agents,
        "errors": result.errors,
        "validation_warnings": result.validation_warnings,
    }


async def analyze_account_async(
    account_id: str,
    progress_callback=None,
    run_id: str | None = None,
) -> dict:
    """Async version of analyze_account."""
    transcript_texts = get_active_transcript_texts(account_id)
    if not transcript_texts:
        raise ValueError(f"No active transcripts for account {account_id}")

    # Fetch deal context from account + transcript age
    with get_session() as session:
        account = session.query(Account).filter_by(id=account_id).one_or_none()
        if not account:
            raise ValueError(f"Account not found: {account_id}")
        from sis.constants import normalize_deal_type
        deal_type = normalize_deal_type(account.deal_type)
        prior_contract_value = account.prior_contract_value

        # Read SF indication fields for gap analysis (Agent 10 Step 5 only)
        sf_data = None
        if any([account.sf_stage, account.sf_forecast_category, account.sf_close_quarter, account.cp_estimate]):
            sf_data = {
                "sf_stage": account.sf_stage,
                "sf_forecast_category": account.sf_forecast_category,
                "sf_close_quarter": account.sf_close_quarter,
                "cp_estimate": account.cp_estimate,
            }

        from sis.db.models import Transcript
        from sqlalchemy import func
        latest_date_str = (
            session.query(func.max(Transcript.call_date))
            .filter_by(account_id=account_id, is_active=1)
            .scalar()
        )
        transcript_age_days = None
        if latest_date_str:
            from datetime import date
            try:
                latest_date = date.fromisoformat(latest_date_str)
                transcript_age_days = (date.today() - latest_date).days
            except (ValueError, TypeError):
                pass

    deal_context = {
        "deal_type": deal_type,
        "prior_contract_value": prior_contract_value,
        "most_recent_transcript_age_days": transcript_age_days,
    }

    pipeline = AnalysisPipeline(progress_callback=progress_callback, run_id=run_id)
    result = await pipeline.run_async(account_id, transcript_texts, deal_context=deal_context, sf_data=sf_data)

    transcript_ids = get_active_transcript_ids(account_id)
    persisted_run_id = _persist_pipeline_result(
        account_id, result, transcript_texts, transcript_ids, existing_run_id=run_id,
    )
    result.run_id = persisted_run_id

    expected_agents = 11 if is_expansion_deal(deal_type) else 10
    return {
        "run_id": persisted_run_id,
        "status": result.status,
        "wall_clock_seconds": round(result.wall_clock_seconds, 1),
        "total_cost_usd": round(result.cost_summary.total_cost_usd, 4),
        "agents_completed": len(result.agent_outputs),
        "agents_total": expected_agents,
        "errors": result.errors,
        "validation_warnings": result.validation_warnings,
    }


def _persist_pipeline_result(
    account_id: str,
    result: PipelineResult,
    transcript_texts: list[str],
    transcript_ids: list[str] | None = None,
    existing_run_id: str | None = None,
) -> str:
    """Persist pipeline results to DB. Returns run_id.

    If existing_run_id is provided, updates the existing AnalysisRun row
    rather than creating a new one.
    """
    with get_session() as session:
        if existing_run_id:
            # Update the pre-created run row
            run = session.query(AnalysisRun).filter_by(id=existing_run_id).first()
            if run:
                run.started_at = result.started_at
                run.completed_at = result.completed_at
                run.status = result.status
                run.total_input_tokens = result.cost_summary.total_input_tokens
                run.total_output_tokens = result.cost_summary.total_output_tokens
                run.total_cost_usd = result.cost_summary.total_cost_usd
                run.model_versions = json.dumps({
                    agent_id: meta.get("model", "unknown")
                    for agent_id, meta in result.agent_metadata.items()
                })
                run.error_log = json.dumps(result.errors) if result.errors else None
                run.deal_type_at_run = result.deal_type
            else:
                # Fallback: create new if somehow the pre-created row is gone
                existing_run_id = None

        if not existing_run_id:
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
                deal_type_at_run=result.deal_type,
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
                deal_type=result.deal_type,
                stage_model="expansion_7stage" if is_expansion_deal(result.deal_type) else "new_logo_7stage",
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
                ai_forecast_category=syn.get("forecast_category", "Realistic"),
                forecast_confidence=None,
                forecast_rationale=syn.get("forecast_rationale"),
                top_positive_signals=json.dumps(syn.get("top_positive_signals", [])),
                top_risks=json.dumps(syn.get("top_risks", [])),
                recommended_actions=json.dumps(syn.get("recommended_actions", [])),
            )

            # Snapshot SF indication fields at run time
            if result.sf_data:
                assessment.sf_stage_at_run = result.sf_data.get("sf_stage")
                assessment.sf_forecast_at_run = result.sf_data.get("sf_forecast_category")
                assessment.sf_close_quarter_at_run = result.sf_data.get("sf_close_quarter")
                assessment.cp_estimate_at_run = result.sf_data.get("cp_estimate")

            # Deterministic gap computation
            if result.sf_data and result.sf_data.get("sf_stage") is not None:
                sf_stage = result.sf_data["sf_stage"]
                sis_stage = syn.get("inferred_stage", 0)
                if sf_stage == sis_stage:
                    assessment.stage_gap_direction = "Aligned"
                elif sf_stage > sis_stage:
                    assessment.stage_gap_direction = "SF-ahead"
                else:
                    assessment.stage_gap_direction = "SIS-ahead"
                assessment.stage_gap_magnitude = abs(sf_stage - sis_stage)

            if result.sf_data and result.sf_data.get("sf_forecast_category"):
                forecast_rank = {"At Risk": 1, "Upside": 2, "Realistic": 3, "Commit": 4}
                sf_rank = forecast_rank.get(result.sf_data["sf_forecast_category"], 0)
                sis_rank = forecast_rank.get(syn.get("forecast_category", ""), 0)
                if sf_rank == sis_rank:
                    assessment.forecast_gap_direction = "Aligned"
                elif sf_rank > sis_rank:
                    assessment.forecast_gap_direction = "SF-more-optimistic"
                else:
                    assessment.forecast_gap_direction = "SIS-more-optimistic"

            # Store Agent 10's gap interpretation if present
            sf_gap = syn.get("sf_gap_analysis")
            if sf_gap:
                assessment.sf_gap_interpretation = sf_gap.get("overall_gap_assessment", "")

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


def get_assessment_delta(account_id: str) -> dict | None:
    """Compare the latest and previous DealAssessment for an account.

    Returns a dict with field-by-field comparison, or None if fewer than 2 assessments exist.
    Each field entry: { "previous": value, "current": value, "changed": bool }
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
            return None

        current = assessments[0]
        previous = assessments[1]

    def _delta(field: str, cur_val, prev_val):
        changed = cur_val != prev_val
        result = {"previous": prev_val, "current": cur_val, "changed": changed}
        # Add numeric delta for scores
        if isinstance(cur_val, (int, float)) and isinstance(prev_val, (int, float)):
            result["delta"] = cur_val - prev_val
        return result

    return {
        "account_id": account_id,
        "current_run_date": current.created_at,
        "previous_run_date": previous.created_at,
        "fields": {
            "health_score": _delta("health_score", current.health_score, previous.health_score),
            "inferred_stage": _delta("inferred_stage", current.inferred_stage, previous.inferred_stage),
            "stage_name": _delta("stage_name", current.stage_name, previous.stage_name),
            "momentum_direction": _delta("momentum_direction", current.momentum_direction, previous.momentum_direction),
            "ai_forecast_category": _delta("ai_forecast_category", current.ai_forecast_category, previous.ai_forecast_category),
            "overall_confidence": _delta("overall_confidence", current.overall_confidence, previous.overall_confidence),
            "top_risks": _delta(
                "top_risks",
                json.loads(current.top_risks or "[]"),
                json.loads(previous.top_risks or "[]"),
            ),
            "recommended_actions": _delta(
                "recommended_actions",
                json.loads(current.recommended_actions or "[]"),
                json.loads(previous.recommended_actions or "[]"),
            ),
        },
    }


def get_assessment_timeline(account_id: str) -> list[dict]:
    """Get all DealAssessments for an account, ordered by date ascending.

    Returns a list of dicts with key metrics per assessment for timeline display.
    """
    with get_session() as session:
        assessments = (
            session.query(DealAssessment)
            .filter_by(account_id=account_id)
            .order_by(DealAssessment.created_at.asc())
            .all()
        )
        return [
            {
                "id": a.id,
                "analysis_run_id": a.analysis_run_id,
                "created_at": a.created_at,
                "health_score": a.health_score,
                "inferred_stage": a.inferred_stage,
                "stage_name": a.stage_name,
                "momentum_direction": a.momentum_direction,
                "ai_forecast_category": a.ai_forecast_category,
                "overall_confidence": a.overall_confidence,
            }
            for a in assessments
        ]


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
        "agent_0e": ("sis.agents.account_health", "build_call"),
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
        raise ValueError(f"Cannot rerun {agent_id}. Only agents 0E and 1-8 can be individually rerun.")

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

    if agent_id == "agent_0e":
        # Agent 0E takes (transcript_texts, timeline_entries, deal_context)
        with get_session() as session:
            acct = session.query(Account).filter_by(id=account_id).one_or_none()
        deal_context = {
            "deal_type": normalize_deal_type(acct.deal_type) if acct else "new_logo",
            "prior_contract_value": acct.prior_contract_value if acct else None,
        }
        call_kwargs = builder(transcript_texts, None, deal_context)
        call_kwargs.setdefault("transcript_count", len(transcript_texts))
    elif agent_id == "agent_1":
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
        deal_type = run.deal_type_at_run or "new_logo"

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

    # Read SF data for gap analysis
    with get_session() as session:
        acct = session.query(Account).filter_by(id=account_id).one_or_none()
        sf_data = None
        if acct and any([acct.sf_stage, acct.sf_forecast_category, acct.sf_close_quarter, acct.cp_estimate]):
            sf_data = {
                "sf_stage": acct.sf_stage,
                "sf_forecast_category": acct.sf_forecast_category,
                "sf_close_quarter": acct.sf_close_quarter,
                "cp_estimate": acct.cp_estimate,
            }

    # Run synthesis
    call_kwargs = synthesis_build_call(agent_outputs, stage_context, sf_data)
    loop = asyncio.new_event_loop()
    try:
        agent10_result = loop.run_until_complete(run_agent_async(**call_kwargs))
    finally:
        loop.close()
    syn = agent10_result.output.model_dump()

    # Create or update the DealAssessment
    with get_session() as session:
        assessment = (
            session.query(DealAssessment)
            .filter_by(analysis_run_id=run_id)
            .first()
        )
        if not assessment:
            assessment = DealAssessment(
                analysis_run_id=run_id,
                account_id=account_id,
                deal_type=deal_type,
                stage_model="expansion_7stage" if is_expansion_deal(deal_type) else "new_logo_7stage",
            )
            session.add(assessment)

        assessment.deal_memo = syn.get("deal_memo", "")
        assessment.contradiction_map = json.dumps(syn.get("contradiction_map", []))
        assessment.inferred_stage = syn.get("inferred_stage", 0)
        assessment.stage_name = syn.get("inferred_stage_name", "")
        assessment.stage_confidence = syn.get("inferred_stage_confidence", 0.0)
        assessment.health_score = syn.get("health_score", 0)
        assessment.health_breakdown = json.dumps(syn.get("health_score_breakdown", []))
        assessment.overall_confidence = syn.get("confidence_interval", {}).get("overall_confidence", 0.0)
        assessment.confidence_rationale = syn.get("confidence_interval", {}).get("rationale")
        assessment.key_unknowns = json.dumps(syn.get("confidence_interval", {}).get("key_unknowns", []))
        assessment.momentum_direction = syn.get("momentum_direction", "Unknown")
        assessment.momentum_trend = syn.get("momentum_trend")
        assessment.ai_forecast_category = syn.get("forecast_category", "Realistic")
        assessment.forecast_rationale = syn.get("forecast_rationale")
        assessment.top_positive_signals = json.dumps(syn.get("top_positive_signals", []))
        assessment.top_risks = json.dumps(syn.get("top_risks", []))
        assessment.recommended_actions = json.dumps(syn.get("recommended_actions", []))

        # Snapshot SF indication fields and compute gap
        if sf_data:
            assessment.sf_stage_at_run = sf_data.get("sf_stage")
            assessment.sf_forecast_at_run = sf_data.get("sf_forecast_category")
            assessment.sf_close_quarter_at_run = sf_data.get("sf_close_quarter")
            assessment.cp_estimate_at_run = sf_data.get("cp_estimate")
            if sf_data.get("sf_stage") is not None:
                sf_stage = sf_data["sf_stage"]
                sis_stage = syn.get("inferred_stage", 0)
                if sf_stage == sis_stage:
                    assessment.stage_gap_direction = "Aligned"
                elif sf_stage > sis_stage:
                    assessment.stage_gap_direction = "SF-ahead"
                else:
                    assessment.stage_gap_direction = "SIS-ahead"
                assessment.stage_gap_magnitude = abs(sf_stage - sis_stage)

        # Mark the run as completed now that Agent 10 has succeeded
        run = session.query(AnalysisRun).filter_by(id=run_id).first()
        if run and run.status != "completed":
            run.status = "completed"

        session.flush()

    return {
        "status": "completed",
        "health_score": syn.get("health_score"),
        "forecast_category": syn.get("forecast_category"),
        "input_tokens": agent10_result.input_tokens,
        "output_tokens": agent10_result.output_tokens,
    }
