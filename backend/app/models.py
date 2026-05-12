"""Pydantic schemas representing SurrealDB records."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class JobAttempt(BaseModel):
    id: Optional[str] = None
    job_id: str
    attempt_number: int
    phase: str
    code_generated: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    success: bool
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class User(BaseModel):
    id: Optional[str] = None
    username: str
    role: str = "user"  # admin | user
    organization_id: Optional[str] = None
    # Wallet auth (Solana/Phantom) — primary auth method
    wallet_address: Optional[str] = None  # Solana public key
    # Billing
    plan: str = "free"  # free | pro | enterprise
    pages_used_month: int = 0
    pages_limit: int = 100  # Based on plan tier
    plan_expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True


class SegmentReview(BaseModel):
    id: Optional[str] = None
    job_id: str
    index: int
    source: str
    target: Optional[str] = None
    edited: Optional[str] = None
    confidence: float = 0.0
    status: str = "pending"  # pending | approved | edited
    location: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Job(BaseModel):
    id: Optional[str] = None
    owner_id: Optional[str] = None
    filename: str
    file_type: str
    file_path: str
    output_path: Optional[str] = None
    xliff_path: Optional[str] = None
    status: str = "pending"
    progress: float = 0.0
    progress_message: Optional[str] = None
    error_message: Optional[str] = None
    segments_count: Optional[int] = None
    duration_seconds: Optional[float] = None
    source_lang: str = "ja"
    target_lang: str = "vi"
    domain: str = "general"
    webhook_url: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GlossaryTerm(BaseModel):
    id: Optional[str] = None
    owner_id: Optional[str] = None
    source_lang: str = "ja"
    target_lang: str = "vi"
    domain: str = "general"
    source_text: str
    target_text: str
    context: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def jp(self) -> str:
        return self.source_text

    @property
    def vi(self) -> str:
        return self.target_text


class ApiKey(BaseModel):
    id: Optional[str] = None
    owner_id: str
    name: str  # "My CI/CD Pipeline"
    key_hash: str  # SHA-256 hash of actual key
    key_prefix: str  # "itk_translate_a1b2c3" (display)
    scope: str = "translate"  # read | translate | admin
    requests_count: int = 0
    requests_limit: Optional[int] = None  # null = unlimited
    pages_used: int = 0
    pages_limit: Optional[int] = None  # null = unlimited
    last_used: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
