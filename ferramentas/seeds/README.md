# Seeds - Dados de Desenvolvimento

Esta pasta centraliza todos os dados de seed para desenvolvimento e testes.

## Estrutura

```
ferramentas/seeds/
├── README.md           # Este arquivo
├── clients.py          # Definições de clientes de teste (personas)
├── knowledge/          # Dados de conhecimento RAG por cliente
│   ├── studio_j.json
│   ├── oficina_mendes.json
│   ├── dra_beatriz.json
│   ├── casa_alma.json
│   ├── pixel_store.json
│   ├── brasa_malte.json
│   └── marcos_eletricista.json
└── run_seeds.py        # Script unificado de execução
```

## Uso

```bash
# Via Makefile (recomendado)
make seed              # Executa todos os seeds (DB + Qdrant)
make seed-db           # Apenas clientes no banco
make seed-qdrant       # Apenas dados RAG no Qdrant
make seed-check        # Verifica estado atual

# Diretamente (desenvolvimento)
python -m ferramentas.seeds.run_seeds --all
python -m ferramentas.seeds.run_seeds --db-only
python -m ferramentas.seeds.run_seeds --qdrant-only
```

## Adicionando Novos Clientes

1. Adicione a persona em `clients.py` seguindo o modelo existente
2. Crie o arquivo de conhecimento em `knowledge/<nome_collection>.json`
3. Execute `make seed` para aplicar

## Formato do Conhecimento (JSON)

```json
{
  "collection": "nome_collection",
  "documents": [
    {
      "doc_id": "identificador_unico",
      "title": "Título do documento",
      "content": "Conteúdo completo do conhecimento..."
    }
  ]
}
```
