from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
JOBS_DIR = BASE_DIR / "data" / "jobs"
STATIC_DIR = BASE_DIR / "app" / "static"

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "75"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
JOB_TTL_MINUTES = int(os.getenv("JOB_TTL_MINUTES", "30"))
WATERMARKS_SERVICE_URL = os.getenv("WATERMARKS_SERVICE_URL", "http://127.0.0.1:18765").rstrip("/")
WATERMARKS_API_KEY = os.getenv("WATERMARKS_API_KEY", "")

ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".html", ".htm",
    ".docx", ".odt", ".epub", ".pdf",
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".svg",
}
