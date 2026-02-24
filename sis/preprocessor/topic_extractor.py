"""Per-call business topic extraction via Haiku.

Extracts 2 concise business topic labels from a call transcript.
Runs at import time (zero dependency on the agent pipeline).

Usage:
    from sis.preprocessor.topic_extractor import extract_business_topics
    topics = extract_business_topics(preprocessed_text)
    # [{"name": "Pricing Negotiation", "duration": 0}, {"name": "Security Compliance", "duration": 0}]
"""

from __future__ import annotations

import json
import logging
import re

from sis.llm.client import get_client

logger = logging.getLogger(__name__)

MODEL = "anthropic/claude-haiku-4-5-20251001"

# How much transcript text to send (keeps cost ~$0.002/call)
_MAX_INPUT_CHARS = 6000

_SYSTEM_PROMPT = """\
You extract the 2 most important BUSINESS topics discussed in a sales call transcript.

Rules:
- Output exactly 2 topics as a JSON array: [{"name": "Topic 1"}, {"name": "Topic 2"}]
- Each topic name must be 2-4 words, in English, title case
- Focus on BUSINESS substance: what was negotiated, evaluated, planned, or decided
- Good examples: "Pricing Negotiation", "Technical POC", "Security Compliance", "Contract Terms", "Chargeback Analysis", "Integration Timeline", "Renewal Discussion"
- BAD examples (never output these): "Small Talk", "Call Setup", "Introductions", "Wrap-Up", "Follow Up", "Next Steps", "General Discussion", "Agenda Review"
- If the call is mostly introductory, extract the business topics that were introduced (e.g., "Product Overview", "Use Case Discovery")
- Always output English labels, even if the transcript is in another language
- Output ONLY the JSON array, nothing else"""

_FEW_SHOT_USER = """\
CALL TITLE: Riskified // JD UK - Chargeback Data Simulation
PARTICIPANTS: John Smith (VP Payments, JD), Sarah Lee (Solutions Engineer, Riskified)

JOHN SMITH (JD): Thanks for setting this up. We've been seeing chargeback rates creep up to about 1.2% on our UK cards...
SARAH LEE (Riskified): That's above the Visa threshold. Let me walk you through how our simulation model works with your historical data...
[...discussion about chargeback patterns, fraud detection thresholds, and integration with JD's payment stack...]
JOHN SMITH: And what about the 3D Secure implementation? We're worried about conversion drop-off...
SARAH LEE: Great question. Our approach is to selectively trigger 3DS only on high-risk transactions..."""

_FEW_SHOT_ASSISTANT = '[{"name": "Chargeback Analysis"}, {"name": "3D Secure Strategy"}]'


def extract_business_topics(
    transcript_text: str,
    call_title: str | None = None,
) -> list[dict] | None:
    """Extract 2 business topics from a transcript using Haiku.

    Args:
        transcript_text: Preprocessed transcript text (from to_agent_text() or DB).
        call_title: Optional call title for additional context.

    Returns:
        List of topic dicts [{"name": "Topic", "duration": 0}] or None on failure.
    """
    # Truncate to budget — take first 60% and last 40% for best coverage
    text = transcript_text.strip()
    if len(text) > _MAX_INPUT_CHARS:
        first_chunk = int(_MAX_INPUT_CHARS * 0.6)
        last_chunk = _MAX_INPUT_CHARS - first_chunk
        text = text[:first_chunk] + "\n\n[...]\n\n" + text[-last_chunk:]

    # Build user message with title context
    user_msg = ""
    if call_title:
        user_msg += f"CALL TITLE: {call_title}\n\n"
    user_msg += text

    try:
        client = get_client()
        response = client.messages.create(
            model=MODEL,
            max_tokens=100,
            system=_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": _FEW_SHOT_USER},
                {"role": "assistant", "content": _FEW_SHOT_ASSISTANT},
                {"role": "user", "content": user_msg},
            ],
        )

        raw = response.content[0].text.strip()

        # Parse JSON — handle potential markdown wrapping
        json_match = re.search(r'\[.*\]', raw, re.DOTALL)
        if not json_match:
            logger.warning("Topic extraction returned non-JSON: %s", raw[:100])
            return None

        topics = json.loads(json_match.group())

        # Validate structure
        if not isinstance(topics, list) or len(topics) == 0:
            return None

        result = []
        for t in topics[:2]:
            name = t.get("name", "").strip()
            if name and len(name) <= 30:
                result.append({"name": name, "duration": 0})

        return result if result else None

    except Exception as e:
        logger.warning("Topic extraction failed: %s", str(e))
        return None
