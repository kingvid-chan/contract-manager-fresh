"""Contract model — core business entity with status lifecycle."""

from datetime import datetime, timezone, date
from sqlalchemy import (
    String, Integer, DateTime, Date, Numeric, Text, ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# Valid status transitions
STATUS_FLOW = {
    "draft": ["pending_review", "terminated"],
    "pending_review": ["approved", "draft"],
    "approved": ["active", "draft"],
    "active": ["expired", "terminated"],
    "expired": [],  # terminal
    "terminated": [],  # terminal
}

VALID_STATUSES = list(STATUS_FLOW.keys())


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_no: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    party_a: Mapped[str] = mapped_column(String(256), nullable=False)
    party_b: Mapped[str] = mapped_column(String(256), nullable=False)
    sign_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    creator: Mapped["User"] = relationship("User", lazy="joined")
    attachments: Mapped[list["Attachment"]] = relationship(
        "Attachment", back_populates="contract", lazy="selectin", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Contract id={self.id} no={self.contract_no!r} status={self.status!r}>"

    def can_transition_to(self, target_status: str) -> bool:
        """Check if this contract's status can move to target_status."""
        return target_status in STATUS_FLOW.get(self.status, [])
