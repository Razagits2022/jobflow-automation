"""Pipeline error types and the RunStatus enum.

All custom exceptions derive from RuntimeError so callers can catch them
broadly (``except Exception``) without special imports, while still allowing
narrow catches (``except CaptchaEncounteredError``) when the distinction matters.
"""

from __future__ import annotations

from enum import StrEnum


class RunStatus(StrEnum):
    """Lifecycle states for an ApplicationRun.

    Terminal states (no further transitions):
        SUBMITTED, FAILED, FAILED_CAPTCHA, FAILED_VALIDATION, SKIPPED_DUPLICATE
    """

    QUEUED = "QUEUED"
    """Run has been enqueued but not yet picked up by a worker."""

    RUNNING = "RUNNING"
    """Worker is actively executing the pipeline for this run."""

    SUBMITTED = "SUBMITTED"
    """Application was submitted successfully. Confirmation artifact saved."""

    FAILED = "FAILED"
    """Unhandled error during the pipeline. Error reason and artifact saved."""

    FAILED_CAPTCHA = "FAILED_CAPTCHA"
    """Anti-bot / CAPTCHA wall detected. Pipeline stopped. Screenshot and HTML saved."""

    FAILED_VALIDATION = "FAILED_VALIDATION"
    """Form-level validation errors detected after fill attempt. Details saved."""

    SKIPPED_DUPLICATE = "SKIPPED_DUPLICATE"
    """Candidate already has a SUBMITTED run for the same normalised URL. Run skipped."""


class CaptchaEncounteredError(RuntimeError):
    """Raised by ``detect_captcha`` when an anti-bot challenge is detected.

    The pipeline catches this, sets status=FAILED_CAPTCHA, saves artifacts, and stops.
    No CAPTCHA-solving or bypass is attempted — this is a terminal outcome by design.
    """


class ValidationFailedError(RuntimeError):
    """Raised when the form shows validation errors after a fill attempt.

    The pipeline catches this, sets status=FAILED_VALIDATION, saves artifacts, and stops.
    """

    def __init__(self, message: str, field_errors: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.field_errors: dict[str, str] = field_errors or {}
