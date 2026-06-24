"""Parser estrutural de Markdown: extrai seções e blocos atômicos.

Compartilhado pelo `DocumentLoader` (normalização/estrutura) e pelo
`SectionAwareChunker` (divisão). Um *bloco* é a menor unidade que o chunker
nunca pode cortar no meio: uma linha de tabela, um passo numerado, um item de
lista ou um parágrafo. Tabelas e passos numerados são o requisito central do
RF-02 — preservá-los íntegros começa por reconhecê-los aqui.

Módulo puro (sem I/O e sem dependências externas): a estrutura do Markdown já é
texto, então a extração de seções/tabelas não exige bibliotecas pesadas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

__all__ = [
    "BlockKind",
    "Block",
    "Section",
    "parse_sections",
]

_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_TABLE = re.compile(r"^\s*\|")
_NUMBERED = re.compile(r"^\s*\d+\.\s+\S")
_LIST = re.compile(r"^\s*[-*]\s+\S")

INTRO_SECTION_TITLE = "Introdução"


class BlockKind(str, Enum):
    """Tipo de bloco. Só `PARAGRAPH` é elegível para overlap (duplicar uma
    tabela ou um passo numerado no overlap descaracterizaria o conteúdo)."""

    PARAGRAPH = "paragraph"
    TABLE = "table"
    NUMBERED = "numbered"
    LIST = "list"


@dataclass(frozen=True)
class Block:
    """Unidade atômica de conteúdo dentro de uma seção."""

    kind: BlockKind
    text: str


@dataclass(frozen=True)
class Section:
    """Trecho do documento sob um mesmo título (heading). A introdução — texto
    antes do primeiro heading — recebe `INTRO_SECTION_TITLE`."""

    title: str
    blocks: list[Block]


def parse_sections(text: str) -> list[Section]:
    """Divide o texto em seções por heading e cada seção em blocos atômicos."""
    sections: list[Section] = []
    current_title = INTRO_SECTION_TITLE
    current_lines: list[str] = []

    def flush_section() -> None:
        blocks = _blocks_from_lines(current_lines)
        if blocks:
            sections.append(Section(title=current_title, blocks=blocks))

    for line in text.splitlines():
        heading = _HEADING.match(line)
        if heading is None:
            current_lines.append(line)
            continue
        flush_section()
        current_title = heading.group(2).strip()
        current_lines = []

    flush_section()
    return sections


def _blocks_from_lines(lines: list[str]) -> list[Block]:
    blocks: list[Block] = []
    index = 0
    total = len(lines)
    while index < total:
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if _TABLE.match(line):
            block, index = _consume_table(lines, index)
        elif _NUMBERED.match(line):
            block, index = _consume_indented_run(lines, index, BlockKind.NUMBERED)
        elif _LIST.match(line):
            block, index = _consume_indented_run(lines, index, BlockKind.LIST)
        else:
            block, index = _consume_paragraph(lines, index)
        blocks.append(block)
    return blocks


def _consume_table(lines: list[str], start: int) -> tuple[Block, int]:
    index = start
    while index < len(lines) and _TABLE.match(lines[index]):
        index += 1
    text = "\n".join(lines[start:index]).rstrip()
    return Block(kind=BlockKind.TABLE, text=text), index


def _consume_indented_run(lines: list[str], start: int, kind: BlockKind) -> tuple[Block, int]:
    """Consome um único item (passo numerado ou item de lista) mais suas linhas
    de continuação, parando no próximo item, tabela, heading ou linha em branco.
    Cada item vira um bloco — assim o empacotamento quebra entre itens, nunca no
    meio de um passo."""
    index = start + 1
    while index < len(lines):
        line = lines[index]
        if not line.strip() or _is_block_start(line):
            break
        index += 1
    text = "\n".join(lines[start:index]).rstrip()
    return Block(kind=kind, text=text), index


def _consume_paragraph(lines: list[str], start: int) -> tuple[Block, int]:
    index = start
    while index < len(lines):
        line = lines[index]
        if not line.strip() or _is_block_start(line):
            break
        index += 1
    text = "\n".join(lines[start:index]).rstrip()
    return Block(kind=BlockKind.PARAGRAPH, text=text), index


def _is_block_start(line: str) -> bool:
    return bool(_TABLE.match(line) or _NUMBERED.match(line) or _LIST.match(line))
