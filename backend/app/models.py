from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    jobs: Mapped[list["CreativeJob"]] = relationship(back_populates="user")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    logo_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    dealerships: Mapped[list["Dealership"]] = relationship(back_populates="account")


class Dealership(Base):
    __tablename__ = "dealerships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line: Mapped[str] = mapped_column(String(512), default="")
    phone: Mapped[str] = mapped_column(String(64), default="")
    website: Mapped[str] = mapped_column(String(255), default="")
    panel_image_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    account: Mapped["Account"] = relationship(back_populates="dealerships")


class CreativeJob(Base):
    __tablename__ = "creative_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    background_path: Mapped[str] = mapped_column(String(512), nullable=False)
    logo_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    logo_upload_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    logo_file_ids_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_assets_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    dealership_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    formats_json: Mapped[str] = mapped_column(Text, nullable=False)
    headline: Mapped[str | None] = mapped_column(String(512), nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    promo_word: Mapped[str | None] = mapped_column(String(32), nullable=True)
    price_display: Mapped[str | None] = mapped_column(String(48), nullable=True)
    accent_hex: Mapped[str | None] = mapped_column(String(16), nullable=True)
    creative_template: Mapped[str] = mapped_column(String(24), default="promo_split", nullable=False)
    ai_generate_background: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    total_tasks: Mapped[int] = mapped_column(Integer, default=0)
    completed_tasks: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    warning_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="jobs")
    outputs: Mapped[list["CreativeOutput"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class CreativeOutput(Base):
    __tablename__ = "creative_outputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("creative_jobs.id"), nullable=False, index=True)
    dealership_id: Mapped[int] = mapped_column(ForeignKey("dealerships.id"), nullable=False)
    format_key: Mapped[str] = mapped_column(String(32), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    dealership_name: Mapped[str] = mapped_column(String(255), default="")

    job: Mapped["CreativeJob"] = relationship(back_populates="outputs")
