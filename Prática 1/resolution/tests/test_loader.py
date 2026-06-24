"""Testes unitários do `DocumentLoader` e da normalização de Markdown."""

from __future__ import annotations

from pathlib import Path

import pytest

from novatech_rag.ingestion.loader import (
    DocumentDescriptor,
    DocumentLoader,
    DocumentLoadError,
    UnsupportedFormatError,
    load_markdown,
)
from novatech_rag.models import DocumentSource


def descriptor_for(path: Path, doc_id: str = "DOC-1") -> DocumentDescriptor:
    return DocumentDescriptor(
        doc_id=doc_id,
        doc_title="Doc",
        version="1.0",
        version_date="2024-01-01",
        source=DocumentSource.REDE,
        is_official=True,
        path=path,
    )


class TestLoadMarkdown:
    def test_normalizes_line_endings_and_trailing_spaces(self, tmp_path: Path) -> None:
        path = tmp_path / "doc.md"
        path.write_bytes(b"# Titulo  \r\n\r\nLinha com espacos   \r\n")

        text = load_markdown(path)

        assert "\r" not in text
        assert text == "# Titulo\n\nLinha com espacos"


class TestDocumentLoader:
    def test_loads_markdown_into_loaded_document(self, tmp_path: Path) -> None:
        path = tmp_path / "doc.md"
        path.write_text("# Politica\n\nConteudo normativo.", encoding="utf-8")

        document = DocumentLoader().load(descriptor_for(path, "POL-X"))

        assert document.doc_id == "POL-X"
        assert document.source is DocumentSource.REDE
        assert "Conteudo normativo." in document.text

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(DocumentLoadError, match="não encontrado"):
            DocumentLoader().load(descriptor_for(tmp_path / "ausente.md"))

    def test_unsupported_extension_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "planilha.xlsx"
        path.write_text("dados", encoding="utf-8")

        with pytest.raises(UnsupportedFormatError, match="sem loader"):
            DocumentLoader().load(descriptor_for(path))

    def test_supports_reports_registered_formats(self) -> None:
        loader = DocumentLoader()
        assert loader.supports(".md") is True
        assert loader.supports(".pdf") is False
