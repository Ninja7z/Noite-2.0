from __future__ import annotations

import zipfile

import pytest

from noite.attachments import (
    AttachmentError,
    extract_attachment,
    select_relevant_text,
)


def make_pdf(text: str) -> bytes:
    stream = f"BT /F1 12 Tf 10 100 Td ({text}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, item in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode() + item + b"\nendobj\n")
    xref = len(output)
    output.extend(b"xref\n0 6\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(output)


def test_extracts_text_and_marks_character_truncation(tmp_path):
    path = tmp_path / "report.txt"
    path.write_text("A" * 45_000, encoding="utf-8")
    result = extract_attachment(path)
    assert result.media_type == "TXT"
    assert len(result.text) == 40_000
    assert result.truncated


def test_retrieves_bounded_excerpt_relevant_to_the_question():
    source = "Opening overview.\n" + ("Routine description.\n" * 160)
    source += "\nThe document records a Qwen GPU memory regression on the GTX 1660.\n"
    source += "\n" + ("Additional appendix detail.\n" * 160)

    excerpt = select_relevant_text(source, "What caused the GPU memory regression?", max_chars=900)

    assert len(excerpt) <= 900
    assert "Qwen GPU memory regression" in excerpt
    assert "Trechos selecionados" in excerpt


def test_extracts_docx_without_executing_document(tmp_path):
    path = tmp_path / "note.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "word/document.xml",
            '<w:document xmlns:w="urn:w"><w:p><w:r><w:t>Olá</w:t></w:r></w:p></w:document>',
        )
    assert extract_attachment(path).text == "Olá"


def test_extracts_xlsx_shared_strings(tmp_path):
    path = tmp_path / "sheet.xlsx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "xl/sharedStrings.xml",
            '<sst xmlns="urn:x"><si><t>Nome</t></si><si><t>Ana</t></si></sst>',
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            '<worksheet xmlns="urn:x"><sheetData><row><c t="s"><v>0</v></c>'
            '<c t="s"><v>1</v></c></row></sheetData></worksheet>',
        )
    assert extract_attachment(path).text == "Nome\tAna"


def test_workbooks_with_more_than_twenty_sheets_mark_omitted_sheets(tmp_path):
    path = tmp_path / "many.xlsx"
    with zipfile.ZipFile(path, "w") as archive:
        for number in range(1, 22):
            archive.writestr(
                f"xl/worksheets/sheet{number}.xml",
                '<worksheet xmlns="urn:x"><sheetData/></worksheet>',
            )
    assert extract_attachment(path).truncated


def test_presentations_with_more_than_one_hundred_slides_mark_truncation(tmp_path):
    path = tmp_path / "many.pptx"
    with zipfile.ZipFile(path, "w") as archive:
        for number in range(1, 102):
            archive.writestr(
                f"ppt/slides/slide{number}.xml",
                '<slide xmlns="urn:x"><t>Text</t></slide>',
            )
    assert extract_attachment(path).truncated


def test_rejects_unsupported_binary_or_oversized_files(tmp_path):
    unknown = tmp_path / "payload.bin"
    unknown.write_bytes(b"binary")
    with pytest.raises(AttachmentError, match="não suportado"):
        extract_attachment(unknown)

    empty = tmp_path / "empty.txt"
    empty.write_bytes(b"")
    with pytest.raises(AttachmentError, match="vazio"):
        extract_attachment(empty)


def test_extracts_pdf_text_with_existing_qtpdf_module(tmp_path):
    path = tmp_path / "paper.pdf"
    path.write_bytes(make_pdf("PDF Noite"))

    result = extract_attachment(path)

    assert result.media_type == "PDF"
    assert "PDF Noite" in result.text


def test_rejects_corrupt_pdf_without_installing_dependencies(tmp_path):
    path = tmp_path / "paper.pdf"
    path.write_bytes(b"%PDF-1.4\ncorrupt")
    with pytest.raises(AttachmentError, match="PDF não pôde ser aberto"):
        extract_attachment(path)
