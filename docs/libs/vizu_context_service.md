Lib: `vizu_context_service`

O que a lib faz
- Provê abstrações para contexto de sessão, injeção de `_internal_context`, helpers para recuperar `cliente_id` seguro, e integração com o mecanismo de execução (LangGraph supervisor).

Observações técnicas
- Responsável por fornecer contexto de execução para nós que chamam ferramentas — por isso é crítico para segurança.

Dependências
- redis / langgraph saver
- libs internas (vizu_auth) para validação de identidades

Stack e versões
- Python 3.11+

Riscos / recomendações
- Risco: bugs aqui podem permitir bypass de autorização.
- Recomendações:
  - Cobrir com testes que simulam requests malformadas/forjadas.
  - Fazer revisão de segurança das APIs que retornam `cliente_id`.
