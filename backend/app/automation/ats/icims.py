"""ICIMS ATS adapter."""

from __future__ import annotations

from app.automation.ats.base import AtsAdapter
from app.automation.ats.generic import GenericAdapter


class ICIMSAdapter(GenericAdapter):
    """ATS adapter for iCIMS (icims.com domains).

    Currently delegates to GenericAdapter; specialized overrides come in follow-up.
    """


_: AtsAdapter = ICIMSAdapter()
