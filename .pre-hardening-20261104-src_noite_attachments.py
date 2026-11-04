"""Bounded, non-executing text extraction for chat attachments."""

from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_EXTRACTED_CHARS = 40_000
MAX_ARCHIVE_EXPANSION_BYTES = 20 * 1024 * 1024
MAX_ATTACHMENT_CONTEXT_CHARS = 12_000
MAX_CONTEXT_PER_ATTACHMENT = 3_000
TEXT_SUFFIXES = {".txt", ".md", ".py", ".json", ".csv", ".xml", ".log", ".yaml", ".yml"}


class AttachmentError(ValueError):
    pass


def _read_zip_member(archive: zipfile.ZipFile, name: str) -> bytes:
    info = archive.getinfo(name)
    if info.file_size > MAX_ARCHIVE_EXPANSION_BYTES:
        raise AttachmentError("O conteúdo descompactado excede o limite de 20 MB.")
    if sum(item.file_size for item in archive.infolist()) > MAX_ARCHIVE_EXPANSION_BYTES:
        raise AttachmentError("O arquivo compactado excede o limite de expansão de 20 MB.")
    return archive.read(name)


@dataclass(frozen=True)
class ExtractedAttachment:
    path: Path
    media_type: str
    size_bytes: int
    text: str
    truncated: bool


def select_relevant_text(text: str, query: str, *, max_chars: int) -> str:
    """Return bounded source excerpts ranked by query-word overlap."""
    if max_chars <= 0 or not text:
        return ""
    if len(text) <= max_chars:
        return text
    chunk_size = min(1200, max_chars)
    overlap = min(160, chunk_size // 5)
    step = max(1, chunk_size - overlap)
    chunks = [(start, text[start : start + chunk_size]) for start in range(0, len(text), step)]
    terms = {
        token.casefold()
        for token in re.findall(r"[\wÀ-ÿ]{3,}", query, flags=re.UNICODE)
        if token.casefold() not in {"que", "para", "com", "uma", "sobre", "this", "that"}
    }

    def score(item: tuple[int, str]) -> tuple[int, int]:
        position, chunk = item
        folded = chunk.casefold()
        overlap_count = sum(folded.count(term) for term in terms)
        # With broad requests such as "resuma", preserve the document's opening sections.
        return (overlap_count if terms else 0, -position)

    ranked = sorted(chunks, key=score, reverse=True)
    selected = []
    used = 0
    for position, chunk in ranked:
        if used >= max_chars:
            break
        excerpt = chunk[: max_chars - used]
        selected.append((position, excerpt))
        used += len(excerpt)
    selected.sort(key=lambda item: item[0])
    content = "\n[… trecho omitido …]\n".join(excerpt for _, excerpt in selected)
    header = "[Trechos selecionados; partes omitidas não foram enviadas.]\n"
    if len(content) + len(header) > max_chars:
        content = content[: max(0, max_chars - len(header))]
    return header + content


def _docx_text(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        xml = ElementTree.fromstring(_read_zip_member(archive, "word/document.xml"))
    return "\n".join(
        "".join(node.text or "" for node in paragraph.iter() if node.tag.endswith("}t"))
        for paragraph in xml.iter()
        if paragraph.tag.endswith("}p")
    )


def _xlsx_text(data: bytes) -> tuple[str, bool]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_xml = ElementTree.fromstring(
                _read_zip_member(archive, "xl/sharedStrings.xml")
            )
            shared = ["".join(node.text or "" for node in item.iter() if node.tag.endswith("}t"))
                      for item in shared_xml]
        sheets = sorted(
            name for name in archive.namelist()
            if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name)
        )
        rows = []
        for sheet in sheets[:20]:
            root = ElementTree.fromstring(_read_zip_member(archive, sheet))
            for row in root.iter():
                if not row.tag.endswith("}row"):
                    continue
                values = []
                for cell in row:
                    if not cell.tag.endswith("}c"):
                        continue
                    value = next((child.text for child in cell if child.tag.endswith("}v")), "")
                    if cell.attrib.get("t") == "s" and value:
                        value = shared[int(value)] if int(value) < len(shared) else ""
                    values.append(value or "")
                rows.append("\t".join(values))
        return "\n".join(rows), len(sheets) > 20


def _pptx_text(data: bytes) -> tuple[str, bool]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        slides = sorted(
            (name for name in archive.namelist()
             if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)),
            key=lambda name: int(re.search(r"slide(\d+)", name).group(1)),
        )
        extracted = []
        for slide in slides[:100]:
            root = ElementTree.fromstring(_read_zip_member(archive, slide))
            extracted.append(" ".join(node.text or "" for node in root.iter()
                                      if node.tag.endswith("}t")))
        return "\n".join(extracted), len(slides) > 100


def extract_attachment(path: Path) -> ExtractedAttachment:
    path = Path(path).resolve(strict=True)
    if not path.is_file():
        raise AttachmentError("O anexo precisa ser um arquivo regular.")
    size = path.stat().st_size
    if size == 0:
        raise AttachmentError("O arquivo está vazio.")
    if size > MAX_FILE_BYTES:
        raise AttachmentError("O arquivo excede o limite de 5 MB.")
    suffix = path.suffix.casefold()
    if suffix not in TEXT_SUFFIXES | {".docx", ".xlsx", ".pptx", ".pdf"}:
        raise AttachmentError(f"Formato não suportado: {suffix or 'sem extensão'}.")
    data = path.read_bytes()
    source_truncated = False
    try:
        if suffix in TEXT_SUFFIXES:
            text = data.decode("utf-8-sig")
            if "\x00" in text:
                raise AttachmentError("O arquivo parece ser binário e não foi executado.")
            if suffix == ".json":
                text = json.dumps(json.loads(text), ensure_ascii=False, indent=2)
            elif suffix == ".csv":
                text = "\n".join("\t".join(row) for row in csv.reader(io.StringIO(text)))
        elif suffix == ".docx":
            text = _docx_text(data)
        elif suffix == ".xlsx":
            text, source_truncated = _xlsx_text(data)
        elif suffix == ".pptx":
            text, source_truncated = _pptx_text(data)
        else:
            try:
                from PySide6.QtPdf import QPdfDocument
            except ImportError as exc:
                raise AttachmentError(
                    "Leitura de PDF requer o módulo QtPdf da instalação desktop PySide6."
                ) from exc
            document = QPdfDocument()
            error = document.load(str(path))
            if error != QPdfDocument.Error.None_:
                raise AttachmentError(
                    f"O PDF não pôde ser aberto pelo QtPdf (erro {error.name})."
                )
            if document.status() != QPdfDocument.Status.Ready:
                raise AttachmentError("O PDF não terminou de carregar para extração de texto.")
            page_count = document.pageCount()
            source_truncated = page_count > 100
            text = "\n".join(
                document.getAllText(page).text()
                for page in range(min(page_count, 100))
            )
            if not text.strip():
                raise AttachmentError(
                    "O PDF não contém texto extraível; OCR de páginas digitalizadas "
                    "não está disponível."
                )
    except (
        UnicodeDecodeError,
        zipfile.BadZipFile,
        ElementTree.ParseError,
        json.JSONDecodeError,
    ) as exc:
        raise AttachmentError(
            "Não foi possível interpretar o arquivo; ele pode estar corrompido."
        ) from exc
    truncated = source_truncated or len(text) > MAX_EXTRACTED_CHARS
    if truncated:
        text = text[:MAX_EXTRACTED_CHARS]
    return ExtractedAttachment(path, suffix[1:].upper(), size, text, truncated)

[executed on device: CRISTNZX-PC (d2b7b666-54bc-4674-9e53-7df270e7da7b)]