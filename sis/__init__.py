"""Riskified Sales Intelligence System (SIS)"""

# Patch asyncio to allow nested event loops (required for Streamlit + async agents)
import nest_asyncio as _nest_asyncio
_nest_asyncio.apply()
