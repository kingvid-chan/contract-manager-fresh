"""ORM models — import all here so Base.metadata knows about every table."""

from app.models.user import User  # noqa: F401
from app.models.contract import Contract  # noqa: F401
from app.models.attachment import Attachment  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
