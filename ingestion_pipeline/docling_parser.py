from docling.document_converter import DocumentConverter
import re


SKIP_SECTIONS = {"references", "acknowledgement", "acknowledgements"}


def _clean_name(raw: str) -> str:
    """'3.1 Data Processing Pipelines' → 'data_processing_pipelines'"""
    cleaned = re.sub(r"^[\d\.\s]+", "", raw.strip())   # strip leading "3.1 "
    cleaned = re.sub(r"[^\w\s]", "", cleaned)           # strip punctuation
    cleaned = cleaned.strip().lower().replace(" ", "_")
    return cleaned or "section"


def _fallback_split(text: str) -> list[dict]:
    """Used when Docling markdown has no ## headings at all."""
    chunks = re.split(r"\n(?=\d+\s+[A-Z])", text)
    sections = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        # First line is the heading
        lines = chunk.splitlines()
        name = _clean_name(lines[0]) if lines else "section"
        sections.append({"section_name": name, "raw_text": chunk})
    return sections or [{"section_name": "full_document", "raw_text": text}]


def extract_sections(file_path: str) -> list[dict]:
    converter = DocumentConverter()
    result = converter.convert(file_path)
    full_text = result.document.export_to_markdown()

    if "## " not in full_text:
        return _fallback_split(full_text)

    sections = []
    # split on markdown headings — keeps heading text as first line of chunk
    chunks = re.split(r"\n(?=## )", full_text)

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        lines = chunk.splitlines()
        heading_line = lines[0]                         # e.g. "## 3 Methodology"
        body = "\n".join(lines[1:]).strip()             # everything after heading

        # FIX: extract the actual name from the heading, not a generic counter
        raw_name = re.sub(r"^##\s*", "", heading_line)  # strip leading "## "
        section_name = _clean_name(raw_name)            # "3 Methodology" → "methodology"

        if not section_name:
            continue

        # skip boilerplate sections — Team B doesn't need them
        if section_name in SKIP_SECTIONS:
            continue

        sections.append({
            "section_name": section_name,
            "raw_text": f"{heading_line}\n{body}".strip(),
        })

    return sections if sections else _fallback_split(full_text)