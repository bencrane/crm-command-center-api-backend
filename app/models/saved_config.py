import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SavedConfig(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "saved_configs"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    config_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # e.g. "dashboard", "workflow", "report"
    config_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship
    organization = relationship("Organization", back_populates="saved_configs")

    def __repr__(self) -> str:
        return f"<SavedConfig id={self.id} type={self.config_type} org_id={self.org_id}>"
