Lib: `vizu_auth`

O que a lib faz
- Implementa autenticação/ autorização: API key strategies, JWT helpers, validação de clientes e quem pode executar ferramentas.

Observações técnicas
- Contém estratégias para header `X-API-KEY` e criação/validação de tokens.
- Foi identificado aviso de depreciação em Pydantic relacionado ao uso de classe `Config`.

Dependências
- pydantic (2.x)
- passlib / cryptography (se houver hashing)

Stack e versões
- Python 3.11+

Riscos / recomendações
- Risco: comportamento da autenticação impacta todo o sistema.
- Recomendações:
  - Migrar para `ConfigDict` em Pydantic para eliminar warnings futuros.
  - Adicionar testes de contrato de autenticação e rotear logs de falhas de autenticação com detalhes suficientes para auditoria.
