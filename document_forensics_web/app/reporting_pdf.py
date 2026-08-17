import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

def generate_pdf_report(manifest: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=TA_CENTER)
    
    story = []
    story.append(Paragraph("Laudo Técnico de Proveniência Documental", title_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph(f"<b>Arquivo:</b> {manifest.get('original_name', 'N/A')}", styles["Normal"]))
    story.append(Paragraph(f"<b>SHA-256:</b> {manifest.get('sha256', 'N/A')}", styles["Normal"]))
    story.append(Paragraph(f"<b>Tamanho:</b> {manifest.get('size_bytes', 0)} bytes", styles["Normal"]))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("<b>1. Resumo Forense</b>", styles["Heading2"]))
    summary = manifest.get("summary", {})
    for key, val in summary.items():
        if isinstance(val, list):
            story.append(Paragraph(f"<b>{key}:</b> {', '.join(val)}", styles["Normal"]))
        else:
            story.append(Paragraph(f"<b>{key}:</b> {val}", styles["Normal"]))
            
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("<b>2. Data Loss Prevention (PII)</b>", styles["Heading2"]))
    forensic = manifest.get("forensic", {})
    dlp = forensic.get("dlp_findings", {}) if forensic else {}
    if not dlp:
        story.append(Paragraph("Nenhum dado sensível detectado.", styles["Normal"]))
    else:
        for k, v in dlp.items():
            if v:
                story.append(Paragraph(f"<b>{k.upper()}:</b> {len(v)} encontrados", styles["Normal"]))
                
    doc.build(story)
    return buffer.getvalue()
