"""Teste de integração da CLI: ingest → query → eval sobre o Anexo A.

Exercita o fluxo real (ChromaDB efêmero + `all-MiniLM-L6-v2`): `ingest` indexa o
corpus, `query` emite um prompt não-vazio com citação, e `eval` gera o relatório
com recall@N. É o "E2E funcional" do MVP. Marcado `integration`: pode baixar o
modelo.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("chromadb")
pytest.importorskip("sentence_transformers")

from novatech_rag.cli import main  # noqa: E402

pytestmark = pytest.mark.integration

_ANEXO_B = Path(__file__).resolve().parents[3] / "anexo-b-chunks-referencia-rag.md"


def _persist_args(persist_dir: Path) -> list[str]:
    return ["--persist-dir", str(persist_dir), "--collection", "cli_anexo_a"]


class TestCliPipeline:
    def test_ingest_then_query_emits_prompt_with_citation(
        self, tmp_path: Path, corpus_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        store = tmp_path / "chroma"

        ingest_code = main([*_persist_args(store), "ingest", str(corpus_dir)])
        capsys.readouterr()
        query_code = main(
            [*_persist_args(store), "query", "Qual o prazo de devolução de mercadorias?"]
        )

        assert ingest_code == 0
        assert query_code == 0
        prompt = capsys.readouterr().out
        assert "Pergunta:" in prompt
        assert "POL-001" in prompt

    def test_query_out_of_base_emits_abstention_prompt(
        self, tmp_path: Path, corpus_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        store = tmp_path / "chroma"
        main([*_persist_args(store), "ingest", str(corpus_dir)])
        capsys.readouterr()

        code = main([*_persist_args(store), "query", "qual a capital da França"])

        assert code == 0
        # min_score default (0.35) pode reter ruído; o teste de abstenção forte está
        # em test_guardrails. Aqui basta o prompt ser emitido sem erro.
        assert "Pergunta:" in capsys.readouterr().out

    def test_eval_generates_report_meeting_recall_target(
        self, tmp_path: Path, corpus_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        store = tmp_path / "chroma"
        report_path = tmp_path / "eval-report.json"
        main([*_persist_args(store), "ingest", str(corpus_dir)])
        capsys.readouterr()

        code = main(
            [*_persist_args(store), "eval", "--gold", str(_ANEXO_B), "--out", str(report_path)]
        )

        assert code == 0
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["recall"]["target_met"] is True
        assert report["guardrails"]["critical_all_passed"] is True
