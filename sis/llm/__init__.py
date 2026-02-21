"""LLM abstraction layer — prompt loading, model routing."""

from .prompt_loader import load_prompt, load_base_fragment, get_prompt_metadata

__all__ = ["load_prompt", "load_base_fragment", "get_prompt_metadata"]
