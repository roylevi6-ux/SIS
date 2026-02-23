"""AnalysisPipeline — 3-step agent execution flow per Technical Architecture Section 3.2.

Manages the full pipeline for one account:
  Step 1: Agents 1-8 (all parallel via asyncio.as_completed)
          Agent 1 (Stage Classifier) runs alongside Agents 2-8.
          Agents 2-8 run without stage context (stage_context=None).
          For expansion deals: Agent 0E also runs in parallel with 1-8.
  Step 2: Agent 9 (Open Discovery / Adversarial) — reads all outputs + stage context
  Step 3: Agent 10 (Synthesis) — reads all outputs including Agent 9 + stage context

Design principles:
- No agent-to-agent communication except through the orchestrator
- Agents are pure functions: (transcripts, context) -> AgentOutput
- asyncio.as_completed for parallel execution with per-agent progress reporting
- Failed agents get retried independently; partial results are acceptable
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

from .cost_tracker import RunCostSummary

logger = logging.getLogger(__name__)


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


class AnalysisPipeline:
    """Manages the 3-step agent execution pipeline for one account.

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

    def _report_progress(self, step_name: str, current: int, total: int = 3) -> None:
        if self._progress_callback:
            self._progress_callback(step_name, current, total)
        logger.info("Pipeline step %d/%d: %s", current, total, step_name)

    def run(
        self,
        account_id: str,
        transcript_texts: list[str],
        timeline_entries: list[str] | None = None,
        deal_context: dict | None = None,
    ) -> PipelineResult:
        """Run the full pipeline synchronously (wraps async version)."""
        return asyncio.run(self.run_async(account_id, transcript_texts, timeline_entries, deal_context))

    async def run_async(
        self,
        account_id: str,
        transcript_texts: list[str],
        timeline_entries: list[str] | None = None,
        deal_context: dict | None = None,
    ) -> PipelineResult:
        """Run the full 3-step pipeline asynchronously.

        Args:
            account_id: Account identifier
            transcript_texts: List of preprocessed transcript texts
            timeline_entries: Optional timeline entries for context
            deal_context: Optional dict with deal_type and prior_contract_value

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
            strip_for_downstream, AgentError,
        )
        from sis.validation import validate_agent_output

        deal_type = deal_context.get("deal_type", "new_logo") if deal_context else "new_logo"
        is_expansion = deal_type.startswith("expansion")

        result = PipelineResult(
            account_id=account_id,
            deal_type=deal_type,
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        pipeline_start = time.time()
        num_transcripts = len(transcript_texts)

        # Initialize progress store if run_id provided
        if self._run_id:
            from sis.orchestrator.progress_store import (
                init_run, mark_agent_running, mark_agent_completed,
                mark_agent_failed, mark_run_completed,
            )
            init_run(self._run_id)

        try:
            # ── STEP 1: Agents 1-8 + optional 0E (all parallel) ────────
            step1_label = "Agents 0E+1-8: Parallel Analysis" if is_expansion else "Agents 1-8: Parallel Analysis"
            self._report_progress(step1_label, 1)

            # Agent 1 has a different build_call signature (no stage_context)
            # Agent 0E has a different signature (deal_context instead of stage_context)
            agent_builders = [
                ("agent_1", None),  # sentinel — built separately below
            ]
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

            # Mark all agents as running in progress store
            if self._run_id:
                for agent_id, _ in agent_builders:
                    mark_agent_running(self._run_id, agent_id)

            # Build call kwargs for each agent
            parallel_tasks = []
            for agent_id, builder in agent_builders:
                if agent_id == "agent_1":
                    call_kwargs = stage_build_call(transcript_texts, timeline_entries)
                elif agent_id == "agent_0e":
                    call_kwargs = builder(transcript_texts, timeline_entries, deal_context)
                else:
                    # Agents 2-8 run without stage context (None)
                    call_kwargs = builder(transcript_texts, None, timeline_entries)
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
                result.agent_outputs[agent_id] = output_dict
                result.agent_metadata[agent_id] = {
                    "input_tokens": agent_result.input_tokens,
                    "output_tokens": agent_result.output_tokens,
                    "elapsed_seconds": agent_result.elapsed_seconds,
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
                        agent_result.attempts,
                    )
                warnings = validate_agent_output(output_dict)
                result.validation_warnings.extend(
                    [f"[{agent_id}] {w}" for w in warnings]
                )

            # Extract stage context from Agent 1's output for downstream agents
            stage_output = result.agent_outputs.get("agent_1")
            if stage_output:
                result.stage_output = stage_output
                stage_context = {
                    "inferred_stage": stage_output["findings"]["inferred_stage"],
                    "stage_name": stage_output["findings"]["stage_name"],
                    "confidence": stage_output["confidence"]["overall"],
                    "reasoning": stage_output["findings"]["reasoning"],
                }
            else:
                stage_context = None
                result.errors.append("[pipeline] Agent 1 failed — stage context unavailable")

            # ── STEP 2: Agent 9 (Open Discovery) ──────────────────────
            self._report_progress("Agent 9: Open Discovery", 2)
            if self._run_id:
                mark_agent_running(self._run_id, "agent_9")
            agent9_call = discovery_build_call(
                transcript_texts, stage_context, result.agent_outputs, timeline_entries
            )
            agent9_result = await run_agent_async(**agent9_call)

            agent9_output = agent9_result.output.model_dump()
            result.agent_outputs["agent_9"] = agent9_output
            result.agent_metadata["agent_9"] = {
                "input_tokens": agent9_result.input_tokens,
                "output_tokens": agent9_result.output_tokens,
                "elapsed_seconds": agent9_result.elapsed_seconds,
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
                    agent9_result.attempts,
                )

            # ── STEP 3: Agent 10 (Synthesis) ──────────────────────────
            self._report_progress("Agent 10: Synthesis", 3)
            if self._run_id:
                mark_agent_running(self._run_id, "agent_10")
            agent10_call = synthesis_build_call(result.agent_outputs, stage_context)
            agent10_result = await run_agent_async(**agent10_call)

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
                    agent10_result.attempts,
                )

            # ── POST-SYNTHESIS VALIDATION ──────────────────────────────
            from sis.validation import validate_synthesis_output
            synthesis_warnings = validate_synthesis_output(
                synthesis_output, agent_outputs=result.agent_outputs,
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

        except Exception as e:
            result.status = "failed"
            result.errors.append(str(e))
            logger.exception("Pipeline failed: %s", e)

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


