# Ferramentas - Vizu Development Toolbox

Este diretório centraliza todas as ferramentas de desenvolvimento, testes, seeds e avaliação do projeto Vizu.

## 📁 Estrutura

```
ferramentas/
├── seeds/                    # Dados de desenvolvimento
│   ├── clients.py               # Definições de personas/clientes
│   ├── knowledge/               # Arquivos JSON de conhecimento RAG
│   ├── run_seeds.py             # Script para popular DB + Qdrant
│   └── README.md                # Documentação dos seeds
├── debug.py                  # Scripts de debug e troubleshooting
├── test_personas_batch.py    # Teste em lote das personas
├── test_google_tools.py      # Testes das ferramentas Google
├── oauth_e2e_test.py         # Testes E2E de OAuth
├── batch_requests.py         # Scripts de batch requests
├── batch_results.csv         # Resultados de testes
├── mensagens_teste.csv       # Dados de teste
├── test_single.csv           # Testes unitários
├── avaliador_old/            # Versão antiga do avaliador
├── crawler/                  # Ferramentas de crawling
├── evaluation_suite/         # Suite de avaliação (Streamlit)
└── spec-kit-generator/       # Gerador de kits de especificação
```

## 🎯 Filosofia

Este diretório serve como uma "caixa de ferramentas" centralizada para desenvolvimento:

- **Seeds**: Dados de desenvolvimento (clientes, conhecimento RAG)
- **Testes**: Scripts de teste, avaliação e validação
- **Debug**: Ferramentas de troubleshooting e análise
- **Avaliação**: Suites para medir qualidade e performance

## 🚀 Como Usar

### Seeds (Dados de Desenvolvimento)

```bash
# Popular banco de dados com clientes de teste
make seed-db

# Popular Qdrant com conhecimento RAG
make seed-qdrant

# Fazer tudo de uma vez
make seed

# Verificar estado atual
make seed-check
```

### Testes

```bash
# Teste em lote das personas (15 mensagens)
make batch-run

# Ou executar diretamente:
python ferramentas/test_personas_batch.py
```

### Debug

```bash
# Scripts de debug
python ferramentas/debug.py
```

## 📋 Convenções

- Scripts Python devem ter shebang e docstring
- Dados de teste ficam em CSV/JSON no diretório raiz
- Seeds são organizados por tipo (clients, knowledge)
- Ferramentas devem ser executáveis via `make` quando possível

## 🔒 Segurança

- Nunca incluir dados reais de produção
- Usar apenas dados fictícios/sintéticos
- Seeds devem ser seguros para rodar em qualquer ambiente
