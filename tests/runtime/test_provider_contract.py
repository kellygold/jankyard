from types import SimpleNamespace
from unittest.mock import Mock, patch
import pytest
from app.llm.client import LLMClient
from app.core.config import config


def test_current_model_parameters_and_provider_is_lazy(monkeypatch):
    monkeypatch.setattr(config, 'OPENAI_API_KEY', 'test-only-placeholder')
    with patch('app.llm.client.openai.OpenAI') as constructor, patch('app.llm.client.openai.AsyncOpenAI') as async_constructor:
        client = LLMClient(provider='openai', model='gpt-6-luna')
        constructor.assert_not_called()
        constructor.return_value.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(finish_reason='stop', message=SimpleNamespace(content='Hello'))])
        assert client.call('system', 'user', max_tokens=300) == 'Hello'
        params = constructor.return_value.chat.completions.create.call_args.kwargs
        assert params['max_completion_tokens'] == 300 and params['reasoning_effort'] == 'none'
        assert 'max_tokens' not in params
        assert constructor.call_args.kwargs['timeout'] == 45.0
        assert constructor.call_args.kwargs['max_retries'] == 0
        async_constructor.assert_not_called()
        client.close()
        constructor.return_value.close.assert_called_once()


def test_no_retired_anthropic_fallback():
    client = LLMClient(provider='anthropic', model='gpt-6-luna')
    with pytest.raises(ValueError, match='available Claude model'):
        client.call('system', 'user')


def test_stage_budget_blocks_second_paid_request_and_resets(monkeypatch):
    from app.llm.budget import stage_budget
    monkeypatch.setattr(config, 'OPENAI_API_KEY', 'test-only-placeholder')
    with patch('app.llm.client.openai.OpenAI') as constructor:
        constructor.return_value.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(finish_reason='stop', message=SimpleNamespace(content='Hello'))])
        client = LLMClient(provider='openai', model='gpt-6-luna')
        for _ in range(2):
            with stage_budget():
                client.call('system', 'user')
                with pytest.raises(RuntimeError, match='more than one'):
                    client.call('system', 'another')
        assert constructor.return_value.chat.completions.create.call_count == 2
        client.close()


@pytest.mark.parametrize('reason,content', [('length', 'JANKYARD-CANARY-7391'), ('content_filter', None), ('stop', None)])
def test_partial_or_filtered_provider_output_is_error(reason, content):
    response = SimpleNamespace(choices=[SimpleNamespace(finish_reason=reason, message=SimpleNamespace(content=content))])
    with pytest.raises(RuntimeError):
        LLMClient._openai_text(response)
