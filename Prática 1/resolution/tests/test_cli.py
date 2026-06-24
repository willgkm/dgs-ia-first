"""Testes unitários da CLI: parsing de subcomandos + log estruturado JSON.

Sem ChromaDB nem modelo: testam só o parser e o formato dos logs (determinístico).
A execução ponta a ponta (ingest→query→eval) fica no teste de integração.
"""

from __future__ import annotations

import io
import json
import logging

from novatech_rag import cli
from novatech_rag.cli import _run_eval, _run_ingest, _run_query, build_parser
from novatech_rag.logging import configure_json_logging, get_logger, log_event


class TestArgumentParsing:
    def test_ingest_parses_directory_and_handler(self) -> None:
        args = build_parser().parse_args(["ingest", "corpus-dir"])

        assert args.command == "ingest"
        assert args.directory == "corpus-dir"
        assert args.handler is _run_ingest

    def test_query_parses_question_and_default_prompt_version(self) -> None:
        args = build_parser().parse_args(["query", "qual o prazo?"])

        assert args.command == "query"
        assert args.question == "qual o prazo?"
        assert args.prompt_version == "v2"
        assert args.handler is _run_query

    def test_eval_parses_defaults_for_gold_and_out(self) -> None:
        args = build_parser().parse_args(["eval"])

        assert args.command == "eval"
        assert args.gold.endswith("anexo-b-chunks-referencia-rag.md")
        assert args.out.endswith("eval-report.json")
        assert args.handler is _run_eval

    def test_top_level_persist_dir_and_collection_override(self) -> None:
        args = build_parser().parse_args(
            ["--persist-dir", "/tmp/store", "--collection", "c1", "query", "q"]
        )

        assert args.persist_dir == "/tmp/store"
        assert args.collection == "c1"

    def test_missing_subcommand_exits_with_error(self) -> None:
        try:
            build_parser().parse_args([])
        except SystemExit as exit_error:
            assert exit_error.code != 0
        else:
            raise AssertionError("esperava SystemExit por subcomando ausente")


class TestStructuredLogging:
    def test_log_event_emits_single_parseable_json_line(self) -> None:
        buffer = io.StringIO()
        configure_json_logging(stream=buffer, level=logging.INFO)
        logger = get_logger("cli")

        log_event(logger, "query_done", result_count=3, below_threshold=False)

        lines = buffer.getvalue().strip().splitlines()
        assert len(lines) == 1
        payload = json.loads(lines[0])
        assert payload["event"] == "query_done"
        assert payload["result_count"] == 3
        assert payload["below_threshold"] is False

    def test_configure_logging_is_idempotent_single_handler(self) -> None:
        buffer = io.StringIO()
        configure_json_logging(stream=buffer)
        configure_json_logging(stream=buffer)
        logger = get_logger("cli")

        log_event(logger, "ingest_done", documents=5)

        assert len(buffer.getvalue().strip().splitlines()) == 1


class TestMainErrorHandling:
    def test_recoverable_error_returns_1_and_logs_command_failed(
        self, monkeypatch, capsys
    ) -> None:
        def boom(args: object) -> int:
            raise ValueError("falha simulada")

        monkeypatch.setattr(cli, "_run_eval", boom)

        code = cli.main(["eval"])

        assert code == 1
        payload = json.loads(capsys.readouterr().err.strip().splitlines()[-1])
        assert payload["event"] == "command_failed"
        assert payload["command"] == "eval"
