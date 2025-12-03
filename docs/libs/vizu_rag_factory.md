Lib: `vizu_rag_factory`

O que a lib faz
- Cria runnables RAG (retrieval-augmented generation) para serviços que precisam buscar contextos em vectorstores como Qdrant.
- Encapsula a configuração do vectorstore, embeddings, e prompt templates.

Observações técnicas
- Integra com `vizu_qdrant_client` para acesso ao vetor store.
- Fornece camadas de cache e controlos de tamanho de contexto.

Dependências
- qdrant-client
- embeddings provider (local/remote)
- langchain components (retriever, prompt templates)

Stack e versões
- Python 3.11+
- qdrant-client versão compatível com o cluster Qdrant (ver lockfile)

Riscos / recomendações
- Risco: mudanças na API de Qdrant podem quebrar indexação/retrieval.
- Recomendações:
  - Testes de integração que validem embedding -> indexação -> recuperação.
  - Monitoramento de latência de queries e taxa de recall.
