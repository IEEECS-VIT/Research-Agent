from dataclasses import dataclass
from pathlib import Path
from typing import Any
import logging

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import PictureItem
import re

logger = logging.getLogger(__name__)

SKIP_SECTIONS = {"references", "acknowledgement", "acknowledgements"}
IMAGE_RESOLUTION_SCALE = 2.0


@dataclass
class ParsedContent:
    full_text: str
    images: list[Any]

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

def _build_converter(file_path: str) -> DocumentConverter:
    if Path(file_path).suffix.lower() != ".pdf":
        return DocumentConverter()

    pipeline_options = PdfPipelineOptions()
    pipeline_options.images_scale = IMAGE_RESOLUTION_SCALE
    pipeline_options.generate_page_images = True
    pipeline_options.generate_picture_images = True

    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

def _extract_picture_images(result: Any) -> list[Any]:
    images = []
    for element, _level in result.document.iterate_items():
        if not isinstance(element, PictureItem):
            continue

        try:
            image = element.get_image(result.document)
            if image is not None:
                images.append(image)
        except Exception as e:
            logger.warning("Failed to extract one picture image: %s - %s", type(e).__name__, e)

    return images

def extract_document_content(file_path: str) -> ParsedContent:
    logger.info("Starting Docling conversion for: %s", file_path)
    try:
        converter = _build_converter(file_path)
        result = converter.convert(file_path)
        full_text = result.document.export_to_markdown()
        images = _extract_picture_images(result)
        
        logger.info(
            "Conversion success. Extracted %d characters and %d picture images.",
            len(full_text), len(images)
        )
        return ParsedContent(full_text=full_text, images=images)
    except Exception as e:
        logger.error("Critical failure during extraction: %s", e, exc_info=True)
        raise

def inject_image_summaries(full_text: str, image_summaries: list[str]) -> str:
    if not image_summaries:
        return full_text

    normalized_summaries = [
        summary if summary.startswith("[Image summary") else f"[Image summary: {summary}]"
        for summary in image_summaries
    ]
    summary_iter = iter(normalized_summaries)

    placeholder_patterns = [
        re.compile(r"(?im)^[ \t]*<!--\s*(?:image|picture)\s*-->[ \t]*$"),
        re.compile(r"(?im)^[ \t]*!\[[^\]\n]*(?:image|picture|figure)?[^\]\n]*\]\([^\)\n]*\)[ \t]*$"),
    ]

    replaced = 0

    def _replace(_match: re.Match) -> str:
        nonlocal replaced
        try:
            replacement = next(summary_iter)
        except StopIteration:
            return _match.group(0)

        replaced += 1
        return replacement

    updated_text = full_text
    for pattern in placeholder_patterns:
        if replaced >= len(normalized_summaries):
            break
        updated_text = pattern.sub(_replace, updated_text, count=len(normalized_summaries) - replaced)

    if replaced < len(normalized_summaries):
        remaining = "\n\n".join(normalized_summaries[replaced:])
        updated_text = f"{updated_text.rstrip()}\n\n## Extracted images\n{remaining}"
        logger.warning(
            "Fewer image placeholders than extracted images. Appended %d image summaries.",
            len(normalized_summaries) - replaced
        )

    logger.info("Replaced %d Docling image placeholders with summaries.", replaced)
    return updated_text

def split_sections(full_text: str) -> list[dict]:
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

def extract_sections(file_path: str) -> list[dict]:
    try:
        content = extract_document_content(file_path)
        return split_sections(content.full_text)
    except Exception as e:
        logger.error("Critical failure during extraction: %s", e, exc_info=True)
        raise
