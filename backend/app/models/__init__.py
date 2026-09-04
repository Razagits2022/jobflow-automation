"""ORM models package.

Import all models here so Alembic can discover them for autogenerate.
"""

from app.models.candidate import Candidate, Resume  # noqa: F401
from app.models.job import JobPosting  # noqa: F401
from app.models.run import ApplicationRun, FieldResult  # noqa: F401
