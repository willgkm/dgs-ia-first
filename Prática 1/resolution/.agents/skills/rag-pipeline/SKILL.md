---
name: rag-pipeline
description: Guides retrieval-augmented generation pipelines - section-aware chunking that preserves tables and numbered steps under an embedding token cap, idempotent vector-store upserts keyed by deterministic chunk ids, similarity retrieval with a minimum-score threshold for abstention, metadata-driven conflict detection across document versions, prompt assembly placing highest-scoring chunks at the context edges, and recall-at-N plus guardrail evaluation. Use when building ingestion, retrieval, prompt-assembly, or evaluation components. Do not use for fine-tuning models or non-RAG data pipelines.
---

# RAG pipeline

Treat the RAG system as a data system: metadata governs disambiguation and abstention, not the model. The model never picks the "current" version and never answers from general knowledge. Pair with `python-conventions` (implementation) and `pytest-testing` (verification).

## Procedures

**Step 1: Ingestion and chunking**
1. Load each source into normalized text plus structure (titles, sections, tables, numbered steps); keep loaders pluggable per format (md/PDF/DOCX/HTML/XLSX).
2. Chunk section-aware, not by fixed token cut. Enforce a token cap that matches the embedding model's input limit (`all-MiniLM-L6-v2` truncates at ~256 word pieces — exceeding it silently degrades the embedding). Apply ~10-15% overlap.
3. Never split a table row or a numbered procedure step across chunks. A table whose rows are cut mid-line is a chunking defect.
4. Attach metadata to every chunk: `doc_id`, `doc_title`, `version`, `version_date`, `section`, `source`, `is_official` (FAQ and other unvalidated sources = `false`), `ingested_at`.

**Step 2: Indexing (idempotent)**
1. Compute a deterministic `chunk_id` from `doc_id|section|ordinal` so reindexing replaces a version's chunks instead of duplicating them.
2. Upsert by `chunk_id`. Reindexing an updated document must leave the chunk count stable for that document.
3. Keep conflicting versions that must coexist (e.g., PROC-042 v1 and v2) as distinct `doc_id`/version pairs — do not overwrite one with the other.

**Step 3: Retrieval and abstention**
1. Embed the question with the same model used at ingestion; query top-K by similarity.
2. Apply a configurable minimum score threshold. If no chunk clears it, set `below_threshold` and stop — the answer will be an explicit "não encontrado" plus escalation, never a generated guess.
3. Support metadata `where` filters; use `is_official` to prioritize official documents over the unvalidated FAQ.

**Step 4: Conflict detection**
1. Group results by `doc_id`; when multiple `version`/`version_date` values appear for the same procedure, emit a `ConflictGroup` listing every version.
2. Resolve conflicts by metadata only. The pipeline surfaces both versions with an alert; it never selects a "current" one absent an explicit validity metadata field.

**Step 5: Prompt assembly**
1. Separate the static system prompt/guardrails (versioned artifact) from dynamic content (chunks, question, history). Estimate and document the token size of each part.
2. Respect the context token budget. When the budget is exceeded, drop the lowest-scoring chunks and record them (`dropped_chunks`).
3. Mitigate lost-in-the-middle: place the highest-scoring chunks at the beginning and end of the context, weaker ones in the middle; cap the number of chunks to avoid diluting attention.
4. When a `ConflictGroup` is present, inject the divergence alert. When `below_threshold`, inject the abstention + escalation instruction. Require source citation (document + section) for every factual claim.

**Step 6: Evaluation**
1. Measure recall@N against the gold coverage map: for each question, check whether the gold chunks appear in the top-N; target ≥80%.
2. Run the guardrail trap suite. Read `references/guardrails.md` for the exact cases and expected behavior before implementing or judging them.
3. Score generation with LLM-as-judge on a rubric (precision, citation, guardrail adherence); treat results as grades, not binary pass/fail.
4. Emit a versioned evaluation report (recall@N, correct-abstention rate, guardrail violations) and list at least two concrete retrieval/prompt problems with proposed fixes.

## Error Handling
* If recall@N is below target, inspect whether gold chunks were retrieved but ranked low (lost-in-the-middle → adjust ordering/cap or add a reranker) versus not retrieved at all (chunking or embedding-model/language mismatch — evaluate a multilingual model).
* If a table answer is wrong, check the chunk boundaries first; a cut table is the most common root cause.
* If the embedding model fails to download, abort ingestion with a clear error — never index with a fallback that changes vector dimensionality.
* If a conflict answer presents only one version, the conflict alert injection or `ConflictDetector` grouping is broken — treat as a critical guardrail failure.
