"""Bounded text-only provider adapter shared by prompt games and legacy agents."""
from typing import Optional
from functools import cached_property
import openai
import anthropic
from app.core.config import config


class LLMClient:
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.provider = provider or config.DEFAULT_LLM_PROVIDER
        self.model = model or config.DEFAULT_MODEL

    @cached_property
    def openai_client(self):
        return openai.OpenAI(api_key=config.OPENAI_API_KEY, timeout=45.0, max_retries=0) if config.OPENAI_API_KEY else None

    @cached_property
    def openai_async_client(self):
        return openai.AsyncOpenAI(api_key=config.OPENAI_API_KEY, timeout=45.0, max_retries=0) if config.OPENAI_API_KEY else None

    @cached_property
    def anthropic_client(self):
        return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, timeout=45.0, max_retries=0) if config.ANTHROPIC_API_KEY else None

    @cached_property
    def anthropic_async_client(self):
        return anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY, timeout=45.0, max_retries=0) if config.ANTHROPIC_API_KEY else None

    def close(self):
        for name in ("openai_client", "anthropic_client"):
            client = self.__dict__.get(name)
            if client is not None:
                client.close()

    def _params(self, system_prompt, messages, temperature, max_tokens):
        if self.provider == "openai":
            params = dict(model=self.model, messages=[{"role": "system", "content": system_prompt}] + messages,
                          temperature=temperature, max_completion_tokens=max_tokens)
            if self.model.startswith("gpt-6-luna"):
                params["reasoning_effort"] = "none"
            return params
        if self.provider == "anthropic":
            if not self.model.startswith("claude-"):
                raise ValueError("Set DEFAULT_MODEL to an available Claude model when using Anthropic")
            return dict(model=self.model, system=system_prompt, messages=messages,
                        temperature=temperature, max_tokens=max_tokens)
        raise ValueError("Unknown model provider")

    def call(self, system_prompt, user_message, temperature=0.7, max_tokens=500):
        return self.call_with_history(system_prompt, [{"role": "user", "content": user_message}], temperature, max_tokens)

    async def acall(self, system_prompt, user_message, temperature=0.7, max_tokens=500):
        return await self.acall_with_history(system_prompt, [{"role": "user", "content": user_message}], temperature, max_tokens)

    def call_with_history(self, system_prompt, messages, temperature=0.7, max_tokens=500):
        params = self._params(system_prompt, messages, temperature, max_tokens)
        if self.provider == "openai":
            if self.openai_client is None:
                raise ValueError("OpenAI API key not configured")
            response = self.openai_client.chat.completions.create(**params)
            return self._openai_text(response)
        if self.anthropic_client is None:
            raise ValueError("Anthropic API key not configured")
        response = self.anthropic_client.messages.create(**params)
        return self._anthropic_text(response)

    async def acall_with_history(self, system_prompt, messages, temperature=0.7, max_tokens=500):
        params = self._params(system_prompt, messages, temperature, max_tokens)
        if self.provider == "openai":
            if self.openai_async_client is None:
                raise ValueError("OpenAI API key not configured")
            response = await self.openai_async_client.chat.completions.create(**params)
            return self._openai_text(response)
        if self.anthropic_async_client is None:
            raise ValueError("Anthropic API key not configured")
        response = await self.anthropic_async_client.messages.create(**params)
        return self._anthropic_text(response)

    @staticmethod
    def _openai_text(response):
        choice = response.choices[0]
        if choice.finish_reason != "stop" or not choice.message.content:
            raise RuntimeError("Model did not return a complete text response")
        return choice.message.content

    @staticmethod
    def _anthropic_text(response):
        text = "".join(block.text for block in response.content if block.type == "text")
        if response.stop_reason != "end_turn" or not text:
            raise RuntimeError("Model did not return a complete text response")
        return text
