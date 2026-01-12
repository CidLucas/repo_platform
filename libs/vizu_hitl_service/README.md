# Vizu HITL Service

Serviço de Human-in-the-Loop para criação de datasets e controle de qualidade.

## Features

- **Avaliação de Critérios**: Decide automaticamente quais interações precisam de revisão humana
- **Fila Redis**: Gerenciamento eficiente de pendências com priorização
- **Configuração por Cliente**: Cada cliente pode ter seus próprios critérios

## Critérios Disponíveis

| Critério | Descrição | Params |
|----------|-----------|--------|
| `low_confidence` | Confiança da LLM abaixo do threshold | `threshold: float` |
| `elicitation_pending` | Elicitation em andamento | — |
| `tool_call_failed` | Ferramenta retornou erro | — |
| `keyword_trigger` | Palavras-chave detectadas | `keywords: List[str]` |
| `first_n_messages` | Primeiras N mensagens | `n: int` |
| `random_sample` | Amostragem aleatória | `rate: float (0-1)` |
| `manual_flag` | Marcação manual | — |
| `sentiment_negative` | Sentimento negativo | `patterns: List[str]` |
| `long_response_time` | Resposta demorada | `threshold_seconds: float` |

## Uso

```python
from vizu_hitl_service import HitlService, HitlQueue
from vizu_models import HitlConfig, HitlCriterion, HitlCriteriaType

# Configura a fila
queue = HitlQueue.from_url("redis://localhost:6379")

# Configura o serviço
config = HitlConfig(
    enabled=True,
    criteria=[
        HitlCriterion(
            type=HitlCriteriaType.LOW_CONFIDENCE,
            enabled=True,
            priority=10,
            params={"threshold": 0.7}
        ),
    ]
)
service = HitlService(queue, config)

# Avalia uma interação
decision = service.evaluate(
    user_message="Quero agendar um corte",
    agent_response="Claro! Para qual dia?",
    client_id=cliente_id,
    confidence_score=0.65,  # < 0.7 → vai para HITL
)

if decision.should_review:
    review = service.submit_for_review(
        decision=decision,
        user_message="...",
        agent_response="...",
        client_id=cliente_id,
        session_id="session-123",
    )
```

## Integração com Langfuse

O serviço pode salvar revisões aprovadas/corrigidas como dataset items no Langfuse:

```python
from langfuse import Langfuse

langfuse = Langfuse()

# Após revisão aprovada
dataset = langfuse.get_or_create_dataset("golden-set-studio-j")
dataset.create_item(
    input={"message": review.user_message},
    expected_output=review.corrected_response or review.agent_response,
    metadata={"criteria": review.criteria_triggered}
)
```
