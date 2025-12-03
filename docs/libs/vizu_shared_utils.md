Lib: `vizu_shared_utils`

O que a lib faz
- Coleção de utilitários compartilhados: helpers de logging, transformação, serialização, e wrappers pequenos usados por serviços.

Observações técnicas
- Deve permanecer pequena e sem dependências pesadas; utilitários amplamente utilizados devem ser estáveis.

Dependências
- standard library, pequenas libs utilitárias (pydantic, typing)

Stack e versões
- Python 3.11+

Riscos / recomendações
- Risco: mudanças breaking aqui afetam muitos serviços.
- Recomendações:
  - Manter compatibilidade retroativa e usar semver quando publicar mudanças.
  - Centralizar exemplos de uso e testes unitários.
