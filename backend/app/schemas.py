import re

from pydantic import BaseModel, Field, field_validator


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """Plain `str` avoids optional `email-validator` dependency for Pydantic's `EmailStr`."""

    email: str = Field(..., min_length=3, max_length=255)
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class AccountOut(BaseModel):
    id: int
    name: str
    slug: str

    class Config:
        from_attributes = True


class DealershipOut(BaseModel):
    id: int
    account_id: int
    code: str
    name: str
    address_line: str
    phone: str
    website: str

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    file_id: str
    filename: str


class JobCreate(BaseModel):
    account_id: int
    dealership_ids: list[int] = Field(..., min_length=1)
    formats: list[str] = Field(
        ...,
        description="Subset of 1080x1080, 1080x1350, 1080x1920",
    )
    logo_enabled: bool = True
    logo_file_id: str | None = None
    logo_file_ids: list[str] | None = Field(
        None,
        description="Optional pool: each output cycles file ids in order (e.g. 5 ids for 5 different logos).",
    )
    extra_assets_enabled: bool = False
    headline: str | None = None
    body: str | None = None
    promo_word: str | None = Field(None, max_length=32, description="Large hero word, e.g. SALE")
    price_display: str | None = Field(None, max_length=48, description="Shown in price disc, e.g. $59,000")
    accent_hex: str | None = Field(None, max_length=16, description="Wedge color #RRGGBB")
    background_file_id: str | None = Field(
        None,
        description="Optional hero image; omit for solid/gradient from accent only.",
    )
    creative_template: str = Field(
        "promo_split",
        max_length=24,
        description="Template id: promo_split, visit_dealer, hero_band, dealer_bottom, dealer_left, dealer_overlay, dealer_minimal, auto, brand_overlay",
    )
    ai_generate_background: bool = Field(
        False,
        description="If true and no background upload: OpenAI Images API generates the hero (needs OPENAI_API_KEY).",
    )

    @field_validator("creative_template")
    @classmethod
    def normalize_template(cls, v: str) -> str:
        t = (v or "promo_split").strip().lower()
        allowed = frozenset(
            {
                "promo_split",
                "visit_dealer",
                "hero_band",
                "dealer_bottom",
                "dealer_left",
                "dealer_overlay",
                "dealer_minimal",
                "auto",
                "brand_overlay",
            }
        )
        if t not in allowed:
            raise ValueError(f"creative_template must be one of: {', '.join(sorted(allowed))}")
        return t

    @field_validator("logo_file_ids")
    @classmethod
    def normalize_logo_ids(cls, v: list[str] | None) -> list[str] | None:
        if not v:
            return None
        out = [s.strip() for s in v if s and str(s).strip()]
        if len(out) > 48:
            raise ValueError("logo_file_ids must have at most 48 entries")
        return out or None

    @field_validator("promo_word", "price_display")
    @classmethod
    def strip_opt(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s or None

    @field_validator("accent_hex")
    @classmethod
    def validate_hex(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        if not s:
            return None
        if not re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", s):
            raise ValueError("accent_hex must be like #f97316 or #f93")
        return s


class JobStatus(BaseModel):
    id: int
    status: str
    total_tasks: int
    completed_tasks: int
    error_message: str | None
    warning_message: str | None = None
    progress_percent: float

    class Config:
        from_attributes = True


class OutputItem(BaseModel):
    id: int
    dealership_id: int
    dealership_name: str
    format_key: str
    url: str

    class Config:
        from_attributes = True


class ZipSelection(BaseModel):
    output_ids: list[int] | None = None
