# Skills → ações

Consulte o `SKILL.md` em `.agents/skills/<nome>/` antes de implementar ou revisar.

| Skill                           | Acionar para…                                                                                                                                          | Não usar se…                                                                    |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------- |
| `code-standards-en`             | Nomes em inglês, PR, CQS, early return, tamanho de métodos/classes                                                                                     | Política exige identificadores localizados                                      |
| `repo-folder-structure`         | Onde criar `features`, pages, controllers/services/data                                                                                                | Layout do monorepo ou framework diferente do template                           |
| `python-conventions`            | Módulos Python, type hints, dataclasses, `Protocol`, ids determinísticos, layout do pacote, `pyproject.toml`                                            | Código JavaScript/TypeScript ou tooling não-Python                              |
| `pytest-testing`                | Testes unitários e de integração em pytest, fixtures, ChromaDB efêmero, mock de embeddings, avaliação LLM-as-judge                                      | Runners JS (Vitest/Jest) ou testes de carga/performance                         |
| `rag-pipeline`                  | Chunking section-aware, embeddings, upsert idempotente, threshold/abstenção, detecção de conflito por metadados, montagem de prompt, recall@N/guardrails | Fine-tuning de modelos ou pipelines de dados não-RAG                            |

**Ordem sugerida por tarefa (PoC Python/RAG):** componentes RAG (ingestão/retrieval/prompt/eval) → `rag-pipeline`, depois `python-conventions`, `code-standards-en`. Testes → `pytest-testing` + `rag-pipeline` (expectativas por componente). Estrutura do pacote → `repo-folder-structure` (adaptado a Python por `python-conventions`).

**Stack legada (Node/TS, fase de produção):** backend HTTP → `express-rest-http`, depois `repo-folder-structure`, `code-standards-en`. Testes JS → `vitest-testing` + skill da camada testada.

# Persistência do Modo Plano

<plan_file>`.codex/plans/[timestamp]-[plan-slug].md`</plan_file>

- **OBRIGATÓRIO ABSOLUTO**: No modo Plano, após o usuário aceitar um plano, **SEMPRE** escreva o plano aceito em um arquivo Markdown dentro de <plan_file>.
- **OBRIGATÓRIO**: Se o plano aceito for atualizado posteriormente, atualize ou adicione o respectivo arquivo Markdown em <plan_file>.

# DESIGN.md

- Toda a UI que você trabalhar, você sempre tem que seguir o ./DESIGN.md completamente
- Leia sempre o DESIGN.md antes de começar tanto planejamento quanto execução de tarefas de UI
