# Vizu Observability Bootstrap

Esta biblioteca centraliza e padroniza a configuração de observabilidade (Logs Estruturados e Tracing Distribuído) para todos os serviços FastAPI da Vizu.

## Propósito

O objetivo é garantir que, com uma única chamada de função, um novo serviço possa:

1.  Emitir logs em formato JSON, com campos `trace_id` e `span_id` automaticamente correlacionados.
2.  Enviar _traces_ de todas as suas requisições HTTP para o Google Cloud Trace.

Isso elimina a necessidade de configuração repetitiva e garante consistência em todo o nosso ecossistema de microserviços.

## Instalação

Dentro do `pyproject.toml` do seu serviço, adicione esta biblioteca como uma dependência de desenvolvimento local:

```toml
[tool.poetry.dependencies]
# ... outras dependências

vizu-observability-bootstrap = { path = "../../libs/vizu_observability_bootstrap", develop = true }
```
