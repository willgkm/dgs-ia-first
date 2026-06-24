"""Camada de prompt (serviços): system prompt versionado + PromptAssembler.

Expõe o `StaticPromptAssembler` (montagem estático + dinâmico, RF-04/RF-12) e o
carregamento do system prompt versionado (v1/v2). A análise v1→v2 e o mapeamento
estático/dinâmico com estimativa de tokens estão em `CHANGELOG.md`.
"""

from .assembler import (
    ABSTENTION_DIRECTIVE,
    StaticPromptAssembler,
    estimate_prompt_tokens,
    load_system_prompt,
)

__all__ = [
    "ABSTENTION_DIRECTIVE",
    "StaticPromptAssembler",
    "estimate_prompt_tokens",
    "load_system_prompt",
]
