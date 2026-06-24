# Resumo das tarefas de implementação do Assistente de IA da NovaTech (RAG)

> PRD: `resolution/prd/prd-novatech-assistente.md`
> Techspec: `resolution/prd/techspec-novatech-assistente.md`
> Escopo: papel **Desenvolvedor** — Exercícios 1.1, 1.2 e 1.3 (PoC open-source).
> Componentes de produção (Azure AI Search/OpenAI, bot Teams/Bot Framework, RF-09/RF-11, RNF-01/02/03/04/08) estão fora desta lista (alvo PROD/fase 2).

## Tarefas

- [x] 1.0 Análise de viabilidade técnica e estratégia de chunking (Ex. 1.1)
- [x] 2.0 Fundação do pacote `novatech_rag/`: modelos de domínio, Protocols e configuração
- [x] 3.0 Ingestão: DocumentLoader + Chunker + EmbeddingProvider + VectorStore
- [x] 4.0 Retrieval: Retriever (top-K + threshold) + ConflictDetector
- [x] 5.0 Camada de prompt: system prompt versionado (v1→v2) + PromptAssembler (Ex. 1.2)
- [x] 6.0 Avaliação: RetrievalEvaluator (recall@N) + GuardrailSuite (LLM-as-judge) (Ex. 1.3)
- [x] 7.0 CLI (`ingest`/`query`/`eval`) + logging estruturado (JSON)

## Ordem e dependências

```
1.0 (análise, independente)
2.0 ──> 3.0 ──> 4.0 ──> 5.0 ──> 6.0
                         └──────> 7.0 (depende de 3.0, 4.0, 5.0)
```

- 2.0 é fundação compartilhada por 3.0–7.0.
- 6.0 (avaliação/guardrails) valida 3.0–5.0 e produz as evidências de homologação.
- 7.0 (CLI) orquestra ingestão/busca/avaliação; depende de 3.0, 4.0 e 5.0.

## Requisito transversal — evidência de uso de IA

Os exercícios de Dev (1.1/1.2/1.3) exigem como entregável a **evidência da interação com IA** (histórico/export do Claude; avaliação das respostas geradas), além do artefato final. Salvar em `evidencias/`:

- `evidencias/1.1-claude-historico.md` — iteração da análise de viabilidade (Tarefa 1.0).
- `evidencias/1.2-respostas-v1-v2.md` — respostas das 2 rodadas do system prompt (Tarefa 5.0).
- `evidencias/1.3-teste-5-perguntas.md` — chunks/scores vs gabarito + resposta do Claude avaliada (Tarefa 6.0).

## Origem dos dados

- Corpus (Anexo A): pasta `anexo-a-documentos-individuais/` na raiz do repositório (5 arquivos `.md`).
- Gabarito (Anexo B): `anexo-b-chunks-referencia-rag.md`.
