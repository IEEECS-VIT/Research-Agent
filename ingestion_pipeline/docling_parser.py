from docling.document_converter import DocumentConverter
import re
import traceback

SKIP_SECTIONS = {"references", "acknowledgement", "acknowledgements"}

def _clean_name(raw: str) -> str:
    try:
        cleaned = re.sub(r"^[\d\.\s]+", "", raw.strip())
        cleaned = re.sub(r"[^\w\s]", "", cleaned)
        cleaned = cleaned.strip().lower().replace(" ", "_")
        return cleaned or "section"
    except Exception:
        return "section"

def _fallback_split(text: str) -> list[dict]:
    try:
        chunks = re.split(r"\n(?=\d+\s+[A-Z])", text)
        sections = []
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            lines = chunk.splitlines()
            name = _clean_name(lines[0]) if lines else "section"
            sections.append({"section_name": name, "raw_text": chunk})
        
        return sections or [{"section_name": "full_document", "raw_text": text}]
    except Exception:
        return [{"section_name": "full_document", "raw_text": text}]

def extract_sections(file_path: str) -> list[dict]:
    print(f"[PARSER] Starting Docling conversion for: {file_path}")
    try:
        converter = DocumentConverter()
        result = converter.convert(file_path)
        full_text = result.document.export_to_markdown()
        
        print(f"[PARSER] Conversion success. Extracted {len(full_text)} characters.")

        if "## " not in full_text:
            return _fallback_split(full_text)

        sections = []
        chunks = re.split(r"\n(?=## )", full_text)

        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue

            lines = chunk.splitlines()
            heading_line = lines[0]
            body = "\n".join(lines[1:]).strip()
            
            raw_name = re.sub(r"^##\s*", "", heading_line)
            section_name = _clean_name(raw_name)

            if not section_name or section_name in SKIP_SECTIONS:
                continue

            sections.append({
                "section_name": section_name,
                "raw_text": f"{heading_line}\n{body}".strip(),
            })

        return sections if sections else _fallback_split(full_text)
    except Exception as e:
        print(f"[PARSER] Critical failure during extraction: {e}")
        traceback.print_exc()
        raise