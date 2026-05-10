import os
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND_ROOT / ".env")


class Settings:
    def __init__(self) -> None:
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
        self.secret_key: str = os.getenv("SECRET_KEY", "change-me-in-production-use-openssl-rand-hex-32")
        self.algorithm: str = "HS256"
        self.access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24)))
        self.database_url: str = os.getenv(
            "DATABASE_URL",
            "sqlite:///" + (_BACKEND_ROOT / "data" / "app.db").resolve().as_posix(),
        )
        self.upload_dir: Path = Path(os.getenv("UPLOAD_DIR", str(_BACKEND_ROOT / "data" / "uploads")))
        self.output_dir: Path = Path(os.getenv("OUTPUT_DIR", str(_BACKEND_ROOT / "data" / "outputs")))
        self.openai_api_key: str | None = os.getenv("OPENAI_API_KEY") or None
        self.openai_api_base: str = (os.getenv("OPENAI_API_BASE") or "https://api.openai.com/v1").rstrip("/")
        self.openai_image_model: str = os.getenv("OPENAI_IMAGE_MODEL", "dall-e-3")


def describe_openai_key_for_logs(key: str | None) -> str:
    """Safe one-line status for logs. Never log the full key."""
    if not (key and str(key).strip()):
        return "OPENAI_API_KEY: not set"
    k = str(key).strip()
    n = len(k)
    if n < 12:
        return f"OPENAI_API_KEY: set (len={n}, value looks truncated — check .env)"
    return f"OPENAI_API_KEY: set, preview {k[:7]}…{k[-4:]} (len={n})"


settings = Settings()
