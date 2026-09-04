"""Greenhouse ATS adapter."""

from __future__ import annotations

from app.automation.ats.base import AtsAdapter
from app.automation.ats.generic import GenericAdapter


class GreenhouseAdapter(GenericAdapter):
    """ATS adapter for Greenhouse (boards.greenhouse.io domains).

    Currently delegates to GenericAdapter; specialized overrides come in follow-up.
    """


_: AtsAdapter = GreenhouseAdapter()
