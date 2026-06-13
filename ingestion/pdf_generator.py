import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from .schema import FinalOrderManifest

def compile_invoice_document(manifest: FinalOrderManifest, target_buyer: str) -> io.BytesIO:
    """
    Compiles a pristine transaction and historical statement matrix directly into a binary stream.
    """
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle('HeaderStyle', parent=styles['Heading1'], fontSize=20, leading=24, spaceAfter=10)
    meta_style = ParagraphStyle('MetaStyle', parent=styles['Normal'], fontSize=11, leading=14, spaceAfter=6)
    
    # Document Identification Header
    story.append(Paragraph("<b>AUTOMATED RETAIL LEDGER SYSTEM STATEMENT</b>", header_style))
    story.append(Paragraph(f"<b>Account Holder:</b> {target_buyer.upper()}", meta_style))
    story.append(Paragraph(f"<b>Settlement Engine Strategy:</b> {manifest.payment_mode.upper()}", meta_style))
    story.append(Spacer(1, 12))
    
    # Extract targeted dataset profile matching specific customer
    split_data = next((split for split in manifest.processed_splits if split.buyer_name == target_buyer), None)
    
    if split_data:
        # Build strict structural data tables
        table_matrix = [["Item System Classification", "Purchased Volume", "Computed Subtotal"]]
        for item in split_data.items:
            table_matrix.append([item.item_name, f"{item.quantity} {item.unit or ''}", f"₹{item.subtotal:.2f}"])
            
        data_table = Table(table_matrix, colWidths=[260, 110, 130])
        data_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2C3E50")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ]))
        story.append(data_table)
        story.append(Spacer(1, 15))
        
        # Financial Math Blocks
        story.append(Paragraph(f"<b>Current Ingestion Cycle Valuation:</b> ₹{split_data.order_total:.2f}", meta_style))
        if manifest.payment_mode == "khata":
            story.append(Paragraph(f"<b>Brought Forward Khata Balances:</b> ₹{split_data.previous_ledger:.2f}", meta_style))
            story.append(Paragraph(f"<b>Aggregated Outstanding Financial Responsibility:</b> ₹{split_data.updated_ledger:.2f}", meta_style))
            
    doc.build(story)
    pdf_buffer.seek(0)
    return pdf_buffer