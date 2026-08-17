from __future__ import annotations

from typing import Any


def _service_suspicious(service: dict[str, Any]) -> int | bool | None:
    value = service.get("suspicious")
    if isinstance(value, (int, bool)):
        return value
    if isinstance(value, list):
        return len(value)
    return None


def build_summary(service: dict[str, Any], forensic: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    suspicious = _service_suspicious(service)
    if suspicious:
        findings.append({
            "severity": "attention",
            "title": "Sinais verificáveis detectados pelo serviço",
            "detail": f"O serviço marcou a inspeção como suspeita: {suspicious}.",
        })
    else:
        findings.append({
            "severity": "ok",
            "title": "Nenhum sinal verificável marcado como suspeito pelo serviço",
            "detail": "Isso não certifica autoria humana nem garante ausência de marcas proprietárias não verificáveis.",
        })

    if forensic.get("format") == "docx":
        unicode_hits = sum((forensic.get("unicode_suspects") or {}).values())
        findings.append({
            "severity": "attention" if unicode_hits else "ok",
            "title": "Unicode invisível/suspeito",
            "detail": f"{unicode_hits} ocorrência(s) encontrada(s) no word/document.xml.",
        })

        core = forensic.get("core_properties") or {}
        personal = [k for k in ("creator", "last_modified_by") if core.get(k)]
        if personal:
            findings.append({
                "severity": "info",
                "title": "Propriedades pessoais do DOCX",
                "detail": "Foram encontrados campos de autoria/modificação que podem ser relevantes para privacidade ou cadeia documental.",
            })

        custom = forensic.get("custom_xml") or {}
        if custom.get("sharepoint_indicators"):
            findings.append({
                "severity": "info",
                "title": "Indicadores de SharePoint/Content Type",
                "detail": "O pacote contém custom XML compatível com fluxos corporativos de documentos.",
            })

        media = forensic.get("media") or []
        software_count = sum(1 for x in media if x.get("software"))
        if software_count:
            findings.append({
                "severity": "info",
                "title": "Metadados de software em imagens",
                "detail": f"{software_count} imagem(ns) incorporada(s) registram software de criação/processamento.",
            })

    attention = sum(1 for x in findings if x["severity"] == "attention")
    status = "atenção" if attention else "sem_alertas_verificaveis"

    return {
        "status": status,
        "findings": findings,
        "disclaimer": (
            "A análise identifica sinais técnicos verificáveis de metadados, Unicode e proveniência. "
            "Ela não prova autoria humana, não determina fraude e não garante que detectores proprietários de IA falharão."
        ),
    }
