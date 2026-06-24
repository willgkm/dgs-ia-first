"""CLI da PoC: `python -m novatech_rag ingest|query|eval`.

Camada de controllers (repo-folder-structure): costura ingestão (3.0), retrieval
(4.0) e montagem de prompt (5.0) e dispara a avaliação (6.0). A geração fica fora
do pipeline automatizado — `query` **emite o prompt montado** para colar no
Claude/Ollama (o `GenerationAdapter` é seam). Cada comando emite logs estruturados
JSON (observabilidade do MVP) e aborta com mensagem clara em falha (sem degradar).

Comandos são verbos; handlers são puros quanto a estado de processo (CQS): leem
configuração, executam o pipeline e devolvem o código de saída.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import cast

from .config import DEFAULT_COLLECTION_NAME, DEFAULT_PERSIST_DIRECTORY, RagConfig
from .eval.anexo_b_gold import load_anexo_b_gold
from .eval.report import build_eval_report, write_eval_report
from .ingestion.chunker import SectionAwareChunker
from .ingestion.embeddings import (
    EmbeddingModelError,
    SentenceTransformerEmbeddingProvider,
)
from .ingestion.loader import DocumentLoader, DocumentLoadError
from .ingestion.pipeline import (
    IngestionComponents,
    build_anexo_a_descriptors,
    ingest_documents,
)
from .ingestion.vector_store import ChromaVectorStore, VectorStoreError
from .logging import configure_json_logging, get_logger, log_event
from .models import AssembledPrompt
from .prompt.assembler import StaticPromptAssembler, load_system_prompt
from .retrieval.retriever import SimilarityRetriever

__all__ = ["build_parser", "main"]

_LOGGER = get_logger("cli")
_DEFAULT_GOLD = "anexo-b-chunks-referencia-rag.md"
_DEFAULT_REPORT_PATH = "reports/eval-report.json"
_DEFAULT_PROMPT_VERSION = "v2"
_EVAL_TOP_N = 5
_RECOVERABLE_ERRORS = (
    EmbeddingModelError,
    VectorStoreError,
    DocumentLoadError,
    FileNotFoundError,
    ValueError,
)


def build_parser() -> argparse.ArgumentParser:
    """Monta o parser de subcomandos (`ingest`, `query`, `eval`)."""
    parser = argparse.ArgumentParser(prog="novatech_rag", description="PoC RAG da NovaTech")
    parser.add_argument("--persist-dir", default=str(DEFAULT_PERSIST_DIRECTORY),
                        help="diretório de persistência do ChromaDB")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION_NAME,
                        help="nome da coleção no vector store")
    subcommands = parser.add_subparsers(dest="command", required=True)
    _add_ingest(subcommands)
    _add_query(subcommands)
    _add_eval(subcommands)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada da CLI. Devolve o código de saída do processo."""
    args = build_parser().parse_args(argv)
    configure_json_logging()
    try:
        return args.handler(args)
    except _RECOVERABLE_ERRORS as error:
        log_event(_LOGGER, "command_failed", command=args.command, error=str(error))
        return 1


def _add_ingest(subcommands: argparse._SubParsersAction) -> None:
    parser = subcommands.add_parser("ingest", help="indexa os documentos do Anexo A")
    parser.add_argument("directory", help="diretório com os .md do Anexo A")
    parser.set_defaults(handler=_run_ingest)


def _add_query(subcommands: argparse._SubParsersAction) -> None:
    parser = subcommands.add_parser("query", help="recupera chunks e emite o prompt montado")
    parser.add_argument("question", help="pergunta do atendente em linguagem natural")
    parser.add_argument("--prompt-version", default=_DEFAULT_PROMPT_VERSION)
    parser.set_defaults(handler=_run_query)


def _add_eval(subcommands: argparse._SubParsersAction) -> None:
    parser = subcommands.add_parser("eval", help="roda a avaliação (recall@N + guardrails)")
    parser.add_argument("--gold", default=_DEFAULT_GOLD, help="caminho do gabarito do Anexo B")
    parser.add_argument("--out", default=_DEFAULT_REPORT_PATH, help="caminho do relatório JSON")
    parser.add_argument("--prompt-version", default=_DEFAULT_PROMPT_VERSION)
    parser.set_defaults(handler=_run_eval)


def _run_ingest(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    corpus = Path(args.directory)
    if not corpus.is_dir():
        log_event(_LOGGER, "ingest_failed", reason="directory_not_found", directory=str(corpus))
        return 1
    embeddings = _build_embeddings(config)
    components = IngestionComponents(
        DocumentLoader(), SectionAwareChunker(config), _build_store(embeddings, config)
    )
    report = ingest_documents(build_anexo_a_descriptors(corpus), components, config=config)
    log_event(
        _LOGGER,
        "ingest_done",
        documents=report.document_count,
        chunks=report.chunk_count,
        oversized_chunks=report.oversized_chunk_count,
        persist_directory=str(config.persist_directory),
    )
    return 0


def _run_query(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    embeddings = _build_embeddings(config)
    retriever = SimilarityRetriever(embeddings, _build_store(embeddings, config))
    assembler = StaticPromptAssembler(load_system_prompt(args.prompt_version))
    started = time.perf_counter()
    bundle = retriever.retrieve(args.question, top_k=config.top_k, min_score=config.min_score)
    assembled = assembler.assemble(args.question, bundle, token_budget=config.token_budget)
    elapsed = time.perf_counter() - started  # retrieval + montagem; exclui o cold-start do modelo
    log_event(
        _LOGGER,
        "query_done",
        question=args.question,
        result_count=len(bundle.results),
        scores=[round(result.score, 4) for result in bundle.results],
        below_threshold=bundle.below_threshold,
        conflicts=[group.doc_id for group in bundle.conflicts],
        dropped_chunks=len(assembled.dropped_chunks),
        prompt_tokens=assembled.estimated_tokens,
        latency_seconds=round(elapsed, 4),
    )
    print(_render_prompt(assembled))
    return 0


def _run_eval(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    gold_path = Path(args.gold)
    if not gold_path.is_file():
        log_event(_LOGGER, "eval_failed", reason="gold_not_found", gold=str(gold_path))
        return 1
    embeddings = _build_embeddings(config)
    retriever = SimilarityRetriever(embeddings, _build_store(embeddings, config))
    assembler = StaticPromptAssembler(load_system_prompt(args.prompt_version))
    gold = load_anexo_b_gold(gold_path)
    report = build_eval_report(retriever, assembler, gold, top_n=_EVAL_TOP_N)
    write_eval_report(Path(args.out), report)
    recall = cast("dict[str, object]", report["recall"])
    guardrails = cast("dict[str, object]", report["guardrails"])
    log_event(
        _LOGGER,
        "eval_done",
        recall_coverage=recall["coverage_ratio"],
        recall_mean=recall["mean_recall"],
        recall_target_met=recall["target_met"],
        critical_all_passed=guardrails["critical_all_passed"],
        abstention_rate=guardrails["abstention_rate"],
        report_path=str(args.out),
    )
    return 0


def _config_from_args(args: argparse.Namespace) -> RagConfig:
    return RagConfig(persist_directory=Path(args.persist_dir), collection_name=args.collection)


def _build_embeddings(config: RagConfig) -> SentenceTransformerEmbeddingProvider:
    return SentenceTransformerEmbeddingProvider(config.embedding_model)


def _build_store(
    embeddings: SentenceTransformerEmbeddingProvider, config: RagConfig
) -> ChromaVectorStore:
    return ChromaVectorStore(embeddings, config)


def _render_prompt(assembled: AssembledPrompt) -> str:
    blocks = [assembled.system, *assembled.context_blocks, f"Pergunta: {assembled.question}"]
    return "\n\n".join(blocks)
