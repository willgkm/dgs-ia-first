"""Logging estruturado (JSON) para a observabilidade do MVP.

Uma linha por evento, JSON parseável (techspec, "Monitoramento → MVP"): cada
registro é um objeto com `event` + campos. O formatter emite apenas a mensagem já
serializada, então os logs da ingestão (`novatech_rag.ingestion`) e da CLI fluem
pelo mesmo handler sem dupla codificação. Sem I/O em tempo de import: a
configuração acontece ao iniciar a CLI.

`import logging` aqui é o módulo padrão (import absoluto); este módulo é
`novatech_rag.logging` e não colide com ele.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import IO

__all__ = ["LOGGER_NAME", "configure_json_logging", "get_logger", "log_event"]

LOGGER_NAME = "novatech_rag"


class _MessageOnlyFormatter(logging.Formatter):
    """Emite só a mensagem (já em JSON), uma linha por evento."""

    def format(self, record: logging.LogRecord) -> str:
        return record.getMessage()


def configure_json_logging(stream: IO[str] | None = None, level: int = logging.INFO) -> None:
    """Instala um handler único de logs JSON no logger raiz do pacote (idempotente)."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    handler = logging.StreamHandler(stream if stream is not None else sys.stderr)
    handler.setFormatter(_MessageOnlyFormatter())
    logger.addHandler(handler)


def get_logger(name: str | None = None) -> logging.Logger:
    """Retorna o logger do pacote (ou um filho nomeado), sob o handler configurado."""
    if name is None:
        return logging.getLogger(LOGGER_NAME)
    return logging.getLogger(f"{LOGGER_NAME}.{name}")


def log_event(logger: logging.Logger, event: str, **fields: object) -> None:
    """Emite um evento estruturado como uma linha JSON (`event` + campos)."""
    logger.info(json.dumps({"event": event, **fields}, ensure_ascii=False, sort_keys=True))
