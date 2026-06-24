# Especificação técnica

> Funcionalidade: Assistente de IA da NovaTech (RAG para Atendimento)
> PRD de origem: `resolution/prd/prd-novatech-assistente.md`
> Escopo: papel **Desenvolvedor** — Exercícios 1.1 (viabilidade), 1.2 (system prompt) e 1.3 (pipeline RAG open-source)

## Resumo executivo

A solução é um pipeline RAG com dois alvos de implantação. O **MVP (PoC open-source)** é uma biblioteca/CLI Python que ingere os documentos da NovaTech, gera embeddings com `sentence-transformers/all-MiniLM-L6-v2`, indexa no **ChromaDB** local e, dada uma pergunta, recupera os chunks mais relevantes e monta o prompt final (system prompt estático + chunks dinâmicos + pergunta). A geração da resposta na PoC é manual (colar o prompt no Claude) ou via **Ollama** local — o pipeline programático termina na montagem do prompt, deixando um *seam* (`GenerationAdapter`) para a geração automatizada na produção.

A **arquitetura-alvo de produção** substitui os componentes locais por serviços gerenciados Azure já contratáveis com as licenças M365 E3 da NovaTech: **Azure AI Search** (vetorização integrada, *Document Layout skill* para chunking semântico, busca híbrida + *semantic ranker*) como retrieval, **Azure OpenAI (GPT-4o)** como gerador, e um bot **Bot Framework SDK** publicado no **Teams** via Microsoft 365 Agents Toolkit. As interfaces do MVP (`Chunker`, `EmbeddingProvider`, `VectorStore`, `Retriever`, `PromptAssembler`) são definidas como abstrações para que a migração PoC→produção troque implementações sem reescrever a orquestração. A decisão central de engenharia é tratar o RAG como sistema de dados: metadados de versão/fonte governam a desambiguação de documentos contraditórios e a abstenção quando não há resposta — não o modelo.

## Arquitetura do sistema

### Visão dos componentes

Pipeline em duas fases (ingestão offline; retrieval/geração em runtime). Componentes **novos** do MVP, agrupados por módulo Python:

- **`ingestion/`**
  - `DocumentLoader` — lê fontes por formato (`.md`/PDF/DOCX/HTML/XLSX), normaliza para texto + estrutura (títulos, seções, tabelas). No MVP processa os `.md` do Anexo A; loaders de PDF/DOCX/HTML/XLSX são plugáveis.
  - `Chunker` — divisão *section-aware* com teto de ~256 tokens e overlap ~10–15%; preserva linhas de tabela e passos numerados (não corta no meio).
  - `EmbeddingProvider` — `all-MiniLM-L6-v2` (384 dims) no MVP; abstração que na produção aponta para a vetorização do Azure AI Search.
  - `VectorStore` — `ChromaDB PersistentClient`; `upsert` idempotente por `chunk_id` determinístico; metadados de versão/fonte.
- **`retrieval/`**
  - `Retriever` — embeda a pergunta, busca top-K por similaridade com *threshold* mínimo; aceita filtro `where` por metadados.
  - `ConflictDetector` — agrupa resultados por `doc_id` e sinaliza presença de múltiplas versões (ex.: PROC-042 v1 + v2).
  - `Reranker` (opcional) — cross-encoder para reordenar candidatos e mitigar *lost in the middle*.
- **`prompt/`**
  - `PromptAssembler` — compõe system prompt estático + chunks ordenados (maior score nas extremidades) + pergunta, respeitando o orçamento de tokens; injeta alerta de conflito quando o `ConflictDetector` aponta divergência.
- **`eval/`**
  - `RetrievalEvaluator` — recall@N contra o mapa de cobertura do Anexo B.
  - `GuardrailSuite` — casos-armadilha (Platinum, carga perigosa, PROC-042) + LLM-as-judge.

**Fluxo de dados (runtime):** pergunta → `Retriever` (embed + busca + threshold) → `ConflictDetector`/`Reranker` → `PromptAssembler` → [PoC: prompt emitido p/ Claude/Ollama] / [produção: `GenerationAdapter` → Azure OpenAI → resposta com citações no Teams].

## Design de implementação

### Principais interfaces

Interfaces como `Protocol`s Python (a stack é Python; o exemplo Go do template é apenas formato). Cada uma isola um ponto de troca PoC↔produção.

```python
from typing import Protocol, Sequence

class Chunker(Protocol):
    def split(self, document: "LoadedDocument") -> list["Chunk"]: ...

class EmbeddingProvider(Protocol):
    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...  # 384 dims (MVP)

class VectorStore(Protocol):
    def upsert(self, chunks: Sequence["Chunk"]) -> None: ...          # idempotente por chunk_id
    def query(self, embedding: list[float], top_k: int,
              where: dict | None = None) -> list["RetrievalResult"]: ...

class Retriever(Protocol):
    def retrieve(self, question: str, top_k: int,
                 min_score: float) -> "RetrievalBundle": ...

class PromptAssembler(Protocol):
    def assemble(self, question: str, bundle: "RetrievalBundle",
                 token_budget: int) -> "AssembledPrompt": ...
```

`GenerationAdapter` (seam, não implementado no MVP): `def generate(self, prompt: AssembledPrompt) -> Answer`.

### Modelos de dados

Entidades de domínio (dataclasses); o esquema do ChromaDB é `documents` + `embeddings` + `metadatas` + `ids`.

- **`ChunkMetadata`**: `doc_id`, `doc_title`, `version`, `version_date`, `section`, `source` (`sharepoint|confluence|rede|faq`), `is_official` (bool — FAQ = `false`), `ingested_at`.
- **`Chunk`**: `chunk_id` (hash determinístico de `doc_id|section|ordinal`), `text`, `metadata: ChunkMetadata`.
- **`RetrievalResult`**: `chunk`, `score` (similaridade), `rank`.
- **`RetrievalBundle`**: `results: list[RetrievalResult]`, `conflicts: list[ConflictGroup]`, `below_threshold: bool`.
- **`ConflictGroup`**: `doc_id`, `versions: list[(version, version_date, chunk_id)]`.
- **`AssembledPrompt`**: `system`, `context_blocks`, `question`, `estimated_tokens`, `dropped_chunks`.

Metadado crítico: `version`/`version_date` e `is_official` são a base para G-07 (divergência) e para priorizar documento oficial sobre o FAQ. `chunk_id` determinístico garante que reindexar substitua a versão anterior (RF-10) sem duplicar.

### Endpoints da API

- **MVP**: sem HTTP — biblioteca + CLI (`ingest`, `query`, `eval`). Comandos: `python -m novatech_rag ingest <dir>`, `... query "<pergunta>"`, `... eval --gold anexo-b`.
- **Produção (Bot Framework no Teams)**: `POST /api/messages` — endpoint padrão do Bot Framework que recebe *Activities* do Teams, dispara retrieval+geração e devolve a resposta com *citations*. Autenticação via Entra ID (App Registration). Demais integrações de retrieval/geração são chamadas server-to-server ao Azure AI Search e Azure OpenAI, não expostas publicamente.

## Pontos de integração

- **sentence-transformers / Hugging Face** (MVP): download do modelo `all-MiniLM-L6-v2` no primeiro uso; cachear localmente; sem rede em runtime após o cache. Tratamento de erro: falha de download → abortar ingestão com mensagem clara (não degradar silenciosamente).
- **ChromaDB** (MVP): persistência local em disco (`PersistentClient`); `upsert` idempotente. Não projetado para 45 usuários concorrentes — restrito à PoC.
- **Ollama / Claude chat** (MVP, geração): geração manual ou via Ollama HTTP local; fora do caminho automatizado.
- **Azure AI Search** (produção): índice vetorial + híbrido + *semantic ranker*; ingestão via *indexer* com *Document Layout skill*. Timeout e *retry* com backoff nas chamadas; filtros por metadado (`is_official`, `version_date`) no lado do serviço.
- **Azure OpenAI (GPT-4o)** (produção): geração com *grounding* nos chunks; orçamento de contexto ≤128K. Erros → fallback para mensagem de indisponibilidade, nunca resposta sem fontes.
- **Microsoft Graph / SharePoint / Confluence** (produção, fase 2): conectores de ingestão automatizada. MVP usa export manual.
- **Teams / Bot Framework + Entra ID** (produção): canal e autenticação; idempotência por `activity.id`.

## Abordagem de testes

### Testes unitários

- `Chunker`: garante teto de ~256 tokens, overlap aplicado, **tabelas não cortadas** (PROC-042 com 15+ colunas) e passos numerados íntegros.
- `VectorStore.upsert`: idempotência — reindexar o mesmo `chunk_id` substitui, não duplica (RF-10).
- `ConflictDetector`: dado resultados de PROC-042 v1 + v2, retorna `ConflictGroup` com as duas versões.
- `PromptAssembler`: respeita `token_budget` (descarta menor score), posiciona maiores scores nas extremidades, injeta alerta de conflito. Sem mocks de LLM (o MVP não chama LLM); mocks apenas para `EmbeddingProvider` em testes determinísticos.

### Testes de integração

- **Ingestão→retrieval ponta a ponta** sobre os 5 documentos do Anexo A em ChromaDB efêmero.
- **Recall@N contra o Anexo B**: para cada pergunta do mapa de cobertura, verificar se os chunks-gabarito aparecem no top-N (meta ≥80%). Dados de teste = Anexo A (corpus) + Anexo B (gabarito).
- **Suite de guardrails**: Platinum (tier inexistente → abstenção), carga perigosa (POL-001 proíbe devolução), PROC-042 (exige ambas as versões + alerta), pergunta fora da base (abstém e sugere escalonar). Avaliação de geração por **LLM-as-judge** com rubrica (precisão, citação, aderência a guardrail), reconhecendo natureza não-determinística (graus, não pass/fail binário).

### Testes E2E

- **MVP: N/A** — não há frontend web; o "E2E" funcional é o teste de integração ingestão→prompt + julgamento da resposta.
- **Produção: Playwright** reservado para o canal Teams (UI conversacional) quando o bot estiver publicado — fluxo pergunta→resposta com citação na interface do Teams.

## Sequenciamento do desenvolvimento

### Ordem de construção

1. **Ingestão + Chunker + EmbeddingProvider + VectorStore** — base de tudo; permite indexar o Anexo A e validar chunking de tabelas primeiro (maior risco técnico).
2. **Retriever + threshold + ConflictDetector** — depende de (1); habilita abstenção e detecção de divergência.
3. **PromptAssembler** — depende de (2); fecha o pipeline da PoC (entrega do Ex. 1.3) e materializa o system prompt estático/dinâmico do Ex. 1.2.
4. **`eval/` (recall@N + GuardrailSuite + LLM-judge)** — valida (1)–(3) contra Anexo B; produz as evidências exigidas pelo exercício.
5. **Reranker (opcional)** — só se o recall@N indicar *lost in the middle*.
6. **Migração de produção** — trocar implementações por Azure AI Search/OpenAI e publicar o bot Teams (Microsoft 365 Agents Toolkit), reusando as mesmas interfaces.

### Dependências técnicas

- Python 3.10+, `chromadb`, `sentence-transformers`; opcional `ollama`. Download inicial do modelo (rede).
- Documentos do Anexo A como arquivos individuais; mapa do Anexo B como gabarito.
- Produção: provisionamento de Azure AI Search + Azure OpenAI, App Registration no Entra ID e permissões de bot no Teams pela TI da NovaTech (bloqueadores de prazo).

## Monitoramento e observabilidade

- **MVP**: logging estruturado (JSON) — por ingestão: nº de docs, chunks gerados, chunks descartados por tamanho; por query: scores de similaridade, `below_threshold`, conflitos detectados, tokens do prompt, latência. Relatório de `eval` (recall@N, taxa de abstenção correta) versionado.
- **Produção**: métricas em formato Prometheus/`/metrics` no serviço do bot — `rag_query_latency_seconds`, `rag_retrieval_recall`, `rag_conflict_detected_total`, `rag_not_found_total`, `rag_prompt_tokens`, `rag_guardrail_violation_total`. Logs em Azure Monitor / Application Insights; dashboards no Grafana (latência P95, taxa de abstenção, violações de guardrail, frescor de ingestão vs SLA de 24h do RNF-05). Alertas em violação de guardrail crítico (G-05/G-06/G-07) e em recall abaixo do limiar.

## Considerações técnicas

### Principais decisões

- **ChromaDB (PoC) vs Azure AI Search (produção)** — *build vs buy*: ChromaDB valida o conceito sem custo (Ex. 1.3); produção usa Azure AI Search pela busca híbrida + *semantic ranker* + vetorização integrada, aproveitando o ecossistema M365. Interfaces comuns evitam *lock-in* prematuro.
- **Teto de chunk ~256 tokens** — o `all-MiniLM-L6-v2` trunca a entrada em 256 *word pieces*; chunks maiores seriam silenciosamente cortados, degradando o embedding. Chunking *section-aware* com teto de 256 + overlap evita isso; produção pode usar chunks maiores com o *Document Layout skill* + modelos de maior contexto.
- **Desambiguação por metadados, não por modelo** — conflito (G-07) e priorização oficial vs FAQ resolvidos por `ConflictDetector` + filtro `where`/`is_official` + alerta no prompt; o LLM nunca escolhe a versão "vigente" sozinho. Metadata filtering é a maior alavanca de qualidade de retrieval (literatura: MRR 0,12→0,68).
- **Abstenção por threshold** — sem chunk acima do `min_score`, o pipeline marca `below_threshold` e o prompt instrui resposta de "não encontrado" + escalonamento (G-03), em vez de gerar com conhecimento geral.
- **Prompt estático vs dinâmico + ordenação nas extremidades** — separa system prompt/guardrails (estático, versionado) de chunks/pergunta (dinâmico) e posiciona maior score nas bordas para mitigar *lost in the middle* (Ex. 1.2).
- **Geração fora do pipeline na PoC** — `GenerationAdapter` como *seam*; mantém a PoC barata e adia a decisão de provedor para a produção.

### Riscos conhecidos

- **Qualidade do `all-MiniLM-L6-v2` em português** — é primariamente anglófono; mitigar avaliando `paraphrase-multilingual-MiniLM-L12-v2`/`bge-m3` no recall@N do Anexo B antes de fixar o modelo.
- **Extração de tabelas e PDFs escaneados** — tabelas de frete e OCR (~15% da base) são o maior risco de extração; OCR fora do MVP (validar com `.md` do Anexo A primeiro).
- **ChromaDB sob concorrência** — inadequado para 45 usuários simultâneos; restrito à PoC, produção em Azure AI Search.
- **Não-determinismo da avaliação de geração** — LLM-as-judge exige rubrica e amostragem; tratar como grau de qualidade, não binário.
- **Frescor de ingestão (RNF-05)** — sem webhook no MVP, atualização depende de execução manual; risco operacional documentado no PRD.

### Conformidade com rules

- **Não existe a pasta `.claude/rules`** neste repositório (verificado via Glob/Context7 CLI). Não há *rules* a aplicar. Caso seja criada futuramente, esta seção deve ser revisada.

### Conformidade com skills

Skills presentes em `resolution/.claude/skills` e `resolution/.agents/skills`:
- **`code-standards-en`** — aplicável: identificadores, símbolos e constantes em **inglês** (`Chunker`, `EmbeddingProvider`, `MAX_CHUNK_TOKENS`), `PascalCase` para classes, verbos em funções (`split`, `embed`, `retrieve`), CQS (`query` puro vs `upsert` mutador), *early return*, métodos <50 linhas. **Desvio consciente**: conteúdo de domínio e prompts ao usuário permanecem em **português** (política de produto) — apenas identificadores em inglês.
- **`repo-folder-structure`** — aplicável parcialmente: a skill descreve layout React/Node; adaptado para pacote Python com camadas equivalentes (`ingestion/`→data, `retrieval/`/`prompt/`→services, CLI→controllers), respeitando a direção de dependência.
- **`context7`** — usada nesta especificação para validar ChromaDB (`PersistentClient`, `upsert`, filtro `where`).
- **`express-rest-http`** — aplicável **apenas** se o serviço do bot de produção for Node/Express; N/A para o MVP Python.
- **`skill-best-practices`** — N/A (não estamos autorando skills).

### Arquivos relevantes e dependentes

- `resolution/prd/prd-novatech-assistente.md` — PRD de origem (requisitos, guardrails, métricas).
- `anexo-a-documentacao-simulada-novatech.md` e os 5 fontes: `POL-001-politica-devolucao.md`, `PROC-042-frete-especial-v1.md`, `PROC-042-v2-frete-especial-revisado.md`, `SLA-2024-tabela-sla-clientes.md`, `FAQ-atendimento.md` — corpus de ingestão.
- `anexo-b-chunks-referencia-rag.md` — gabarito de recall@N.
- `exercicio-fase-1-entendimento.md` — escopo dos Exercícios 1.1/1.2/1.3 do Desenvolvedor.
- `resolution/.claude/skills/*`, `resolution/.agents/skills/context7/SKILL.md` — skills de conformidade.
- (a criar) pacote `novatech_rag/` com módulos `ingestion/`, `retrieval/`, `prompt/`, `eval/`.

## Matriz de rastreabilidade (PRD → techspec)

> Seção complementar. O vínculo requisito→implementação também está descrito ao longo das seções acima (Visão dos componentes, Principais decisões, Abordagem de testes); esta tabela o consolida de forma auditável. `MVP` = PoC open-source; `PROD` = arquitetura-alvo de produção.

### Requisitos funcionais

| ID PRD | Requisito (resumo) | Componente / Interface | Alvo | Verificação |
|--------|--------------------|------------------------|------|-------------|
| RF-01 | Ingerir PDF/DOCX/HTML/XLSX e indexar com metadados | `DocumentLoader`, `EmbeddingProvider`, `VectorStore`, `ChunkMetadata` | MVP | Teste de integração ingestão→retrieval |
| RF-02 | Chunking que preserva unidades semânticas (não corta tabelas) | `Chunker` (section-aware, teto ~256, overlap) | MVP | Unit `Chunker`: tabelas/passos íntegros |
| RF-03 | Recuperar top-N com score + threshold | `Retriever` | MVP | Recall@N sobre Anexo B (≥80%) |
| RF-04 | Montar prompt ≤128K, descartar menor score | `PromptAssembler` (`token_budget`, `dropped_chunks`) | MVP | Unit `PromptAssembler`: respeita orçamento |
| RF-05 | Citar fonte obrigatória | `PromptAssembler` (`context_blocks`) + system prompt | MVP | `GuardrailSuite` (G-01) |
| RF-06 | Não afirmar dados ausentes dos chunks | threshold/abstenção + system prompt | MVP | `GuardrailSuite` (perguntas-armadilha) |
| RF-07 | Ausência → declarar + escalonar | `Retriever.below_threshold` + `PromptAssembler` | MVP | `GuardrailSuite` (10 perguntas sem resposta) |
| RF-08 | Versões conflitantes → ambas + alerta | `ConflictDetector` + `PromptAssembler` | MVP | Integração PROC-042 v1+v2 |
| RF-09 | Disponível no Microsoft Teams | Bot Framework SDK, `POST /api/messages` | PROD | E2E Playwright no canal Teams |
| RF-10 | Atualização incremental (substituir versão) | `VectorStore.upsert` idempotente + `chunk_id` determinístico | MVP | Unit `upsert`: reindexar não duplica |
| RF-11 | Reiniciar contexto após N turnos (anti context rot) | Gestão de sessão do bot | PROD | Teste comparativo sessão longa |
| RF-12 | System prompt versionado, estático vs dinâmico | módulo `prompt/`, `AssembledPrompt` | MVP | Inspeção do repositório (v1/v2) |

### Requisitos não-funcionais

| ID PRD | Requisito (resumo) | Componente / Mecanismo | Alvo | Verificação |
|--------|--------------------|------------------------|------|-------------|
| RNF-01 | Resposta ≤10s (P95) | `rag_query_latency_seconds` | PROD | Dashboard Grafana / teste de carga |
| RNF-02 | ≥45 consultas simultâneas | Azure AI Search + Azure OpenAI | PROD | Teste de concorrência (ChromaDB N/A) |
| RNF-03 | ≥192 consultas/dia sem degradação | Serviço de produção | PROD | Teste de volume |
| RNF-04 | Disponibilidade ≥99% (comercial) | Azure + Teams | PROD | Monitoramento de uptime |
| RNF-05 | Documento atualizado ≤24h | Pipeline de ingestão + métrica de frescor | MVP/PROD | Logging de ingestão; alerta de frescor |
| RNF-06 | Orçamento de contexto ≤128K | `PromptAssembler.token_budget` | MVP | Unit `PromptAssembler` |
| RNF-07 | Formatos PDF/DOCX/HTML/XLSX | `DocumentLoader` (loaders plugáveis) | MVP | Teste por formato |
| RNF-08 | Isolamento de dados no ambiente autorizado | Entra ID / Azure | PROD | Revisão de segurança |
| RNF-09 | Stack do PoC gratuita/open-source | ChromaDB + sentence-transformers | MVP | Build sem dependência paga |

### Guardrails

| ID PRD | Guardrail (resumo) | Componente / Mecanismo | Alvo | Verificação |
|--------|--------------------|------------------------|------|-------------|
| G-01 | Citar documento/seção em toda resposta factual | `PromptAssembler` + system prompt | MVP | `GuardrailSuite`: presença de citação |
| G-02 | Não inventar prazos/valores fora dos chunks | threshold + system prompt | MVP | `GuardrailSuite`: perguntas-armadilha |
| G-03 | Sem resposta → declarar + escalonar | `Retriever.below_threshold` + `PromptAssembler` | MVP | `GuardrailSuite`: ≥9/10 escalonam |
| G-04 | Português formal, sem jargão técnico | system prompt | MVP | `GuardrailSuite` / LLM-judge |
| G-05 | Carga perigosa NÃO pode ser devolvida | grounding + `GuardrailSuite` | MVP | Caso POL-001 (exceção) |
| G-06 | Tier "Platinum" não existe | threshold/grounding + `GuardrailSuite` | MVP | Caso SLA-2024 (Gold/Silver/Standard) |
| G-07 | Conflito → ambas as versões + alerta | `ConflictDetector` + `PromptAssembler` | MVP | Caso PROC-042 v1+v2 |
| G-08 | Não encerrar com certeza sem alerta de divergência | `ConflictDetector` + `PromptAssembler` | MVP | Caso PROC-042: ausência de alerta = falha |
