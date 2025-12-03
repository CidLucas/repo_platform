Lib: `vizu_models`

O que a lib faz
- Tipos de domínio compartilhados (pydantic/SQLModel) usados por serviços e libs.

Observações técnicas
- Fonte de verdade para DTOs entre serviços; alterações devem considerar compatibilidade retroativa.

Dependências
- pydantic (v2.x recomendado)
- typing_extensions quando necessário

Stack e versões
- Python 3.11+
- pydantic 2.x — rever uso de `Config` vs `ConfigDict` para evitar deprecations.

Riscos / recomendações
- Risco: mudanças em modelos podem quebrar serviços consumidores.
- Recomendações:
  - Adotar versionamento semântico para mudanças breaking e publicar changelogs.
  - Cobrir modelos com testes de serialização/deserialização.
