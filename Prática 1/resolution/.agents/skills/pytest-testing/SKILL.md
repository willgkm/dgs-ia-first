---
name: pytest-testing
description: Defines pytest conventions for unit and integration tests - arrange-act-assert structure, fixtures for ephemeral resources, parametrize for case tables, mocking embedding providers for determinism, markers for integration tests, and treating LLM-as-judge evaluation as graded rubrics rather than binary pass or fail. Use when adding tests, structuring a test suite, or reviewing coverage. Do not use for JavaScript test runners such as Vitest or Jest, or for load testing.
---

# pytest testing

Every task ships its own unit and integration tests. This skill defines how to write them in pytest for this RAG codebase.

## Procedures

**Step 1: Structure and layout**
1. Mirror the package under `tests/`: unit tests as `tests/test_<module>.py`; integration tests under `tests/integration/`.
2. Write each test in arrange-act-assert order with one clear behavior per test; name tests `test_<unit>_<condition>_<expected>`.
3. Mark integration tests with `@pytest.mark.integration` and register the marker in `pyproject.toml`/`pytest.ini` so unit runs can exclude them (`pytest -m "not integration"`).
4. Keep assertions specific: assert on the value and reason (e.g., `bundle.below_threshold is True`), not just truthiness.

**Step 2: Determinism and fixtures**
1. Make unit tests deterministic. Mock `EmbeddingProvider` to return fixed vectors so similarity ordering is known; never call the real model in unit tests.
2. Provide ephemeral external resources via fixtures: create a temporary ChromaDB `PersistentClient` under `tmp_path` and tear it down after the test. Never write to the project's real store.
3. Build domain objects through small factory helpers/fixtures (`make_chunk(...)`) to keep tests readable.
4. Use `@pytest.mark.parametrize` for case tables (chunk-size limits, threshold boundaries, conflict vs no-conflict) instead of copy-pasted tests.

**Step 3: Coverage required by the tasks**
1. `Chunker`: assert the token cap holds, overlap is applied, table rows stay intact, and numbered steps are not split mid-step.
2. `VectorStore.upsert`: assert reindexing the same `chunk_id` replaces rather than duplicates (count is stable).
3. `ConflictDetector`: given PROC-042 v1 + v2 results, assert a `ConflictGroup` with both versions.
4. `Retriever`: assert `below_threshold` when all scores fall under `min_score`; assert the `where` metadata filter is applied.
5. `PromptAssembler`: assert the token budget is respected (lowest scores dropped), highest scores sit at the edges, conflict alert is injected, and abstention instruction appears when `below_threshold`.
6. Integration: run ingestion→retrieval→prompt over Anexo A in an ephemeral store; assert PROC-042 yields both versions plus alert, and out-of-base questions yield abstention.

**Step 4: Evaluation tests (non-deterministic generation)**
1. Compute recall@N over the Anexo B gold map with deterministic assertions (the retrieval layer is deterministic); assert the aggregate meets the ≥80% target.
2. For generation quality, treat LLM-as-judge as a graded rubric (precision, citation, guardrail adherence), not binary pass/fail. Assert rubric scores clear a threshold and tolerate variance; do not assert exact strings on model output.
3. Keep guardrail trap cases (Platinum, dangerous cargo, PROC-042, out-of-base) as explicit, individually named tests.

**Step 5: Run**
1. Run `pytest -m "not integration"` for the fast unit loop; run `pytest` for the full suite including integration.
2. Treat any skipped or xfail test as a reported gap, not a pass.

## Error Handling
* If a test is flaky because it hits the real embedding model or a shared store, replace the dependency with a mock or a `tmp_path` fixture — flakiness signals a missing isolation boundary.
* If an integration test needs network to download a model, mark it and document the prerequisite; do not let it fail silently in CI.
* If a guardrail generation test fails intermittently, re-examine the rubric threshold before weakening the assertion, since generation is non-deterministic by nature.
