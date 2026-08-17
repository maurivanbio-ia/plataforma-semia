from __future__ import annotations

import re

# PII Regex Patterns for Brazil / General
PII_PATTERNS = {
    "cpf": re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),
    "cnpj": re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"),
    "processo_judicial": re.compile(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b"), # Padrão CNJ
    "coordenadas": re.compile(r"\b[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?)\s*,\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)\b"),
}

def analyze_pii(text: str) -> dict[str, list[str]]:
    """
    Scans the given text for Personally Identifiable Information (PII)
    and sensitive data using Regular Expressions.
    """
    findings = {}
    for key, pattern in PII_PATTERNS.items():
        if key == "coordenadas":
            matches = [m.group(0) for m in pattern.finditer(text)]
        else:
            matches = pattern.findall(text)
            
        if matches:
            # Deduplicate and sort
            findings[key] = sorted(list(set(matches)))
            
    return findings
