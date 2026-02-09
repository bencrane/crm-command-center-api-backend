import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SalesforceConnection(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "salesforce_connections"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Encrypted tokens (Fernet-encrypted strings stored as text)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)

    instance_url: Mapped[str] = mapped_column(String(512), nullable=False)
    salesforce_org_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationship
    organization = relationship("Organization", back_populates="salesforce_connections")

    def __repr__(self) -> str:
        return f"<SalesforceConnection id={self.id} org_id={self.org_id}>"
