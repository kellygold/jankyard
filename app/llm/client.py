"""
LLM Client Wrapper

Provides unified interface for calling different LLM providers.
Supports both sync and async methods for flexibility.
"""
from typing import Optional, Dict, Any, List
import openai
import anthropic
from app.core.config import config


class LLMClient:
    """Unified client for LLM API calls (sync and async)"""
    
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize LLM client
        
        Args:
            provider: 'openai' or 'anthropic', defaults to config
            model: Model name, defaults to config
        """
        self.provider = provider or config.DEFAULT_LLM_PROVIDER
        self.model = model or config.DEFAULT_MODEL
        
        # Initialize sync clients
        if config.OPENAI_API_KEY:
            self.openai_client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
            self.openai_async_client = openai.AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        else:
            self.openai_client = None
            self.openai_async_client = None
            
        if config.ANTHROPIC_API_KEY:
            self.anthropic_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
            self.anthropic_async_client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
        else:
            self.anthropic_client = None
            self.anthropic_async_client = None
    
    def call(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        """
        Call LLM with system prompt and user message
        
        Args:
            system_prompt: System instructions for the LLM
            user_message: User message/prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Max tokens in response
            
        Returns:
            LLM response as string
        """
        if self.provider == "openai":
            return self._call_openai(system_prompt, user_message, temperature, max_tokens)
        elif self.provider == "anthropic":
            return self._call_anthropic(system_prompt, user_message, temperature, max_tokens)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def _call_openai(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Call OpenAI API"""
        if not self.openai_client:
            raise ValueError("OpenAI API key not configured")
        
        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {str(e)}")
    
    def _call_anthropic(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Call Anthropic API"""
        if not self.anthropic_client:
            raise ValueError("Anthropic API key not configured")
        
        try:
            response = self.anthropic_client.messages.create(
                model=self.model if self.model.startswith("claude") else "claude-3-haiku-20240307",
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.content[0].text
        except Exception as e:
            raise RuntimeError(f"Anthropic API error: {str(e)}")
    
    # =========================================================================
    # ASYNC METHODS
    # =========================================================================
    
    async def acall(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        """
        Async version of call() - use in async contexts for better performance.
        """
        if self.provider == "openai":
            return await self._acall_openai(system_prompt, user_message, temperature, max_tokens)
        elif self.provider == "anthropic":
            return await self._acall_anthropic(system_prompt, user_message, temperature, max_tokens)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    async def _acall_openai(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Async call to OpenAI API"""
        if not self.openai_async_client:
            raise ValueError("OpenAI API key not configured")
        
        try:
            response = await self.openai_async_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {str(e)}")
    
    async def _acall_anthropic(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Async call to Anthropic API"""
        if not self.anthropic_async_client:
            raise ValueError("Anthropic API key not configured")
        
        try:
            response = await self.anthropic_async_client.messages.create(
                model=self.model if self.model.startswith("claude") else "claude-3-haiku-20240307",
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.content[0].text
        except Exception as e:
            raise RuntimeError(f"Anthropic API error: {str(e)}")
    
    async def acall_with_history(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        """Async version of call_with_history()"""
        if self.provider == "openai":
            if not self.openai_async_client:
                raise ValueError("OpenAI API key not configured")
            
            response = await self.openai_async_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system_prompt}] + messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
            
        elif self.provider == "anthropic":
            if not self.anthropic_async_client:
                raise ValueError("Anthropic API key not configured")
            
            response = await self.anthropic_async_client.messages.create(
                model=self.model if self.model.startswith("claude") else "claude-3-haiku-20240307",
                system=system_prompt,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.content[0].text
    
    def call_with_history(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        """
        Call LLM with conversation history
        
        Args:
            system_prompt: System instructions
            messages: List of {"role": "user"/"assistant", "content": "..."}
            temperature: Sampling temperature
            max_tokens: Max tokens in response
            
        Returns:
            LLM response
        """
        if self.provider == "openai":
            if not self.openai_client:
                raise ValueError("OpenAI API key not configured")
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system_prompt}] + messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
            
        elif self.provider == "anthropic":
            if not self.anthropic_client:
                raise ValueError("Anthropic API key not configured")
            
            response = self.anthropic_client.messages.create(
                model=self.model if self.model.startswith("claude") else "claude-3-haiku-20240307",
                system=system_prompt,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.content[0].text
