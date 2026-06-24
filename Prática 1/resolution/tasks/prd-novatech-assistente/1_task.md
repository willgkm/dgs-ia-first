# Tarefa 1.0: Análise de viabilidade técnica e estratégia de chunking

## Visão geral

Produzir o documento de análise de viabilidade técnica (Ex. 1.1 / UC-04): riscos por tipo de fonte, estimativa fundamentada do tamanho da base em tokens, cálculo do orçamento de contexto por query e definição justificada da estratégia de chunking. Entrega de discovery — **não há código de produto nesta tarefa**, mas há critérios verificáveis.

<skills>
### Conformidade com skills

- `code-standards-en` — aplicável apenas a identificadores/constantes que o documento eventualmente proponha (ex.: `MAX_CHUNK_TOKENS`); conteúdo do documento permanece em português (política de produto).
- `repo-folder-structure`, `express-rest-http`, `skill-best-practices`, `context7` — **N/A** nesta tarefa (entrega documental).
</skills>

<requirements>
- Analisar cada tipo de fonte (PDF com tabelas complexas, PDF escaneado, wiki com links internos, planilhas com fórmulas interdependentes) e listar os desafios específicos para o pipeline RAG.
- Estimar o tamanho total da base em tokens com a fórmula do PRD (~12M tokens) e mostrar o cálculo.
- Calcular o orçamento de contexto por query: 128K − ~2K (system prompt + instruções) ≈ 126K, e o nº teórico de chunks de ~256/500 tokens, registrando a limitação prática por *lost in the middle*.
- Justificar a estratégia de chunking (section-aware, teto ~256 tokens, overlap 10–15%) pelo tipo de pergunta esperada e pelo efeito *lost in the middle*.
- Documentar o risco do `all-MiniLM-L6-v2` em português e a alternativa de avaliação (`paraphrase-multilingual`/`bge-m3`).
- Submeter a análise a revisão crítica (Claude) e incorporar o feedback.
- **Capturar a evidência de uso de IA (entregável obrigatório do Ex. 1.1):** salvar o histórico/export da conversa com o Claude (prompt inicial, feedback recebido e mudanças incorporadas) como artefato versionado.
</requirements>

## Subtarefas

- [x] 1.1 Mapear riscos por tipo de documento (PDF/tabela, PDF escaneado/OCR fora do MVP, HTML/wiki, XLSX).
- [x] 1.2 Calcular e documentar a estimativa de tokens da base (mostrar a conta).
- [x] 1.3 Calcular o orçamento de contexto por query e o limite prático de chunks.
- [x] 1.4 Definir e justificar a estratégia de chunking (referência: techspec "Principais decisões").
- [x] 1.5 Registrar risco de idioma do modelo de embeddings e plano de avaliação.
- [x] 1.6 Submeter ao Claude, registrar feedback e revisar o documento.
- [x] 1.7 Exportar/salvar o histórico da conversa com o Claude como evidência de uso de IA.

## Detalhes de implementação

Seguir as seções **"Resumo executivo"**, **"Casos de uso → UC-04"**, **"Requisitos não-funcionais (RNF-06/07/09)"** do PRD e **"Considerações técnicas → Principais decisões / Riscos conhecidos"** do techspec. Não reproduzir cálculos aqui — referenciar `techspec-novatech-assistente.md`.

## Critérios de sucesso

- Documento entregue ao Tech Lead com: tabela de riscos por tipo de fonte, estimativa de tokens com cálculo visível, orçamento de contexto e estratégia de chunking justificada.
- Estimativa de tokens consistente com a ordem de grandeza do PRD (~12M).
- Registro explícito do feedback do Claude e das mudanças incorporadas.

## Testes da tarefa

- [ ] Testes unitários — N/A (entrega documental). Verificação por *checklist* dos `<requirements>`.
- [ ] Testes de integração — N/A.
- [ ] Testes E2E — N/A.
- [x] Revisão: validar que cada item dos requisitos está coberto no documento (revisão por par/Tech Lead).

## Arquivos relevantes

- `resolution/tasks/prd-novatech-assistente/analise-viabilidade-1.1.md` (a criar) — documento de saída.
- `resolution/tasks/prd-novatech-assistente/evidencias/1.1-claude-historico.md` (a criar) — evidência da iteração com o Claude.
- `resolution/prd/prd-novatech-assistente.md`, `resolution/prd/techspec-novatech-assistente.md` — fontes.
- `exercicio-fase-1-entendimento.md` — escopo do Ex. 1.1.
