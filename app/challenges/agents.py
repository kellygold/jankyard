"""
Agent Infrastructure for Multi-Agent Challenges

Provides standard models for defining AI agents and conversation turns
in multi-agent challenges.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class Agent:
    """
    Represents an AI agent in a multi-agent challenge.
    
    Example:
        junior_dev = Agent(
            name='junior',
            role='Junior Developer',
            system_prompt='You are an enthusiastic junior developer...',
            model='gpt-4',
            temperature=0.8
        )
    """
    name: str
    """Unique identifier for this agent (e.g., 'junior', 'manager', 'judge')"""
    
    role: str
    """Human-readable role description (e.g., 'Junior Developer')"""
    
    system_prompt: str
    """System prompt that defines the agent's personality and behavior"""
    
    model: str = 'gpt-4'
    """LLM model to use for this agent (e.g., 'gpt-4', 'gpt-4o', 'gpt-3.5-turbo')"""
    
    temperature: float = 0.7
    """Sampling temperature (0.0 = deterministic, 1.0 = creative)"""
    
    max_tokens: int = 200
    """Maximum tokens in agent's response"""
    
    def __post_init__(self):
        """Validate agent configuration"""
        if not self.name:
            raise ValueError("Agent name cannot be empty")
        if not self.system_prompt:
            raise ValueError(f"Agent '{self.name}' must have a system_prompt")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(f"Agent '{self.name}' temperature must be between 0.0 and 2.0")
        if self.max_tokens < 1:
            raise ValueError(f"Agent '{self.name}' max_tokens must be positive")


@dataclass
class ConversationTurn:
    """
    Represents a single turn in a multi-agent conversation.
    
    Used by challenges to define conversation flow. The orchestrator
    converts these into standardized SSE events.
    
    Example usage:
        # User speaks
        yield ConversationTurn(
            agent='user',
            message='I have a great idea for a new feature',
            type='message'
        )
        
        # Agent thinks
        yield ConversationTurn(
            agent='junior',
            type='thinking'
        )
        
        # Agent responds
        response = await self.call_agent('junior', user_message)
        yield ConversationTurn(
            agent='junior',
            message=response,
            type='message',
            metadata={'approved': True}
        )
    """
    agent: str
    """Name of the agent performing this turn (matches Agent.name)"""
    
    message: str = ''
    """
    Message content for this turn.
    Empty for 'thinking' events, populated for 'message' and 'judgment' events.
    """
    
    type: str = 'message'
    """
    Type of turn:
    - 'thinking': Agent is processing (shows loading indicator)
    - 'message': Agent sends a message
    - 'judgment': Agent provides evaluation/scoring
    - 'update': System state update
    """
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """
    Optional metadata for this turn.
    Examples:
    - {'round': 2, 'approved': True}
    - {'score': 85, 'confidence': 0.9}
    - {'step': 3, 'tokens_used': 150}
    """
    
    def __post_init__(self):
        """Validate turn configuration"""
        valid_types = ['thinking', 'message', 'judgment', 'update', 'complete', 'error', 'attack', 'response', 'summary']
        if self.type not in valid_types:
            raise ValueError(f"Turn type must be one of {valid_types}, got '{self.type}'")
        
        if self.type in ['message', 'judgment', 'attack', 'response', 'summary'] and not self.message:
            raise ValueError(f"Turn type '{self.type}' requires a message")
    
    def to_sse_event(self) -> Dict[str, Any]:
        """
        Convert this turn into a standardized SSE event.
        
        Returns:
            Dictionary in standardized event format:
            {
                'type': str,
                'agent': str,
                'data': dict,
                'metadata': dict
            }
        """
        event = {
            'type': self.type,
            'agent': self.agent,
            'data': {},
            'metadata': self.metadata
        }
        
        # Add message content if present
        if self.message:
            event['data']['message'] = self.message
            # For backward compatibility with some frontends
            if self.type == 'message':
                event['data']['content'] = self.message
        
        return event


# Type alias for conversation flow generators
ConversationFlow = Any  # Actually AsyncGenerator[ConversationTurn, None] but avoiding circular import
