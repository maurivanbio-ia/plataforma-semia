from __future__ import annotations

import io
from typing import Any

from PIL import Image, ExifTags


def analyze_image_bytes(data: bytes, name: str = "image") -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": name,
        "format": None,
        "width": None,
        "height": None,
        "mode": None,
        "metadata": {},
        "exif": {},
        "software": None,
    }
    try:
        with Image.open(io.BytesIO(data)) as im:
            result.update({
                "format": im.format,
                "width": im.width,
                "height": im.height,
                "mode": im.mode,
            })
            metadata = {}
            for k, v in (im.info or {}).items():
                if isinstance(v, (str, int, float, bool)):
                    metadata[str(k)] = v
                elif isinstance(v, bytes) and len(v) <= 256:
                    metadata[str(k)] = v.decode("utf-8", errors="replace")
            result["metadata"] = metadata

            exif_out = {}
            try:
                exif = im.getexif()
                for tag_id, value in exif.items():
                    tag = ExifTags.TAGS.get(tag_id, str(tag_id))
                    if isinstance(value, bytes):
                        value = value[:256].decode("utf-8", errors="replace")
                    elif not isinstance(value, (str, int, float, bool)):
                        value = str(value)[:500]
                    exif_out[tag] = value
            except Exception:
                pass
            result["exif"] = exif_out

            software_candidates = [
                metadata.get("Software"), metadata.get("software"),
                exif_out.get("Software"), exif_out.get("ProcessingSoftware"),
            ]
            result["software"] = next((x for x in software_candidates if x), None)
    except Exception as exc:
        result["error"] = f"Não foi possível interpretar a imagem: {exc}"
    return result
