"""Testes unitários do `SectionAwareChunker` (RF-02).

Cobre os critérios da tarefa: teto de ~256 tokens, overlap aplicado, tabela do
PROC-042 não cortada e passos numerados íntegros. Mistura entradas sintéticas
(mecânica controlada) com os arquivos reais do Anexo A (critérios de sucesso).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from novatech_rag.config import RagConfig
from novatech_rag.ingestion.chunker import SectionAwareChunker, estimate_tokens
from novatech_rag.ingestion.loader import DocumentDescriptor, DocumentLoader
from novatech_rag.models import DocumentSource, LoadedDocument

_FIXED_CLOCK = lambda: datetime(2024, 1, 1, tzinfo=timezone.utc)  # noqa: E731


def _in_both(first: str, second: str, index: int) -> bool:
    token = f"Token{index:02d}"
    return token in first and token in second


def make_document(text: str, doc_id: str = "DOC-1") -> LoadedDocument:
    return LoadedDocument(
        doc_id=doc_id,
        doc_title="Documento de teste",
        version="1.0",
        version_date="2024-01-01",
        source=DocumentSource.REDE,
        is_official=True,
        text=text,
    )


def load_anexo(corpus_dir: Path, filename: str, doc_id: str) -> LoadedDocument:
    descriptor = DocumentDescriptor(
        doc_id=doc_id,
        doc_title=doc_id,
        version="1.0",
        version_date="2024-01-01",
        source=DocumentSource.SHAREPOINT,
        is_official=True,
        path=corpus_dir / filename,
    )
    return DocumentLoader().load(descriptor)


@pytest.fixture
def chunker() -> SectionAwareChunker:
    return SectionAwareChunker(RagConfig(), clock=_FIXED_CLOCK)


class TestTokenCap:
    def test_long_section_is_split_under_the_cap(self) -> None:
        config = RagConfig(max_chunk_tokens=60, chunk_overlap_ratio=0.1)
        paragraphs = "\n\n".join(f"Parágrafo número {i} com texto." for i in range(40))
        document = make_document(f"## Seção longa\n\n{paragraphs}")

        chunks = SectionAwareChunker(config, clock=_FIXED_CLOCK).split(document)

        assert len(chunks) > 1
        for chunk in chunks:
            assert estimate_tokens(chunk.text) <= config.max_chunk_tokens

    def test_oversized_atomic_table_is_kept_whole(self) -> None:
        config = RagConfig(max_chunk_tokens=20, chunk_overlap_ratio=0.1)
        rows = "\n".join(f"| Região {i} | Multiplicador {i} valor |" for i in range(15))
        document = make_document(f"## Tabela\n\n| Região | Multiplicador |\n|--|--|\n{rows}")

        chunks = SectionAwareChunker(config, clock=_FIXED_CLOCK).split(document)

        table_chunks = [c for c in chunks if "Região 0" in c.text]
        assert len(table_chunks) == 1
        assert "Região 14" in table_chunks[0].text


class TestOverlap:
    def test_consecutive_chunks_share_overlap_text(self) -> None:
        config = RagConfig(max_chunk_tokens=50, chunk_overlap_ratio=0.15)
        # Cada parágrafo tem um marcador único (TokenNN), então a presença do
        # mesmo marcador em dois chunks só pode vir do overlap, não da repetição.
        paragraphs = "\n\n".join(f"Token{i:02d} conteudo isolado." for i in range(30))
        document = make_document(f"## Seção\n\n{paragraphs}")

        chunks = SectionAwareChunker(config, clock=_FIXED_CLOCK).split(document)

        assert len(chunks) >= 2
        shared = {f"Token{i:02d}" for i in range(30) if _in_both(chunks[0].text, chunks[1].text, i)}
        assert shared, "nenhum parágrafo de borda foi repetido entre chunks vizinhos"

    def test_zero_overlap_ratio_produces_no_repeated_paragraph(self) -> None:
        config = RagConfig(max_chunk_tokens=40, chunk_overlap_ratio=0.0)
        paragraphs = "\n\n".join(f"Conteudo{i:02d} unico." for i in range(20))
        document = make_document(f"## Seção\n\n{paragraphs}")

        chunks = SectionAwareChunker(config, clock=_FIXED_CLOCK).split(document)

        joined = [c.text for c in chunks]
        for token in (f"Conteudo{i:02d}" for i in range(20)):
            assert sum(token in text for text in joined) == 1


class TestNumberedSteps:
    def test_numbered_step_is_not_split_across_chunks(self) -> None:
        config = RagConfig(max_chunk_tokens=45, chunk_overlap_ratio=0.1)
        steps = "\n".join(
            f"{i}. Passo {i} com uma instrução suficientemente longa para ocupar espaço."
            for i in range(1, 9)
        )
        document = make_document(f"## Procedimento\n\n{steps}")

        chunks = SectionAwareChunker(config, clock=_FIXED_CLOCK).split(document)

        for step in range(1, 9):
            sentence = f"Passo {step} com uma instrução"
            holding = [c.text for c in chunks if sentence in c.text]
            assert len(holding) == 1, f"passo {step} dividido ou duplicado"


class TestAnexoA:
    def test_proc_042_v1_multiplier_table_stays_intact(self, corpus_dir: Path) -> None:
        document = load_anexo(corpus_dir, "PROC-042-frete-especial-v1.md", "PROC-042-v1")

        chunks = SectionAwareChunker(RagConfig(), clock=_FIXED_CLOCK).split(document)

        table_chunks = [c for c in chunks if "| Sul | 1.2 |" in c.text]
        assert len(table_chunks) == 1
        table = table_chunks[0].text
        for row in ("| Sul | 1.2 |", "| Sudeste | 1.0 |", "| Norte | 1.6 |"):
            assert row in table

    def test_pol_001_procedure_steps_are_each_intact(self, corpus_dir: Path) -> None:
        document = load_anexo(corpus_dir, "POL-001-politica-devolucao.md", "POL-001")

        chunks = SectionAwareChunker(RagConfig(), clock=_FIXED_CLOCK).split(document)

        fragment = "O time de atendimento tem 4 horas úteis para triagem"
        holding = [c.text for c in chunks if fragment in c.text]
        assert len(holding) == 1

    def test_chunks_carry_provenance_metadata(self, corpus_dir: Path) -> None:
        document = load_anexo(corpus_dir, "FAQ-atendimento.md", "FAQ-atendimento")

        chunks = SectionAwareChunker(RagConfig(), clock=_FIXED_CLOCK).split(document)

        assert chunks
        sample = chunks[0]
        assert sample.metadata.doc_id == "FAQ-atendimento"
        assert sample.metadata.section
        assert sample.metadata.ingested_at == _FIXED_CLOCK()

    def test_chunk_ids_are_deterministic_across_runs(self, corpus_dir: Path) -> None:
        document = load_anexo(corpus_dir, "SLA-2024-tabela-sla-clientes.md", "SLA-2024")
        chunker = SectionAwareChunker(RagConfig(), clock=_FIXED_CLOCK)

        first = [c.chunk_id for c in chunker.split(document)]
        second = [c.chunk_id for c in chunker.split(document)]

        assert first == second
        assert len(set(first)) == len(first)
