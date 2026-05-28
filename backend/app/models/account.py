"""WebAccount model — account pool for web channel (P2)."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WebAccount(Base):
    __tablename__ = "web_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(100), nullable=False)

    # Status values: active | paused | need_relogin | disabled
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)

    # Path to user_data_dir or storage_state JSON file — never store raw cookies here
    storage_state_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)

    daily_quota: Mapped[int] = mapped_column(Integer, nullable=False, default=40)
    used_today: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quota_reset_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paused_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
