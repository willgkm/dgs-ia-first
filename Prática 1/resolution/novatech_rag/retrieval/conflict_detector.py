"""`ConflictDetector`: agrupa resultados por documento-base e sinaliza versões divergentes.

Desambiguação por metadados (techspec, "Desambiguação por metadados"): o detector
reúne os `RetrievalResult` de um mesmo documento-base — `PROC-042-v1` e `PROC-042-v2`
têm `doc_id` distintos (coexistem, RF-10) mas a mesma chave-base `PROC-042` — e,
quando duas ou mais versões aparecem juntas, emite um `ConflictGroup`. O modelo
nunca escolhe a versão vigente; o pipeline apenas expõe ambas para o alerta de
divergência (G-07/G-08). `detect` é puro (CQS): consulta os resultados e devolve
os grupos, sem mutar nada.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from ..models import ConflictGroup, ConflictVersion, RetrievalResult

__all__ = ["ConflictDetector", "conflict_key"]

# Sufixo de versão no `doc_id` (`-v1`, `-v2`, ...). `PROC-042-v1`/`PROC-042-v2`
# colapsam em `PROC-042`; `POL-001`/`SLA-2024` (sem sufixo) ficam inalterados.
_VERSION_SUFFIX = re.compile(r"-v\d+$", re.IGNORECASE)


def conflict_key(doc_id: str) -> str:
    """Chave-base do documento: remove o sufixo de versão (`-v\\d+`) do `doc_id`."""
    return _VERSION_SUFFIX.sub("", doc_id)


class ConflictDetector:
    """Detecta versões divergentes do mesmo documento-base entre os resultados."""

    def detect(self, results: Sequence[RetrievalResult]) -> list[ConflictGroup]:
        versions_by_base = self._group_versions_by_base(results)
        return [
            self._build_group(base, versions)
            for base, versions in versions_by_base.items()
            if len(versions) > 1
        ]

    def _group_versions_by_base(
        self, results: Sequence[RetrievalResult]
    ) -> dict[str, dict[str, ConflictVersion]]:
        versions_by_base: dict[str, dict[str, ConflictVersion]] = {}
        for result in results:
            metadata = result.chunk.metadata
            versions = versions_by_base.setdefault(conflict_key(metadata.doc_id), {})
            if metadata.doc_id in versions:
                continue
            versions[metadata.doc_id] = ConflictVersion(
                version=metadata.version,
                version_date=metadata.version_date,
                chunk_id=result.chunk.chunk_id,
            )
        return versions_by_base

    def _build_group(self, base: str, versions: dict[str, ConflictVersion]) -> ConflictGroup:
        ordered = sorted(
            versions.values(), key=lambda version: (version.version_date, version.version)
        )
        return ConflictGroup(doc_id=base, versions=ordered)
