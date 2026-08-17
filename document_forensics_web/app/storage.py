from __future__ import annotations

import json
import shutil
import time
import uuid
from pathlib import Path

from .config import JOBS_DIR, JOB_TTL_MINUTES


def ensure_storage() -> None:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)


def cleanup_expired_jobs() -> None:
    ensure_storage()
    cutoff = time.time() - JOB_TTL_MINUTES * 60
    for path in JOBS_DIR.iterdir():
        if not path.is_dir():
            continue
        try:
            if path.stat().st_mtime < cutoff:
                shutil.rmtree(path, ignore_errors=True)
        except FileNotFoundError:
            pass


def create_job() -> tuple[str, Path]:
    ensure_storage()
    cleanup_expired_jobs()
    job_id = uuid.uuid4().hex
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=False)
    return job_id, job_dir


def get_job_dir(job_id: str) -> Path:
    if not job_id or any(c not in "0123456789abcdef" for c in job_id.lower()) or len(job_id) != 32:
        raise FileNotFoundError("invalid job id")
    path = JOBS_DIR / job_id
    if not path.is_dir():
        raise FileNotFoundError("job not found or expired")
    path.touch(exist_ok=True)
    return path


def write_manifest(job_dir: Path, payload: dict) -> None:
    (job_dir / "manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_manifest(job_dir: Path) -> dict:
    return json.loads((job_dir / "manifest.json").read_text(encoding="utf-8"))
