from __future__ import annotations

import io
import zipfile

from app.analyzers.docx import analyze_docx


def make_docx() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'/>")
        z.writestr(
            "docProps/core.xml",
            """<cp:coreProperties xmlns:cp='http://schemas.openxmlformats.org/package/2006/metadata/core-properties' xmlns:dc='http://purl.org/dc/elements/1.1/' xmlns:dcterms='http://purl.org/dc/terms/1.1/'><dc:creator>Ana</dc:creator><cp:lastModifiedBy>Bruno</cp:lastModifiedBy><cp:revision>2</cp:revision></cp:coreProperties>""",
        )
        z.writestr(
            "word/settings.xml",
            """<w:settings xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:rsids><w:rsid w:val='001'/><w:rsid w:val='002'/></w:rsids></w:settings>""",
        )
        z.writestr(
            "word/document.xml",
            """<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body><w:p><w:r><w:t>Hello\u200bWorld</w:t></w:r><w:r><w:instrText> PAGEREF _Toc123 </w:instrText></w:r></w:p><w:ins/><w:del/><w:sdt/></w:body></w:document>""",
        )
        z.writestr("customXml/item1.xml", "<root><contentTypeName>Document</contentTypeName><sharepoint>yes</sharepoint></root>")
    return buf.getvalue()


def test_docx_analysis_core_fields():
    result = analyze_docx(make_docx())
    assert result["core_properties"]["creator"] == "Ana"
    assert result["core_properties"]["last_modified_by"] == "Bruno"
    assert result["revision_history"]["unique_rsids"] == 2
    assert result["revision_history"]["insertions"] == 1
    assert result["revision_history"]["deletions"] == 1
    assert result["content_controls"]["count"] == 1
    assert result["unicode_suspects"]["zero_width_space"] == 1
    assert result["fields"]["PAGEREF"] == 1
    assert result["custom_xml"]["sharepoint_indicators"] is True
