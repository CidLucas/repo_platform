# Variacoes: PoC SQL Skill

## Baseline
- **System prompt:** prompt atual de producao (atendente/default)
- **Modelo:** deepseek-v4-flash (Ollama Cloud)
- **Eixo:** —
- **Caracteristica:** prompt atual, sem modificacoes

## v1-fewshot
- **System prompt:** adiciona 3 exemplos few-shot de perguntas e respostas SQL
- **Modelo:** deepseek-v4-flash (Ollama Cloud)
- **Eixo:** Structure (few-shot)
- **Hipotese:** exemplos concretos reduzem ambiguidade na geracao do SQL, aumentando a taxa de acerto em perguntas similares
- **Risco:** pode aumentar tokens em ~500 por request; exemplos podem viesar para os padroes mostrados

## v2-cot
- **System prompt:** chain-of-thought explicito com 6 passos de raciocinio (identificar dado, filtros, agregacao, ordenacao, montar pergunta, chamar ferramenta)
- **Modelo:** deepseek-v4-flash (Ollama Cloud)
- **Eixo:** Structure (chain-of-thought)
- **Hipotese:** raciocinio estruturado reduz erros em perguntas complexas com multiplos filtros e agregacoes
- **Risco:** aumenta significativamente tokens e latencia; pode gerar SQL prolixo em perguntas simples

## v3-anthropic
- **System prompt:** mesmo prompt da baseline
- **Modelo:** claude-sonnet-4-6 (Anthropic API)
- **Eixo:** Modelo
- **Hipotese:** Claude Sonnet pode ter melhor compreensao semantica para SQL, especialmente em perguntas ambiguas
- **Risco:** custo muito maior (~$3/1M input vs ~$0.15 do DeepSeek); latencia pode ser maior

---

## Matriz de Variacao

| Variacao | Verbosity | Structure | Tone | Constraints | Modelo |
|:---------|:---------:|:---------:|:----:|:-----------:|:------:|
| baseline | default | flat | formal | medias | DeepSeek |
| v1-fewshot | default | **few-shot** | formal | medias | DeepSeek |
| v2-cot | **verbose** | **chain-of-thought** | formal | **explicitas** | DeepSeek |
| v3-anthropic | default | flat | formal | medias | **Claude** |
