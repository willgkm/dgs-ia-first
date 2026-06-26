# Estratégia de Skills — NovaTech Assistant (Dev 2.3)

> Skills são artefatos `.md` que encapsulam **como gerar** tipos específicos de output de
> forma consistente entre humanos e agentes (Copilot, Claude Code). Hierarquia:
> **Foundation** (convenções globais) → **Domain** (padrões por camada) → **Artifact**
> (receitas de geração). Cada nível **lê os anteriores**.

## Encadeamento de dependência

```
Foundation (substrato comum a TODO código)
  typescript-conventions   ← base de todas
  error-handling           (assume typescript-conventions)
  project-structure        (assume typescript-conventions)
        │
        ▼
Domain (padrões por camada — lê Foundation)
  azure-functions-endpoint · azure-ai-search-integration
  react-components · testing-patterns
        │
        ▼
Artifact (receitas completas — lê Domain + Foundation)
  create-rag-endpoint · create-integration-test · create-react-card
```

**Regra de leitura:** ao gerar um artefato, o agente lê de cima para baixo — primeiro a(s)
Foundation aplicável(is), depois a Domain da camada, e por fim a receita Artifact. Conflito
de regra → vence o nível mais baixo (Foundation é fonte da verdade de estilo).

---

## Como cada artefato repetido do projeto vira skill

| Artefato repetido (enunciado 2.3) | Skill(s) que o governam |
|-----------------------------------|--------------------------|
| Endpoints Azure Functions com padrão RAG | `azure-functions-endpoint` + `create-rag-endpoint` |
| Testes de integração de endpoints | `testing-patterns` + `create-integration-test` |
| Componentes React (cards, forms) do painel | `react-components` + `create-react-card` |
| Documentação técnica (ADRs, README de módulo) | `create-adr-and-readme` *(proposta — ver abaixo)* |
| Specs de produto (template SDD) | `create-sdd-spec` *(proposta — criada pelo Product Specialist)* |

> As duas últimas linhas **não** têm stub no scaffold atual. Proponho adicioná-las para a
> árvore cobrir 100% dos artefatos repetidos sem deixar skills "órfãs" — `create-adr-and-readme`
> (Artifact, criada pelo Dev/TL) e `create-sdd-spec` (Artifact, **criada pelo Product
> Specialist**, demonstrando que skills não são só de dev).

---

## Mapeamento por skill (nome · frase-ativação · cria · consome · frequência)

### Foundation
| Skill | Frase-ativação | Cria | Consome | Freq. |
|-------|----------------|------|---------|-------|
| **typescript-conventions** | "vou gerar/editar qualquer `.ts`" | Tech Lead | todos os devs + Copilot/Claude Code | **altíssima** (toda geração de código) |
| **error-handling** | "tratar erros/retry/logging em service ou handler" | Tech Lead (c/ Dev Sênior) | devs backend + Copilot | alta |
| **project-structure** | "criar arquivo/módulo novo e decidir onde mora" | Tech Lead | todos os devs + Copilot | média-alta |

### Domain
| Skill | Frase-ativação | Cria | Consome | Freq. |
|-------|----------------|------|---------|-------|
| **azure-functions-endpoint** | "criar/alterar um HTTP endpoint Azure Functions v4" | Tech Lead / Dev Sênior | devs backend + Copilot | alta (vários endpoints) |
| **azure-ai-search-integration** | "consultar ou indexar no Azure AI Search" | Dev Sênior | devs backend + Copilot | média |
| **react-components** | "criar um componente do painel web" | Dev frontend (apoio Product Specialist / Claude Design) | devs frontend + Copilot | média |
| **testing-patterns** | "escrever teste (Vitest + msw)" | QA (c/ Dev Sênior) | devs + QA + Copilot | alta |

### Artifact
| Skill | Frase-ativação | Cria | Consome | Freq. |
|-------|----------------|------|---------|-------|
| **create-rag-endpoint** | "gerar um endpoint RAG completo do zero" | Dev Sênior (c/ Copilot) | devs + Copilot | média (recorrente) |
| **create-integration-test** | "gerar teste de integração de um endpoint" | QA + Dev (c/ Copilot) | devs + QA + Copilot | alta |
| **create-react-card** | "gerar card/formulário React do painel" | Dev frontend (c/ Copilot) | devs frontend + Copilot | média |
| *create-adr-and-readme* (proposta) | "documentar uma decisão (ADR) ou README de módulo" | Dev / Tech Lead | devs + Copilot | média |
| *create-sdd-spec* (proposta) | "escrever requirements/plan/tasks no formato SDD" | **Product Specialist** (c/ Claude) | PS / TL / devs | média |

---

## Estado de implementação
| Skill | Status |
|-------|--------|
| `foundation/typescript-conventions.md` | ✅ **escrita** (skill base — Ex. 2.3) |
| Demais 9 stubs | ⬜ vazias (a preencher em iterações seguintes / podem ser geradas em paralelo) |
| 2 skills propostas | 🆕 a criar (cobrir ADR/README e specs SDD) |

## Critérios de "skill madura" (geral)
1. Um artefato gerado com a skill no contexto **compila/passa lint** sem ajuste manual.
2. A skill foi **testada com o Copilot** (gerou output aderente em ≥3 rodadas).
3. Tem exemplos DO/DON'T com **código real** do projeto (não abstrações).
4. Anti-padrões refletem erros que o Copilot **de fato** comete sem a guidance.
