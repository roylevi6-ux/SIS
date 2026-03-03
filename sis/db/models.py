"""SQLAlchemy ORM models — all 10 tables per Technical Architecture Section 4.

Design principles:
- TEXT for timestamps (ISO 8601), UUIDs, and JSON columns (SQLite compat)
- INTEGER for booleans (0/1 for SQLite, maps to BOOLEAN in PostgreSQL)
- REAL for money/scores (maps to NUMERIC in PostgreSQL)
- All JSON columns store serialized JSON strings
- Foreign keys enforced via PRAGMA in SQLite, native in PostgreSQL
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, ForeignKey, Index, Integer, Text, Float, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


# ─── users ─────────────────────────────────────────────────────────────


class User(Base):
    __tablename__ = "users"

    id = Column(Text, primary_key=True, default=_uuid)
    name = Column(Text, nullable=False)
    email = Column(Text, nullable=False, unique=True)
    role = Column(Text, nullable=False)  # admin | gm | vp | team_lead | ic
    team_id = Column(Text, ForeignKey("teams.id"), nullable=True)
    is_active = Column(Integer, default=1)  # boolean
    created_at = Column(Text, nullable=False, default=_now)

    # Relationships
    team = relationship("Team", foreign_keys=[team_id], back_populates="members")

    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_role", "role"),
    )


# ─── user_preferences ─────────────────────────────────────────────────


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Text, primary_key=True, default=_uuid)
    user_id = Column(Text, ForeignKey("users.id"), nullable=False)
    preference_key = Column(Text, nullable=False)
    preference_value = Column(Text, nullable=False)  # JSON string
    updated_at = Column(Text, nullable=False, default=_now)

    __table_args__ = (
        UniqueConstraint("user_id", "preference_key", name="uq_user_preference"),
        Index("ix_user_preferences_user", "user_id"),
    )


# ─── teams ─────────────────────────────────────────────────────────────


class Team(Base):
    __tablename__ = "teams"

    id = Column(Text, primary_key=True, default=_uuid)
    name = Column(Text, nullable=False)
    parent_id = Column(Text, ForeignKey("teams.id"), nullable=True)
    leader_id = Column(Text, ForeignKey("users.id", use_alter=True), nullable=True)
    level = Column(Text, nullable=False)  # org | division | team
    created_at = Column(Text, nullable=False, default=_now)

    # Relationships
    parent = relationship("Team", remote_side=[id], backref="children")
    leader = relationship("User", foreign_keys=[leader_id])
    members = relationship("User", foreign_keys=[User.team_id], back_populates="team")

    __table_args__ = (
        Index("ix_teams_parent", "parent_id"),
        Index("ix_teams_level", "level"),
    )


# ─── accounts ───────────────────────────────────────────────────────────


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Text, primary_key=True, default=_uuid)
    account_name = Column(Text, nullable=False)
    cp_estimate = Column(Float, nullable=True)  # Contribution Profit estimate ($)
    ic_forecast_category = Column(Text, nullable=True)  # Commit/Realistic/Upside/At Risk
    team_lead = Column(Text, nullable=True)
    ae_owner = Column(Text, nullable=True)
    team_name = Column(Text, nullable=True)
    deal_type = Column(Text, nullable=False, default="new_logo")  # new_logo | expansion_upsell | expansion_cross_sell | expansion_both
    prior_contract_value = Column(Float, nullable=True)  # Existing MRR if applicable
    sf_stage = Column(Integer, nullable=True)  # SF stage number (1-7)
    sf_forecast_category = Column(Text, nullable=True)  # "Commit" / "Realistic" / "Upside" / "At Risk"
    sf_close_quarter = Column(Text, nullable=True)  # Expected close quarter, e.g. "Q2 2026"
    owner_id = Column(Text, ForeignKey("users.id"), nullable=True)
    created_at = Column(Text, nullable=False, default=_now)
    updated_at = Column(Text, nullable=False, default=_now, onupdate=_now)

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    transcripts = relationship("Transcript", back_populates="account", order_by="Transcript.call_date.desc()")
    analysis_runs = relationship("AnalysisRun", back_populates="account", order_by="AnalysisRun.started_at.desc()")
    deal_assessments = relationship("DealAssessment", back_populates="account", order_by="DealAssessment.created_at.desc()")
    score_feedback = relationship("ScoreFeedback", back_populates="account")
    coaching_entries = relationship("CoachingEntry", back_populates="account")


# ─── transcripts ────────────────────────────────────────────────────────


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(Text, primary_key=True, default=_uuid)
    account_id = Column(Text, ForeignKey("accounts.id"), nullable=False)
    call_date = Column(Text, nullable=False)  # ISO 8601 date
    participants = Column(Text, nullable=True)  # JSON array [{name, role, company}]
    duration_minutes = Column(Integer, nullable=True)
    raw_text = Column(Text, nullable=False)
    preprocessed_text = Column(Text, nullable=True)
    token_count = Column(Integer, nullable=True)
    call_title = Column(Text, nullable=True)  # Short title from Gong (e.g. "QBR", "Technical Review")
    call_topics = Column(Text, nullable=True)  # JSON: [{"name": "Pricing", "duration": 120}]
    gong_call_id = Column(Text, nullable=True)  # Gong's unique call ID for dedup
    upload_source = Column(Text, default="manual")
    is_active = Column(Integer, default=1)  # boolean: 1=active, 0=archived
    created_at = Column(Text, nullable=False, default=_now)

    # Relationships
    account = relationship("Account", back_populates="transcripts")

    __table_args__ = (
        Index("ix_transcripts_account_date", "account_id", "call_date"),
        UniqueConstraint("account_id", "gong_call_id", name="uq_transcript_gong_call"),
    )


# ─── analysis_runs ──────────────────────────────────────────────────────


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id = Column(Text, primary_key=True, default=_uuid)
    account_id = Column(Text, ForeignKey("accounts.id"), nullable=False)
    started_at = Column(Text, nullable=False, default=_now)
    completed_at = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="pending")  # pending/running/completed/failed/partial
    trigger = Column(Text, default="manual")  # manual/scheduled/rerun
    transcript_ids = Column(Text, nullable=True)  # JSON array of transcript IDs
    total_input_tokens = Column(Integer, nullable=True)
    total_output_tokens = Column(Integer, nullable=True)
    total_cost_usd = Column(Float, nullable=True)
    model_versions = Column(Text, nullable=True)  # JSON: {agent_1: "haiku", ...}
    prompt_config_version = Column(Text, nullable=True)
    error_log = Column(Text, nullable=True)  # JSON array of errors
    deal_type_at_run = Column(Text, nullable=True)  # Snapshots which pipeline mode was used

    # Relationships
    account = relationship("Account", back_populates="analysis_runs")
    agent_analyses = relationship("AgentAnalysis", back_populates="analysis_run", order_by="AgentAnalysis.agent_id")
    deal_assessment = relationship("DealAssessment", back_populates="analysis_run", uselist=False)

    __table_args__ = (
        Index("ix_analysis_runs_account", "account_id", "started_at"),
    )


# ─── agent_analyses ─────────────────────────────────────────────────────


class AgentAnalysis(Base):
    __tablename__ = "agent_analyses"

    id = Column(Text, primary_key=True, default=_uuid)
    analysis_run_id = Column(Text, ForeignKey("analysis_runs.id"), nullable=False)
    account_id = Column(Text, ForeignKey("accounts.id"), nullable=False)  # denormalized
    agent_id = Column(Text, nullable=False)  # agent_1_stage, agent_2_relationship, etc.
    agent_name = Column(Text, nullable=False)
    transcript_count_analyzed = Column(Integer, nullable=True)
    narrative = Column(Text, nullable=False)
    findings = Column(Text, nullable=True)  # JSON: agent-specific structured data
    evidence = Column(Text, nullable=True)  # JSON array of evidence citations
    confidence_overall = Column(Float, nullable=True)
    confidence_rationale = Column(Text, nullable=True)
    data_gaps = Column(Text, nullable=True)  # JSON array of strings
    sparse_data_flag = Column(Integer, default=0)  # boolean
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)
    elapsed_seconds = Column(Float, nullable=True)
    prep_seconds = Column(Float, nullable=True)
    model_used = Column(Text, nullable=True)
    retries = Column(Integer, default=0)
    status = Column(Text, default="completed")  # completed/failed/skipped
    created_at = Column(Text, nullable=False, default=_now)

    # Relationships
    analysis_run = relationship("AnalysisRun", back_populates="agent_analyses")

    __table_args__ = (
        Index("ix_agent_analyses_run", "analysis_run_id"),
        Index("ix_agent_analyses_account_agent", "account_id", "agent_id", "created_at"),
    )


# ─── deal_assessments ───────────────────────────────────────────────────


class DealAssessment(Base):
    __tablename__ = "deal_assessments"

    id = Column(Text, primary_key=True, default=_uuid)
    analysis_run_id = Column(Text, ForeignKey("analysis_runs.id"), nullable=False)
    account_id = Column(Text, ForeignKey("accounts.id"), nullable=False)
    deal_type = Column(Text, nullable=True)  # new_logo | expansion_upsell | expansion_cross_sell | expansion_both
    stage_model = Column(Text, nullable=True)  # "new_logo_7stage" | "expansion_7stage"

    # Synthesis narrative
    deal_memo = Column(Text, nullable=False)
    manager_brief = Column(Text, nullable=True)           # VP-targeted blunt advisor brief
    attention_level = Column(Text, nullable=True)          # "act" / "watch" / "none"
    deal_memo_sections = Column(Text, nullable=True)       # JSON: structured sections with health signals
    contradiction_map = Column(Text, nullable=True)  # JSON array
    # Stage inference
    inferred_stage = Column(Integer, nullable=False)
    stage_name = Column(Text, nullable=False)
    stage_confidence = Column(Float, nullable=False)
    stage_reasoning = Column(Text, nullable=True)

    # Health score
    health_score = Column(Integer, nullable=False)
    health_breakdown = Column(Text, nullable=False)  # JSON: component breakdown

    # Confidence
    overall_confidence = Column(Float, nullable=False)
    confidence_rationale = Column(Text, nullable=True)
    key_unknowns = Column(Text, nullable=True)  # JSON array

    # Momentum
    momentum_direction = Column(Text, nullable=False)  # Improving/Stable/Declining
    momentum_trend = Column(Text, nullable=True)

    # Forecast
    ai_forecast_category = Column(Text, nullable=False)  # Commit/Realistic/Upside/At Risk
    forecast_confidence = Column(Float, nullable=True)
    forecast_rationale = Column(Text, nullable=True)

    # Signals and actions
    top_positive_signals = Column(Text, nullable=True)  # JSON array
    top_risks = Column(Text, nullable=True)  # JSON array
    recommended_actions = Column(Text, nullable=True)  # JSON array

    # Divergence (computed post-hoc)
    divergence_flag = Column(Integer, default=0)  # boolean
    divergence_explanation = Column(Text, nullable=True)

    # SF indication snapshot (values at time of analysis run)
    sf_stage_at_run = Column(Integer, nullable=True)
    sf_forecast_at_run = Column(Text, nullable=True)
    sf_close_quarter_at_run = Column(Text, nullable=True)
    cp_estimate_at_run = Column(Float, nullable=True)

    # Gap analysis (computed post-pipeline)
    stage_gap_direction = Column(Text, nullable=True)  # "Aligned" / "SF-ahead" / "SIS-ahead"
    stage_gap_magnitude = Column(Integer, nullable=True)  # Absolute stage difference (0-6)
    forecast_gap_direction = Column(Text, nullable=True)  # "Aligned" / "SF-more-optimistic" / "SIS-more-optimistic"
    sf_gap_interpretation = Column(Text, nullable=True)  # Agent 10's natural language gap analysis

    created_at = Column(Text, nullable=False, default=_now)

    # Relationships
    analysis_run = relationship("AnalysisRun", back_populates="deal_assessment")
    account = relationship("Account", back_populates="deal_assessments")
    score_feedback = relationship("ScoreFeedback", back_populates="deal_assessment")

    __table_args__ = (
        Index("ix_deal_assessments_account", "account_id", "created_at"),
        UniqueConstraint("analysis_run_id", name="uq_deal_assessment_run"),
    )


# ─── score_feedback ─────────────────────────────────────────────────────


class ScoreFeedback(Base):
    __tablename__ = "score_feedback"

    id = Column(Text, primary_key=True, default=_uuid)
    account_id = Column(Text, ForeignKey("accounts.id"), nullable=False)
    deal_assessment_id = Column(Text, ForeignKey("deal_assessments.id"), nullable=False)
    author = Column(Text, nullable=False)
    feedback_date = Column(Text, nullable=False, default=_now)

    health_score_at_time = Column(Integer, nullable=False)
    disagreement_direction = Column(Text, nullable=False)  # too_high / too_low
    reason_category = Column(Text, nullable=False)  # off_channel / stakeholder_context / stage_mismatch / score_too_high / recent_change / other
    free_text = Column(Text, nullable=True)
    off_channel_activity = Column(Integer, default=0)  # boolean

    resolution = Column(Text, default="pending")  # pending / accepted / rejected
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(Text, nullable=True)
    resolved_by = Column(Text, nullable=True)

    created_at = Column(Text, nullable=False, default=_now)

    # Relationships
    account = relationship("Account", back_populates="score_feedback")
    deal_assessment = relationship("DealAssessment", back_populates="score_feedback")

    __table_args__ = (
        Index("ix_score_feedback_account", "account_id", "created_at"),
    )


# ─── coaching_entries ──────────────────────────────────────────────────


class CoachingEntry(Base):
    __tablename__ = "coaching_entries"

    id = Column(Text, primary_key=True, default=_uuid)
    account_id = Column(Text, ForeignKey("accounts.id"), nullable=False)
    rep_name = Column(Text, nullable=False)
    coach_name = Column(Text, nullable=False)
    dimension = Column(Text, nullable=False)
    coaching_date = Column(Text, nullable=False, default=_now)
    feedback_text = Column(Text, nullable=False)
    dimension_score_at_time = Column(Integer, nullable=True)
    health_score_at_time = Column(Integer, nullable=True)
    incorporated = Column(Integer, default=0)  # boolean
    incorporated_at = Column(Text, nullable=True)
    incorporated_notes = Column(Text, nullable=True)
    created_at = Column(Text, nullable=False, default=_now)

    # Relationships
    account = relationship("Account", back_populates="coaching_entries")

    __table_args__ = (
        Index("ix_coaching_entries_rep", "rep_name", "coaching_date"),
        Index("ix_coaching_entries_account", "account_id", "dimension"),
    )


# ─── calibration_logs ───────────────────────────────────────────────────


class CalibrationLog(Base):
    __tablename__ = "calibration_logs"

    id = Column(Text, primary_key=True, default=_uuid)
    calibration_date = Column(Text, nullable=False, default=_now)
    config_version = Column(Text, nullable=False)
    config_previous_version = Column(Text, nullable=True)
    feedback_items_reviewed = Column(Integer, nullable=True)
    agent_prompt_changes = Column(Text, nullable=True)  # JSON
    config_changes = Column(Text, nullable=True)  # JSON
    stage_weight_changes = Column(Text, nullable=True)  # JSON
    golden_test_results = Column(Text, nullable=True)  # JSON
    tl_agreement_rates = Column(Text, nullable=True)  # JSON
    approved_by = Column(Text, nullable=True)
    created_at = Column(Text, nullable=False, default=_now)


# ─── prompt_versions ────────────────────────────────────────────────────


class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id = Column(Text, primary_key=True, default=_uuid)
    agent_id = Column(Text, nullable=False)
    version = Column(Text, nullable=False)
    prompt_template = Column(Text, nullable=False)
    calibration_config_version = Column(Text, nullable=True)
    change_notes = Column(Text, nullable=True)
    is_active = Column(Integer, default=1)  # boolean
    created_at = Column(Text, nullable=False, default=_now)

    __table_args__ = (
        UniqueConstraint("agent_id", "version", name="uq_prompt_version"),
        Index("ix_prompt_active", "agent_id", "is_active"),
    )


# ─── chat_sessions ──────────────────────────────────────────────────────


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Text, primary_key=True, default=_uuid)
    user_name = Column(Text, nullable=True)
    started_at = Column(Text, nullable=False, default=_now)
    last_message_at = Column(Text, nullable=True)

    # Relationships
    messages = relationship("ChatMessage", back_populates="session", order_by="ChatMessage.created_at")


# ─── chat_messages ──────────────────────────────────────────────────────


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Text, primary_key=True, default=_uuid)
    session_id = Column(Text, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(Text, nullable=False)  # user / assistant
    content = Column(Text, nullable=False)
    tokens_used = Column(Integer, nullable=True)
    model_used = Column(Text, nullable=True)
    created_at = Column(Text, nullable=False, default=_now)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")

    __table_args__ = (
        Index("ix_chat_messages_session", "session_id", "created_at"),
    )


# ─── usage_events ──────────────────────────────────────────────────────


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id = Column(Text, primary_key=True, default=_uuid)
    event_type = Column(Text, nullable=False)  # page_view, chat_query, brief_view, feedback_submit, etc.
    user_name = Column(Text, nullable=True)
    account_id = Column(Text, nullable=True)
    page_name = Column(Text, nullable=True)
    event_metadata = Column(Text, nullable=True)  # JSON
    created_at = Column(Text, nullable=False, default=_now)

    __table_args__ = (
        Index("ix_usage_events_type_date", "event_type", "created_at"),
        Index("ix_usage_events_user", "user_name", "created_at"),
    )


# ─── user_action_logs ─────────────────────────────────────────────────


class UserActionLog(Base):
    __tablename__ = "user_action_logs"

    id = Column(Text, primary_key=True, default=_uuid)
    user_name = Column(Text, nullable=True)
    action_type = Column(Text, nullable=False)  # page_view / ic_forecast_set / analysis_run / transcript_upload / feedback_submit / chat_query / brief_export / calibration / setting_change
    action_detail = Column(Text, nullable=True)  # Human-readable description
    account_id = Column(Text, ForeignKey("accounts.id"), nullable=True)
    account_name = Column(Text, nullable=True)  # denormalized for fast display
    page_name = Column(Text, nullable=True)
    ip_address = Column(Text, nullable=True)
    session_id = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)  # JSON: extra context
    created_at = Column(Text, nullable=False, default=_now)

    __table_args__ = (
        Index("ix_action_logs_user_date", "user_name", "created_at"),
        Index("ix_action_logs_type_date", "action_type", "created_at"),
        Index("ix_action_logs_account", "account_id", "created_at"),
    )


# ─── quotas ─────────────────────────────────────────────────────────────


class Quota(Base):
    __tablename__ = "quotas"

    id = Column(Text, primary_key=True, default=_uuid)
    user_id = Column(Text, ForeignKey("users.id"), nullable=False)
    period = Column(Text, nullable=False)    # "2026" for annual
    amount = Column(Float, nullable=False)   # Annual quota in USD
    created_at = Column(Text, default=_now)
    updated_at = Column(Text, default=_now)

    __table_args__ = (
        UniqueConstraint("user_id", "period", name="uq_quota_user_period"),
    )
