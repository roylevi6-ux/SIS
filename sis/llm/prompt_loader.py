"""Prompt loader — loads YAML prompt templates and renders with Jinja2.

Per Technical Architecture Appendix A:
- Each prompt is a YAML file with metadata + system_prompt
- Jinja2 variables (account_name, transcripts, stage_context, calibration)
  are rendered at call time
- Prompts are loaded from the prompts/ directory at project root
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from jinja2 import Environment, BaseLoader

from sis.config import PROJECT_ROOT

PROMPTS_DIR = PROJECT_ROOT / "prompts"

# Cache loaded prompts
_prompt_cache: dict[str, dict] = {}


def load_prompt(agent_filename: str, variables: Optional[dict] = None) -> str:
    """Load and render a prompt template.

    Args:
        agent_filename: YAML filename (e.g., "agent_01_stage.yml")
        variables: Optional Jinja2 template variables for rendering

    Returns:
        Rendered system prompt string
    """
    prompt_data = _load_yaml(agent_filename)
    system_prompt = prompt_data.get("system_prompt", "")

    if variables:
        env = Environment(loader=BaseLoader())
        template = env.from_string(system_prompt)
        system_prompt = template.render(**variables)

    return system_prompt


def load_base_fragment() -> str:
    """Load the shared base prompt fragment (evidence rules, confidence scale)."""
    base_data = _load_yaml("_base.yml")
    return base_data.get("fragment", "")


def get_prompt_metadata(agent_filename: str) -> dict:
    """Get metadata for a prompt template (agent_id, name, version, model)."""
    prompt_data = _load_yaml(agent_filename)
    return prompt_data.get("metadata", {})


def list_prompts() -> list[dict]:
    """List all available prompt templates with their metadata."""
    prompts = []
    for path in sorted(PROMPTS_DIR.glob("agent_*.yml")):
        data = _load_yaml(path.name)
        meta = data.get("metadata", {})
        meta["filename"] = path.name
        prompts.append(meta)
    return prompts


def _load_yaml(filename: str) -> dict:
    """Load and cache a YAML prompt file."""
    if filename in _prompt_cache:
        return _prompt_cache[filename]

    path = PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    _prompt_cache[filename] = data
    return data
