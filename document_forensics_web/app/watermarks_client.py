from __future__ import annotations

import base64
import httpx

from .config import WATERMARKS_API_KEY, WATERMARKS_SERVICE_URL


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if WATERMARKS_API_KEY:
        headers["Authorization"] = f"Bearer {WATERMARKS_API_KEY}"
    return headers


async def health() -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{WATERMARKS_SERVICE_URL}/health", headers=_headers())
        r.raise_for_status()
        return r.json()


async def capabilities() -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{WATERMARKS_SERVICE_URL}/capabilities", headers=_headers())
        r.raise_for_status()
        return r.json()


async def inspect_file(data: bytes, name: str) -> dict:
    payload = {"file": base64.b64encode(data).decode("ascii"), "name": name}
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(f"{WATERMARKS_SERVICE_URL}/inspect", headers=_headers(), json=payload)
        r.raise_for_status()
        return r.json()


async def clean_file(data: bytes, name: str, options: dict | None = None) -> tuple[bytes, dict]:
    payload = {
        "file": base64.b64encode(data).decode("ascii"),
        "name": name,
        "options": options or {},
    }
    async with httpx.AsyncClient(timeout=180.0) as client:
        r = await client.post(f"{WATERMARKS_SERVICE_URL}/clean", headers=_headers(), json=payload)
        r.raise_for_status()
        result = r.json()
    cleaned = base64.b64decode(result["cleaned"])
    return cleaned, result
