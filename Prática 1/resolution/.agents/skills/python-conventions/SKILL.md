---
name: python-conventions
description: Specifies Python conventions for this codebase - PEP 8 module layout, type hints on public functions, dataclasses for domain models, typing.Protocol for swappable interfaces, deterministic ids via hashing, explicit exceptions over silent degradation, and pyproject.toml packaging. Use when writing or reviewing Python modules, defining domain models or interfaces, or structuring a Python package. Do not use for JavaScript or TypeScript code, or for non-Python tooling.
---

# Python conventions

Complements `code-standards-en` (English identifiers, CQS, early return, sizing) with Python-specific idioms. Apply both. Domain content and user-facing prompt text stay in Portuguese; identifiers, symbols, and constants stay in English.

## Procedures

**Step 1: Package layout**
1. Target Python 3.10+ syntax (`list[str]`, `dict | None`, `X | None` unions).
2. Organize the package by layer mirroring the techspec modules: `ingestion/` (data), `retrieval/` and `prompt/` (services), CLI entrypoint (controllers), `eval/` (tooling). Dependencies point inward: services may import models; models import nothing from services.
3. Place an `__init__.py` in every package directory; expose only the intended public surface from each `__init__.py`.
4. Declare dependencies and build config in `pyproject.toml`. Pin a minimum Python version; list runtime deps (`chromadb`, `sentence-transformers`) separately from optional ones (`ollama`) via extras.

**Step 2: Domain models and interfaces**
1. Model domain entities as `@dataclass` (use `frozen=True` for value objects such as `Chunk`, `ChunkMetadata`). Annotate every field with a type.
2. Define swappable boundaries as `typing.Protocol` classes, not abstract base classes, so implementations need no explicit inheritance (`Chunker`, `EmbeddingProvider`, `VectorStore`, `Retriever`, `PromptAssembler`).
3. Type-hint every public function and method, including the return type. Prefer `Sequence`/`Mapping` for read-only parameters and concrete `list`/`dict` for returns.
4. Generate deterministic identifiers with a stable hash of normalized inputs (`hashlib.sha256` over `f"{doc_id}|{section}|{ordinal}"`), never with `id()`, object identity, or a non-seeded random source. Determinism is what makes upserts idempotent.

**Step 3: Behavior and errors**
1. Raise explicit, typed exceptions on unrecoverable conditions (e.g., embedding-model download failure) instead of returning `None` or degrading silently. Define narrow custom exceptions when callers must distinguish failure modes.
2. Catch only the specific exceptions a step can recover from; let unexpected ones propagate.
3. Keep functions pure where possible (CQS): retrieval/query functions return data without mutating; `upsert`-style mutators return `None`.
4. Use `pathlib.Path` for filesystem paths, never string concatenation. Manage external resources with context managers.
5. Avoid module-level side effects (no I/O, no model loading at import time); perform such work inside functions or lazy initializers.

**Step 4: Validation**
1. Format and lint before committing. Run `ruff check .` and `ruff format .` (or the project's configured formatter) and resolve all findings.
2. Run `mypy` (or `pyright`) on the package if type checking is configured; treat type errors as build failures.

## Error Handling
* If the metadata of a new skill or module must be validated, run `python3 ../skill-best-practices/scripts/validate-metadata.py` only after confirming a real interpreter is installed; the Windows Store alias is not a Python interpreter.
* If a `Protocol` implementation diverges from its interface, the type checker reports the mismatch — fix the implementation, do not relax the `Protocol`.
* If localized Portuguese copy and English-only identifiers conflict, keep identifiers English and copy Portuguese, per product policy.
