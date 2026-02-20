"""Standardized agent output schema per PRD Section 7.4.

All 9 analysis agents (1-9) produce output wrapped in this envelope.
Agent-specific structured data goes in the ``findings`` field.
Pipeline metadata (deal_id, analysis_date) is injected post-LLM by the orchestrator.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class EvidenceCitation(BaseModel):
    """A structured evidence citation linking a claim to transcript data."""

    claim_id: str = Field(
        description="snake_case identifier matching a finding, max 30 chars",
        max_length=30,
    )
    transcript_index: int = Field(
        description="Which transcript (1-indexed) this evidence comes from",
        ge=1,
    )
    speaker: str = Field(
        description="Speaker as NAME (Company -- Role)",
    )
    quote: str = Field(
        description="Verbatim quote or [paraphrased] summary from transcript",
    )
    interpretation: str = Field(
        description="One sentence explaining causal relevance of this evidence",
    )


class ConfidenceAssessment(BaseModel):
    """Structured confidence assessment with rationale and gaps."""

    overall: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0) per calibration scale",
    )
    rationale: str = Field(
        description="1-2 sentence explanation of confidence level",
    )
    data_gaps: list[str] = Field(
        default_factory=list,
        description="Specific data gaps that limit confidence",
    )


# ---------------------------------------------------------------------------
# Prompt fragment appended to every agent's system prompt (Agents 1-9)
# ---------------------------------------------------------------------------

ENVELOPE_PROMPT_FRAGMENT = """\

## Evidence Citation Rules
For every factual claim, provide evidence citations (3-5 most important only):
- `claim_id`: snake_case, max 30 characters, matches a specific finding
- `transcript_index`: which transcript (1-indexed)
- `speaker`: format as "NAME (Company -- Role)" when known
- `quote`: verbatim text, or mark with [paraphrased] if summarizing
- `interpretation`: one sentence explaining why this evidence matters

## Confidence Assessment Rules
Produce a confidence score covering your ENTIRE output quality:
- 0.9-1.0: Unambiguous -- multiple corroborating quotes, consistent across transcripts
- 0.7-0.89: Clear -- 1-2 corroborating quotes, minor ambiguity
- 0.5-0.69: Some signal -- single data point or ambiguous language
- 0.3-0.49: Weak -- inference without direct evidence
- 0.1-0.29: Speculative -- minimal basis, flagging the question only
Include a rationale and list specific data gaps.

## Sparse Data Flag
Set sparse_data_flag=true if fewer than 3 full transcripts were provided. \
When sparse_data_flag=true, confidence MUST NOT exceed 0.75 unless explicitly justified."""
