# SIS
Riskified Sales Intelligence System — 10-agent AI pipeline for deal health analysis from Gong transcripts

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 15 + TypeScript + Radix UI |
| **API** | FastAPI (Python) |
| **Backend** | Python services + SQLAlchemy ORM |
| **Database** | SQLite (PostgreSQL-compatible schema) |
| **LLM** | Anthropic Claude via LiteLLM |

## Quick Start

```bash
# Backend (port 8000)
cd /Users/roylevierez/Documents/Sales/SIS
source .venv/bin/activate
uvicorn sis.api.main:app --reload

# Frontend (port 3000)
cd frontend
npm run dev
```

## Project Structure

```
sis/
├── api/              # FastAPI routes + schemas
├── agents/           # 10-agent pipeline (prompts + output models)
├── orchestrator/     # Pipeline execution (asyncio)
├── preprocessor/     # Gong transcript parsing
├── services/         # Business logic (accounts, transcripts, gdrive, etc.)
├── db/               # SQLAlchemy ORM models + engine
└── config.py         # Environment + YAML config

frontend/
├── src/app/          # Next.js pages (App Router)
├── src/components/   # React components (Radix UI)
├── src/lib/          # API client, hooks, auth, types
└── package.json

planning/             # PRD, Technical Architecture, POC Build Plan
docs/plans/           # Feature implementation plans
```
