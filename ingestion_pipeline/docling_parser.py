import os
import json
import traceback
from typing import List, Dict
# Lazy import of docling to avoid import errors if not installed
def _get_converter():
    try:
        from docling.document_converter import DocumentConverter
        return DocumentConverter()
    except Exception as e:
        # docling not installed or import failed
        print(f"[DOCLING_PARSER] Docling library not available: {e}")
        return None
def extract_sections(file_path: str) -> List[Dict[str, str]]:
    """Extract sections from a document.
    This function attempts to use the ``docling`` library to parse PDFs/DOCX
    files into structured sections. If ``docling`` is unavailable or the
    conversion fails, it falls back to a simple raw‑text extraction.
    Returns a list of dictionaries with keys ``section_name`` and ``raw_text``.
    """
    converter = _get_converter()
    if converter is None:
        # Fallback: read the file as plain text
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return [{"section_name": os.path.basename(file_path), "raw_text": content}]
        except Exception as e:
            print(f"[DOCLING_PARSER] Fallback read failed: {e}")
            raise
    try:
        # Convert the document; docling returns a Document object with blocks
        result = converter.convert(file_path)
        # Export to markdown to get a readable string
        markdown = result.document.export_to_markdown()
        # Simple heuristic: split by markdown headings (lines starting with '#')
        sections = []
        current_name = "Untitled"
        current_text = []
        for line in markdown.splitlines():
            if line.startswith("#"):
                # Save previous section
                if current_text:
                    sections.append({"section_name": current_name, "raw_text": "\n".join(current_text)})
                # New heading
                current_name = line.lstrip("# ").strip() or "Untitled"
                current_text = []
            else:
                current_text.append(line)
        # Append last section
        if current_text:
            sections.append({"section_name": current_name, "raw_text": "\n".join(current_text)})
        # Ensure at least one section
        if not sections:
            sections.append({"section_name": os.path.basename(file_path), "raw_text": markdown})
        return sections
    except Exception as e:
        print(f"[DOCLING_PARSER] Docling conversion failed: {e}")
        traceback.print_exc()
        # Fallback to raw text read
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return [{"section_name": os.path.basename(file_path), "raw_text": content}]
        except Exception as e2:
            print(f"[DOCLING_PARSER] Final fallback read failed: {e2}")
            raise
