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
        # 1. Update candidate
        payload = {
            "fullName": "Jane Tester",
            "email": "jane.tester@example.com",
            "phone": "+1 (555) 234-5678",
            "location": "New York, NY",
            "title": "Staff Backend Engineer",
            "yearsExperience": 7,
            "workAuthorized": True,
            "education": "MS Computer Science",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
        }
        put_res = await client.put("/api/candidate", json=payload)
        assert put_res.status_code == 200
        data = put_res.json()
        assert data["fullName"] == "Jane Tester"
        assert data["email"] == "jane.tester@example.com"
        assert data["yearsExperience"] == 7
        assert "FastAPI" in data["skills"]

        # 2. Get candidate
        get_res = await client.get("/api/candidate")
        assert get_res.status_code == 200
        cand_data = get_res.json()
        assert cand_data["fullName"] == "Jane Tester"
        assert cand_data["title"] == "Staff Backend Engineer"


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
