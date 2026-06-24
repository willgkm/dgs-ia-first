# System prompt — análise de versões (v1 → v2)

> Artefato de código versionado (RF-12). Documenta a evolução do system prompt, o
> mapeamento de partes estáticas vs dinâmicas e a estimativa de tokens de cada
> parte. As respostas das duas rodadas de teste no Claude e a análise crítica
> estão em `../../tasks/prd-novatech-assistente/evidencias/1.2-respostas-v1-v2.md`.

## Mapeamento estático vs dinâmico (RF-12)

O prompt enviado ao modelo tem uma parte **estática** (versionada, igual em toda
consulta) e uma parte **dinâmica** (montada por consulta pelo `PromptAssembler`).

| Parte | Natureza | Origem | Tokens (estimados) |
|-------|----------|--------|--------------------|
| System prompt (`system_prompt_v2.md`) | **Estática** | Artefato versionado | ~965 |
| Pergunta do atendente | Dinâmica | Entrada em runtime | ~10 (varia) |
| Bloco de trecho recuperado (cabeçalho de proveniência + texto) | Dinâmica | `Retriever` → `PromptAssembler` | ~64 por trecho |
| Alerta de divergência (G-07/G-08) | Dinâmica condicional | Injetado quando há `ConflictGroup` | ~69 por grupo |
| Instrução de abstenção (G-03) | Dinâmica condicional | Injetada quando `below_threshold` | ~49 |
| Histórico de conversa | Dinâmica | Gestão de sessão do bot (PROD) | fora do MVP |

> Estimativa por `estimate_prompt_tokens` (aproximação determinística do tokenizer;
> a produção injeta o tokenizer exato do modelo via `token_counter`).

**Orçamento por consulta.** Um prompt típico com 5 trechos e sem conflito ocupa
≈ 965 + 10 + 5×64 ≈ **1.295 tokens** — muito abaixo do default de 8.000 e do teto
de 128K do GPT-4o (RNF-06). O `PromptAssembler` garante o teto descartando os
trechos de menor score (`dropped_chunks`) quando o orçamento aperta (RF-04).

## v1 — baseline (`system_prompt_v1.md`)

Primeira redação, deliberadamente enxuta (~276 tokens). Cobre identidade, regras
genéricas de comportamento, formato de resposta e uso dos trechos. **Lacunas
conhecidas**, expostas pelo teste com as 3 perguntas do Ex. 1.2:

- Guardrails apenas genéricos: não tratava explicitamente carga perigosa (G-05)
  nem o tier inexistente "Platinum" (G-06) — abria espaço para inverter a exceção
  ou inventar SLA.
- Conflito de versões tratado como "mencione a divergência", sem exigir a
  apresentação de **ambas** as versões nem proibir a escolha arbitrária (G-07/G-08).
- Sem **ordem de prioridade entre fontes** (oficial vs FAQ não validado).
- Frase de abstenção não padronizada (G-03) e citação sem formato fixo (G-01).
- Permitia "responda em português" sem vetar jargão técnico ao atendente (G-04).

## v2 — versão revisada (`system_prompt_v2.md`)

Reescrita orientada pelos guardrails do PRD e pela análise das respostas v1.
Mudanças e motivação:

| # | Mudança | Guardrail | Motivação |
|---|---------|-----------|-----------|
| 1 | Guardrails numerados G-01..G-08 explícitos | G-01..G-08 | Rastreabilidade direta ao PRD; cada regra verificável. |
| 2 | Regra dedicada de **carga perigosa não devolvível** (POL-001 §3.2) | G-05 | v1 podia inverter a exceção — falha crítica de compliance. |
| 3 | Regra dedicada negando o tier **"Platinum"** | G-06 | v1 podia inventar SLA para tier inexistente. |
| 4 | Conflito exige **ambas** as versões + alerta, proíbe escolher vigente | G-07/G-08 | v1 só "mencionava" a divergência; risco de resposta de versão única. |
| 5 | Seção própria de **ordem de prioridade entre fontes** | G-02 | Documento oficial precede o FAQ não validado; conflito de versões não é resolvido pelo modelo. |
| 6 | Frase de ausência **exata** + escalada | G-03 | Padroniza a abstenção; habilita verificação automática. |
| 7 | Formato de citação fixo `Fonte: <documento>, seção <...>` | G-01 | Citação verificável em 100% das respostas factuais. |
| 8 | Veto explícito a jargão técnico de IA/TI | G-04 | Respostas acessíveis ao atendente. |

**Custo.** v2 cresceu de ~276 para ~965 tokens (parte estática). O acréscimo é
irrelevante diante do orçamento de 128K (RNF-06) e compra robustez nos guardrails
críticos (G-05/G-06/G-07), cuja meta de violação é 0% pré go-live.

## Seção de ordem de prioridade entre fontes (Ex. 1.2 / subtarefa 5.2)

Registrada como seção própria do system prompt v2 ("Ordem de prioridade entre
fontes"):

1. **Documento oficial > FAQ não validado** — quando a resposta vier só do FAQ, o
   assistente sinaliza que é orientação informal.
2. **Versões divergentes do mesmo documento não são resolvidas pelo modelo** —
   ambas são apresentadas com alerta; a vigência é confirmada pelo supervisor.
3. **Sem cobertura → abstenção** — em vez de preencher a lacuna com suposições.
