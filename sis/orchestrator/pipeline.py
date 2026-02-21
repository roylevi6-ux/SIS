"""AnalysisPipeline — 4-step agent execution flow per Technical Architecture Section 3.2.

Manages the full 10-agent pipeline for one account:
  Step 1: Agent 1 (Stage & Progress) — sequential
  Step 2: Agents 2-8 (7 specialized agents) — parallel via asyncio.gather
  Step 3: Agent 9 (Open Discovery / Adversarial) — sequential
  Step 4: Agent 10 (Synthesis) — sequential

Design principles:
- No agent-to-agent communication except through the orchestrator
- Agents are pure functions: (transcripts, context) -> AgentOutput
- asyncio.gather for parallel execution with return_exceptions=True
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
    """Manages the 4-step agent execution pipeline for one account.

    Usage:
        pipeline = AnalysisPipeline()
        result = pipeline.run(account_id, transcript_texts, timeline_entries)
        # or async:
        result = await pipeline.run_async(account_id, transcript_texts, timeline_entries)
    """

    def __init__(self, progress_callback: Callable[[str, int, int], None] | None = None):
        """Initialize pipeline.

        Args:
            progress_callback: Optional callback(step_name, current_step, total_steps)
                for UI progress reporting.
        """
        self._progress_callback = progress_callback

    def _report_progress(self, step_name: str, current: int, total: int = 4) -> None:
        if self._progress_callback:
            self._progress_callback(step_name, current, total)
        logger.info("Pipeline step %d/%d: %s", current, total, step_name)

    def run(
        self,
        account_id: str,
        transcript_texts: list[str],
        timeline_entries: list[str] | None = None,
    ) -> PipelineResult:
        """Run the full pipeline synchronously (wraps async version)."""
        return asyncio.run(self.run_async(account_id, transcript_texts, timeline_entries))

    async def run_async(
        self,
        account_id: str,
        transcript_texts: list[str],
        timeline_entries: list[str] | None = None,
    ) -> PipelineResult:
        """Run the full 4-step pipeline asynchronously.

        Args:
            account_id: Account identifier
            transcript_texts: List of preprocessed transcript texts
            timeline_entries: Optional timeline entries for context

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
        from sis.agents.runner import (
            run_agent, run_agent_async, run_agents_parallel,
            strip_for_downstream, AgentError,
        )
        from sis.validation import validate_agent_output

        result = PipelineResult(
            account_id=account_id,
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        pipeline_start = time.time()
        num_transcripts = len(transcript_texts)

        try:
            # ── STEP 1: Agent 1 (Stage & Progress) ────────────────────
            self._report_progress("Agent 1: Stage & Progress", 1)
            agent1_call = stage_build_call(transcript_texts, timeline_entries)
            agent1_result = await run_agent_async(**agent1_call)

            stage_output = agent1_result.output.model_dump()
            result.stage_output = stage_output
            result.agent_outputs["agent_1"] = stage_output
            result.agent_metadata["agent_1"] = {
                "input_tokens": agent1_result.input_tokens,
                "output_tokens": agent1_result.output_tokens,
                "elapsed_seconds": agent1_result.elapsed_seconds,
                "model": agent1_result.model,
                "attempts": agent1_result.attempts,
            }
            result.cost_summary.add(
                "agent_1", agent1_result.model,
                agent1_result.input_tokens, agent1_result.output_tokens,
                agent1_result.elapsed_seconds, agent1_result.attempts - 1,
            )

            # Validate
            warnings = validate_agent_output(stage_output)
            result.validation_warnings.extend(
                [f"[Agent 1] {w}" for w in warnings]
            )

            # Extract stage context for downstream agents
            stage_context = {
                "inferred_stage": stage_output["findings"]["inferred_stage"],
                "stage_name": stage_output["findings"]["stage_name"],
                "confidence": stage_output["confidence"]["overall"],
                "reasoning": stage_output["findings"]["reasoning"],
            }

            # ── STEP 2: Agents 2-8 (parallel) ─────────────────────────
            self._report_progress("Agents 2-8: Parallel Analysis", 2)

            agent_builders = [
                ("agent_2", relationship_build_call),
                ("agent_3", commercial_build_call),
                ("agent_4", momentum_build_call),
                ("agent_5", technical_build_call),
                ("agent_6", eb_build_call),
                ("agent_7", msp_build_call),
                ("agent_8", competitive_build_call),
            ]

            parallel_tasks = []
            for agent_id, builder in agent_builders:
                call_kwargs = builder(transcript_texts, stage_context, timeline_entries)
                # Ensure transcript_count is set for sparse_data_flag injection
                call_kwargs.setdefault("transcript_count", num_transcripts)
                parallel_tasks.append(call_kwargs)

            parallel_results = await run_agents_parallel(parallel_tasks)

            for (agent_id, _), agent_result in zip(agent_builders, parallel_results):
                if isinstance(agent_result, Exception):
                    result.errors.append(f"[{agent_id}] {agent_result}")
                    logger.error("[%s] Failed: %s", agent_id, agent_result)
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
                warnings = validate_agent_output(output_dict)
                result.validation_warnings.extend(
                    [f"[{agent_id}] {w}" for w in warnings]
                )

            # ── STEP 3: Agent 9 (Open Discovery) ──────────────────────
            self._report_progress("Agent 9: Open Discovery", 3)
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

            # ── STEP 4: Agent 10 (Synthesis) ──────────────────────────
            self._report_progress("Agent 10: Synthesis", 4)
            agent10_call = synthesis_build_call(result.agent_outputs, stage_context)
            agent10_result = await run_agent_async(**agent10_call)

            synthesis_output = agent10_result.output.model_dump()
            result.synthesis_output = synthesis_output
            result.cost_summary.add(
                "agent_10", agent10_result.model,
                agent10_result.input_tokens, agent10_result.output_tokens,
                agent10_result.elapsed_seconds, agent10_result.attempts - 1,
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
        logger.info(
            "Pipeline finished: status=%s, cost=$%.4f, time=%.1fs, agents=%d/%d",
            result.status,
            result.cost_summary.total_cost_usd,
            result.wall_clock_seconds,
            len(result.agent_outputs),
            10,
        )
        return result
