import io
import re
import hashlib
from typing import List, Dict, Any, Tuple
import pypdf

from app.models.policy import (
    PolicySection,
    PageExtractionReport,
    ExtractionQualityReport,
)

class PDFExtractorService:
    """
    Extracts text, preserves page boundaries, detects headings/clauses,
    and analyzes extraction quality (detecting scanned/empty pages).
    """

    @staticmethod
    def compute_sha256(content: bytes) -> str:
        hasher = hashlib.sha256()
        hasher.update(content)
        return hasher.hexdigest()

    @classmethod
    def extract_document(cls, file_bytes: bytes) -> Tuple[List[Dict[str, Any]], ExtractionQualityReport, List[PolicySection]]:
        """
        Extracts raw pages, quality report, and structured sections from PDF bytes.
        """
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        total_pages = len(reader.pages)

        pages_data: List[Dict[str, Any]] = []
        page_reports: List[PageExtractionReport] = []
        scanned_count = 0
        low_confidence_pages: List[int] = []
        all_notes: List[str] = []

        for idx, page in enumerate(reader.pages):
            page_num = idx + 1
            raw_text = page.extract_text() or ""
            cleaned_text = raw_text.strip()
            char_count = len(cleaned_text)

            has_images = len(page.images) > 0
            is_scanned = char_count < 40
            warnings = []

            if is_scanned:
                scanned_count += 1
                low_confidence_pages.append(page_num)
                quality_score = 0.2 if char_count == 0 else 0.4
                warnings.append("Low character density: page may be scanned or image-based.")
            else:
                quality_score = 1.0 if char_count > 200 else 0.8

            report = PageExtractionReport(
                page_number=page_num,
                character_count=char_count,
                has_images=has_images,
                is_scanned_flag=is_scanned,
                quality_score=quality_score,
                warnings=warnings
            )
            page_reports.append(report)

            pages_data.append({
                "page_number": page_num,
                "text": cleaned_text,
                "char_count": char_count,
                "is_scanned": is_scanned
            })

        if scanned_count == 0:
            overall_quality = "HIGH"
            all_notes.append("High confidence digital text extracted across all pages.")
        elif scanned_count < (total_pages / 2):
            overall_quality = "MEDIUM"
            all_notes.append(f"{scanned_count} pages flagged with low text density.")
        else:
            overall_quality = "LOW_NEEDS_OCR"
            all_notes.append(f"Majority of pages ({scanned_count}/{total_pages}) are scanned or low-density. OCR routing recommended.")

        quality_report = ExtractionQualityReport(
            total_pages=total_pages,
            scanned_pages_count=scanned_count,
            low_confidence_pages=low_confidence_pages,
            overall_quality=overall_quality,
            notes=all_notes
        )

        sections = cls.parse_sections(pages_data)
        return pages_data, quality_report, sections

    @classmethod
    def parse_sections(cls, pages_data: List[Dict[str, Any]]) -> List[PolicySection]:
        """
        Parses structured sections with page numbers, numbered clauses, and headings.
        Supports both hierarchical numbered sections and tabular clinical categories.
        """
        sections: List[PolicySection] = []
        section_idx = 1

        # Pattern for explicit section numbers: e.g. "Section 4.2.1", "Section 1.0", "Article 2"
        section_prefix_pattern = re.compile(
            r'^(?:Section|Article|Clause)\s+([\d.]+)\s*(?:[:.\-–]\s*)?(.*)$',
            re.IGNORECASE
        )

        # Pattern for major clinical document titles
        known_major_headings = [
            "DESCRIPTION",
            "POLICY/CRITERIA",
            "EQUIPMENT-SPECIFIC CRITERIA",
            "CODING IMPLICATIONS",
            "BACKGROUND",
            "REVIEWS, REVISIONS, AND APPROVALS",
            "REFERENCES",
            "IMPORTANT REMINDER"
        ]

        # Common clinical equipment categories in tabular guidelines
        known_categories = [
            "BURN GARMENTS",
            "CARDIAC EQUIPMENT",
            "COMPRESSION THERAPY EQUIPMENT",
            "DIABETES CARE EQUIPMENT",
            "HEAT, COLD & LIGHT THERAPY EQUIPMENT",
            "NEWBORN CARE EQUIPMENT",
            "OTHER EQUIPMENT",
            "PROSTHETICS AND ORTHOTICS EQUIPMENT",
            "PUMPS",
            "RESPIRATORY EQUIPMENT",
            "SURGICAL SUPPLIES",
            "WALKERS",
            "WHEELCHAIRS",
            "WOUND CARE"
        ]

        for page in pages_data:
            page_num = page["page_number"]
            text = page["text"]
            if not text:
                continue

            lines = text.split("\n")
            current_sec_num = f"P{page_num}.0"
            current_heading = f"Page {page_num} Overview"
            current_buffer: List[str] = []
            has_table = False

            def flush_section():
                nonlocal section_idx, current_buffer, has_table, current_sec_num, current_heading
                if current_buffer:
                    content_str = "\n".join(current_buffer).strip()
                    if len(content_str) > 0:
                        sections.append(PolicySection(
                            id=f"SEC-{section_idx:03d}",
                            section_number=current_sec_num,
                            heading=current_heading,
                            page_number=page_num,
                            content=content_str,
                            character_count=len(content_str),
                            table_detected=has_table
                        ))
                        section_idx += 1
                    current_buffer = []
                    has_table = False

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue

                if "|" in stripped or "\t" in stripped:
                    has_table = True

                # Ignore table of contents dot leaders (e.g. "BURN GARMENTS ......... 2")
                if "....." in stripped:
                    current_buffer.append(stripped)
                    continue

                matched_heading = False

                # 1. Check explicit "Section X.Y"
                sec_match = section_prefix_pattern.match(stripped)
                if sec_match:
                    flush_section()
                    current_sec_num = f"Section {sec_match.group(1)}"
                    current_heading = sec_match.group(2).strip() or f"Clause {sec_match.group(1)}"
                    matched_heading = True

                # 2. Check known major headings or Roman numerals (e.g. "I. Policy/Criteria")
                elif any(stripped.upper().startswith(h) for h in known_major_headings) or re.match(r'^[IVXLCDM]+\.\s+[A-Z]', stripped):
                    flush_section()
                    current_sec_num = f"P{page_num}.{section_idx}"
                    current_heading = stripped
                    matched_heading = True

                # 3. Check known tabular category titles (e.g. "WHEELCHAIRS", "BURN GARMENTS")
                elif any(stripped.upper() == cat or stripped.upper() == f"{cat} CRITERIA" or stripped.upper() == f"{cat} CRITERIA HCPCS" for cat in known_categories):
                    flush_section()
                    clean_cat = stripped.replace("CRITERIA", "").replace("HCPCS", "").strip()
                    current_sec_num = f"P{page_num}.{clean_cat[:4].upper()}"
                    current_heading = clean_cat
                    has_table = True
                    matched_heading = True

                # 4. Check standard decimal numbered section "4.2.1 Clinical Indication"
                elif re.match(r'^\d+\.\d+(?:\.\d+)+\s+[A-Z]', stripped):
                    parts = stripped.split(" ", 1)
                    flush_section()
                    current_sec_num = f"Section {parts[0]}"
                    current_heading = parts[1].strip() if len(parts) > 1 else f"Section {parts[0]}"
                    matched_heading = True

                if not matched_heading:
                    current_buffer.append(stripped)

            flush_section()

        return sections
