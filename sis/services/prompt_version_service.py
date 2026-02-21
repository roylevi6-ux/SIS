"""Prompt version control service — Git-like versioning with rollback per PRD Sec 8.

Manages prompt versions per agent: create, list, rollback, and diff.
"""

from __future__ import annotations

import difflib
from typing import Optional

from sis.db.session import get_session
from sis.db.models import PromptVersion


def list_versions(agent_id: Optional[str] = None) -> list[dict]:
    """List all prompt versions, optionally filtered by agent_id."""
    with get_session() as session:
        query = session.query(PromptVersion).order_by(
            PromptVersion.agent_id, PromptVersion.created_at.desc()
        )
        if agent_id:
            query = query.filter_by(agent_id=agent_id)
        return [
            {
                "id": v.id,
                "agent_id": v.agent_id,
                "version": v.version,
                "prompt_template": v.prompt_template,
                "calibration_config_version": v.calibration_config_version,
                "change_notes": v.change_notes,
                "is_active": bool(v.is_active),
                "created_at": v.created_at,
            }
            for v in query.all()
        ]


def get_active_version(agent_id: str) -> Optional[dict]:
    """Get the currently active prompt version for an agent."""
    with get_session() as session:
        v = (
            session.query(PromptVersion)
            .filter_by(agent_id=agent_id, is_active=1)
            .order_by(PromptVersion.created_at.desc())
            .first()
        )
        if not v:
            return None
        return {
            "id": v.id,
            "agent_id": v.agent_id,
            "version": v.version,
            "prompt_template": v.prompt_template,
            "calibration_config_version": v.calibration_config_version,
            "change_notes": v.change_notes,
            "is_active": True,
            "created_at": v.created_at,
        }


def create_version(
    agent_id: str,
    version: str,
    prompt_template: str,
    change_notes: Optional[str] = None,
    calibration_config_version: Optional[str] = None,
) -> dict:
    """Create a new prompt version, deactivating previous active version."""
    with get_session() as session:
        # Deactivate all previous versions for this agent
        session.query(PromptVersion).filter_by(
            agent_id=agent_id, is_active=1
        ).update({"is_active": 0})

        new_version = PromptVersion(
            agent_id=agent_id,
            version=version,
            prompt_template=prompt_template,
            change_notes=change_notes,
            calibration_config_version=calibration_config_version,
            is_active=1,
        )
        session.add(new_version)
        session.flush()
        return {
            "id": new_version.id,
            "agent_id": new_version.agent_id,
            "version": new_version.version,
            "is_active": True,
            "created_at": new_version.created_at,
        }


def rollback_version(agent_id: str, version_id: str) -> dict:
    """Reactivate a previous version, deactivating the current one."""
    with get_session() as session:
        target = session.query(PromptVersion).filter_by(id=version_id).one_or_none()
        if not target:
            raise ValueError(f"Version not found: {version_id}")
        if target.agent_id != agent_id:
            raise ValueError(f"Version {version_id} does not belong to agent {agent_id}")

        # Deactivate all versions for this agent
        session.query(PromptVersion).filter_by(
            agent_id=agent_id, is_active=1
        ).update({"is_active": 0})

        # Activate the target version
        target.is_active = 1
        session.flush()
        return {
            "id": target.id,
            "agent_id": target.agent_id,
            "version": target.version,
            "is_active": True,
        }


def diff_versions(version_id_a: str, version_id_b: str) -> str:
    """Return a unified diff between two prompt versions."""
    with get_session() as session:
        a = session.query(PromptVersion).filter_by(id=version_id_a).one_or_none()
        b = session.query(PromptVersion).filter_by(id=version_id_b).one_or_none()
        if not a:
            raise ValueError(f"Version A not found: {version_id_a}")
        if not b:
            raise ValueError(f"Version B not found: {version_id_b}")

        diff = difflib.unified_diff(
            a.prompt_template.splitlines(keepends=True),
            b.prompt_template.splitlines(keepends=True),
            fromfile=f"{a.agent_id} v{a.version}",
            tofile=f"{b.agent_id} v{b.version}",
        )
        return "".join(diff)
