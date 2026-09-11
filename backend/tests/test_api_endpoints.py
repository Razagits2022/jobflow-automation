"""Test suite for Phase 1 API endpoints."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_subscribe_endpoint() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/subscribe")
        assert res.status_code == 200
        assert res.json() == {"subscribed": True}


@pytest.mark.asyncio
async def test_candidate_endpoints() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Update candidate with simplified schema
        payload = {
            "fullName": "Jane Tester",
            "email": "jane.tester@example.com",
            "phone": "+1 (555) 234-5678",
            "location": "New York, NY",
            "workAuthorized": True,
            "resumeSummary": "Staff Backend Engineer with 7 years experience in Python, FastAPI, PostgreSQL, and Docker. MS Computer Science.",
        }
        put_res = await client.put("/api/candidate", json=payload)
        assert put_res.status_code == 200
        data = put_res.json()
        assert data["fullName"] == "Jane Tester"
        assert data["email"] == "jane.tester@example.com"
        assert "Staff Backend Engineer" in data["resumeSummary"]

        # 2. Get candidate
        get_res = await client.get("/api/candidate")
        assert get_res.status_code == 200
        cand_data = get_res.json()
        assert cand_data["fullName"] == "Jane Tester"
        assert cand_data["resumeSummary"] == payload["resumeSummary"]


@pytest.mark.asyncio
async def test_candidate_legacy_fallback() -> None:
    """Verify that a candidate profile stored with legacy fields synthesizes resumeSummary on read."""
    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.models.candidate import Candidate

    async with AsyncSessionLocal() as session:
        stmt = select(Candidate).order_by(Candidate.created_at.asc()).limit(1)
        res = await session.execute(stmt)
        cand = res.scalar_one_or_none()
        if cand:
            cand.profile = {
                "location": "Boston, MA",
                "title": "Lead Architect",
                "yearsExperience": 10,
                "education": "BS Information Systems",
                "skills": ["Go", "Kubernetes", "AWS"],
            }
            await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        get_res = await client.get("/api/candidate")
        assert get_res.status_code == 200
        data = get_res.json()
        assert "Lead Architect" in data["resumeSummary"]
        assert "Years of Experience: 10" in data["resumeSummary"]
        assert "BS Information Systems" in data["resumeSummary"]
        assert "Kubernetes" in data["resumeSummary"]


@pytest.mark.asyncio
async def test_candidate_resume_upload() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resume_content = b"""Alex Rivera
alex.rivera@example.com
+1 (555) 987-6543
Full Stack Engineer
Austin, TX

Experience:
5 years building web applications with Python, React, and PostgreSQL.

Education:
BS in Computer Engineering
"""
        files = {"file": ("test_resume.txt", resume_content, "text/plain")}
        res = await client.post("/api/candidate/resume", files=files)
        assert res.status_code == 200
        data = res.json()
        assert "fullName" in data
        assert "email" in data
        assert data["email"] == "alex.rivera@example.com" or "@" in data["email"]


@pytest.mark.asyncio
async def test_jobs_and_runs_workflow() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Post new job URLs
        job_urls = [
            "https://jobs.lever.co/example/frontend-engineer",
            "https://boards.greenhouse.io/example/python-dev",
        ]
        post_res = await client.post("/api/jobs", json={"urls": job_urls})
        assert post_res.status_code == 201
        created_jobs = post_res.json()
        assert len(created_jobs) >= 1

        first_job_id = created_jobs[0]["id"]

        # 2. Get queued jobs
        list_res = await client.get("/api/jobs")
        assert list_res.status_code == 200
        queued_list = list_res.json()
        assert any(j["id"] == first_job_id for j in queued_list)

        # 3. Start applying
        start_res = await client.post("/api/runs/start")
        assert start_res.status_code == 200
        runs_data = start_res.json()
        assert isinstance(runs_data, list)

        # 4. Get runs
        runs_res = await client.get("/api/runs")
        assert runs_res.status_code == 200
        runs_list = runs_res.json()
        assert len(runs_list) >= 1
        assert "status" in runs_list[0]
        assert "createdAt" in runs_list[0]

        # 5. Get stats
        stats_res = await client.get("/api/stats")
        assert stats_res.status_code == 200
        stats = stats_res.json()
        assert stats["total"] >= 1
        assert "submitted" in stats
        assert "failedCaptcha" in stats
