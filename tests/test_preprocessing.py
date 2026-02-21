"""Test transcript preprocessing — filler removal, speaker normalization, truncation."""

from __future__ import annotations


class TestRemoveFillers:
    def test_removes_um(self):
        from sis.services.transcript_service import _remove_fillers
        result = _remove_fillers("So um I think we should proceed")
        assert "um" not in result
        assert "I think we should proceed" in result

    def test_removes_uh(self):
        from sis.services.transcript_service import _remove_fillers
        result = _remove_fillers("The deal is uh going well")
        assert "uh" not in result

    def test_removes_basically(self):
        from sis.services.transcript_service import _remove_fillers
        result = _remove_fillers("We basically, need to close this deal")
        assert "basically" not in result.lower()

    def test_removes_essentially(self):
        from sis.services.transcript_service import _remove_fillers
        result = _remove_fillers("It's essentially, a good deal")
        assert "essentially" not in result.lower()

    def test_preserves_meaningful_content(self):
        from sis.services.transcript_service import _remove_fillers
        text = "The timeline for deployment is three months."
        result = _remove_fillers(text)
        assert result == text

    def test_cleans_double_spaces(self):
        from sis.services.transcript_service import _remove_fillers
        result = _remove_fillers("We um need this um done")
        assert "  " not in result

    def test_empty_input(self):
        from sis.services.transcript_service import _remove_fillers
        result = _remove_fillers("")
        assert result == ""


class TestNormalizeSpeakers:
    def test_simple_speaker(self):
        from sis.services.transcript_service import _normalize_speakers
        result = _normalize_speakers("John Smith: Hello everyone")
        assert result == "JOHN SMITH: Hello everyone"

    def test_speaker_with_company(self):
        from sis.services.transcript_service import _normalize_speakers
        result = _normalize_speakers("Jane Doe (Riskified): Let me explain")
        assert "JANE DOE" in result
        assert "(Riskified)" in result

    def test_already_uppercase(self):
        from sis.services.transcript_service import _normalize_speakers
        result = _normalize_speakers("ALICE JONES: Testing")
        assert result == "ALICE JONES: Testing"

    def test_non_speaker_line_preserved(self):
        from sis.services.transcript_service import _normalize_speakers
        result = _normalize_speakers("This is regular content without a speaker.")
        assert result == "This is regular content without a speaker."

    def test_multiline(self):
        from sis.services.transcript_service import _normalize_speakers
        text = "Alice: Hello\nBob: Hi there\nRegular line"
        result = _normalize_speakers(text)
        assert "ALICE: Hello" in result
        assert "BOB: Hi there" in result
        assert "Regular line" in result


class TestPreprocess:
    def test_returns_text_and_token_count(self):
        from sis.services.transcript_service import _preprocess
        result = _preprocess("Hello world")
        assert "text" in result
        assert "token_count" in result
        assert result["token_count"] > 0

    def test_short_text_not_truncated(self):
        from sis.services.transcript_service import _preprocess
        result = _preprocess("Short text")
        assert "[TRUNCATED" not in result["text"]

    def test_truncation_applied_for_long_text(self):
        from sis.services.transcript_service import _preprocess, MAX_TOKEN_BUDGET
        # Generate text that exceeds 8K tokens (roughly 4 chars per token)
        long_text = "This is a test sentence. " * 10000  # ~250K chars, ~50K tokens
        result = _preprocess(long_text)
        assert result["token_count"] == MAX_TOKEN_BUDGET
        assert "[TRUNCATED AT 8K TOKENS]" in result["text"]

    def test_preprocessing_removes_fillers(self):
        from sis.services.transcript_service import _preprocess
        text = "John: Um, I think we should um proceed with the deal"
        result = _preprocess(text)
        assert "um" not in result["text"].lower().split()

    def test_preprocessing_normalizes_speakers(self):
        from sis.services.transcript_service import _preprocess
        text = "john smith: Hello everyone"
        result = _preprocess(text)
        assert "JOHN SMITH:" in result["text"]
