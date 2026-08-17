from __future__ import annotations

from pathlib import Path
from typing import Any

from .docx import analyze_docx
from .image import analyze_image_bytes

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}


def local_forensic_analysis(data: bytes, filename: str) -> dict[str, Any]:
    ext = Path(filename).suffix.lower()
    if ext == ".docx":
        return analyze_docx(data)
    if ext in IMAGE_EXTS:
        return {"format": ext.lstrip("."), "image": analyze_image_bytes(data, filename)}
    return {
        "format": ext.lstrip(".") or "unknown",
        "note": "A análise forense local aprofundada deste MVP está implementada para DOCX e imagens. Para este formato, o relatório principal vem do watermarks-remover.",
    }
