import io
from fpdf import FPDF
import pypdf

def generate_sample_policy_pdf(
    insurer: str = "United Healthcare",
    policy_name: str = "Head CT Clinical Guideline",
    version: str = "2026.1"
) -> bytes:
    """Generates a valid 3-page digital text policy PDF with numbered sections."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Page 1
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"{insurer} - Clinical Coverage Guideline", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "I", 12)
    pdf.cell(0, 8, f"{policy_name} (Version {version})", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(10)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Section 1.0 Coverage Scope", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, "This medical policy sets forth diagnostic criteria for outpatient computed tomography. Applicable CPT codes include 70450 and 70460.")
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Section 4.2.1 Clinical Indication", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, "Patient must have documented neurological signs or symptoms, such as severe persistent headaches with atypical features, dizziness, or visual disturbance.")

    # Page 2
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Section 4.2.2 Duration of Symptoms", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, "Symptoms must persist for at least 6 weeks of active outpatient care prior to imaging.")
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Section 4.2.3 Previous Conservative Treatment", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, "A documented course of conservative therapy must be attempted without improvement.")

    # Page 3
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Section 4.2.6 Contrast Justification", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, "If intravenous contrast is requested, clinical rationale must establish suspicion of mass or neoplasm.")

    output_buf = io.BytesIO()
    pdf.output(output_buf)
    return output_buf.getvalue()

def generate_scanned_mock_pdf() -> bytes:
    """Generates a blank/empty page PDF to simulate a scanned image PDF with zero text."""
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_blank_page(width=612, height=792)
    output_buf = io.BytesIO()
    writer.write(output_buf)
    return output_buf.getvalue()
