Lib: `vizu_qdrant_client`

O que a lib faz
- Cliente utilitário para comunicação com Qdrant (indexação, busca vetorial, gerenciamento de collections).

Observações técnicas
- Encapsula criação de coleções, políticas de upsert e mapping de metadados.

Dependências
- qdrant-client

Stack e versões
- Qdrant (versão compatível com o cluster usado em dev); verificar `docker-compose` para versão exata.

Riscos / recomendações
- Risco: mudanças em esquema de metadados podem invalidar buscas existentes.
- Recomendações:
  - Persistir versão do mapping em metadados de collections.
  - Monitorar e alertar para falhas de indexação.
