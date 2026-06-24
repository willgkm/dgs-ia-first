# Review: Task 2.0 - Fundação do pacote `novatech_rag/` — modelos de domínio, Protocols e configuração

**Revisor**: AI Code Reviewer
**Data**: 2026-06-14
**Arquivo da task**: 2_task.md
**Status**: APROVADO

## Resumo

A Task 2.0 estabelece a fundação do pacote Python `novatech_rag/`: estrutura em camadas (`ingestion/`, `retrieval/`, `prompt/`, `eval/`), dataclasses de domínio imutáveis, `Protocol`s que isolam os pontos de troca PoC↔produção e a configuração central tipada. A implementação está fiel à techspec ("Modelos de dados" e "Principais interfaces"), cobre todos os requisitos e critérios de sucesso da task e adere às skills `python-conventions`, `code-standards-en` e `repo-folder-structure` (adaptada a Python).

A qualidade do código é alta: type hints completos com sintaxe 3.10+, `@dataclass(frozen=True)` para todos os value objects, `Protocol`s `@runtime_checkable`, `chunk_id` determinístico via `hashlib.sha256`, validação explícita na configuração e cobertura de testes abrangente (51 testes). A verificação local foi reexecutada no venv do projeto e confirma: `pytest` = 51 passed; `ruff check`, `ruff format --check` e `mypy` limpos para `novatech_rag` e `tests` (os achados de ruff/format reportados no repositório estão em scripts de skills fora do escopo desta task).

A política consciente de identificadores em inglês + conteúdo/docstrings em português está corretamente aplicada e não foi classificada como violação.

## Arquivos Revisados

| Arquivo | Status | Problemas |
|---------|--------|-----------|
| `pyproject.toml` | ✅ OK | 0 |
| `README.md` | ✅ OK | 0 |
| `novatech_rag/__init__.py` | ✅ OK | 0 |
| `novatech_rag/models.py` | ✅ OK | 0 |
| `novatech_rag/interfaces.py` | ✅ OK | 0 |
| `novatech_rag/config.py` | ✅ OK | 0 |
| `novatech_rag/ingestion/__init__.py` | ✅ OK | 0 |
| `novatech_rag/retrieval/__init__.py` | ✅ OK | 0 |
| `novatech_rag/prompt/__init__.py` | ✅ OK | 0 |
| `novatech_rag/eval/__init__.py` | ✅ OK | 0 |
| `tests/test_models.py` | ✅ OK | 0 |
| `tests/test_config.py` | ✅ OK | 0 |
| `tests/test_package_smoke.py` | ✅ OK | 0 |

## Problemas Encontrados

### 🔴 Problemas Críticos

Nenhum problema crítico encontrado.

### 🟡 Problemas Major

Nenhum problema major encontrado.

### 🟢 Problemas Minor

1. **`novatech_rag/config.py:44` — `DEFAULT_PERSIST_DIRECTORY` como `Path` relativo.**
   O default `Path(".chroma")` é resolvido relativo ao diretório de trabalho corrente (CWD), não à raiz do pacote/projeto. Para a PoC executada via CLI a partir da raiz isso é aceitável, mas pode gerar diretórios `.chroma` em locais inesperados conforme o CWD do invocador. Sugestão (opcional, para a Tarefa 3.0 quando o `VectorStore` consumir o caminho): documentar que o caminho é relativo ao CWD ou resolvê-lo contra uma raiz conhecida. Não bloqueante na fundação.

2. **`novatech_rag/models.py:71,107,157` — `version_date` como `str` em vez de `date`/`datetime`.**
   O campo é `str` com comentário indicando ISO-8601 ordenável lexicograficamente. A escolha é deliberada e coerente com a serialização de metadados do ChromaDB (que aceita apenas str/int/float/bool) e com a techspec, mas abre margem para datas mal-formadas não validadas. Como a fundação não faz parsing de datas, é aceitável manter `str`; registrar como ponto de atenção para validação na ingestão (Tarefa 3.0).

3. **`tests/test_package_smoke.py:70` — stub com parâmetro sem type hint.**
   `def embed(self, texts):  # type: ignore[no-untyped-def]` desabilita a checagem de tipo localmente. É um stub de teste para validar `@runtime_checkable` e o `type: ignore` é intencional/justificado, mas uma anotação `texts: Sequence[str]` eliminaria a necessidade do ignore e exercitaria melhor a conformidade ao `Protocol`. Cosmético.

## ✅ Destaques Positivos

- **`chunk_id` determinístico correto e bem testado** (`models.py:49-57`): `hashlib.sha256` sobre `f"{doc_id}|{section}|{ordinal}"` com separador extraído para a constante `CHUNK_ID_SEPARATOR`. Os testes em `test_models.py` cobrem determinismo (mesmas entradas → mesmo id), unicidade (entradas diferentes → ids diferentes, incluindo ordinais consecutivos), formato hex de 64 chars e o cenário-chave de reindexação idempotente (RF-10).
- **Cobertura completa dos metadados de domínio** (`ChunkMetadata`): `version`, `version_date`, `is_official` e `source` (enum `DocumentSource`) presentes, atendendo G-07 (divergência) e priorização oficial vs FAQ. Teste explícito `test_faq_metadata_is_not_official` valida o caso FAQ = `is_official=False`.
- **`GenerationAdapter` corretamente modelado como seam não-implementado** (`interfaces.py:82-90`): declarado como `Protocol` com docstring explicando que a geração da PoC é manual/Ollama e a produção fornece o adaptador para Azure OpenAI. Exatamente o desenho da techspec.
- **Configuração com guardas explícitas e CQS** (`config.py`): `RagConfig` frozen com `__post_init__` validando `token_budget` (positivo e ≤128K via `TOKEN_BUDGET_LIMIT`, mapeado a RNF-06), `top_k`, `min_score ∈ [0,1]`, `chunk_overlap_ratio ∈ [0,1)`. Mensagens de erro claras em português. Testes cobrem limite exato, acima do limite e valores inválidos.
- **Direção de dependência respeitada** (`python-conventions` Etapa 1): `models.py` não importa de `retrieval/`/`prompt/`/`eval/`; `interfaces.py` importa apenas de `.models`; `__init__` expõe surface pública explícita via `__all__`. Layout em camadas documentado no README e nas docstrings dos submódulos.
- **Melhoria sobre a techspec**: a techspec descreve `ConflictGroup.versions` como `list[(version, version_date, chunk_id)]` (tupla); a implementação introduz a dataclass nomeada `ConflictVersion`, mais legível e tipada, sem perder informação. Refinamento positivo, não desvio.
- **Constantes nomeadas em vez de números mágicos** (`config.py`): `MAX_CHUNK_TOKENS`, `EMBEDDING_DIMENSIONS`, `TOKEN_BUDGET_LIMIT`, etc., com comentários rastreando RNFs.
- **`from __future__ import annotations`** aplicado consistentemente; sem efeitos colaterais a nível de módulo (sem I/O ou carga de modelo no import), aderindo a `python-conventions` Etapa 3.5.

## Conformidade com Padrões

| Padrão | Status |
|--------|--------|
| Padrões de Código (`code-standards-en`) | ✅ |
| Python / type hints (`python-conventions`) | ✅ |
| Estrutura de pacote (`repo-folder-structure` adaptado) | ✅ |
| REST/HTTP | N/A (MVP sem HTTP; produção fora do escopo da task) |
| Logging | N/A (não exigido na fundação) |
| React | N/A (PoC Python sem frontend) |
| Testes (`pytest`) | ✅ |

## Recomendações

1. (Minor, Tarefa 3.0) Decidir e documentar a resolução de `DEFAULT_PERSIST_DIRECTORY` relativa ao CWD vs raiz do projeto quando o `VectorStore` for implementado.
2. (Minor, Tarefa 3.0) Validar `version_date` no momento da ingestão (parsing ISO-8601) já que o modelo mantém `str` por design de serialização.
3. (Cosmético) Anotar `texts: Sequence[str]` no stub de `test_package_smoke.py` para remover o `# type: ignore[no-untyped-def]`.
4. (Opcional) Considerar adicionar uma docstring de módulo curta em `pyproject.toml`/seção de extras esclarecendo que `ollama` e `dev` são opcionais — já está claro via comentário, apenas reforço.

## Veredito

Implementação **APROVADA**. A fundação cumpre integralmente os requisitos e os três critérios de sucesso da Task 2.0: pacote importável (smoke test confirma top-level + 7 submódulos + surface pública), `chunk_id` estável e único (testes de determinismo/unicidade), e dataclasses cobrindo todos os campos de versão (G-07) e `is_official`. Os `Protocol`s incluem o seam `GenerationAdapter` não-implementado, e a configuração impõe `token_budget` ≤128K. Verificação de tipos, lint, formatação e testes estão verdes para o escopo da task.

Os três pontos minor são não-bloqueantes e endereçáveis nas tarefas subsequentes (3.0/5.0). Nenhuma mudança é exigida antes de prosseguir. A base está pronta para a Tarefa 3.0 (ingestão).
