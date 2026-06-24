# Análise de viabilidade técnica e estratégia de chunking — Assistente de IA da NovaTech

> Exercício 1.1 (papel Desenvolvedor) · Caso de uso UC-04 · Destinatário: Tech Lead
> Fontes: `resolution/prd/prd-novatech-assistente.md`, `resolution/prd/techspec-novatech-assistente.md`, `exercicio-fase-1-entendimento.md`
> Evidência de uso de IA (revisão crítica): `evidencias/1.1-claude-historico.md`
> Versão: v2 (incorpora revisão crítica — ver seção 7 e arquivo de evidência)

## 0. Conclusão executiva

O projeto é **tecnicamente viável** com RAG, mas a viabilidade depende muito mais da **engenharia do pipeline de dados** (extração, chunking, metadados de versão) do que da escolha do modelo. A base (ordem de **6–12 milhões de tokens** — ver seção 2) excede em **~50× a 95×** a janela de contexto do GPT-4o (128K), tornando a busca seletiva (retrieval) **obrigatória** — não é opcional nem substituível por "colar tudo no contexto". Os três maiores riscos técnicos são, nesta ordem: (1) **extração de tabelas/planilhas** sem perder estrutura; (2) **idioma do modelo de embeddings** (`all-MiniLM-L6-v2` é primariamente anglófono); e (3) **gerenciamento de orçamento de contexto** com mitigação de *lost in the middle*. Nenhum é bloqueante, mas todos exigem validação empírica (recall@N contra o Anexo B) antes de fixar decisões.

---

## 1. Riscos por tipo de fonte

Cada formato impõe um desafio distinto de **extração** e **chunking**. A tabela abaixo mapeia o desafio, o impacto na qualidade da resposta e a estratégia de tratamento. A coluna "MVP?" indica se o tratamento entra na PoC open-source ou fica para produção/fase 2.

| Fonte / Formato | Desafio para o pipeline RAG | Impacto na resposta | Estratégia de tratamento | MVP? |
|---|---|---|---|---|
| **PDF com tabelas complexas** (frete PROC-042, 15+ colunas) | Extração em fluxo linear quebra o alinhamento linha/coluna; chunking por tamanho fixo corta a tabela no meio; texto tabular "achatado" gera embedding ruim. | Pergunta numérica ("multiplicador do Sul") recupera fragmento sem o cabeçalho ou com a linha errada → valor incorreto ou citação inútil. | Extração *layout-aware* (em produção, *Document Layout skill* do Azure AI Search); chunking **section-aware** que mantém **linha de tabela íntegra** e serializa a tabela como Markdown preservando cabeçalho. Validar manualmente os chunks de PROC-042 antes do go-live. | Sim (chunking); extração avançada parcialmente |
| **PDF escaneado** (~15% do SharePoint) | Sem camada de texto → nada a extrair sem OCR. | **Lacuna silenciosa de cobertura**: o assistente não responde sobre esses documentos e *não sabe que não sabe* — pode abster-se corretamente (bom) ou, pior, responder com base em documento parcial relacionado. | OCR **fora do escopo do MVP** (RNF/PRD). Mitigação no MVP: **inventariar e marcar** esses documentos como "não indexados" e informar os atendentes da limitação no treinamento de go-live. OCR em fase 2. | Não (só inventário) |
| **HTML/Wiki (Confluence)** com links internos + macros customizadas | Links entre páginas e macros perdem o sentido quando o HTML é achatado em texto; *boilerplate* de navegação vira ruído; contexto que mora em outra página some. | Resposta perde dependências cruzadas (ex.: procedimento que referencia outra página) ou indexa menu/rodapé como se fosse conteúdo → chunk irrelevante no topo. | Remover *boilerplate*; **expandir macros** na extração; capturar alvos de link como **metadado** (ou inlinar conteúdo crítico referenciado); preservar a hierarquia de seções como base do chunking. | Sim (extração HTML básica) |
| **XLSX com fórmulas interdependentes** | Célula pode trazer a fórmula (`=A2*1,3`) em vez do valor; interdependências entre abas/células se perdem; semântica tabular é difícil de embedar. | "Quanto custa o frete para 600kg?" não casa com uma planilha cujo sentido está numa cadeia de fórmulas, não no texto literal das células. | Extrair **valores calculados** (não as fórmulas) + cabeçalhos; **serializar cada linha como afirmação em linguagem natural** ("Região Norte: multiplicador 1.8") para casar com a forma da pergunta; capturar aba/coluna como metadado. | Sim |

**Leitura transversal:** os quatro casos confirmam a tese do techspec de que **RAG é um sistema de engenharia de dados** — a qualidade da resposta é decidida na extração/chunking, antes de qualquer chamada de modelo. Tabelas (PDF e XLSX) concentram o maior risco técnico e devem ser o primeiro alvo de validação.

---

## 2. Estimativa do tamanho da base em tokens (cálculo visível)

Regra prática adotada (conforme briefing UC-04): **1 token ≈ 0,75 palavra** ⇒ `tokens = palavras ÷ 0,75`.

| Fonte | Volume | Palavras (estimadas) | Tokens (÷ 0,75) |
|---|---|---|---|
| SharePoint (PDF/DOCX) | 800 docs × 10 págs × 500 palavras/pág | 4.000.000 | **≈ 5,33M** |
| Confluence (Wiki) | 400 págs × 1.500 palavras | 600.000 | **≈ 0,80M** |
| Pasta de rede (XLSX) | 50 planilhas × ~2.000 palavras-equivalentes¹ | 100.000 | **≈ 0,13M** |
| **Total (fórmula literal)** | | **4.700.000** | **≈ 6,3M tokens** |

¹ As planilhas não têm "palavras" no sentido textual; estimo ~2.000 palavras-equivalentes por planilha após serialização de linhas/valores. Contribuição pequena e de baixa sensibilidade no total.

**Reconciliação com o número do PRD (~12M):** a fórmula literal dá **~6,3M**, cerca de **metade** do número-cabeçalho de ~12M citado no PRD/cenário. A divergência não invalida nenhuma conclusão — é uma questão de premissa, não de ordem de grandeza:

- Para a soma chegar a ~12M **só com os PDFs**, a média precisaria ser de **~22 páginas/documento** (não 10) a 500 palavras/página, ou densidade textual maior por página (DOCX corporativos densos, anexos, tabelas). 10 páginas/500 palavras é uma premissa **conservadora-baixa**.
- Há ainda *overhead* não contabilizado na fórmula simples: marcação de tabelas, metadados, repetição de cabeçalhos por chunk.

**Conclusão de viabilidade (independe do número exato):** seja **6,3M** (fórmula) ou **12M** (envelope conservador do PRD), a base excede a janela de 128K em **~50× a ~95×**. A conclusão arquitetural é a mesma e robusta: **a base completa jamais cabe no contexto → retrieval seletivo é mandatório.** Adoto a faixa **6–12M tokens** no documento; o número não muda a decisão.

---

## 3. Orçamento de contexto por query e limite prático de chunks

### 3.1 Cálculo do orçamento (visível)

```
Janela do modelo (GPT-4o) ............................ 128.000 tokens
(−) System prompt + guardrails + instruções ......... ~2.000 tokens
(=) Orçamento disponível para chunks + pergunta ...... ~126.000 tokens
```

Número **teórico** de chunks que cabem:

```
Chunks de ~500 tokens : 126.000 ÷ 500 ≈ 252 chunks
Chunks de ~256 tokens : 126.000 ÷ 256 ≈ 492 chunks   (teto adotado — ver seção 4)
```

### 3.2 Limitação prática — por que NÃO usar ~252/492 chunks

O número teórico é uma armadilha. "Quanto maior melhor" é **falso** para contexto de LLM por dois efeitos combinados:

- ***Lost in the middle***: informação posicionada no meio de um contexto longo é processada com menos atenção que a do início e do fim. Encher 126K com 250+ chunks praticamente **garante** que o chunk correto, se cair no meio, seja ignorado — mesmo tendo sido recuperado corretamente.
- **Diluição de atenção / ruído**: cada chunk irrelevante adicional compete por atenção e aumenta a chance de o modelo misturar fontes (ex.: misturar PROC-042 v1 e v2 sem perceber).

Há ainda uma **correção ao cálculo** que o orçamento ingênuo omite: a janela de 128K precisa também acomodar os **tokens de saída** (a resposta gerada) e, em conversa no Teams, o **histórico acumulado** (RF-11, risco de *context rot*). O orçamento real para chunks é, portanto, **menor** que 126K — deve-se reservar margem para resposta (ordem de alguns milhares de tokens) e para o histórico de turnos.

**Limite prático recomendado:** recuperar **top-K na faixa de 5 a 15 chunks** (não 250), posicionar os de **maior score nas extremidades** do prompt e descartar os de menor score quando o orçamento apertar (RF-04). O valor exato de K deve ser **calibrado empiricamente pelo recall@N do Anexo B**, não fixado por dedução.

---

## 4. Estratégia de chunking (justificada)

**Decisão (alinhada ao techspec — "Principais decisões"):** chunking **section-aware**, com teto de **~256 tokens** (`MAX_CHUNK_TOKENS`) e **overlap de 10–15%**, preservando linhas de tabela e passos numerados íntegros.

Justificativa em três eixos:

1. **Restrição técnica do modelo de embeddings (motivo primário do teto de 256):** o `all-MiniLM-L6-v2` **trunca a entrada em 256 *word pieces***. Um chunk maior que isso é **silenciosamente cortado** antes de virar embedding — o vetor representa só o começo do chunk, degradando o retrieval sem nenhum erro visível. O teto de ~256 tokens não é estético: é o **limite do modelo**. (Em produção, com *Document Layout skill* + modelo de maior contexto, chunks maiores ficam viáveis.)

2. **Tipo de pergunta esperada (favorece chunks pequenos e precisos):** as perguntas reais do atendente são **factuais e específicas** — "prazo de devolução para carga perigosa", "multiplicador do Sul", "SLA do cliente Gold". Cada uma aponta para **uma seção ou uma linha de tabela** específica. Chunks pequenos e *section-aware* aumentam a **precisão** do retrieval (o chunk recuperado é quase só a resposta) e reduzem ruído no contexto. Chunks grandes diluiriam a resposta em texto vizinho irrelevante.

3. ***Lost in the middle* (favorece poucos chunks bem posicionados):** como K é pequeno (seção 3.2) e os chunks são curtos e precisos, cabe posicionar os de maior score nas extremidades. Section-aware + teto baixo + overlap garante que a unidade semântica (a linha da tabela de frete, o passo do procedimento) chegue **inteira** a uma das extremidades — exatamente onde a atenção do modelo é maior.

**O overlap (10–15%)** preserva contexto nas fronteiras entre chunks (ex.: uma frase de exceção que ficaria órfã no corte), sem inflar demais a base. **Não** se usa corte fixo de tokens "cego" (RF-02): isso cortaria a tabela PROC-042 no meio de uma linha — falha conhecida e crítica.

---

## 5. Risco de idioma do modelo de embeddings + plano de avaliação

**Risco:** `sentence-transformers/all-MiniLM-L6-v2` é treinado **primariamente em inglês**. A base da NovaTech e as perguntas dos atendentes são **em português**. Embeddings sub-ótimos para PT-BR podem **rebaixar o recall** — o chunk correto existe e foi indexado, mas não aparece no top-K porque a similaridade semântica em português é capturada com menos fidelidade. Esse risco é **mascarado**: o pipeline "roda" e parece funcionar, mas erra silenciosamente na recuperação.

**Plano de avaliação (decisão baseada em dados, não em fé):**
1. Manter `all-MiniLM-L6-v2` como **baseline** da PoC (atende ao RNF-09: gratuito/open-source).
2. Medir **recall@N contra o mapa de cobertura do Anexo B** com o baseline.
3. Avaliar, na mesma métrica e mesmo gabarito, os candidatos **multilíngues**: `paraphrase-multilingual-MiniLM-L12-v2` e `bge-m3`.
4. **Fixar o modelo** apenas após comparar recall@N. Se o multilíngue elevar o recall de forma relevante sem violar RNF-09, adotá-lo; caso contrário, manter o baseline e documentar a decisão.

Esse plano transforma uma incerteza ("será que funciona em português?") em **critério mensurável de homologação** (recall@N ≥ 80% do Anexo B).

---

## 6. Síntese de riscos e mitigações (para o Tech Lead)

| # | Risco técnico | Prob. | Impacto | Mitigação acionável |
|---|---|---|---|---|
| R1 | Extração/chunking quebra tabelas (PROC-042, XLSX) | Alta | Alto | Chunking section-aware com linha de tabela íntegra; validação manual dos chunks de tabela antes do go-live; teste de retrieval específico para frete. |
| R2 | Embeddings fracos em português rebaixam recall silenciosamente | Média/Alta | Alto | Benchmark recall@N baseline vs. `paraphrase-multilingual`/`bge-m3` no Anexo B antes de fixar o modelo. |
| R3 | *Lost in the middle* / diluição com K alto | Média | Médio | K pequeno (5–15); maiores scores nas extremidades; calibrar K pelo recall@N; reranker opcional só se necessário. |
| R4 | Cobertura silenciosa: PDFs escaneados (~15%) ausentes da base | Média | Médio | Inventariar e marcar como não-indexados; informar atendentes; OCR em fase 2. |
| R5 | Documentos contraditórios (PROC-042 v1 vs v2) misturados sem alerta | Alta (confirmado) | Alto | Metadado `version`/`version_date`/`is_official` em todo chunk; desambiguação por metadados (ConflictDetector + alerta no prompt), nunca pelo modelo. |
| R6 | Orçamento de contexto ignora saída + histórico (overflow/context rot) | Média | Médio | Reservar margem para tokens de resposta e histórico; reiniciar contexto após N turnos (RF-11). |

---

## 7. Perguntas em aberto para o Tech Lead

1. **Vigência do PROC-042:** o assistente só pode *alertar* sobre a divergência (G-07) — a NovaTech vai designar quem decide a versão vigente antes do go-live? Sem isso, o conflito é permanente por design.
2. **Premissa de tamanho da base:** confirmar se ~10 páginas/doc é realista; se a média for ~20+, a base real fica perto dos 12M e dimensiona infra/custos de ingestão.
3. **Modelo de produção:** a janela de 128K do GPT-4o é confirmada como alvo? Reservar margem de saída/histórico muda o K efetivo.

---

> **Nota de conformidade (skill `code-standards-en`):** este documento permanece em **português** por política de produto. Apenas identificadores/constantes propostos (`MAX_CHUNK_TOKENS`, `is_official`, `version_date`) seguem o padrão em inglês, consistente com o techspec.
