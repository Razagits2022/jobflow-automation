"""Inter-job pacing. All delay logic lives here so it can be toggled in one place.

Controlled by settings.inter_job_delay_enabled:
  - False (testing): every offset is zero, jobs run immediately.
  - True (production): each job starts a random 5-20 min after the previous one.
"""

from __future__ import annotations

import random
from datetime import timedelta

from app.core.config import settings


def _random_gap_seconds() -> float:
    lo = settings.inter_job_delay_min_minutes * 60
    hi = settings.inter_job_delay_max_minutes * 60
    return random.uniform(lo, hi)


def compute_start_offsets(count: int) -> list[timedelta]:
    """Return a start offset per job. First job starts now; each next one is
    deferred by a random gap after the previous. All zero when disabled."""
    if not settings.inter_job_delay_enabled or count <= 0:
        return [timedelta(0) for _ in range(max(count, 0))]
    offsets: list[timedelta] = []
    cumulative = 0.0
    for _ in range(count):
        offsets.append(timedelta(seconds=cumulative))
        cumulative += _random_gap_seconds()
    return offsets
