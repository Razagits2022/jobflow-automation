"""Lever ATS adapter."""

from __future__ import annotations

from app.automation.ats.base import AtsAdapter
from app.automation.ats.generic import GenericAdapter


class LeverAdapter(GenericAdapter):
    """ATS adapter for Lever (jobs.lever.co domains).

    Currently delegates to GenericAdapter; specialized overrides come in follow-up.
    """


_: AtsAdapter = LeverAdapter()
