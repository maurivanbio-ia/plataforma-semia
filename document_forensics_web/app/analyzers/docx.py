from __future__ import annotations

import io
import re
import zipfile
from collections import Counter
from datetime import datetime
from typing import Any
from xml.etree import ElementTree as ET

from .image import analyze_image_bytes
from .dlp import analyze_pii

NS = {
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
}

UNICODE_SUSPECTS = {
    "zero_width_space": "\u200b",
    "zero_width_non_joiner": "\u200c",
    "zero_width_joiner": "\u200d",
    "word_joiner": "\u2060",
    "bom": "\ufeff",
    "soft_hyphen": "\u00ad",
    "lre": "\u202a",
    "rle": "\u202b",
    "pdf_bidi": "\u202c",
    "lro": "\u202d",
    "rlo": "\u202e",
    "line_separator": "\u2028",
    "paragraph_separator": "\u2029",
}

MAX_ZIP_MEMBERS = 5000
MAX_UNCOMPRESSED = 300 * 1024 * 1024


def _read_xml(zf: zipfile.ZipFile, path: str) -> ET.Element | None:
    try:
        raw = zf.read(path)
    except KeyError:
        return None
    try:
        return ET.fromstring(raw)
    except ET.ParseError:
        return None


def _text(root: ET.Element | None, path: str, ns: dict | None = None) -> str | None:
    if root is None:
        return None
    el = root.find(path, ns or NS)
    return (el.text or "").strip() if el is not None and el.text else None


def _local_name(tag: str) -> str:
    return tag.split("}")[-1]


def analyze_docx(data: bytes) -> dict[str, Any]:
    out: dict[str, Any] = {
        "format": "docx",
        "core_properties": {},
        "app_properties": {},
        "revision_history": {},
        "content_controls": {},
        "comments": {},
        "fields": {},
        "custom_xml": {},
        "unicode_suspects": {},
        "media": [],
        "zip_timeline": {},
        "warnings": [],
    }

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            infos = zf.infolist()
            if len(infos) > MAX_ZIP_MEMBERS:
                raise ValueError("DOCX contém quantidade excessiva de partes internas")
            total_uncompressed = sum(i.file_size for i in infos)
            if total_uncompressed > MAX_UNCOMPRESSED:
                raise ValueError("DOCX excede o limite seguro de conteúdo descompactado")

            names = set(zf.namelist())

            core = _read_xml(zf, "docProps/core.xml")
            if core is not None:
                out["core_properties"] = {
                    "creator": _text(core, "dc:creator"),
                    "last_modified_by": _text(core, "cp:lastModifiedBy"),
                    "created": _text(core, "dcterms:created"),
                    "modified": _text(core, "dcterms:modified"),
                    "revision": _text(core, "cp:revision"),
                    "title": _text(core, "dc:title"),
                    "subject": _text(core, "dc:subject"),
                    "keywords": _text(core, "cp:keywords"),
                    "category": _text(core, "cp:category"),
                }

            app = _read_xml(zf, "docProps/app.xml")
            if app is not None:
                app_props = {}
                wanted = {
                    "Application", "AppVersion", "Template", "TotalTime", "Pages",
                    "Words", "Characters", "Paragraphs", "Lines", "Company", "Manager",
                }
                for child in app:
                    key = _local_name(child.tag)
                    if key in wanted:
                        app_props[key] = (child.text or "").strip() or None
                out["app_properties"] = app_props

            settings = _read_xml(zf, "word/settings.xml")
            rsids: set[str] = set()
            if settings is not None:
                for el in settings.iter():
                    if _local_name(el.tag).lower().startswith("rsid"):
                        for key, value in el.attrib.items():
                            if _local_name(key) in {"val", "rsid", "rsidR", "rsidDel", "rsidP", "rsidRDefault"} and value:
                                rsids.add(value)
                track_changes = any(_local_name(el.tag) == "trackRevisions" for el in settings.iter())
            else:
                track_changes = False
            out["revision_history"] = {
                "unique_rsids": len(rsids),
                "track_revisions_enabled": track_changes,
            }

            doc_raw = zf.read("word/document.xml") if "word/document.xml" in names else b""
            doc_text = doc_raw.decode("utf-8", errors="replace")
            
            # Executa a busca de PII (Data Loss Prevention)
            out["dlp_findings"] = analyze_pii(doc_text)
            
            doc = _read_xml(zf, "word/document.xml")
            insertions = deletions = sdts = 0
            instr_texts: list[str] = []
            if doc is not None:
                for el in doc.iter():
                    local = _local_name(el.tag)
                    if local == "ins": insertions += 1
                    elif local == "del": deletions += 1
                    elif local == "sdt": sdts += 1
                    elif local == "instrText" and el.text:
                        instr_texts.append(el.text.strip())
            out["revision_history"].update({
                "insertions": insertions,
                "deletions": deletions,
            })
            out["content_controls"] = {"count": sdts}

            field_counts = Counter()
            for txt in instr_texts:
                upper = txt.upper()
                if "PAGEREF" in upper: field_counts["PAGEREF"] += 1
                if re.search(r"\bTOC\b", upper): field_counts["TOC"] += 1
                if re.search(r"\bSEQ\b", upper): field_counts["SEQ"] += 1
                if "HYPERLINK" in upper: field_counts["HYPERLINK"] += 1
            out["fields"] = dict(field_counts)

            comments = _read_xml(zf, "word/comments.xml")
            comment_count = 0
            if comments is not None:
                comment_count = sum(1 for el in comments.iter() if _local_name(el.tag) == "comment")
            out["comments"] = {"present": "word/comments.xml" in names, "count": comment_count}

            custom_items = sorted(n for n in names if n.startswith("customXml/item") and n.endswith(".xml") and "Props" not in n)
            custom_hits = []
            for item in custom_items[:100]:
                raw = zf.read(item)
                low = raw.lower()
                flags = []
                if b"sharepoint" in low or b"contenttypename" in low or b"formtemplates" in low:
                    flags.append("sharepoint_or_content_type")
                if b"bibliograph" in low or b"apa" in low:
                    flags.append("bibliography")
                custom_hits.append({"part": item, "flags": flags})
            out["custom_xml"] = {
                "item_count": len(custom_items),
                "items": custom_hits,
                "sharepoint_indicators": any("sharepoint_or_content_type" in x["flags"] for x in custom_hits),
            }

            suspects = {}
            for label, char in UNICODE_SUSPECTS.items():
                count = doc_text.count(char)
                if count:
                    suspects[label] = count
            out["unicode_suspects"] = suspects

            media_names = sorted(n for n in names if n.startswith("word/media/") and not n.endswith("/"))
            for media_name in media_names[:200]:
                try:
                    media_data = zf.read(media_name)
                    entry = analyze_image_bytes(media_data, media_name)
                    entry["bytes"] = len(media_data)
                    out["media"].append(entry)
                except Exception as exc:
                    out["media"].append({"name": media_name, "error": str(exc)})

            timestamps = []
            part_timeline = []
            for info in infos:
                try:
                    dt = datetime(*info.date_time).isoformat()
                    timestamps.append(dt)
                    if info.filename in {"word/document.xml", "docProps/core.xml", "docProps/app.xml"} or info.filename.startswith("word/media/"):
                        part_timeline.append({"part": info.filename, "timestamp": dt})
                except Exception:
                    continue
            out["zip_timeline"] = {
                "earliest": min(timestamps) if timestamps else None,
                "latest": max(timestamps) if timestamps else None,
                "selected_parts": part_timeline[:250],
            }

    except zipfile.BadZipFile:
        out["warnings"].append("O arquivo não é um pacote DOCX/ZIP válido.")
    except Exception as exc:
        out["warnings"].append(str(exc))

    return out
