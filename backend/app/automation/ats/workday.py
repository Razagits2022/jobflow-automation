"""Workday ATS adapter."""

from __future__ import annotations

from app.automation.ats.base import AtsAdapter
from app.automation.ats.generic import GenericAdapter


class WorkdayAdapter(GenericAdapter):
    """ATS adapter for Workday (myworkdayjobs.com domains).

    Currently delegates to GenericAdapter; specialized overrides come in follow-up.
    """


_: AtsAdapter = WorkdayAdapter()
