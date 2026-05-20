import pytest

from blu_agent_framework.utils.llm_parse import parse_first_json


class DummyLLM:
    def __init__(self, text):
        self.text = text

    async def ainvoke(self, *args, **kwargs):
        return self.text


async def run_parse_integration(fake_text: str):
    # Simulate the orchestrator calling the LLM and then parsing
    from blu_agent_framework.utils.llm_parse import parse_first_json

    parsed = parse_first_json(fake_text)
    return parsed


@pytest.mark.asyncio
async def test_orchestrator_parse_valid_json():
    text = 'Assistant: ```json\n{"action": "plan", "steps": []}\n```'
    parsed = await run_parse_integration(text)
    assert parsed == {"action": "plan", "steps": []}


@pytest.mark.asyncio
async def test_orchestrator_parse_no_json():
    text = 'Assistant: I can\'t provide that.'
    parsed = await run_parse_integration(text)
    assert parsed is None
