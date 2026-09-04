# 🚀 JobFlow — Autonomous AI Job Application Engine

[![Next.js](https://img.shields.io/badge/Next.js-16.3-black?style=for-the-badge&logo=next.js)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19.0-61DAFB?style=for-the-badge&logo=react)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python)](https://python.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v4.0-38B2AC?style=for-the-badge&logo=tailwind-css)](https://tailwindcss.com/)
[![Playwright](https://img.shields.io/badge/Playwright-Automation-2EAD33?style=for-the-badge&logo=playwright)](https://playwright.dev/)
[![DeepSeek](https://img.shields.io/badge/DeepSeek-AI_Reasoning-FF6F00?style=for-the-badge)](https://deepseek.com/)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?style=for-the-badge&logo=supabase)](https://supabase.com/)

**JobFlow** is a full-stack, autonomous job application platform designed to apply to tech job postings completely hands-free. Powered by DeepSeek AI reasoning, Playwright browser automation, and an asynchronous task queue, JobFlow extracts form fields, maps candidate profiles, uploads tailored resumes, handles custom dropdowns, detects CAPTCHA challenges, and records visual screenshot proofs of every submission.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Next.js App Shell (Port 3000)                     │
│  - /profile  (Profile & Skills)      - /apply (Job URL Staging & CSV)       │
│  - /runs     (Live Polling & Proof)  - /dashboard (Aggregated Metrics)      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTP / REST (/api/*)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FastAPI REST Service (Port 8000)                  │
│  - Candidate & Resume Upload API     - Job URL Enqueue & Deduplication      │
│  - Application Run Dispatcher        - Visual Proof Streaming               │
└──────────────────┬───────────────────┬──────────────────────────────────────┘
                   │                   │
    Async Sessions │      Arq Task     │ Shared Redis Connection Pool
    (Supabase)     ▼      Enqueue      ▼ (127.0.0.1:6379)
┌───────────────────────┐   ┌─────────────────────────────────────────────────┐
│  PostgreSQL Database  │   │          Arq Background Worker Process          │
│  - candidates         │   │  - Unhandled Error Containment                  │
│  - resumes            │   │  - Duplicate Application Guard                  │
│  - job_postings       │   └────────────────────────┬────────────────────────┘
│  - application_runs   │                            │
│  - field_results      │                            │ Executes
└───────────────────────┘                            ▼
                            ┌─────────────────────────────────────────────────┐
                            │          Playwright Automation Pipeline         │
                            │  1. Zyte Extract & DeepSeek AI Job Analysis     │
                            │  2. Application Nav & Popup Tab Handling        │
                            │  3. DOM Input/Select/File Field Extraction      │
                            │  4. DeepSeek Profile-to-Field Mapping           │
                            │  5. Controlled Form Filling & Resume Upload     │
                            │  6. Challenge Detection (Turnstile/reCAPTCHA)   │
                            │  7. Form Validation & Submit Verification       │
                            │  8. Screenshot Proof Artifact Persistence       │
                            └─────────────────────────────────────────────────┘
```

---

## ✨ Key Features

- 🧠 **AI Perception & Field Mapping**: Parses resumes (`.pdf`, `.docx`, `.txt`) and reasons over arbitrary DOM structures via DeepSeek LLM (with heuristic offline fallback).
- 🤖 **Autonomous Browser Execution**: Native Playwright automation engine tailored for **Workday**, **Greenhouse**, **Lever**, **iCIMS**, and generic custom portals.
- ⚡ **Background Worker Queue**: Distributed task processing powered by **Arq** and **Redis** with unhandled error containment.
- 📸 **Audit Trail & Proof Verification**: Captures and streams full-page confirmation screenshots for every run (`/api/runs/{id}/screenshot`).
- 🛡️ **Defensive Protection**: Anti-duplicate application guards and active challenge detection (Cloudflare Turnstile, reCAPTCHA, hCaptcha, PerimeterX, DataDome).
- 🎨 **Unified Design System**: Clean SaaS layout built with Next.js 16 App Router, React 19, Tailwind CSS v4 CSS-first tokens, and Zustand.

---

## 📁 Repository Structure

```
JobAutomation/
├── backend/                  # FastAPI Application & Worker Service
│   ├── app/
│   │   ├── api/              # REST API Routes (/api/candidate, /api/jobs, /api/runs)
│   │   ├── automation/       # Playwright Pipeline, Adapters & Steps
│   │   ├── core/             # App Settings & Shared Redis Pool
│   │   ├── db/               # SQLAlchemy Async Engine & Supabase Session
│   │   ├── integrations/     # DeepSeek AI, Zyte Extraction & Resume Parser
│   │   ├── models/           # SQLAlchemy Declarative Models
│   │   ├── schemas/          # Pydantic Request & Response Schemas
│   │   └── workers/          # Arq Background Task Worker
│   ├── alembic/              # Database Migrations
│   ├── tests/                # Pytest Test Suite & Playwright Smoke Tests
│   └── pyproject.toml        # Python Dependencies (uv / hatchling)
│
└── frontend/                 # Next.js 16 Web Console & Marketing Site
    ├── src/
    │   ├── app/              # App Router Routes ((marketing), (flow), (app))
    │   ├── components/       # Reusable UI Primitives (Button, Card, StatusBadge)
    │   └── lib/              # Zustand Store & Axios API Client
    └── package.json          # Frontend Dependencies (pnpm / npm)
```

---

## 🚀 Quickstart & Installation

### Prerequisites

- **Node.js** v18+ and **pnpm** (or `npm`)
- **Python** v3.11+ and **`uv`** package manager
- **Redis Server** running locally on `127.0.0.1:6379`
- **PostgreSQL Database** (e.g. Supabase project)

---

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Install Python dependencies
uv sync

# Install Playwright browser binaries
uv run playwright install chromium

# Copy environment template & update credentials
cp .env.example .env

# Run database migrations (Alembic)
uv run alembic upgrade head

# Start FastAPI API server (Port 8000)
uv run uvicorn app.main:app --port 8000 --reload
```

In a separate terminal, start the **Arq worker process**:

```bash
cd backend
uv run arq app.workers.worker.WorkerSettings
```

---

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies
pnpm install

# Start Next.js development server (Port 3000)
pnpm dev
```

Open `http://localhost:3000` in your browser to access JobFlow!

---

## ⚙️ Environment Variables

### Backend Config (`backend/.env`)

| Variable | Description |
|---|---|
| `DATABASE_URL` | Supabase / PostgreSQL async connection string (`postgresql+asyncpg://...`) |
| `REDIS_URL` | Redis connection URL (`redis://127.0.0.1:6379/0`) |
| `DEEPSEEK_API_KEY` | DeepSeek LLM API key (`sk-...`) |
| `ZYTE_API_KEY` | Zyte API key for structured job scraping |
| `APP_ENV` | Environment mode (`development` / `production`) |
| `LOG_LEVEL` | Application logging level (`INFO` / `DEBUG`) |

### Frontend Config (`frontend/.env.local`)

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_URL` | Base URL of the FastAPI backend (`http://localhost:8000`) |

---

## 🧪 Testing & Quality Gates

### Backend Verification

```bash
cd backend

# Run complete pytest test suite
uv run pytest

# Code linting check
uv run ruff check

# Strict static type checking
uv run mypy app
```

### Frontend Verification

```bash
cd frontend

# TypeScript type check
pnpm tsc --noEmit

# ESLint check
pnpm lint

# Production build check
pnpm build
```

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.
