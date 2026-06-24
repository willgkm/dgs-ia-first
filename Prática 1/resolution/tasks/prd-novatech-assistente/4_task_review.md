# Review: Task 4.0 - Retrieval — Retriever (top-K + threshold) + ConflictDetector

**Revisor**: AI Code Reviewer
**Data**: 2026-06-23
**Arquivo da task**: 4_task.md
**Status**: APROVADO

## Resumo

A Tarefa 4.0 entrega a recuperação em runtime: `SimilarityRetriever` (embed da pergunta + busca top-K no `VectorStore` + threshold mínimo com abstenção + repasse de filtro `where`) e `ConflictDetector` (reagrupamento por documento-base via `conflict_key` e emissão de `ConflictGroup` quando há versões divergentes). A `Retriever` (Protocol) em `interfaces.py` ganhou o parâmetro opcional `where`, mantendo a paridade de contrato PoC↔produção (Azure AI Search) e honrando a subtarefa 4.3.

A implementação é de alta qualidade e aderente aos requisitos da task (RF-03, RF-07, RF-08, G-03, G-07) e às skills (`rag-pipeline`, `python-conventions`, `code-standards-en`, `pytest-testing`): identificadores em inglês com `snake_case`/`PascalCase` (o padrão real do repo, não camelCase), CQS (`retrieve` e `detect` puros), early return na abstenção, type hints completos, sem efeitos de import. A desambiguação é estritamente por metadados — o modelo nunca escolhe a versão vigente. Verificações de ambiente executadas e confirmadas: **103 testes passando** (suíte completa, 23 deles desta tarefa), **ruff** limpo e **mypy** sem erros (16 arquivos). Não foram encontrados problemas críticos ou major; apenas observações minor não-bloqueantes.

## Arquivos Revisados

| Arquivo | Status | Problemas |
|---------|--------|-----------|
| `novatech_rag/retrieval/conflict_detector.py` | ✅ OK | Nenhum |
| `novatech_rag/retrieval/retriever.py` | ✅ OK | 1 minor (🟢) |
| `novatech_rag/retrieval/__init__.py` | ✅ OK | Nenhum |
| `novatech_rag/interfaces.py` | ✅ OK | 1 minor (🟢) |
| `tests/test_conflict_detector.py` | ✅ OK | Nenhum |
| `tests/test_retriever.py` | ✅ OK | Nenhum |
| `tests/integration/test_retrieval.py` | ✅ OK | Nenhum |

## Problemas Encontrados

### 🔴 Problemas Críticos

Nenhum problema crítico encontrado.

Verificações específicas confirmadas como corretas:

- **RF-03 (top-K + score + threshold)**: `retrieve` embeda a pergunta com o mesmo provider da ingestão (`retriever.py:43`), consulta top-K via `vector_store.query(embedding, top_k, where)` e devolve `RetrievalBundle` com `results`, `conflicts` e `below_threshold` (`retriever.py:44-49`), exatamente o modelo da techspec ("Modelos de dados → RetrievalBundle").
- **RF-07 / G-03 (abstenção por threshold)**: o filtro `result.score >= min_score` (`retriever.py:45`) mantém apenas o que passa; quando nada sobrevive, há early return com `below_threshold=True` e `results`/`conflicts` vazios (`retriever.py:46-47`). Cobre a "Abstenção por threshold" da techspec. Os testes `test_below_threshold_when_all_scores_under_min_score`, `test_keeps_only_results_at_or_above_min_score` e o limite inclusivo `test_score_equal_to_min_score_is_kept` (score == min_score é mantido) validam a fronteira.
- **Subtarefa 4.3 (filtro `where`)**: `where` é repassado intacto ao store (`retriever.py:44`); o `Protocol` `Retriever` foi atualizado de forma coerente com `VectorStore.query` (`interfaces.py:70-76`). Os testes `test_where_filter_is_passed_through_to_the_store` e `test_no_where_filter_passes_none` provam o repasse e o default `None`.
- **RF-08 / G-07 (versões conflitantes)**: `ConflictDetector.detect` agrupa por `conflict_key(doc_id)` — remove o sufixo `-v\d+` (`conflict_detector.py:23-28`), reagrupando `PROC-042-v1`/`PROC-042-v2` (doc_ids distintos que coexistem por RF-10) sob a chave-base `PROC-042`, exatamente como descreve o comentário em `ingestion/pipeline.py:75-77`. Só emite `ConflictGroup` quando há mais de uma versão distinta (`conflict_detector.py:39`). Confere com "ConflictDetector: dado resultados de PROC-042 v1 + v2, retorna `ConflictGroup` com as duas versões" da techspec.
- **Desambiguação por metadados, nunca pelo modelo**: a detecção opera exclusivamente sobre `result.chunk.metadata` (`doc_id`, `version`, `version_date`) e `chunk_id` (`conflict_detector.py:46-55`); não há heurística textual nem seleção de versão "vigente". Alinhado a `rag-pipeline` Passo 4 ("Resolve conflicts by metadata only").
- **Critérios de sucesso da task** validados no teste de integração sobre o Anexo A em ChromaDB efêmero: cobertura sem abstenção (`test_covered_question_retrieves_pol_001_without_abstaining`), abstenção fora da base (`test_out_of_base_question_marks_below_threshold`) e detecção das duas versões do PROC-042 na pergunta de frete (`test_freight_question_detects_both_proc_042_versions`, asserindo `{"1.0", "2.0"}`).
- **CQS / pureza**: `retrieve` e `detect` consultam e devolvem dados sem mutar estado; os helpers privados `_group_versions_by_base` e `_build_group` são puros. Sem efeitos colaterais em import (sem I/O nem carregamento de modelo no nível do módulo).
- **Determinismo dos testes unitários**: `test_retriever.py` usa o `fake_embedding_provider` (do `conftest.py`, bag-of-words com hash, sem rede) + `StubVectorStore` com scores controlados; `test_conflict_detector.py` constrói `RetrievalResult` direto, sem ChromaDB nem modelo. A integração isola o caminho que baixa o modelo com `importorskip("chromadb")`/`importorskip("sentence_transformers")` e o marker `integration`.

### 🟡 Problemas Major

Nenhum problema major encontrado.

### 🟢 Problemas Minor

1. **`retriever.py:41` e `interfaces.py:75` — `where: dict | None` usa `dict` nu.** Coerente com a assinatura de `VectorStore.query` (`interfaces.py:59`) e com a techspec, então **não é divergência**. Ainda assim, `Mapping[str, Any] | None` exprimiria melhor a intenção de leitura. Esta é a mesma observação minor já registrada na review da Tarefa 3.0 (item 3); manter consistência com o `Protocol` é aceitável, mas se for ajustar, ajuste os três pontos (`VectorStore`, `Retriever`, `SimilarityRetriever`) de uma vez. Não-bloqueante.

2. **`retriever.py:34` — linha de inicialização do `ConflictDetector` no construtor.** A linha
   ```python
   self._conflicts = conflict_detector if conflict_detector is not None else ConflictDetector()
   ```
   tem 99 caracteres (dentro do `line-length = 100` do ruff, por isso passa). É legível, mas um pequeno default poderia clarificar a intenção:
   ```python
   self._conflicts = conflict_detector or ConflictDetector()
   ```
   Atenção: `or` trataria um detector "falsy" como ausente — como `ConflictDetector` não define `__bool__`, qualquer instância é truthy e o comportamento é idêntico; ainda assim o `is not None` explícito é mais defensivo e correto. Manter como está é a escolha mais segura. Observação puramente estilística, não-bloqueante.

## ✅ Destaques Positivos

- **`conflict_key` extraída e exportada**: isolar a regra do sufixo de versão (`-v\d+`) numa função pura testável (`conflict_detector.py:26-28`), exportada no `__all__`, é a decisão de design que torna o reagrupamento PROC-042 explícito e verificável de forma independente — coberto por `TestConflictKey` com tabela `parametrize` (inclui `-V3` maiúsculo via `re.IGNORECASE` e os casos sem sufixo `POL-001`/`SLA-2024`/`FAQ-atendimento` que ficam inalterados).
- **Ordenação determinística das versões no `ConflictGroup`**: `sorted(..., key=lambda v: (v.version_date, v.version))` (`conflict_detector.py:59-61`) garante saída cronológica estável independentemente da ordem de chegada — provado por `test_versions_are_ordered_chronologically` (entrada v2 antes de v1 → saída ["1.0","2.0"]).
- **Chunk representativo por versão é o melhor ranqueado**: ao deduplicar por `doc_id` mantendo a primeira ocorrência (`conflict_detector.py:49-50`), e como o store devolve os resultados em ordem de rank, cada `ConflictVersion` aponta para o `chunk_id` de melhor score daquela versão — comportamento sutil e correto, explicitamente coberto por `test_representative_chunk_id_is_the_best_ranked_per_version`.
- **Teste de wiring do conflito sob threshold**: `test_conflict_dropped_when_one_version_is_below_threshold` prova que o conflito só emerge se ambas as versões sobreviverem ao `min_score` (a detecção roda sobre os resultados já filtrados, `retriever.py:45-48`) — exatamente o acoplamento correto entre abstenção e detecção, e um caso que muitas implementações esquecem.
- **Threshold de integração calibrado com critério documentado**: `_ABSTENTION_MIN_SCORE = 0.90` com comentário explicando que valida a abstenção sem depender da calibração absoluta do score (modelo primariamente anglófono — risco já documentado na techspec), deixando a validação fina de recall@N para a Tarefa 6.0. Pragmatismo de teste correto.
- **Docstrings que ancoram requisitos**: cada módulo amarra o comportamento aos requisitos (RF-07/G-03 na abstenção, G-07/G-08 no conflito) e cita a techspec, facilitando rastreabilidade sem poluir o corpo com comentários linha-a-linha.
- **Testes legíveis com AAA e nomes no padrão** `test_<unit>_<condition>_<expected>`, asserções específicas (`is True`/`is False`, listas exatas de scores/versões), fábrica `make_result` parametrizável e `StubVectorStore` que registra `last_where`/`last_top_k` para verificar o repasse — exatamente o que `pytest-testing` pede.

## Conformidade com Padrões

| Padrão | Status |
|--------|--------|
| Padrões de Código (`code-standards-en`: inglês, snake_case/PascalCase, CQS, early return, métodos <50 linhas, sem números mágicos) | ✅ |
| Python / Type hints (mypy) | ✅ `mypy novatech_rag` sem erros; type hints completos; `dict` nu em `where` (minor, alinhado ao Protocol) |
| RAG pipeline (`rag-pipeline`: embed com mesmo modelo, top-K, threshold/abstenção, filtro `where` por `is_official`, conflito por metadados, nunca pelo modelo) | ✅ |
| Logging | N/A (logging estruturado de query previsto na camada de orquestração/CLI — Tarefa 7.0) |
| Testes (`pytest-testing`: unit determinístico com embeddings mockados, ChromaDB efêmero, `importorskip`, marker `integration`, AAA, `parametrize`) | ✅ — 23 testes da tarefa / 103 totais passando |

## Recomendações

1. (Opcional) Padronizar `where` como `Mapping[str, Any] | None` em `VectorStore.query`, `Retriever.retrieve` e `SimilarityRetriever.retrieve` simultaneamente, se quiser aderência estrita de intenção de tipo. Herda da observação da Tarefa 3.0.
2. (Opcional) Considerar uma asserção adicional no unit do retriever verificando que `bundle.results` preserva a ordem de rank vinda do store (hoje validado indiretamente pela ordem dos scores). Cosmético.

Nenhuma recomendação é bloqueante.

## Veredito

**APROVADO.** A Tarefa 4.0 cumpre integralmente os requisitos (RF-03, RF-07, RF-08) e gates (G-03, G-07), bem como os três critérios de sucesso (cobertura recupera o documento certo, fora-da-base marca abstenção, frete recupera ambas as versões do PROC-042 com `ConflictGroup`). A desambiguação é por metadados, nunca pelo modelo, conforme `rag-pipeline`. Verificações de ambiente passam integralmente: `pytest -q` (103 passando), `ruff check` limpo e `mypy` sem erros. Os dois itens minor são puramente estilísticos/de precisão de tipo e não impedem a aprovação. Liberado para prosseguir à Tarefa 5.0 (PromptAssembler).
