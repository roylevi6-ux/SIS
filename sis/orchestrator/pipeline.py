"""AnalysisPipeline — 5-step agent execution flow per Technical Architecture Section 3.2.

Manages the full pipeline for one account:
  Step 1: Agent 1 (Stage Classifier) runs FIRST, alone (Haiku — fast, cheap)
  Step 2: Extract stage_context from Agent 1's output
  Step 3: Agents 0E + 2-8 run in PARALLEL, ALL receiving stage_context
          For expansion deals: Agent 0E also runs in parallel with 2-8.
  Step 4: Agent 9 (Open Discovery / Adversarial) — reads all outputs + stage context
  Step 5: Agent 10 (Synthesis) — reads all outputs including Agent 9 + stage context

Agent 1 feeds stage context to ALL downstream agents so they can adjust
their analysis based on where the deal is in the pipeline (e.g., Commercial
analysis differs at Stage 3 vs Stage 6).

Design principles:
- No agent-to-agent communication except through the orchestrator
- Agents are pure functions: (transcripts, context) -> AgentOutput
- asyncio.as_completed for parallel execution with per-agent progress reporting
- Failed agents get retried independently; partial results are acceptable
- Agent 1 failure is non-fatal: pipeline continues with stage_context=None
- All results persisted to DB via the service layer
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from .budget import RunBudget
from .cost_tracker import RunCostSummary

logger = logging.getLogger(__name__)


def _penalize_confidence(
    output_dict: dict,
    transcript_count: int,
    most_recent_age_days: int | None = None,
) -> list[str]:
    """Apply confidence penalties to an agent output dict in place.

    Returns list of warning strings for any penalties applied.
    """
    from sis.validation import apply_confidence_penalties

    conf = output_dict.get("confidence", {})
    raw = conf.get("overall")
    if not isinstance(raw, (int, float)):
        return []

    sparse = output_dict.get("sparse_data_flag", False)

    adjusted, reasons = apply_confidence_penalties(
        raw_confidence=raw,
        transcript_count=transcript_count,
        most_recent_transcript_age_days=most_recent_age_days,
        sparse_data_flag=sparse,
    )

    if reasons:
        conf["overall"] = round(adjusted, 2)
        conf["penalties_applied"] = reasons
        logger.info(
            "Confidence adjusted %.2f -> %.2f: %s",
            raw, adjusted, "; ".join(reasons),
        )

    return [f"CONFIDENCE_PENALTY: {r}" for r in reasons]


class _CancelledError(Exception):
    """Internal signal that the pipeline was cancelled by the user."""


@dataclass
class PipelineResult:
    """Result of a full pipeline run."""

    run_id: str | None = None
    account_id: str = ""
    deal_type: str = "new_logo"
    status: str = "pending"  # pending/running/completed/partial/failed
    stage_output: dict | None = None
    agent_outputs: dict[str, dict] = field(default_factory=dict)  # agent_id -> output dict
    agent_metadata: dict[str, dict] = field(default_factory=dict)  # agent_id -> {tokens, time, model, attempts}
    synthesis_output: dict | None = None
    validation_warnings: list[str] = field(default_factory=list)
    cost_summary: RunCostSummary = field(default_factory=RunCostSummary)
    errors: list[str] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""
    wall_clock_seconds: float = 0.0
    sf_data: dict | None = None  # SF indication data for gap computation


class AnalysisPipeline:
    """Manages the 5-step agent execution pipeline for one account.

    Flow:
        Step 1: Agent 1 (Stage Classifier) — solo, Haiku, fast
        Step 2: Extract stage_context
        Step 3: Agents 0E + 2-8 — parallel, all with stage_context
        Step 4: Agent 9 (Open Discovery)
        Step 5: Agent 10 (Synthesis)

    Usage:
        pipeline = AnalysisPipeline()
        result = pipeline.run(account_id, transcript_texts, timeline_entries)
        # or async:
        result = await pipeline.run_async(account_id, transcript_texts, timeline_entries)
    """

    def __init__(
        self,
        progress_callback: Callable[[str, int, int], None] | None = None,
        run_id: str | None = None,
    ):
        """Initialize pipeline.

        Args:
            progress_callback: Optional callback(step_name, current_step, total_steps)
                for UI progress reporting.
            run_id: Optional run ID for progress store tracking.
        """
        self._progress_callback = progress_callback
        self._run_id = run_id

    def _report_progress(self, step_name: str, current: int, total: int = 5) -> None:
        if self._progress_callback:
            self._progress_callback(step_name, current, total)
        logger.info("Pipeline step %d/%d: %s", current, total, step_name)

    def run(
        self,
        account_id: str,
        transcript_texts: list[str],
        timeline_entries: list[str] | None = None,
        deal_context: dict | None = None,
        sf_data: dict | None = None,
    ) -> PipelineResult:
        """Run the full pipeline synchronously (wraps async version)."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.run_async(account_id, transcript_texts, timeline_entries, deal_context, sf_data))
        finally:
            loop.close()

    async def run_async(
        self,
        account_id: str,
        transcript_texts: list[str],
        timeline_entries: list[str] | None = None,
        deal_context: dict | None = None,
        sf_data: dict | None = None,
    ) -> PipelineResult:
        """Run the full 3-step pipeline asynchronously.

        Args:
            account_id: Account identifier
            transcript_texts: List of preprocessed transcript texts
            timeline_entries: Optional timeline entries for context
            deal_context: Optional dict with deal_type and prior_contract_value
            sf_data: Optional dict with SF indication fields for gap computation (Agent 10 Step 5 only)

        Returns:
            PipelineResult with all agent outputs, synthesis, and cost data
        """
        # Lazy imports to avoid circular dependencies
        from sis.agents.stage_classifier import build_call as stage_build_call
        from sis.agents.relationship import build_call as relationship_build_call
        from sis.agents.commercial import build_call as commercial_build_call
        from sis.agents.momentum import build_call as momentum_build_call
        from sis.agents.technical import build_call as technical_build_call
        from sis.agents.economic_buyer import build_call as eb_build_call
        from sis.agents.msp_next_steps import build_call as msp_build_call
        from sis.agents.competitive import build_call as competitive_build_call
        from sis.agents.open_discovery import build_call as discovery_build_call
        from sis.agents.synthesis import build_call as synthesis_build_call
        from sis.agents.account_health import build_call as account_health_build_call
        from sis.agents.runner import (
            run_agent, run_agent_async,
            strip_for_synthesis, strip_for_adversarial,
            strip_for_downstream, AgentError,
        )
        from sis.validation import validate_agent_output

        from sis.constants import normalize_deal_type, is_expansion_deal
        raw_deal_type = deal_context.get("deal_type", "new_logo") if deal_context else "new_logo"
        deal_type = normalize_deal_type(raw_deal_type)
        is_expansion = is_expansion_deal(deal_type)
        budget = RunBudget()

        result = PipelineResult(
            account_id=account_id,
            deal_type=deal_type,
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        pipeline_start = time.time()
        result.sf_data = sf_data
        num_transcripts = len(transcript_texts)
        transcript_age_days = deal_context.get("most_recent_transcript_age_days") if deal_context else None

        # Initialize progress store if run_id provided
        if self._run_id:
            from sis.orchestrator.progress_store import (
                init_run, mark_agent_running, mark_agent_completed,
                mark_agent_failed, mark_run_completed, is_cancelled,
                get_snapshot,
            )
            init_run(self._run_id)

        try:
            # ── STEP 1: Agent 1 (Stage Classifier) — runs FIRST, alone ──
            # Agent 1 uses Haiku (fast, cheap) and classifies the deal stage.
            # Its output feeds stage_context to ALL downstream agents.
            self._report_progress("Agent 1: Stage Classification", 1)
            if self._run_id:
                mark_agent_running(self._run_id, "agent_1")

            stage_context = None
            try:
                build_start = time.time()
                agent1_call = stage_build_call(
                    transcript_texts, timeline_entries, deal_context,
                )
                agent1_call.setdefault("transcript_count", num_transcripts)
                build_elapsed = time.time() - build_start
                agent1_result = await run_agent_async(**agent1_call)
                total_prep = build_elapsed + agent1_result.prep_seconds

                agent1_output = agent1_result.output.model_dump()
                result.agent_outputs["agent_1"] = agent1_output
                result.agent_metadata["agent_1"] = {
                    "input_tokens": agent1_result.input_tokens,
                    "output_tokens": agent1_result.output_tokens,
                    "elapsed_seconds": agent1_result.elapsed_seconds,
                    "prep_seconds": total_prep,
                    "model": agent1_result.model,
                    "attempts": agent1_result.attempts,
                }
                result.cost_summary.add(
                    "agent_1", agent1_result.model,
                    agent1_result.input_tokens, agent1_result.output_tokens,
                    agent1_result.elapsed_seconds, agent1_result.attempts - 1,
                )
                if self._run_id:
                    mark_agent_completed(
                        self._run_id, "agent_1",
                        agent1_result.input_tokens, agent1_result.output_tokens,
                        agent1_result.elapsed_seconds, agent1_result.model,
                        agent1_result.attempts, prep_seconds=total_prep,
                    )
                warnings = validate_agent_output(agent1_output)
                result.validation_warnings.extend(
                    [f"[agent_1] {w}" for w in warnings]
                )
                penalty_warnings = _penalize_confidence(agent1_output, num_transcripts, transcript_age_days)
                result.validation_warnings.extend(
                    [f"[agent_1] {w}" for w in penalty_warnings]
                )

                # Extract stage context for all downstream agents
                result.stage_output = agent1_output
                stage_context = {
                    "deal_type": deal_type,
                    "stage_model": agent1_output["findings"].get("stage_model", "new_logo_7"),
                    "inferred_stage": agent1_output["findings"]["inferred_stage"],
                    "stage_name": agent1_output["findings"]["stage_name"],
                    "confidence": agent1_output["confidence"]["overall"],
                    "reasoning": agent1_output["findings"]["reasoning"],
                }
                logger.info(
                    "Agent 1 completed: stage=%d (%s), confidence=%.2f, deal_type=%s",
                    stage_context["inferred_stage"],
                    stage_context["stage_name"],
                    stage_context["confidence"],
                    stage_context["deal_type"],
                )
            except Exception as exc:
                # Agent 1 failure is non-fatal — continue without stage context
                result.errors.append(f"[agent_1] {exc}")
                logger.error("Agent 1 failed — continuing without stage context: %s", exc)
                if self._run_id:
                    mark_agent_failed(self._run_id, "agent_1", str(exc))

            # ── Cancellation check before Step 2 ──
            if self._run_id and is_cancelled(self._run_id):
                logger.info("Pipeline cancelled before Step 2")
                result.status = "cancelled"
                raise _CancelledError()

            # ── STEP 2: Agents 0E + 2-8 (parallel, all with stage_context) ──
            step2_label = "Agents 0E+2-8: Parallel Analysis" if is_expansion else "Agents 2-8: Parallel Analysis"
            self._report_progress(step2_label, 2)

            agent_builders = []
            if is_expansion:
                agent_builders.append(("agent_0e", account_health_build_call))
            agent_builders.extend([
                ("agent_2", relationship_build_call),
                ("agent_3", commercial_build_call),
                ("agent_4", momentum_build_call),
                ("agent_5", technical_build_call),
                ("agent_6", eb_build_call),
                ("agent_7", msp_build_call),
                ("agent_8", competitive_build_call),
            ])

            # Mark all parallel agents as running in progress store
            if self._run_id:
                for agent_id, _ in agent_builders:
                    mark_agent_running(self._run_id, agent_id)

            # Build call kwargs — ALL agents now receive stage_context
            parallel_tasks = []
            build_times: dict[str, float] = {}
            for agent_id, builder in agent_builders:
                build_start = time.time()
                if agent_id == "agent_0e":
                    # Agent 0E: (transcripts, timeline, deal_context, stage_context)
                    call_kwargs = builder(
                        transcript_texts, timeline_entries, deal_context, stage_context,
                    )
                else:
                    # Agents 2-8: (transcripts, stage_context, timeline)
                    call_kwargs = builder(transcript_texts, stage_context, timeline_entries)
                build_times[agent_id] = time.time() - build_start
                call_kwargs.setdefault("transcript_count", num_transcripts)
                parallel_tasks.append(call_kwargs)

            # Wrapper that returns (agent_id, result) for as_completed matching
            async def _tagged_run(aid: str, kwargs: dict):
                r = await run_agent_async(**kwargs)
                return aid, r

            tagged_tasks = [
                asyncio.create_task(_tagged_run(aid, kw))
                for (aid, _), kw in zip(agent_builders, parallel_tasks)
            ]

            for completed_future in asyncio.as_completed(tagged_tasks):
                try:
                    agent_id, agent_result = await completed_future
                except Exception as exc:
                    result.errors.append(f"[parallel] {exc}")
                    logger.error("[parallel] Agent failed: %s", exc)
                    continue

                output_dict = agent_result.output.model_dump()
                total_prep = build_times.get(agent_id, 0.0) + agent_result.prep_seconds
                result.agent_outputs[agent_id] = output_dict
                result.agent_metadata[agent_id] = {
                    "input_tokens": agent_result.input_tokens,
                    "output_tokens": agent_result.output_tokens,
                    "elapsed_seconds": agent_result.elapsed_seconds,
                    "prep_seconds": total_prep,
                    "model": agent_result.model,
                    "attempts": agent_result.attempts,
                }
                result.cost_summary.add(
                    agent_id, agent_result.model,
                    agent_result.input_tokens, agent_result.output_tokens,
                    agent_result.elapsed_seconds, agent_result.attempts - 1,
                )
                if self._run_id:
                    mark_agent_completed(
                        self._run_id, agent_id,
                        agent_result.input_tokens, agent_result.output_tokens,
                        agent_result.elapsed_seconds, agent_result.model,
                        agent_result.attempts, prep_seconds=total_prep,
                    )
                warnings = validate_agent_output(output_dict)
                result.validation_warnings.extend(
                    [f"[{agent_id}] {w}" for w in warnings]
                )
                penalty_warnings = _penalize_confidence(output_dict, num_transcripts, transcript_age_days)
                result.validation_warnings.extend(
                    [f"[{agent_id}] {w}" for w in penalty_warnings]
                )

            # ── Cancellation check before Step 3 ──
            if self._run_id and is_cancelled(self._run_id):
                logger.info("Pipeline cancelled before Step 3")
                result.status = "cancelled"
                raise _CancelledError()

            # ── Budget check after parallel batch ──
            violations = budget.check(result.cost_summary, result.errors)
            if violations:
                logger.warning("Budget exceeded after parallel batch: %s", violations)
                result.errors.append(f"[budget] {'; '.join(violations)}")
                result.status = "partial"
                raise _CancelledError()

            # ── STEP 3: Agent 9 (Open Discovery) ──────────────────────
            self._report_progress("Agent 9: Open Discovery", 3)
            if self._run_id:
                mark_agent_running(self._run_id, "agent_9")
            try:
                build_start = time.time()
                agent9_call = discovery_build_call(
                    transcript_texts, stage_context, result.agent_outputs, timeline_entries
                )
                build_elapsed = time.time() - build_start
                agent9_result = await run_agent_async(**agent9_call)
                total_prep = build_elapsed + agent9_result.prep_seconds

                agent9_output = agent9_result.output.model_dump()
                result.agent_outputs["agent_9"] = agent9_output
                result.agent_metadata["agent_9"] = {
                    "input_tokens": agent9_result.input_tokens,
                    "output_tokens": agent9_result.output_tokens,
                    "elapsed_seconds": agent9_result.elapsed_seconds,
                    "prep_seconds": total_prep,
                    "model": agent9_result.model,
                    "attempts": agent9_result.attempts,
                }
                result.cost_summary.add(
                    "agent_9", agent9_result.model,
                    agent9_result.input_tokens, agent9_result.output_tokens,
                    agent9_result.elapsed_seconds, agent9_result.attempts - 1,
                )
                if self._run_id:
                    mark_agent_completed(
                        self._run_id, "agent_9",
                        agent9_result.input_tokens, agent9_result.output_tokens,
                        agent9_result.elapsed_seconds, agent9_result.model,
                        agent9_result.attempts, prep_seconds=total_prep,
                    )
                penalty_warnings = _penalize_confidence(agent9_output, num_transcripts, transcript_age_days)
                result.validation_warnings.extend(
                    [f"[agent_9] {w}" for w in penalty_warnings]
                )
            except Exception as exc:
                result.errors.append(f"[agent_9] {exc}")
                logger.error("Agent 9 (Open Discovery) failed: %s", exc)
                if self._run_id:
                    mark_agent_failed(self._run_id, "agent_9", str(exc))

            # ── Cancellation check before Step 4 ──
            if self._run_id and is_cancelled(self._run_id):
                logger.info("Pipeline cancelled before Step 4")
                result.status = "cancelled"
                raise _CancelledError()

            # ── Budget check after Agent 9 ──
            violations = budget.check(result.cost_summary, result.errors)
            if violations:
                logger.warning("Budget exceeded after Agent 9: %s", violations)
                result.errors.append(f"[budget] {'; '.join(violations)}")
                result.status = "partial"
                raise _CancelledError()

            # ── STEP 4: Agent 10 (Synthesis) ──────────────────────────
            self._report_progress("Agent 10: Synthesis", 4)
            if self._run_id:
                mark_agent_running(self._run_id, "agent_10")
            try:
                build_start = time.time()
                agent10_call = synthesis_build_call(result.agent_outputs, stage_context, sf_data)
                build_elapsed = time.time() - build_start
                agent10_result = await run_agent_async(**agent10_call)
                total_prep = build_elapsed + agent10_result.prep_seconds

                synthesis_output = agent10_result.output.model_dump()
                result.synthesis_output = synthesis_output
                result.cost_summary.add(
                    "agent_10", agent10_result.model,
                    agent10_result.input_tokens, agent10_result.output_tokens,
                    agent10_result.elapsed_seconds, agent10_result.attempts - 1,
                )
                if self._run_id:
                    mark_agent_completed(
                        self._run_id, "agent_10",
                        agent10_result.input_tokens, agent10_result.output_tokens,
                        agent10_result.elapsed_seconds, agent10_result.model,
                        agent10_result.attempts, prep_seconds=total_prep,
                    )
            except Exception as exc:
                result.errors.append(f"[agent_10] {exc}")
                logger.error("Agent 10 (Synthesis) failed: %s", exc)
                if self._run_id:
                    mark_agent_failed(self._run_id, "agent_10", str(exc))

            # ── Cancellation check before Step 5 ──
            if self._run_id and is_cancelled(self._run_id):
                logger.info("Pipeline cancelled before Step 5")
                result.status = "cancelled"
                raise _CancelledError()

            # ── STEP 5: POST-SYNTHESIS VALIDATION ─────────────────────
            if result.synthesis_output:
                self._report_progress("Post-synthesis validation", 5)
                from sis.validation import validate_synthesis_output
                synthesis_warnings = validate_synthesis_output(
                    result.synthesis_output, agent_outputs=result.agent_outputs,
                    deal_type=deal_type,
                )
                if synthesis_warnings:
                    result.validation_warnings.extend(synthesis_warnings)
                    logger.warning(
                        "Synthesis validation: %d warnings: %s",
                        len(synthesis_warnings),
                        synthesis_warnings,
                    )

            # Determine final status
            failed_agents = [e for e in result.errors]
            if failed_agents:
                result.status = "partial"
            else:
                result.status = "completed"

        except _CancelledError:
            result.status = "cancelled"
            logger.info("Pipeline cancelled for account %s", account_id)

        except Exception as e:
            result.status = "failed"
            result.errors.append(str(e))
            logger.exception("Pipeline failed: %s", e)
            # Safety net: mark any still-running agents as failed
            if self._run_id:
                snapshot = get_snapshot(self._run_id)
                if snapshot:
                    for agent_id, agent_data in snapshot.get("agents", {}).items():
                        if agent_data.get("status") == "running":
                            mark_agent_failed(self._run_id, agent_id, f"Pipeline failed: {e}")

        result.completed_at = datetime.now(timezone.utc).isoformat()
        result.wall_clock_seconds = time.time() - pipeline_start

        # Update progress store with terminal status
        if self._run_id:
            mark_run_completed(self._run_id, result.status)

        expected_agents = 11 if is_expansion else 10
        logger.info(
            "Pipeline finished: status=%s, cost=$%.4f, time=%.1fs, agents=%d/%d",
            result.status,
            result.cost_summary.total_cost_usd,
            result.wall_clock_seconds,
            len(result.agent_outputs),
            expected_agents,
        )
        return result


