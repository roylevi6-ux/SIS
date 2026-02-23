"""Riskified Sales Intelligence System (SIS)"""

# Patch asyncio to allow nested event loops (required for Streamlit + async agents).
# Skip when running under uvloop (used by uvicorn) — uvloop doesn't support patching.
import asyncio as _asyncio

try:
    _loop = _asyncio.get_event_loop()
except RuntimeError:
    _loop = None

if _loop is None or type(_loop).__module__ != "uvloop":
    import nest_asyncio as _nest_asyncio
    _nest_asyncio.apply()
