"""`DocumentLoader`: lê uma fonte por formato e normaliza para `LoadedDocument`.

No MVP processa os `.md` do Anexo A; loaders de PDF/DOCX/HTML/XLSX são plugáveis
por extensão (RF-01, RNF-07). A proveniência (doc_id, versão, fonte, oficialidade)
vem de um `DocumentDescriptor` — os `.md` carregam metadados em prosa, não em
campos legíveis por máquina, então o mapeamento é explícito (ver `pipeline.py`).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..models import DocumentSource, LoadedDocument
from .sections import parse_sections

__all__ = [
    "DocumentDescriptor",
    "UnsupportedFormatError",
    "DocumentLoadError",
    "DocumentLoader",
    "load_markdown",
]


class DocumentLoadError(RuntimeError):
    """Falha ao ler ou normalizar um documento."""


class UnsupportedFormatError(DocumentLoadError):
    """Extensão sem loader registrado (ex.: PDF/DOCX antes de plugados)."""


@dataclass(frozen=True)
class DocumentDescriptor:
    """Proveniência de um documento + caminho da fonte. Imutável: cada documento
    do corpus é um descriptor distinto, sem estado compartilhado."""

    doc_id: str
    doc_title: str
    version: str
    version_date: str
    source: DocumentSource
    is_official: bool
    path: Path


def load_markdown(path: Path) -> str:
    """Lê um `.md` e normaliza apenas o que não altera a estrutura: quebras de
    linha e espaços à direita. Headings, tabelas e listas permanecem intactos —
    é deles que `parse_sections` extrai a estrutura."""
    raw = path.read_text(encoding="utf-8")
    lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(line.rstrip() for line in lines).strip()


# Loaders plugáveis por extensão (RNF-07). PDF/DOCX/HTML/XLSX entram aqui sem
# tocar o restante do pipeline; ausência → erro explícito, nunca degradação.
_LOADERS: dict[str, Callable[[Path], str]] = {".md": load_markdown}


class DocumentLoader:
    """Despacha a leitura por extensão e devolve um `LoadedDocument` normalizado.

    A extração de seções/tabelas é validada na carga (o texto precisa render ao
    menos uma seção) e reaproveitada pelo `Chunker`, que opera sobre o mesmo texto.
    """

    def __init__(self, loaders: dict[str, Callable[[Path], str]] | None = None) -> None:
        self._loaders = dict(loaders) if loaders is not None else dict(_LOADERS)

    def supports(self, extension: str) -> bool:
        return extension.lower() in self._loaders

    def load(self, descriptor: DocumentDescriptor) -> LoadedDocument:
        path = descriptor.path
        if not path.exists():
            raise DocumentLoadError(f"Documento não encontrado: {path}")
        loader = self._loaders.get(path.suffix.lower())
        if loader is None:
            raise UnsupportedFormatError(
                f"Formato sem loader registrado: {path.suffix!r} ({path.name}). "
                f"Formatos disponíveis: {sorted(self._loaders)}."
            )
        text = loader(path)
        if not parse_sections(text):
            raise DocumentLoadError(f"Documento sem conteúdo estruturável: {path.name}")
        return LoadedDocument(
            doc_id=descriptor.doc_id,
            doc_title=descriptor.doc_title,
            version=descriptor.version,
            version_date=descriptor.version_date,
            source=descriptor.source,
            is_official=descriptor.is_official,
            text=text,
        )
