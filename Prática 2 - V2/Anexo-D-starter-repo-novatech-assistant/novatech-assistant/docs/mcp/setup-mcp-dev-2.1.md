# Configuração e uso de MCP servers — NovaTech Assistant

> **Exercício 2.1 (Desenvolvedor).** Configuração, execução real e análise de risco
> dos MCP servers locais que dão aos agentes de IA (Claude / Copilot) acesso ao
> repositório, à documentação da NovaTech e ao corpus de "recuperação" (RAG).
> **Tudo local e gratuito** — nenhum serviço pago ou externo (sem Azure, Confluence,
> GitHub remoto). Substituímos esses serviços por *reference servers* do protocolo MCP.

---

## 1. O que é MCP (resumo operacional)

MCP (Model Context Protocol) padroniza como modelos de IA se conectam a ferramentas
externas. Um server expõe três primitivas:

- **Tools** — ações que o agente pode executar (ex.: `read_text_file`, `git_log`, `write_file`).
- **Resources** — dados read-only que o agente pode listar/ler.
- **Prompts** — templates de prompt reutilizáveis.

Servers rodam **localmente** via `npx` (Node) ou `uvx` (Python) e falam JSON-RPC 2.0
sobre stdio — não precisam ser serviços na nuvem.

---

## 2. Mapeamento: necessidade do projeto → server

| # | Necessidade do projeto | Server escolhido | Expõe (primitivas) | Quem consome | Escopo recebido | Acesso |
|---|------------------------|------------------|--------------------|--------------|-----------------|--------|
| 1 | Ler/editar **código, specs, skills, testes, prompts, ADRs** | `filesystem-workspace` | Tools (read/list/**write/edit**) | Claude Code, Copilot (devs, TL) | `./src ./specs ./skills ./tests ./prompts ./docs/adr ./docs/runbooks` | **leitura+escrita** |
| 2 | Ler **documentação de negócio** (era Confluence) | `filesystem-sources` | Tools (read/list) | todos os agentes | `./docs/novatech` | **read-only** (ACL de SO) |
| 3 | "Recuperar" **chunks** do corpus (era Azure AI Search) | `filesystem-sources` | Tools (read/list) | agentes que simulam RAG | `./data/retrieval-corpus` | **read-only** (ACL de SO) |
| 4 | **Histórico, diff e branches** do repo (era GitHub) | `git` | Tools (`git_log`, `git_diff`, `git_branch`, `git_status`, `git_show`, …) | devs, TL | repositório local (`.`) | leitura (commit/reset desabilitados por política — ver §5) |
| 5 | **Memória persistente** de decisões e linguagem ubíqua | `memory` | Tools (grafo de conhecimento) | todos os agentes | `./.mcp/memory.json` | leitura+escrita (grafo local) |
| 6 | Aprender as **primitivas de MCP** | `everything` | Tools + Resources + Prompts (exemplos) | devs (aprendizado) | — | — |

> **Decisão de design:** o `filesystem` foi dividido em **duas instâncias** porque o
> *reference server* `@modelcontextprotocol/server-filesystem` (v2026.1.14) **não tem
> modo read-only** — ele sempre registra as tools `write_file`, `edit_file`,
> `create_directory` e `move_file` (todas com `destructiveHint: true`). Separar as fontes
> de negócio numa instância própria permite (a) dar a elas o **menor escopo possível** e
> (b) impor read-only na **camada de SO** (ACL), independente do server. Ver §4 e §5.

---

## 3. Configuração final (`.mcp/mcp.json`)

```json
{
  "mcpServers": {
    "filesystem-workspace": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem",
               "./src", "./specs", "./skills", "./tests", "./prompts",
               "./docs/adr", "./docs/runbooks"]
    },
    "filesystem-sources": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem",
               "./docs/novatech", "./data/retrieval-corpus"]
    },
    "git": {
      "command": "uvx",
      "args": ["mcp-server-git", "--repository", "."]
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"],
      "env": { "MEMORY_FILE_PATH": "./.mcp/memory.json" }
    },
    "everything": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-everything"]
    }
  }
}
```

### Pré-requisitos verificados neste ambiente
- Node `v22.19.0` + npm `10.9.3` (fornece `npx`).
- Python `3.12.10`; `uv`/`uvx 0.11.24` instalado via `pip install --user uv` (fornece `uvx`
  para o `mcp-server-git`). Garanta que `…\Python312\Scripts` esteja no `PATH`.
- Git `2.51.0`.

---

## 4. Least privilege — concreto e justificado

O princípio do menor privilégio é aplicado em **duas camadas**:

### Camada 1 — Escopo (no próprio server)
O filesystem server só enxerga os diretórios passados como argumento; **nada mais do disco
é alcançável**. Em particular, **não montamos a raiz do repositório**, o que mantém fora de
alcance:

- `.env` (segredos), `node_modules/`, `.git/` interno;
- `infra/parameters/*.bicepparam` (podem conter strings de conexão);
- `AGENTS.md`, `package.json`, `tsconfig.json` (arquivos de raiz — editados por humanos/TL,
  não por geração em massa).

Cada escopo é o **mínimo suficiente** para a função:
- **workspace (rw):** exatamente as pastas onde o agente legitimamente *gera* artefatos —
  código (`src`), specs, skills, testes, prompts e ADRs/runbooks. Nada além.
- **sources (ro):** apenas as duas pastas de leitura (`docs/novatech`, `data/retrieval-corpus`).
  Não precisam de escrita — são a fonte da verdade, consumida, nunca alterada pelo agente.

> **Evidência (f):** uma tentativa de ler `../../../../.env` pela instância `sources` foi
> rejeitada: `Access denied - path outside allowed directories`.

### Camada 2 — Read-only (no SO)
Como o server não tem flag de read-only, as duas pastas-fonte receberam **deny-write via ACL
do Windows** para o usuário que roda o agente:

```powershell
icacls "docs\novatech"          /deny "DB1\melo.willian:(OI)(CI)(WD,AD)"
icacls "data\retrieval-corpus"  /deny "DB1\melo.willian:(OI)(CI)(WD,AD)"
# Reverter, se necessário:
# icacls "docs\novatech"         /remove:d "DB1\melo.willian"
# icacls "data\retrieval-corpus" /remove:d "DB1\melo.willian"
```

Assim, mesmo que um agente (ou um prompt malicioso) invoque `write_file` sobre uma fonte,
o **SO recusa** a operação — a leitura continua funcionando.

> **Evidência (e):** `write_file` em `docs/novatech/_write_test.md` retornou
> `EPERM: operation not permitted` e o arquivo **não** foi criado. Em contraste, `write_file`
> em `specs/` (instância workspace) retornou `Successfully wrote…` e o arquivo foi confirmado
> em disco. Read-only das fontes está **efetivamente** imposto.

---

## 5. Evidência de execução real

Servers subidos localmente e exercitados via cliente JSON-RPC stdio (handshake `initialize`
→ `notifications/initialized` → `tools/call`). Saídas reais abaixo (acentos podem aparecer
truncados no console; os arquivos em disco são UTF-8).

### (a) Escopo do server `filesystem-sources` — `list_allowed_directories`
```
Allowed directories:
…\novatech-assistant\docs\novatech
…\novatech-assistant\data\retrieval-corpus
```

### (b) Listar a documentação de negócio — `list_directory ./docs/novatech`
```
[FILE] FAQ-atendimento.md
[FILE] POL-001-politica-devolucao.md
[FILE] PROC-042-frete-especial-v1.md
[FILE] PROC-042-v2-frete-especial-revisado.md
[FILE] README.md
[FILE] SLA-2024-tabela-sla-clientes.md
```

### (c) Ler um documento — `read_text_file ./docs/novatech/POL-001-politica-devolucao.md`
```
# POL-001 — Política de Devolução de Mercadorias
Versão: 3.1  |  Última atualização: 15/01/2024
…
### 3.2. Exceções ao prazo geral
As seguintes categorias de carga NÃO são elegíveis para devolução pelo processo padrão:
- Cargas perigosas classificadas nas classes 1 a 6 da ANTT (Resolução ANTT nº 5.947/2021)…
```

### (d) Recuperar chunk relevante — gabarito do Anexo B
Pergunta de domínio: **"Posso devolver carga perigosa?"**
Mapa de cobertura (Anexo B) → chunk que DEVE ser recuperado: **POL-001-B**.
Lendo `./data/retrieval-corpus/chunks-novatech.md` via MCP, o chunk esperado está presente:
```
**Chunk POL-001-A** — Seção 3.1: Prazo geral
> O cliente pode solicitar a devolução de mercadorias em até 7 (sete) dias úteis…
**Chunk POL-001-B** — Seção 3.2: Exceções
> As seguintes categorias de carga NÃO são elegíveis para devolução pelo processo padrão:
> Cargas perigosas classificadas nas classes 1 a 6 da ANTT…
```
→ Retrieval coerente com o gabarito: a resposta correta ("carga perigosa NÃO pode ser
devolvida pelo processo padrão") está fundamentada no chunk POL-001-B.

### (e) Read-only imposto — `write_file` em `docs/novatech` → NEGADO
```
EPERM: operation not permitted, open '…\docs\novatech\_write_test.md'
```

### (f) Least privilege — leitura fora do escopo (`.env`) → NEGADO
```
Access denied - path outside allowed directories: C:\Users\melo.willian\Documents\.env
not in …\docs\novatech, …\data\retrieval-corpus
```

### (g) Histórico do repositório — server `git`, `git_log`
```
serverInfo: {'name': 'mcp-git', 'version': '1.28.0'}
Commit history:
Commit: 'bbdd03aeecd7e349a2bfc93849e0552a0b766ac6'
Author: Trilha AI First <trilha@db1.local>
Date:   2026-06-09 18:13:30+00:00
Message: 'chore: starter repo (Anexo D) — estrutura + dados semeados dos Anexos A e B'
```
`git_branch` → `* master`. Acesso de leitura ao histórico via MCP confirmado.

### (h) Workspace é leitura+escrita — `write_file` em `specs/` → SUCESSO
```
Successfully wrote to …\specs\_mcp_write_probe.md
```
(arquivo confirmado em disco e depois removido — era só prova de escrita).

### (i) Memória persistente — server `memory`, `create_entities` + persistência
Gravadas 3 entidades (linguagem ubíqua + decisão) e persistidas em `./.mcp/memory.json`:
```
{"type":"entity","name":"carga perigosa","entityType":"termo-dominio",
 "observations":["Classes 1-6 da ANTT (Resolucao 5.947/2021)",
                 "NAO elegivel para devolucao pelo processo padrao (POL-001 sec 3.2)"]}
{"type":"entity","name":"tier Gold","entityType":"termo-dominio", …}
{"type":"entity","name":"ADR-0002","entityType":"decisao",
 "observations":["Context budget: ~4K tokens system + ~8K chunks por query"]}
```

> **Como reproduzir:** ver `docs/mcp/README-evidencia.md` (driver `mcp_evidence.py` +
> sequência JSON-RPC). Cada server pode ser exercitado isoladamente via `npx`/`uvx`.

---

## 6. Análise de riscos (setup local) e mitigações

| # | Risco | Por que importa neste setup local | Mitigação aplicada / acionável |
|---|-------|-----------------------------------|--------------------------------|
| **R1** | **Escopo amplo expõe segredos** — montar a raiz do repo no filesystem server daria ao agente acesso a `.env`, `infra/parameters/*.bicepparam`, `.git/`. | Um prompt injection num documento lido poderia induzir o agente a ler/exfiltrar `.env`. | **Não montamos a raiz**; só as pastas necessárias. `.env` já está no `.gitignore`. Evidência (f): leitura de `.env` rejeitada como *outside allowed directories*. |
| **R2** | **Escrita sem gate** — o filesystem server expõe `write_file`/`edit_file`/`move_file` sem aprovação humana; o agente pode sobrescrever a fonte da verdade (docs/corpus) e "consertar" a base para casar com uma resposta. | Adulterar `docs/novatech` ou `data/retrieval-corpus` comprometeria todo o RAG silenciosamente. | Fontes isoladas na instância `sources` + **deny-write por ACL** (camada de SO). Evidência (e): `write_file` → `EPERM`. Escrita do agente fica confinada ao workspace, onde passa por code review/PR antes de merge. |
| **R3** | **Server `git` expõe operações de escrita** (`git_commit`, `git_add`, `git_reset`, `git_checkout`) — o agente poderia commitar/resetar sem revisão. | Um `git_reset --hard` ou commit automático burlaria o validation gate de code review. | **Política:** o server `git` é autorizado apenas para *leitura* (log/diff/branch/show); operações de escrita do Git são feitas por humanos. Reforço técnico recomendado: client que permita allow-list de tools por server (desabilitar `git_commit`/`git_reset`/`git_checkout`), e nunca aprovar essas tools em modo automático. |
| **R4** | **Pacotes baixados via `npx -y`/`uvx`** rodam código de terceiros com as permissões do usuário (supply-chain). | `-y` aceita instalar sem confirmação; um pacote comprometido teria acesso ao escopo concedido. | Fixar versões (`@modelcontextprotocol/server-filesystem@<versão>`), revisar o `mcp.json` em PR (quem adiciona server justifica escopo), e rodar tudo com o usuário de menor privilégio. |

> Riscos **R1** e **R2** são os exigidos pelo exercício (exposição de segredos por escopo
> amplo; escrita sem gate). R3 e R4 são reforços específicos deste setup local.

---

## 7. Resumo dos entregáveis

1. **Mapeamento** necessidade → server → escopo (§2).
2. **`.mcp/mcp.json`** final, com least privilege concreto (§3, arquivo no repo).
3. **Evidência de execução real** — leu doc, recuperou chunk, leu git, e provou
   read-only/least-privilege (§5).
4. **Análise de riscos** com mitigações acionáveis (§6).
