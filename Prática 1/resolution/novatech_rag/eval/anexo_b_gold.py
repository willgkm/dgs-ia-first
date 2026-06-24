"""Carregamento do gabarito do Anexo B (mapa de cobertura pergunta → chunks).

O Anexo B lista, por pergunta, os chunks que **devem** ser recuperados e os que
**podem** aparecer. Os rótulos de chunk (`POL-001-B`, `PROC-042v2-A`, `FAQ-15`...)
são mapeados para o `doc_id` indexado no pipeline — a granularidade de avaliação é
o documento-fonte, sinal estável e determinístico (a seção exata varia com o
chunker). Linhas marcadas "Nenhum chunk relevante" viram casos de abstenção.

`load_anexo_b_gold` é puro (lê o arquivo e devolve as entradas; não muta estado).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

__all__ = ["GoldEntry", "chunk_label_to_doc_id", "load_anexo_b_gold"]

_COVERAGE_HEADING = "## Mapa de cobertura"
_TABLE_ROW = re.compile(r"^\s*\|(.+)\|\s*$")
_QUOTED = re.compile(r"“([^”]+)”|\"([^\"]+)\"")
_CHUNK_LABEL = re.compile(r"(?:POL-001|SLA-2024|PROC-042v2|PROC-042|FAQ)-[A-Za-z0-9]+")
_NO_RELEVANT_CHUNK = "nenhum chunk relevante"


@dataclass(frozen=True)
class GoldEntry:
    """Uma linha do mapa de cobertura: pergunta + documentos esperados.

    `expected_doc_ids` são os documentos que devem ser recuperados; `should_abstain`
    marca perguntas sem cobertura na base (o pipeline deve abster-se, não recuperar).
    """

    question: str
    expected_doc_ids: frozenset[str]
    optional_doc_ids: frozenset[str]
    should_abstain: bool


def chunk_label_to_doc_id(label: str) -> str:
    """Mapeia um rótulo de chunk do Anexo B para o `doc_id` indexado.

    `PROC-042v2-*` precede `PROC-042-*` para não confundir a versão revisada com a
    original; o FAQ colapsa em `FAQ-atendimento` (um único documento-fonte)."""
    if label.startswith("POL-001"):
        return "POL-001"
    if label.startswith("SLA-2024"):
        return "SLA-2024"
    if label.startswith("PROC-042v2"):
        return "PROC-042-v2"
    if label.startswith("PROC-042"):
        return "PROC-042-v1"
    if label.startswith("FAQ"):
        return "FAQ-atendimento"
    raise ValueError(f"Rótulo de chunk não reconhecido: {label!r}")


def load_anexo_b_gold(path: Path) -> list[GoldEntry]:
    """Lê o arquivo do Anexo B e extrai as entradas do mapa de cobertura."""
    rows = _coverage_rows(path.read_text(encoding="utf-8"))
    return [entry for row in rows if (entry := _parse_row(row)) is not None]


def _coverage_rows(text: str) -> list[list[str]]:
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(_COVERAGE_HEADING))
    rows: list[list[str]] = []
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        match = _TABLE_ROW.match(line)
        if match is None:
            continue
        rows.append([cell.strip() for cell in match.group(1).split("|")])
    return rows


def _parse_row(cells: list[str]) -> GoldEntry | None:
    if len(cells) < 2:
        return None
    question_cell, must_cell = cells[0], cells[1]
    optional_cell = cells[2] if len(cells) > 2 else ""
    if question_cell.lower().startswith("pergunta") or set(question_cell) <= {"-", ":"}:
        return None
    question = _extract_question(question_cell)
    if not question:
        return None
    return GoldEntry(
        question=question,
        expected_doc_ids=_doc_ids(must_cell),
        optional_doc_ids=_doc_ids(optional_cell),
        should_abstain=_NO_RELEVANT_CHUNK in must_cell.lower(),
    )


def _extract_question(cell: str) -> str:
    match = _QUOTED.search(cell)
    if match is not None:
        return next(group for group in match.groups() if group is not None).strip()
    return cell.strip()


def _doc_ids(cell: str) -> frozenset[str]:
    return frozenset(chunk_label_to_doc_id(label) for label in _unique(_CHUNK_LABEL.findall(cell)))


def _unique(labels: Iterable[str]) -> list[str]:
    seen: dict[str, None] = {}
    for label in labels:
        seen.setdefault(label, None)
    return list(seen)
