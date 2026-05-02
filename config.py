"""
config.py
=========
Central configuration for the AI-QG application.
Loads environment variables, validates required settings, and provides path constants.
"""

import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env file
# ---------------------------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------------------------
# Base paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
IS_VERCEL = os.getenv("VERCEL") == "1"

if IS_VERCEL:
    UPLOAD_DIR = Path("/tmp/uploads")
    OUTPUT_DIR = Path("/tmp/outputs")
    LOG_DIR = Path("/tmp/logs")
    EXPORT_DIR = Path("/tmp/exports")
else:
    UPLOAD_DIR = BASE_DIR / "uploads"
    OUTPUT_DIR = BASE_DIR / "outputs"
    LOG_DIR = BASE_DIR / "logs"
    STATIC_DIR = BASE_DIR / "static"
    EXPORT_DIR = STATIC_DIR / "exports"

# Ensure directories exist
for _dir in [UPLOAD_DIR, OUTPUT_DIR, LOG_DIR, EXPORT_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Flask settings
# ---------------------------------------------------------------------------
class FlaskConfig:
    """Flask application configuration."""

    SECRET_KEY: str = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))
    DEBUG: bool = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")
    HOST: str = os.getenv("FLASK_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("FLASK_PORT", "5000"))
    MAX_CONTENT_LENGTH: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "16")) * 1024 * 1024


# ---------------------------------------------------------------------------
# Supabase settings
# ---------------------------------------------------------------------------
class SupabaseConfig:
    """Supabase connection configuration."""

    URL: str = os.getenv("SUPABASE_URL", "")
    KEY: str = os.getenv("SUPABASE_KEY", "")
    STORAGE_BUCKET: str = "documents"

    @classmethod
    def validate(cls) -> bool:
        """Return True if Supabase credentials are configured."""
        return bool(cls.URL and cls.KEY)


# ---------------------------------------------------------------------------
# Hugging Face settings
# ---------------------------------------------------------------------------
class HuggingFaceConfig:
    """Hugging Face API configuration."""

    API_TOKEN: str = os.getenv("HF_API_TOKEN", "")
    PRIMARY_MODEL: str = "valhalla/t5-base-qg-hl"
    FALLBACK_MODEL: str = "iarfmoose/t5-base-question-generator"
    API_URL: str = "https://api-inference.huggingface.co/models/"
    TIMEOUT: int = 60
    MAX_RETRIES: int = 3

    @classmethod
    def validate(cls) -> bool:
        """Return True if HF API token is configured."""
        return bool(cls.API_TOKEN)


# ---------------------------------------------------------------------------
# NLP settings
# ---------------------------------------------------------------------------
class NLPConfig:
    """NLP pipeline configuration."""

    SPACY_MODEL: str = "en_core_web_md"
    SENTENCE_TRANSFORMER_MODEL: str = "all-MiniLM-L6-v2"
    MIN_SENTENCE_LENGTH: int = 5
    MAX_KEYWORDS: int = 30
    TOP_SENTENCES: int = 20
    SIMILARITY_THRESHOLD: float = 0.85


# ---------------------------------------------------------------------------
# Logging settings
# ---------------------------------------------------------------------------
class LogConfig:
    """Logging configuration."""

    LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
    DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    FILE: Path = LOG_DIR / "app.log"


# ---------------------------------------------------------------------------
# Allowed file extensions
# ---------------------------------------------------------------------------
ALLOWED_EXTENSIONS: set[str] = {"pdf", "docx", "txt"}


def allowed_file(filename: str) -> bool:
    """Check if a filename has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
