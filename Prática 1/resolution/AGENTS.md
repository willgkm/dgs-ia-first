# Skills → ações

Consulte o `SKILL.md` em `.agents/skills/<nome>/` antes de implementar ou revisar.

| Skill                           | Acionar para…                                                                                                                                          | Não usar se…                                                                    |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------- |
| `code-standards-en`             | Nomes em inglês, PR, CQS, early return, tamanho de métodos/classes                                                                                     | Política exige identificadores localizados                                      |
| `repo-folder-structure`         | Onde criar `features`, pages, controllers/services/data                                                                                                | Layout do monorepo ou framework diferente do template                           |
                                     |

**Ordem sugerida por tarefa:** backend HTTP → `express-rest-http`, depois `repo-folder-structure`, `nodejs-typescript-conventions`, `code-standards-en`. Frontend → `ui-ux-pro-max` (design/UX e sistema visual), depois `react-frontend-conventions`, `repo-folder-structure`, `nodejs-typescript-conventions`, `code-standards-en`. Testes → `vitest-testing` + skill da camada testada.

# Persistência do Modo Plano

<plan_file>`.codex/plans/[timestamp]-[plan-slug].md`</plan_file>

- **OBRIGATÓRIO ABSOLUTO**: No modo Plano, após o usuário aceitar um plano, **SEMPRE** escreva o plano aceito em um arquivo Markdown dentro de <plan_file>.
- **OBRIGATÓRIO**: Se o plano aceito for atualizado posteriormente, atualize ou adicione o respectivo arquivo Markdown em <plan_file>.

# DESIGN.md

- Toda a UI que você trabalhar, você sempre tem que seguir o ./DESIGN.md completamente
- Leia sempre o DESIGN.md antes de começar tanto planejamento quanto execução de tarefas de UI
