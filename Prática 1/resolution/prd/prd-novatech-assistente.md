# PRD — Assistente de IA da NovaTech (RAG para Atendimento)

## Resumo executivo

A equipe de atendimento da NovaTech (45 pessoas) gasta em média 12 minutos por chamado buscando informações em ~1.250 documentos distribuídos em três sistemas distintos (SharePoint, Confluence, pasta de rede). Com 320 chamados/dia e 60% deles exigindo consulta a documentação, o custo operacional em tempo de busca é de aproximadamente 2.304 minutos/dia (~38 horas) desperdiçados em navegação manual. Isso gera respostas inconsistentes, atrasos e escaladas desnecessárias para o supervisor em 15% dos chamados.

A DB1 construirá um assistente de IA baseado em RAG (Retrieval-Augmented Generation) integrado ao Microsoft Teams que permite ao atendente fazer perguntas em linguagem natural e receber respostas fundamentadas na documentação oficial, com citação de fonte rastreável. O sistema será construído em Python com ChromaDB e sentence-transformers como prova de conceito open-source, evoluindo para Azure AI Services em produção. A meta é reduzir o tempo médio de busca de 12 minutos para menos de 2 minutos por chamado ao go-live, em um prazo de 3 meses (discovery + desenvolvimento + go-live).

---

## Problema

### Contexto de negócio

A NovaTech opera 320 chamados de atendimento por dia, dos quais ~192 (60%) exigem que o atendente consulte a documentação interna para responder. Essa documentação está fragmentada em três fontes não integradas:

| Fonte | Volume | Formato | Frequência de atualização | Responsável |
|-------|--------|---------|--------------------------|-------------|
| SharePoint | ~800 documentos | PDF, DOCX | Mensal | Operações, Compliance |
| Confluence | ~400 páginas | HTML/Wiki | Semanal | TI, Comercial |
| Pasta de rede | ~50 planilhas | XLSX | Mensal | Comercial |

O volume estimado da base em tokens é de aproximadamente 12 milhões de tokens — excedendo em 93× a janela de contexto do GPT-4o (128K tokens), o que torna a busca manual inevitável sem RAG. O tempo médio de busca é de 12 minutos por chamado, gerando ~2.304 minutos perdidos por dia somente em navegação.

Agravante estrutural: documentos contraditórios coexistem na base sem indicação de vigência (ex.: PROC-042 e PROC-042-v2 apresentam multiplicadores regionais divergentes), e o FAQ de atendimento contém 47 respostas informais sem validação formal — sendo que ao menos uma categoria de cliente citada nele (tier "Platinum") não existe na documentação oficial, representando risco direto de alucinação e desinformação.

### Usuários afetados

**Atendente de suporte (45 pessoas):** usuário primário. Recebe dúvidas de clientes sobre prazos, fretes, devoluções e reclamações. Precisa de respostas rápidas, corretas e rastreáveis. Hoje navega manualmente entre 3 sistemas, abre em média 4 fontes por chamado, e em 15% dos casos não encontra a resposta e escala para o supervisor.

**Supervisor de atendimento:** ponto de escalada quando o atendente não encontra resposta. Beneficia-se indiretamente pela redução de escaladas evitáveis — hoje absorve chamados que não foram atendidos por limitação de busca, não por complexidade genuína.

**Admin de documentação (3 áreas — Operações, Compliance, Comercial):** publica e atualiza documentos sem processo unificado de revisão. Precisa garantir que a base do assistente reflita a versão vigente dos documentos após cada atualização mensal (SharePoint, pasta de rede) ou semanal (Confluence).

### Impacto atual (sem a solução)

- **Produtividade:** ~38 horas/dia de tempo de atendimento consumido por busca manual em vez de atendimento ao cliente.
- **Inconsistência:** atendentes consultam fontes diferentes e dão respostas divergentes sobre o mesmo procedimento — especialmente crítico para PROC-042, cujas duas versões com multiplicadores diferentes coexistem sem indicação de qual está vigente.
- **Escaladas evitáveis:** 15% dos chamados são escalados ao supervisor porque o atendente não encontrou a resposta a tempo — não por falta de informação na base, mas por limitação de busca manual.
- **Risco de compliance:** respostas baseadas em versões desatualizadas ou no FAQ informal (sem validação) podem contradizer a política oficial vigente, gerando passivos operacionais e regulatórios.

---

## Solução proposta

### Visão geral

O Assistente de IA da NovaTech é uma interface conversacional disponível no Microsoft Teams que permite ao atendente perguntar em linguagem natural — "Qual o prazo de devolução para carga perigosa?" — e receber em segundos uma resposta fundamentada em trechos reais da documentação oficial, com indicação do documento de origem e da seção relevante.

Por baixo, o sistema aplica RAG: documentos das três fontes são ingeridos, divididos em chunks que preservam unidades semânticas, convertidos em representações vetoriais (embeddings) e armazenados em um banco vetorial. A cada pergunta, o sistema recupera os chunks mais relevantes e os fornece como contexto para o modelo de linguagem gerar a resposta — ancorando cada afirmação em documentação verificável, não em conhecimento genérico do modelo.

O sistema não substitui o julgamento do atendente — ele entrega informação fundamentada para que o atendente tome a decisão correta. Quando não encontra resposta na base, declara explicitamente e orienta a escalada. Quando detecta versões conflitantes, apresenta ambas com alerta, sem escolher arbitrariamente.

### Escopo do MVP

**O que está incluído no MVP:**
- Pipeline de ingestão: extração de texto dos formatos PDF, DOCX, HTML/Wiki e XLSX, divisão em chunks com estratégia que preserva unidades semânticas, geração de embeddings com `sentence-transformers/all-MiniLM-L6-v2` e indexação no vector store (ChromaDB no PoC, Azure AI Search em produção).
- Busca por similaridade: dada uma pergunta do atendente, recuperar os N chunks mais relevantes com score de similaridade, filtrando chunks abaixo do threshold mínimo.
- Montagem de prompt: composição do contexto completo (system prompt estático + chunks recuperados + pergunta) com orçamento de contexto gerenciado e posicionamento estratégico de chunks para mitigar o efeito *lost in the middle*.
- Geração de resposta via LLM com citação obrigatória de fonte (documento + seção).
- Guardrails no system prompt: sem invenção de prazos/valores não documentados, escalada explícita quando sem resposta, alertas de versões conflitantes, resposta em português formal.
- Integração com Microsoft Teams como canal de entrega ao atendente.
- Tratamento de documentos contraditórios: detecção de versões conflitantes e exibição com alerta explícito.
- System prompt versionado no repositório com mapeamento de partes estáticas e dinâmicas.

**O que está fora do escopo do MVP:**
- Painel de administração de documentos para o admin: ingestão é via script manual no MVP. Automação via webhook SharePoint/Confluence fica para fase 2.
- Feedback estruturado do atendente sobre qualidade das respostas (mecanismo de rating/correção): fase 2, após validação do comportamento base em produção.
- Integração direta via API do SharePoint e Confluence para ingestão automatizada: MVP usa arquivos exportados manualmente. API fica para fase 2.
- OCR para documentos escaneados (~15% dos PDFs do SharePoint): fase 2, após validação do pipeline principal com documentos nativo-digitais.
- Enriquecimento do contexto com dados do cliente (tier, histórico): fase 2, quando o padrão de perguntas em produção estiver mapeado.

---

## Casos de uso

### UC-01: Consulta de informação pelo atendente

**Ator:** Atendente de suporte
**Pré-condição:** Atendente está em atendimento ativo no Teams e tem uma dúvida sobre procedimento, prazo, frete ou política de devolução.
**Fluxo principal:**
1. Atendente digita a pergunta em linguagem natural no canal do assistente no Teams.
2. O sistema converte a pergunta em embedding e recupera os N chunks mais relevantes da base vetorial (score ≥ 0,70).
3. O sistema monta o prompt (system prompt + chunks + pergunta) dentro do orçamento de contexto definido, com chunks de maior score posicionados no início e no fim.
4. O LLM gera resposta em português formal com indicação da fonte (nome do documento e seção).
5. A resposta é exibida ao atendente no Teams com o trecho de origem referenciado.
6. O atendente usa a informação para responder ao cliente.

**Fluxo alternativo:**
- **Documentos contraditórios recuperados:** O assistente exibe ambas as versões com alerta: "Atenção: existem versões divergentes deste documento. Versão [identificador A, data]: [conteúdo]. Versão [identificador B, data]: [conteúdo]. Consulte seu supervisor para confirmar qual está vigente antes de usar esta informação."
- **Pergunta sem resposta na base (score < 0,70):** O assistente responde: "Não encontrei informação sobre isso na documentação disponível. Recomendo escalar para seu supervisor ou consultar diretamente a área responsável."
- **Contexto da conversa acumulado:** O sistema reinicia o contexto após o limite de turnos configurado, informando ao atendente: "Sessão reiniciada para manter a qualidade das respostas. Pode continuar sua pergunta."

**Pós-condição:** O atendente recebeu uma resposta fundamentada na documentação oficial com citação verificável, em menos de 2 minutos a partir da submissão da pergunta.

---

### UC-02: Escalada ao supervisor por ausência de resposta

**Ator:** Atendente de suporte
**Pré-condição:** O assistente retornou resposta de "não encontrado" para a pergunta do atendente.
**Fluxo principal:**
1. O assistente declara explicitamente que não encontrou informação relevante na base.
2. O assistente sugere a ação concreta: "Recomendo escalar para seu supervisor."
3. O atendente decide escalar o chamado ao supervisor manualmente via Teams.

**Fluxo alternativo:**
- **Atendente reformula a pergunta:** Retorna ao UC-01 com nova formulação. O sistema trata a reformulação como nova query independente.

**Pós-condição:** O atendente tomou decisão consciente de escalar, sem tentar responder com base em informação não encontrada ou gerada pelo LLM sem fundamentação.

---

### UC-03: Atualização de documento na base

**Ator:** Admin de documentação (Operações, Compliance ou Comercial)
**Pré-condição:** Um documento foi publicado ou atualizado em alguma das fontes (SharePoint, Confluence, pasta de rede).
**Fluxo principal:**
1. Admin exporta o documento atualizado no formato suportado (PDF, DOCX, HTML, XLSX).
2. Admin executa o script de ingestão apontando para o arquivo novo/atualizado.
3. O pipeline identifica o documento pelo identificador (ex: "PROC-042"), remove os chunks da versão anterior e indexa os novos chunks com metadados de data de versão.
4. O assistente passa a usar a versão atualizada nas próximas consultas.

**Fluxo alternativo:**
- **Documento atualizado com mesmo código e versões que devem coexistir (ex: PROC-042-v2):** O pipeline mantém ambas as versões indexadas com metadados de data e registra o conflito para acionamento do guardrail G-07 nas consultas. O assistente exibirá alerta de versões divergentes (ver UC-01 fluxo alternativo).

**Pós-condição:** A documentação atualizada está disponível para consulta em até 24 horas após o processamento do pipeline.

---

### UC-04: Análise de viabilidade técnica (Desenvolvedor — Ex. 1.1)

**Ator:** Desenvolvedor
**Pré-condição:** Desenvolvedor recebeu o briefing técnico com os tipos de documentos da NovaTech e o conceito de context engineering aplicado a RAG.
**Fluxo principal:**
1. Desenvolvedor analisa cada tipo de fonte (PDFs com tabelas complexas, PDFs escaneados, wiki com links internos, planilhas com fórmulas interdependentes) e identifica os desafios específicos para o pipeline de RAG.
2. Desenvolvedor estima o tamanho da base em tokens (~800 PDFs × 10 págs × 500 palavras/pág ÷ 0,75 + ~400 págs wiki × 1.500 palavras ÷ 0,75 + ~50 planilhas ≈ 12M tokens total).
3. Desenvolvedor calcula o orçamento de contexto: janela de 128K tokens − 2K (system prompt + instruções) = ~126K tokens disponíveis por query, comportando ~252 chunks de 500 tokens — mas limitado na prática para mitigar *lost in the middle*.
4. Desenvolvedor define estratégia de chunking justificada pelo tipo de pergunta esperada e pelo efeito *lost in the middle*.
5. Desenvolvedor submete a análise ao Claude para revisão crítica e incorpora o feedback recebido.

**Pós-condição:** Documento de análise de viabilidade técnica entregue ao Tech Lead com riscos por tipo de documento, estimativa de tokens fundamentada e estratégia de chunking justificada.

---

### UC-05: Prototipação e teste de system prompt (Desenvolvedor — Ex. 1.2)

**Ator:** Desenvolvedor
**Pré-condição:** Guardrails definidos pelo Product Specialist disponíveis; 3 chunks simulados do Anexo B disponíveis para teste; Claude disponível como ambiente de teste.
**Fluxo principal:**
1. Desenvolvedor escreve o system prompt v1 com seções claras: identidade, regras de comportamento, formato de resposta e instruções para uso dos chunks.
2. Desenvolvedor mapeia as partes estáticas (system prompt completo, guardrails fixos) e dinâmicas (chunks recuperados, pergunta, histórico de conversa) e estima tamanho em tokens de cada parte.
3. Desenvolvedor testa o prompt no Claude com as 3 perguntas de teste: prazo de devolução para carga perigosa, SLA do cliente Gold, frete para 600kg para Manaus.
4. Desenvolvedor analisa cada resposta: correção factual, citação de fonte, aderência aos guardrails.
5. Desenvolvedor itera para o system prompt v2 corrigindo os problemas encontrados e testa novamente.

**Pós-condição:** System prompt v2 testado e documentado com análise crítica das diferenças de qualidade entre v1 e v2, versionado no repositório.

---

### UC-06: Construção e validação do pipeline RAG open-source (Desenvolvedor — Ex. 1.3)

**Ator:** Desenvolvedor
**Pré-condição:** Documentos do Anexo A disponíveis como arquivos `.md` individuais; mapa de cobertura do Anexo B disponível como gabarito de avaliação; stack instalada (Python, ChromaDB, sentence-transformers).
**Fluxo principal:**
1. Desenvolvedor implementa script de ingestão: lê documentos do Anexo A, divide em chunks com estratégia justificada, gera embeddings com `all-MiniLM-L6-v2`, armazena no ChromaDB com metadados.
2. Desenvolvedor implementa função de busca: recebe pergunta, gera embedding, recupera N chunks mais similares com scores de similaridade.
3. Desenvolvedor implementa função de montagem de prompt: system prompt + chunks recuperados + pergunta.
4. Desenvolvedor testa com ≥ 5 perguntas do mapa de cobertura do Anexo B, comparando chunks recuperados com o gabarito.
5. Desenvolvedor cola o prompt montado no Claude para obter resposta e avalia: correção factual, citação de fonte, aderência aos guardrails.
6. Desenvolvedor identifica ≥ 2 problemas encontrados (ex: chunk errado recuperado, tabela cortada no meio, documento irrelevante no topo) e propõe correções concretas.

**Pós-condição:** Pipeline funcional documentado com evidências de teste, análise de problemas com comparação ao gabarito do Anexo B e propostas de correção.

---

## Requisitos funcionais

| ID | Requisito | Prioridade | Critério de aceitação |
|----|-----------|------------|----------------------|
| RF-01 | O sistema deve ingerir documentos nos formatos PDF, DOCX, HTML e XLSX, extrair o texto e indexá-los no vector store com metadados de data de versão, fonte e identificador do documento. | Must | Dado um documento em cada formato suportado, após execução do script de ingestão, o documento deve ser recuperável por busca semântica com pergunta relacionada ao seu conteúdo. |
| RF-02 | O sistema deve dividir documentos em chunks com estratégia que preserve unidades semânticas (ex: por seção com overlap de 10%), não por corte fixo de tokens sem contexto. | Must | Chunks de tabelas (como PROC-042) não devem ser cortados no meio de uma linha. Chunks de procedimentos numerados devem conter o passo completo. Verificável inspecionando o conteúdo dos chunks indexados. |
| RF-03 | Dada uma pergunta em linguagem natural, o sistema deve recuperar os N chunks mais relevantes da base com score de similaridade, aplicando threshold mínimo configurável. | Must | Para cada pergunta do mapa de cobertura do Anexo B, os chunks corretos devem estar entre os N primeiros resultados em ≥ 80% dos casos (recall@N). |
| RF-04 | O sistema deve montar o prompt completo (system prompt + chunks + pergunta) respeitando o orçamento de contexto máximo (≤ 128K tokens para GPT-4o). Quando o orçamento for excedido, os chunks de menor score devem ser descartados. | Must | O prompt montado nunca deve exceder a janela de contexto do modelo configurado. Verificável medindo o tamanho em tokens do prompt gerado. |
| RF-05 | O assistente deve citar obrigatoriamente a fonte de cada afirmação factual (nome do documento, seção e data de versão quando disponível). | Must | Em 100% das respostas geradas a partir de chunks, o nome do documento de origem deve constar explicitamente na resposta. |
| RF-06 | O assistente não deve afirmar prazos, valores numéricos ou regras que não estejam presentes nos chunks recuperados para aquela query. | Must | Dado um prompt onde os chunks não contêm a resposta, o assistente deve declarar ausência de informação em ≥ 95% dos testes. Verificável com conjunto de perguntas-armadilha (ex: tier Platinum, pergunta fora do escopo da base). |
| RF-07 | Quando não encontrar informação relevante na base (nenhum chunk acima do threshold), o assistente deve informar explicitamente a ausência e recomendar escalada ao supervisor. | Must | Dado conjunto de 10 perguntas sem resposta na base, o assistente deve recomendar escalada em ≥ 9 casos. |
| RF-08 | Quando recuperar chunks de versões conflitantes do mesmo documento (mesmo identificador, datas ou versões diferentes), o assistente deve apresentar ambas as versões com alerta explícito de divergência. | Must | Para pergunta sobre PROC-042, se chunks de v1 e v2 forem recuperados, a resposta deve apresentar os valores das duas versões e o alerta de divergência. Resposta que apresenta apenas uma versão = falha. |
| RF-09 | O sistema deve estar disponível via Microsoft Teams como canal primário de interação para os atendentes, sem necessidade de sair para outra ferramenta. | Must | Atendente deve conseguir enviar pergunta e receber resposta dentro da interface do Teams. Verificável com teste de ponta a ponta no ambiente Teams. |
| RF-10 | O pipeline de ingestão deve suportar atualização incremental: ao reindexar um documento, os chunks da versão anterior são substituídos pelos da nova versão. | Must | Após reindexação de documento atualizado, consultas devem retornar conteúdo da nova versão. Verificável consultando o mesmo tema antes e após reindexação. |
| RF-11 | O sistema deve encerrar e reiniciar o contexto da conversa após número de turnos configurável, para prevenir context rot, informando o atendente sobre o reinício. | Should | Em sessão com > N turnos configurados, pergunta idêntica feita no turno 1 e no turno N+1 deve ter qualidade de resposta equivalente. Verificável com teste comparativo de sessão longa. |
| RF-12 | O system prompt deve ser versionado como artefato de código no repositório, com estrutura que distingue explicitamente partes estáticas das partes dinâmicas, e estimativa de tamanho em tokens de cada parte documentada. | Should | O repositório deve conter ao menos o system prompt v1 e v2 com registro das diferenças e motivação das mudanças. Verificável inspecionando o repositório. |

---

## Requisitos não-funcionais

| ID | Requisito | Métrica | Referência |
|----|-----------|---------|------------|
| RNF-01 | Tempo de resposta por consulta | ≤ 10 segundos (P95) da submissão da pergunta até exibição da resposta completa no Teams | Meta de negócio: < 2 min por chamado; o tempo de resposta do assistente deve ser negligível nesse total |
| RNF-02 | Capacidade de consultas simultâneas | ≥ 45 consultas simultâneas | 45 atendentes podem consultar ao mesmo tempo em pico de demanda |
| RNF-03 | Volume diário de consultas sem degradação | ≥ 192 consultas/dia | 60% de 320 chamados/dia |
| RNF-04 | Disponibilidade em horário comercial | ≥ 99% (seg–sex, 08h–18h) | Atendimento opera em horário comercial; indisponibilidade impacta diretamente o SLA de atendimento |
| RNF-05 | Prazo de disponibilização de documentos atualizados | ≤ 24 horas após execução do pipeline de ingestão | Documentação atualizada mensalmente (SharePoint, rede) e semanalmente (Confluence) |
| RNF-06 | Orçamento de contexto por query | ≤ 128K tokens (GPT-4o) ou conforme janela do modelo configurado em produção | Base total estimada: ~12M tokens; orçamento por query é limitado pela janela do modelo, não pelo volume total |
| RNF-07 | Formatos suportados pelo pipeline de ingestão | PDF, DOCX, HTML/Wiki, XLSX | 800 docs PDF/DOCX (SharePoint), 400 páginas HTML (Confluence), 50 planilhas XLSX (pasta de rede) |
| RNF-08 | Isolamento de dados: documentos indexados não devem ser expostos fora do ambiente Microsoft da NovaTech | 0 incidentes de exposição de conteúdo fora do ambiente autorizado | Requisito de segurança e compliance da NovaTech |
| RNF-09 | Stack do PoC: exclusivamente gratuita e open-source | Python + ChromaDB + sentence-transformers (`all-MiniLM-L6-v2`) sem custo de licença | Validação técnica obrigatória antes de provisionar Azure AI Services |

---

## Guardrails do assistente

| # | Guardrail | Tipo | Como verificar |
|---|-----------|------|----------------|
| G-01 | O assistente deve citar o nome do documento e a seção de origem em toda resposta que contenha fato, prazo, valor ou regra. | DEVE | Inspecionar a resposta: toda afirmação factual deve ter referência explícita ao documento. Automação: verificar presença de padrão "Fonte:" ou nome de documento na saída. |
| G-02 | O assistente não deve afirmar prazos, valores numéricos ou regras que não estejam presentes nos chunks recuperados para aquela query. | NÃO DEVE | Testar com pergunta cujos chunks não contêm a resposta. Assistente deve declarar ausência, não inventar. Ex: perguntar sobre tier "Platinum" — resposta correta: "não encontrado na documentação". |
| G-03 | Quando nenhum chunk relevante for encontrado na base, o assistente deve declarar explicitamente "Não encontrei informação sobre isso na documentação disponível" e recomendar escalada ao supervisor. | DEVE | Conjunto de 10 perguntas sem resposta na base; assistente deve usar frase de ausência e recomendar escalada em ≥ 9 casos. |
| G-04 | O assistente deve responder exclusivamente em português formal e acessível, sem jargão técnico de IA ou TI nas respostas ao atendente. | DEVE | Revisão manual de amostra de respostas; ausência de termos como "embedding", "vector store", "LLM", "token" nas respostas exibidas ao atendente. |
| G-05 | O assistente não deve afirmar que cargas perigosas (classes 1 a 6 da ANTT) podem ser devolvidas. | NÃO DEVE | Perguntar "Posso devolver carga perigosa?" — resposta correta: NÃO pode ser devolvida (conforme POL-001, seção 3.2 — exceção explícita). Qualquer resposta que afirme que sim, ou que omita a exceção, é falha crítica de guardrail. |
| G-06 | O assistente não deve afirmar a existência do tier de cliente "Platinum" nem fornecer SLAs para esse tier. | NÃO DEVE | Perguntar "Qual o SLA do cliente Platinum?" — resposta correta: declarar que o tier não existe na documentação (SLA-2024 define apenas Gold, Silver e Standard). Resposta com SLA inventado para Platinum = falha crítica. |
| G-07 | Quando recuperar chunks de versões conflitantes do mesmo documento, o assistente deve apresentar ambas as versões com alerta de divergência, sem escolher arbitrariamente uma versão como correta. | DEVE | Perguntar sobre multiplicador regional Sul do PROC-042 — assistente deve citar v1 (1.2, mar/2023) e v2 (1.3, nov/2023) com alerta. Resposta que apresenta apenas uma versão sem mencionar o conflito = falha. |
| G-08 | O assistente não deve encerrar resposta sobre tema com versões conflitantes com afirmação de certeza absoluta sem alerta de divergência. | NÃO DEVE | Qualquer resposta sobre PROC-042 que não inclua alerta de versões conflitantes quando ambas estiverem indexadas = falha. |

---

## Tratamento de casos especiais

### Documentos contraditórios

Quando o pipeline recuperar chunks de versões conflitantes de um mesmo documento (identificadas por mesmo código de procedimento com datas ou numerações de versão diferentes), o assistente deve:
1. Apresentar o conteúdo de **ambas as versões**, identificando claramente o identificador e data de cada uma.
2. Incluir alerta explícito: "Atenção: existem versões divergentes deste procedimento. Confirme com seu supervisor ou com a área responsável qual versão está vigente antes de usar esta informação."
3. **Não escolher** uma versão como "correta" sem base factual (ou seja, sem metadado de vigência explícito nos documentos).

Exemplo crítico: PROC-042 (multiplicadores Sul: 1.2, mar/2023) vs. PROC-042-v2 (multiplicadores Sul: 1.3, nov/2023). O assistente deve apresentar ambos com o alerta — nunca silenciar um deles por ser "mais antigo".

**Requisito de produto para o admin:** O pipeline de ingestão deve registrar metadado de data de publicação nos chunks de todos os documentos ingeridos, para que o assistente possa informar qual é mais recente mesmo quando os próprios documentos não indicam vigência explícita.

### Ausência de resposta na base

Quando nenhum chunk com score de similaridade acima do threshold configurável for encontrado para a pergunta do atendente, o assistente deve:
1. Declarar explicitamente: "Não encontrei informação sobre isso na documentação disponível."
2. Recomendar ação concreta: "Recomendo escalar para seu supervisor ou consultar diretamente a área [Operações / Compliance / Comercial] responsável por este procedimento."
3. **Nunca** gerar resposta com base no conhecimento geral do LLM sobre logística ou frete (ex: regras genéricas do setor não presentes na documentação da NovaTech).

Isso é especialmente crítico para perguntas sobre tiers inexistentes (ex: "Platinum"), exceções a regras (ex: carga perigosa — onde uma resposta genérica incorreta pode gerar consequências operacionais e de compliance), e perguntas fora do escopo da documentação indexada.

### Atualização de documentos

Quando um documento é atualizado em qualquer das três fontes:
1. O admin de documentação executa o pipeline de ingestão com o arquivo atualizado.
2. O sistema identifica o documento pelo identificador e **substitui os chunks da versão anterior**, exceto quando a nova versão deve coexistir com a anterior por razões de auditoria ou quando é um documento com numeração diferente (como PROC-042-v2 em relação ao PROC-042).
3. O documento atualizado deve estar disponível para consulta em **até 24 horas** após o processamento.
4. Se o documento atualizado introduzir novos conflitos com outros documentos já indexados, o pipeline deve registrar o conflito nos metadados para acionamento dos guardrails G-07 e G-08 nas consultas subsequentes.

**Risco operacional:** A NovaTech não tem processo unificado de revisão entre as três áreas. O assistente pode refletir documentos desatualizados por semanas se o pipeline de ingestão não for acionado após cada publicação. A mitigação no MVP é a notificação manual ao admin após publicação em qualquer das fontes; automação via webhook fica para fase 2.

---

## Métricas de sucesso

| Métrica | Baseline atual | Meta | Prazo |
|---------|---------------|------|-------|
| Tempo médio de busca por chamado | 12 min | < 2 min | Go-live (3 meses) |
| Taxa de escaladas por "atendente não encontrou resposta" | ~15% dos chamados | < 5% dos chamados | 60 dias pós go-live |
| % de respostas com citação de fonte verificável | 0% (busca manual não gera rastreabilidade) | ≥ 95% | Go-live |
| Taxa de respostas incorretas críticas (guardrails G-05, G-06, G-07 violados) | Não medido | 0% em testes de guardrail pré go-live | Homologação |
| Cobertura de recuperação correta — recall@N | N/A | ≥ 80% das perguntas do mapa de cobertura do Anexo B | Homologação |
| Tempo de disponibilização de documento atualizado após ingestão | Imediato (atendente busca manualmente) | ≤ 24h após execução do pipeline | Go-live |

---

## Riscos de produto

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Alucinação do assistente (inventa procedimentos, prazos ou tiers inexistentes) | Alta | Alto | Guardrails explícitos no system prompt (G-02, G-05, G-06); threshold de similaridade mínimo para aceitar chunks como contexto; test suite com perguntas-armadilha do Anexo B antes do go-live; revisão manual de amostra de respostas em produção. |
| Documentos contraditórios gerando respostas mistas sem alerta (ex: PROC-042 v1 e v2 com multiplicadores divergentes) | Alta — confirmado: ao menos 2 versões coexistem sem indicação de vigência | Alto | Pipeline de ingestão registra metadado de versão/data em todos os chunks; guardrail G-07 obriga apresentação de ambas as versões quando conflito detectado; validação com mapa de cobertura do Anexo B antes do go-live. |
| Context rot em conversas longas no Teams (atendente faz 5+ perguntas na mesma sessão) | Média | Médio | Limite configurável de turnos por sessão (RF-11) com reinicialização automática e aviso ao atendente; monitoramento de qualidade em sessões longas como parte do plano de testes. |
| Documentação desatualizada na base por ausência de processo unificado de revisão entre as 3 áreas | Alta | Alto | SLA de ingestão de 24h documentado (RNF-05); designação de responsável por área para notificação ao admin após publicação; fase 2: automação via webhook SharePoint/Confluence para ingestão proativa. |
| Chunking que corta tabelas ao meio (ex: tabela de frete PROC-042 com 15+ colunas) | Alta | Médio | Estratégia de chunking por seção semântica, não por token fixo (RF-02); validação manual dos chunks de documentos com tabelas complexas antes do go-live; testes de retrieval específicos para perguntas sobre fretes. |
| Lost in the middle: chunks corretos recuperados mas ignorados pelo LLM por posicionamento central no contexto | Média | Médio | Chunks mais relevantes (maior score) posicionados no início e fim do contexto; limitar N de chunks para não diluir atenção do modelo; testes comparativos de qualidade por posição de chunk. |
| FAQ informal (47 Q&As sem validação) gerando respostas com autoridade indevida, incluindo tier Platinum inexistente | Alta | Alto | FAQ indexado com metadado explícito de "fonte não-oficial — não validado formalmente"; system prompt instrui o modelo a priorizar documentos oficiais sobre o FAQ e alertar quando a resposta vier exclusivamente do FAQ; curadoria do FAQ antes da ingestão inicial. |
| Escalabilidade e confiabilidade do ChromaDB em produção com 45 usuários simultâneos | Baixa (ChromaDB é explicitamente para PoC) | Médio | ChromaDB é exclusivo para o PoC (Ex. 1.3); produção usa Azure AI Search. Documentar claramente no PRD e techspec que a stack open-source não é para produção. |

---

## Restrições e dependências

- **Prazo total:** 3 meses (discovery + desenvolvimento + go-live) — sem margem para escopo creep no MVP. Funcionalidades marcadas como "fase 2" não devem ser implementadas no prazo atual.
- **Stack do PoC:** exclusivamente ferramentas open-source gratuitas (Python, ChromaDB, sentence-transformers `all-MiniLM-L6-v2`) — validação técnica obrigatória antes de qualquer provisiona-mento de serviço pago.
- **Stack de produção:** Azure AI Services (Azure AI Search + Azure OpenAI) aproveitando licenças Microsoft 365 E3 já disponíveis na NovaTech; provisionamento dos serviços Azure depende de aprovação interna da NovaTech — dependência crítica de prazo.
- **Integração Teams:** requer criação de App no Azure Active Directory da NovaTech e concessão de permissões de bot no Teams pela equipe de TI da NovaTech — dependência crítica do canal de entrega do MVP.
- **Acesso às fontes de dados:** pipeline de ingestão do MVP usa arquivos exportados manualmente; acesso às APIs do SharePoint e Confluence não é bloqueante para o MVP, mas necessário para automação na fase 2.
- **Documentos escaneados:** ~15% dos PDFs do SharePoint requerem OCR e não serão cobertos pelo pipeline do MVP. Atendentes devem ser informados dessa limitação no treinamento de go-live.
- **Curadoria prévia da base:** NovaTech deve designar um responsável por área (Operações, Compliance, Comercial) para validar os documentos antes da ingestão inicial — especialmente para resolver qual versão do PROC-042 está vigente. Sem curadoria mínima, documentos contraditórios e o FAQ não-validado contaminam a base desde o primeiro dia.
- **Resolução de conflito PROC-042:** NovaTech deve definir, antes do go-live, qual versão do PROC-042 está vigente e registrar isso como metadado de vigência. O assistente pode alertar sobre o conflito, mas não pode resolver o problema de governança de documentos da empresa.

---

## Critérios de aceitação do produto

- [ ] Pipeline de ingestão processa com sucesso ao menos 1 documento de cada formato suportado (PDF, DOCX, HTML, XLSX) e os torna recuperáveis por busca semântica com pergunta relacionada ao conteúdo.
- [ ] Para ≥ 80% das perguntas do mapa de cobertura do Anexo B, os chunks corretos estão entre os N primeiros resultados recuperados (recall@N definido no techspec).
- [ ] Para as perguntas-armadilha do Anexo B — tier Platinum, carga perigosa, PROC-042 contraditório — o assistente responde corretamente em 100% dos testes (zero alucinações críticas pré go-live).
- [ ] Toda resposta gerada a partir de chunks contém citação explícita do documento de origem.
- [ ] Dado prompt com pergunta sobre carga perigosa, o assistente responde que carga perigosa (classes 1 a 6 da ANTT) NÃO pode ser devolvida — não inverte a exceção do POL-001, seção 3.2.
- [ ] Dado prompt com chunks de ambas as versões do PROC-042, a resposta do assistente apresenta os valores das duas versões e o alerta de divergência.
- [ ] Dado prompt com pergunta sobre cliente Platinum, o assistente declara que o tier não existe na documentação (SLA-2024 define apenas Gold, Silver e Standard).
- [ ] Quando nenhum chunk relevante for recuperado (abaixo do threshold configurado), o assistente declara ausência de informação e recomenda escalada ao supervisor — sem inventar resposta.
- [ ] O assistente está disponível no Microsoft Teams e responde em ≤ 10 segundos (P95) para perguntas do conjunto de teste.
- [ ] Documento novo/atualizado ingerido via pipeline está disponível para consulta em ≤ 24 horas após a execução do pipeline de ingestão.
- [ ] O system prompt está versionado no repositório com mapeamento explícito de partes estáticas e dinâmicas e estimativa de tamanho em tokens de cada parte documentada.
- [ ] O pipeline PoC roda em ambiente local com Python + ChromaDB + sentence-transformers sem dependência de serviço pago ou licença.

---

## Glossário

| Termo | Definição |
|-------|-----------|
| RAG | Retrieval-Augmented Generation — técnica em que o LLM gera respostas usando trechos recuperados de uma base de documentos, ancorando as afirmações em fontes verificáveis e reduzindo o risco de alucinação. |
| Chunk | Trecho de documento indexado no vector store para recuperação por similaridade. O tamanho e a estratégia de divisão em chunks afetam diretamente a qualidade das respostas — chunks que cortam tabelas ou procedimentos ao meio degradam a recuperação. |
| Embedding | Representação numérica vetorial de um texto que captura seu significado semântico. Permite comparar a similaridade entre a pergunta do atendente e os chunks indexados sem correspondência exata de palavras. |
| Vector store | Banco de dados otimizado para armazenar e consultar embeddings por similaridade. No PoC: ChromaDB (local, open-source). Em produção: Azure AI Search. |
| Context rot | Degradação da qualidade das respostas quando o contexto acumulado na conversa é muito longo — o LLM passa a ignorar informações fornecidas no início da sessão. Mitiga-se reiniciando o contexto após N turnos configurados. |
| Lost in the middle | Efeito pelo qual informações posicionadas no meio de um contexto longo são menos processadas pelo LLM do que informações no início ou no fim. Exige posicionamento estratégico dos chunks mais relevantes nas extremidades do prompt. |
| Alucinação | Resposta gerada pelo LLM que parece correta e confiante, mas não está fundamentada nos documentos-fonte — o modelo "inventa" fatos. Risco crítico em domínios como compliance e logística, onde respostas incorretas têm consequências operacionais. |
| System prompt | Conjunto de instruções estáticas enviadas ao LLM antes da pergunta do usuário, definindo identidade, regras de comportamento, formato de resposta e guardrails. Tratado como artefato de código — versionado e testado. |
| Orçamento de contexto | Quantidade máxima de tokens disponível por query após descontar o system prompt estático e metadados fixos. Define quantos chunks podem ser incluídos na resposta sem exceder a janela de contexto do modelo. |
| Guardrail | Restrição de comportamento do assistente. Pode ser probabilístico (implementado como instrução no system prompt — o modelo tenta seguir, mas pode falhar) ou determinístico (validado por filtro no código — sempre garantido). |
| Ingestão | Processo de extração de texto dos documentos-fonte, divisão em chunks, geração de embeddings e indexação no vector store. |
| Recall@N | Métrica de qualidade do pipeline de retrieval: proporção de perguntas para as quais os chunks corretos aparecem entre os N primeiros resultados recuperados. Meta: ≥ 80% das perguntas do Anexo B. |
| Threshold de similaridade | Score mínimo de similaridade que um chunk precisa ter em relação à pergunta para ser incluído no contexto. Chunks abaixo do threshold são descartados para evitar que conteúdo irrelevante contamine a resposta. |
