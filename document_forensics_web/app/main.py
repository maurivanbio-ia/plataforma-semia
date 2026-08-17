from __future__ import annotations

import json
from pathlib import Path

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .analyzers.generic import local_forensic_analysis
from .analyzers.docx_diff import diff_forensic
from .config import ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES, MAX_UPLOAD_MB, STATIC_DIR
from .reporting import build_summary
from .security import safe_filename, sha256_bytes
from .storage import create_job, get_job_dir, read_manifest, write_manifest
from .watermarks_client import capabilities, clean_file, health, inspect_file

app = FastAPI(
    title="Document Provenance Analyzer",
    version="0.1.0",
    description="Upload, inspeção técnica, proveniência e higienização documental.",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


async def read_upload_limited(upload: UploadFile) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            raise HTTPException(413, f"Arquivo excede o limite de {MAX_UPLOAD_MB} MB.")
        chunks.append(chunk)
    return b"".join(chunks)


def _ext(name: str) -> str:
    return Path(name).suffix.lower()


def _cleaned_name(name: str) -> str:
    p = Path(name)
    return f"{p.stem}_cleaned{p.suffix}"


@app.get("/", response_class=HTMLResponse)
async def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def api_health() -> dict:
    try:
        wm = await health()
        return {"ok": True, "watermarks": wm}
    except Exception as exc:
        return {"ok": False, "watermarks_error": str(exc)}


@app.get("/api/capabilities")
async def api_capabilities() -> dict:
    try:
        return await capabilities()
    except Exception as exc:
        raise HTTPException(503, f"Serviço watermarks-remover indisponível: {exc}")


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)) -> JSONResponse:
    original_name = safe_filename(file.filename or "arquivo")
    extension = _ext(original_name)
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, f"Formato não suportado: {extension or 'sem extensão'}")

    data = await read_upload_limited(file)
    if not data:
        raise HTTPException(400, "Arquivo vazio.")

    job_id, job_dir = create_job()
    original_path = job_dir / original_name
    original_path.write_bytes(data)

    try:
        service_report = await inspect_file(data, original_name)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"Falha no watermarks-remover: HTTP {exc.response.status_code}") from exc
    except Exception as exc:
        raise HTTPException(503, f"Não foi possível alcançar o watermarks-remover: {exc}") from exc

    forensic = local_forensic_analysis(data, original_name)
    summary = build_summary(service_report, forensic)

    manifest = {
        "job_id": job_id,
        "original_name": original_name,
        "cleaned_name": _cleaned_name(original_name),
        "size_bytes": len(data),
        "sha256": sha256_bytes(data),
        "service": service_report,
        "forensic": forensic,
        "summary": summary,
        "clean": None,
    }
    write_manifest(job_dir, manifest)

    return JSONResponse(manifest)


@app.post("/api/clean/{job_id}")
async def clean(job_id: str) -> JSONResponse:
    try:
        job_dir = get_job_dir(job_id)
        manifest = read_manifest(job_dir)
    except FileNotFoundError:
        raise HTTPException(404, "Análise expirada ou inexistente.")

    original_name = manifest["original_name"]
    original_path = job_dir / original_name
    if not original_path.exists():
        raise HTTPException(404, "Arquivo original temporário não encontrado.")

    data = original_path.read_bytes()
    try:
        cleaned, clean_report = await clean_file(data, original_name, options={})
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:1000]
        raise HTTPException(502, f"Falha na higienização: HTTP {exc.response.status_code}: {detail}") from exc
    except Exception as exc:
        raise HTTPException(503, f"Falha ao acessar o serviço de higienização: {exc}") from exc

    cleaned_name = manifest["cleaned_name"]
    cleaned_path = job_dir / cleaned_name
    cleaned_path.write_bytes(cleaned)

    post_forensic = local_forensic_analysis(cleaned, cleaned_name)
    post_inspect = await inspect_file(cleaned, cleaned_name)

    clean_payload = {
        "name": cleaned_name,
        "size_bytes": len(cleaned),
        "sha256": sha256_bytes(cleaned),
        "service_clean_report": clean_report,
        "post_inspection": post_inspect,
        "post_forensic": post_forensic,
        "comparison": {
            "size_delta": len(cleaned) - manifest["size_bytes"],
            "sha256_changed": sha256_bytes(cleaned) != manifest["sha256"],
            "diff_forensic": diff_forensic(manifest.get("forensic", {}), post_forensic) if manifest.get("forensic") and manifest["forensic"].get("format") == "docx" else None
        },
    }
    manifest["clean"] = clean_payload
    write_manifest(job_dir, manifest)
    return JSONResponse({"job_id": job_id, "clean": clean_payload})


@app.get("/api/report/{job_id}")
async def report(job_id: str) -> JSONResponse:
    try:
        job_dir = get_job_dir(job_id)
        return JSONResponse(read_manifest(job_dir))
    except FileNotFoundError:
        raise HTTPException(404, "Análise expirada ou inexistente.")


@app.get("/api/download/{job_id}/cleaned")
async def download_cleaned(job_id: str) -> FileResponse:
    try:
        job_dir = get_job_dir(job_id)
        manifest = read_manifest(job_dir)
    except FileNotFoundError:
        raise HTTPException(404, "Análise expirada ou inexistente.")

    if not manifest.get("clean"):
        raise HTTPException(409, "A cópia higienizada ainda não foi gerada.")
    path = job_dir / manifest["cleaned_name"]
    if not path.exists():
        raise HTTPException(404, "Arquivo higienizado não encontrado.")
    return FileResponse(path, filename=manifest["cleaned_name"], media_type="application/octet-stream")


@app.get("/api/download/{job_id}/report.json")
async def download_report(job_id: str) -> FileResponse:
    try:
        job_dir = get_job_dir(job_id)
        manifest_path = job_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError
    except FileNotFoundError:
        raise HTTPException(404, "Análise expirada ou inexistente.")
    return FileResponse(manifest_path, filename=f"report_{job_id}.json", media_type="application/json")


@app.get("/api/download/{job_id}/report.pdf")
async def download_report_pdf(job_id: str) -> Response:
    try:
        job_dir = get_job_dir(job_id)
        manifest = read_manifest(job_dir)
    except FileNotFoundError:
        raise HTTPException(404, "Análise expirada ou inexistente.")
        
    from .reporting_pdf import generate_pdf_report
    pdf_bytes = generate_pdf_report(manifest)
    
    return Response(
        content=pdf_bytes, 
        media_type="application/pdf", 
        headers={"Content-Disposition": f"attachment; filename=laudo_{job_id}.pdf"}
    )
