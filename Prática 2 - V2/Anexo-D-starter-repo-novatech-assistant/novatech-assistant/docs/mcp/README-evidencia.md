# Como reproduzir a evidência de uso dos MCP servers

A evidência do exercício 2.1 foi gerada subindo os servers de verdade e falando
JSON-RPC 2.0 sobre stdio com eles. O driver `mcp_evidence.py` (nesta pasta) automatiza
o handshake e as chamadas de tool.

## Pré-requisitos
- Node + `npx`, Python + `uvx` (`pip install --user uv`), Git. Garanta `…\Python312\Scripts` no `PATH`.
- Rodar a partir da raiz do repositório (`novatech-assistant/`).
- Aplicar o read-only das fontes (uma vez):
  ```powershell
  icacls "docs\novatech"         /deny "<DOMINIO>\<usuario>:(OI)(CI)(WD,AD)"
  icacls "data\retrieval-corpus" /deny "<DOMINIO>\<usuario>:(OI)(CI)(WD,AD)"
  ```

## Uso do driver
`mcp_evidence.py` recebe um JSON de configuração e imprime as respostas relevantes:

```json
{
  "cmd": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "./docs/novatech", "./data/retrieval-corpus"],
  "cwd": ".",
  "steps": [
    {"method": "tools/call", "params": {"name": "list_allowed_directories", "arguments": {}}},
    {"method": "tools/call", "params": {"name": "read_text_file",
      "arguments": {"path": "<abs>/docs/novatech/POL-001-politica-devolucao.md", "head": 45}}}
  ],
  "labels": {"escopo": 2, "ler doc": 3}
}
```
```bash
python docs/mcp/mcp_evidence.py config.json
```

## Verificação rápida sem o driver (pipe direto)
Qualquer server pode ser exercitado com um pipe de 3 linhas JSON-RPC:

```bash
printf '%s\n' \
'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"d","version":"1"}}}' \
'{"jsonrpc":"2.0","method":"notifications/initialized"}' \
'{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
| npx -y @modelcontextprotocol/server-filesystem ./docs/novatech
```

## Notas
- Na primeira execução, `npx`/`uvx` baixam os pacotes (pode levar ~30–60s).
- O `read_graph` do memory e o read-back imediato após `write_file` podem retornar vazio
  no driver por ser uma corrida com a escrita assíncrona — o **estado em disco** é a fonte
  de verdade (ex.: `.mcp/memory.json`).
- Em uso real, esses servers são carregados pelo cliente do agente (Claude Code / extensão
  Copilot) a partir do `.mcp/mcp.json`, e as tools aparecem prefixadas pelo nome do server
  (ex.: `filesystem-sources.read_text_file`).
