"""Tests for core runner functions: _extract_json, strip_for_downstream,
build_analysis_prompt, _inject_deterministic_fields.

Covers four critical functions:
- _extract_json(): LLM response parsing (3 formats + edge cases)
- strip_for_downstream(): token reduction before Agents 9/10
- build_analysis_prompt(): prompt assembly for Agents 2-8
- _inject_deterministic_fields(): transcript_count and sparse_data_flag injection

No LLM API calls are made — all functions are pure / use simple Pydantic models.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from sis.agents.runner import (
    _extract_json,
    _find_json_object,
    strip_for_downstream,
    build_analysis_prompt,
    _inject_deterministic_fields,
)


# ---------------------------------------------------------------------------
# Minimal Pydantic models for _inject_deterministic_fields tests
# ---------------------------------------------------------------------------


class _ModelWithBothFields(BaseModel):
    agent_id: str = "agent_test"
    transcript_count_analyzed: int = 0
    sparse_data_flag: bool = False


class _ModelWithoutFields(BaseModel):
    agent_id: str = "agent_test"


class _ModelWithCountOnly(BaseModel):
    agent_id: str = "agent_test"
    transcript_count_analyzed: int = 0


# ---------------------------------------------------------------------------
# Tests: _extract_json
# ---------------------------------------------------------------------------


class TestExtractJsonPureJson:
    """LLM responds with a bare JSON object — the happy path."""

    def test_simple_object(self):
        assert _extract_json('{"key": "value"}') == {"key": "value"}

    def test_nested_object(self):
        assert _extract_json('{"outer": {"inner": 42}}') == {"outer": {"inner": 42}}

    def test_object_with_array(self):
        assert _extract_json('{"items": [1, 2, 3], "count": 3}') == {"items": [1, 2, 3], "count": 3}

    def test_leading_trailing_whitespace(self):
        assert _extract_json('   \n  {"key": "value"}   \n') == {"key": "value"}

    def test_numeric_values(self):
        assert _extract_json('{"score": 0.85, "count": 3, "flag": false}') == {"score": 0.85, "count": 3, "flag": False}

    def test_null_value(self):
        assert _extract_json('{"name": null}') == {"name": None}

    def test_empty_object(self):
        assert _extract_json("{}") == {}


class TestExtractJsonCodeBlock:
    """LLM wraps its JSON in a markdown code block."""

    def test_json_fenced_block(self):
        assert _extract_json('```json\n{"key": "value"}\n```') == {"key": "value"}

    def test_plain_fenced_block(self):
        assert _extract_json('```\n{"key": "value"}\n```') == {"key": "value"}

    def test_fenced_block_with_prose_before(self):
        raw = 'Here is the output:\n\n```json\n{"key": "value"}\n```'
        assert _extract_json(raw) == {"key": "value"}

    def test_fenced_block_multiline_json(self):
        raw = '```json\n{\n  "agent_id": "agent_2",\n  "confidence": 0.75\n}\n```'
        assert _extract_json(raw) == {"agent_id": "agent_2", "confidence": 0.75}


class TestExtractJsonEmbeddedInProse:
    """LLM adds explanatory prose before or after the JSON object."""

    def test_json_after_prose(self):
        assert _extract_json('Here is the result: {"key": "value"} hope this helps') == {"key": "value"}

    def test_json_after_colon_newline(self):
        assert _extract_json('Here is my analysis:\n\n{"score": 0.8}') == {"score": 0.8}

    def test_nested_json_in_prose(self):
        raw = 'The analysis result: {"findings": {"stage": 3}, "confidence": 0.7} done.'
        assert _extract_json(raw) == {"findings": {"stage": 3}, "confidence": 0.7}


class TestExtractJsonMalformed:
    """LLM produces invalid JSON — function must return None gracefully."""

    def test_missing_closing_brace(self):
        assert _extract_json('{"key": "value"') is None

    def test_trailing_comma(self):
        assert _extract_json('{"key": "value",}') is None

    def test_single_quotes(self):
        assert _extract_json("{'key': 'value'}") is None

    def test_truncated_mid_string(self):
        assert _extract_json('{"message": "this string is cut off') is None


class TestExtractJsonEdgeCases:

    def test_empty_string(self):
        assert _extract_json("") is None

    def test_whitespace_only(self):
        assert _extract_json("   \n\t  ") is None

    def test_no_json_at_all(self):
        assert _extract_json("Sorry, I cannot analyze this transcript.") is None

    def test_json_array_extracts_inner_object(self):
        # _find_json_object finds the { inside the array, so inner object is extracted
        assert _extract_json('[{"key": "value"}]') == {"key": "value"}

    def test_two_objects_returns_first(self):
        assert _extract_json('First: {"a": 1} and then {"b": 2}') == {"a": 1}


# ---------------------------------------------------------------------------
# Tests: _find_json_object
# ---------------------------------------------------------------------------


class TestFindJsonObject:
    def test_simple_extraction(self):
        assert _find_json_object('prefix {"key": "val"} suffix') == '{"key": "val"}'

    def test_no_opening_brace(self):
        assert _find_json_object("no braces here") is None

    def test_brace_inside_string_value(self):
        text = '{"template": "use {placeholder} here"}'
        assert _find_json_object(text) == text

    def test_nested_depth(self):
        text = '{"a": {"b": {"c": 1}}}'
        assert _find_json_object(text) == text

    def test_unclosed_returns_none(self):
        assert _find_json_object('{"key": "value"') is None


# ---------------------------------------------------------------------------
# Tests: strip_for_downstream
# ---------------------------------------------------------------------------


class TestStripForDownstream:

    def test_removes_evidence(self):
        result = strip_for_downstream({
            "agent_id": "agent_2",
            "evidence": [{"quote": "text", "interpretation": "matters"}],
            "findings": {"champion": {"identified": True}},
            "confidence": {"overall": 0.75, "rationale": "good"},
        })
        assert "evidence" not in result

    def test_removes_narrative(self):
        result = strip_for_downstream({
            "agent_id": "agent_2",
            "narrative": "Long explanation...",
            "findings": {"multithreading_depth": "Moderate"},
            "confidence": {"overall": 0.70},
        })
        assert "narrative" not in result

    def test_removes_data_quality_notes_from_findings(self):
        result = strip_for_downstream({
            "agent_id": "agent_3",
            "findings": {
                "commercial_signals": "budget confirmed",
                "data_quality_notes": ["Only one transcript"],
            },
            "confidence": {"overall": 0.60},
        })
        assert "data_quality_notes" not in result["findings"]
        assert "commercial_signals" in result["findings"]

    def test_preserves_agent_id(self):
        result = strip_for_downstream({"agent_id": "agent_4", "findings": {}, "confidence": {"overall": 0.8}})
        assert result["agent_id"] == "agent_4"

    def test_preserves_findings_core(self):
        result = strip_for_downstream({
            "agent_id": "agent_5",
            "findings": {"technical_fit": "strong", "integration_risk": "low"},
            "confidence": {"overall": 0.85},
        })
        assert result["findings"] == {"technical_fit": "strong", "integration_risk": "low"}

    def test_strips_confidence_to_overall_only(self):
        result = strip_for_downstream({
            "agent_id": "agent_6",
            "confidence": {"overall": 0.72, "rationale": "verbose", "data_gaps": ["gap"]},
            "findings": {},
        })
        assert result["confidence"] == {"overall": 0.72}

    def test_preserves_sparse_data_flag(self):
        result = strip_for_downstream({
            "agent_id": "agent_8",
            "sparse_data_flag": True,
            "findings": {},
            "confidence": {"overall": 0.55},
        })
        assert result["sparse_data_flag"] is True

    def test_empty_output(self):
        assert strip_for_downstream({}) == {}

    def test_full_roundtrip(self):
        result = strip_for_downstream({
            "agent_id": "agent_2",
            "narrative": "Prose...",
            "evidence": [{"quote": "q", "interpretation": "i"}],
            "sparse_data_flag": False,
            "transcript_count_analyzed": 4,
            "findings": {
                "stakeholders": [{"name": "Alice"}],
                "data_quality_notes": ["Note"],
            },
            "confidence": {"overall": 0.80, "rationale": "good", "data_gaps": ["gap"]},
        })
        assert "evidence" not in result
        assert "narrative" not in result
        assert "data_quality_notes" not in result.get("findings", {})
        assert "rationale" not in result.get("confidence", {})
        assert result["agent_id"] == "agent_2"
        assert result["findings"]["stakeholders"] == [{"name": "Alice"}]
        assert result["confidence"]["overall"] == 0.80


# ---------------------------------------------------------------------------
# Tests: build_analysis_prompt
# ---------------------------------------------------------------------------


class TestBuildAnalysisPrompt:

    _INSTRUCTION = "Analyze relationship dynamics."
    _TRANSCRIPTS = ["Transcript A text here.", "Transcript B text here."]

    def test_minimal_call(self):
        prompt = build_analysis_prompt(self._TRANSCRIPTS, None, None, self._INSTRUCTION)
        assert "Transcript A text here." in prompt
        assert "Transcript B text here." in prompt
        assert self._INSTRUCTION in prompt
        assert "2 full transcripts" in prompt

    def test_call_numbering(self):
        prompt = build_analysis_prompt(["First.", "Second."], None, None, "Analyze.")
        assert "Call 1 of 2" in prompt
        assert "Call 2 of 2" in prompt

    def test_with_stage_context(self):
        ctx = {
            "deal_type": "new_logo",
            "stage_model": "new_logo_7",
            "inferred_stage": 3,
            "stage_name": "Evaluation",
            "confidence": 0.80,
            "reasoning": "Consistent signals.",
        }
        prompt = build_analysis_prompt(self._TRANSCRIPTS, ctx, None, self._INSTRUCTION)
        assert "STAGE CONTEXT" in prompt
        assert "Evaluation" in prompt

    def test_without_stage_context_omits_section(self):
        prompt = build_analysis_prompt(self._TRANSCRIPTS, None, None, self._INSTRUCTION)
        assert "STAGE CONTEXT" not in prompt

    def test_with_expansion_deal_context(self):
        deal = {"deal_type": "expansion_upsell", "prior_contract_value": 50000}
        prompt = build_analysis_prompt(self._TRANSCRIPTS, None, None, self._INSTRUCTION, deal_context=deal)
        assert "DEAL CONTEXT" in prompt
        assert "EXPANSION" in prompt
        assert "$50,000" in prompt

    def test_new_logo_omits_deal_context(self):
        deal = {"deal_type": "new_logo"}
        prompt = build_analysis_prompt(self._TRANSCRIPTS, None, None, self._INSTRUCTION, deal_context=deal)
        assert "DEAL CONTEXT" not in prompt

    def test_with_timeline(self):
        timeline = ["2025-01-15 | Discovery call", "2025-02-01 | Technical deep-dive"]
        prompt = build_analysis_prompt(self._TRANSCRIPTS, None, timeline, self._INSTRUCTION)
        assert "DEAL TIMELINE" in prompt
        assert "Discovery call" in prompt

    def test_without_timeline_omits_section(self):
        prompt = build_analysis_prompt(self._TRANSCRIPTS, None, None, self._INSTRUCTION)
        assert "DEAL TIMELINE" not in prompt

    def test_empty_timeline_omits_section(self):
        prompt = build_analysis_prompt(self._TRANSCRIPTS, None, [], self._INSTRUCTION)
        assert "DEAL TIMELINE" not in prompt

    def test_instruction_appended(self):
        prompt = build_analysis_prompt(["text"], None, None, "Do the thing now.")
        assert "Do the thing now." in prompt
        assert "Respond with JSON only." in prompt


# ---------------------------------------------------------------------------
# Tests: _inject_deterministic_fields
# ---------------------------------------------------------------------------


class TestInjectDeterministicFields:

    def test_injects_transcript_count(self):
        model = _ModelWithBothFields()
        _inject_deterministic_fields(model, transcript_count=5)
        assert model.transcript_count_analyzed == 5

    def test_sparse_flag_true_when_lte_2(self):
        for count in [1, 2]:
            model = _ModelWithBothFields()
            _inject_deterministic_fields(model, transcript_count=count)
            assert model.sparse_data_flag is True

    def test_sparse_flag_false_when_gte_3(self):
        for count in [3, 4, 10]:
            model = _ModelWithBothFields()
            _inject_deterministic_fields(model, transcript_count=count)
            assert model.sparse_data_flag is False

    def test_noop_when_count_is_none(self):
        model = _ModelWithBothFields(transcript_count_analyzed=99, sparse_data_flag=True)
        _inject_deterministic_fields(model, transcript_count=None)
        assert model.transcript_count_analyzed == 99
        assert model.sparse_data_flag is True

    def test_no_error_when_model_lacks_fields(self):
        model = _ModelWithoutFields()
        _inject_deterministic_fields(model, transcript_count=3)
        assert model.agent_id == "agent_test"

    def test_partial_model_count_only(self):
        model = _ModelWithCountOnly()
        _inject_deterministic_fields(model, transcript_count=7)
        assert model.transcript_count_analyzed == 7
