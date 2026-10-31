"""
Base challenge interface for Jankyard.ai

All challenges must inherit from BaseChallenge and implement the required methods.
This provides a generic interface for the sandbox runner to interact with any challenge.

Supports both single-agent and multi-agent challenges with automatic detection.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple, Optional, AsyncGenerator, TYPE_CHECKING
from enum import Enum
import html
import json

# Avoid circular imports
if TYPE_CHECKING:
    from app.challenges.agents import Agent, ConversationTurn


def sanitize_for_sse(data: Any) -> Any:
    """
    Recursively sanitize data for SSE transmission to prevent XSS.
    Escapes HTML in all string values.
    """
    if isinstance(data, str):
        return html.escape(data)
    elif isinstance(data, dict):
        return {k: sanitize_for_sse(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_for_sse(item) for item in data]
    else:
        return data


def sse_event(event_data: Dict[str, Any]) -> str:
    """
    Create a sanitized SSE event string.
    All string values are HTML-escaped to prevent XSS.
    """
    sanitized = sanitize_for_sse(event_data)
    return f"data: {json.dumps(sanitized)}\n\n"


class ChallengeStatus(Enum):
    """Status of a challenge run"""
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class ChallengeResult:
    """Result of a challenge run"""
    status: ChallengeStatus
    score: int
    steps: int
    success: bool
    logs: List[Dict[str, Any]]
    replay_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


@dataclass
class StepResult:
    """Result of a single step in the challenge"""
    observation: Dict[str, Any]
    reward: int
    done: bool
    info: Dict[str, Any]


class BaseChallenge(ABC):
    """
    Abstract base class for all Jankyard challenges.
    
    Supports both single-agent and multi-agent patterns:
    - Single-agent: Just implement reset() and step()
    - Multi-agent: Add agents dict and conversation_flow()
    
    The system auto-detects which pattern you're using.
    """
    
    # Multi-agent support (override in subclass if needed)
    agents: Dict[str, 'Agent'] = {}  # Empty = single-agent challenge
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the challenge.
        
        Args:
            config: Optional configuration dictionary for the challenge
        """
        self.config = config or {}
        self.current_step = 0
        self.total_score = 0
        self.logs: List[Dict[str, Any]] = []
        self.replay_data: List[Dict[str, Any]] = []
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the challenge"""
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for the challenge"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the challenge is about"""
        pass
    
    @property
    @abstractmethod
    def max_steps(self) -> int:
        """Maximum number of steps allowed"""
        pass
    
    @property
    @abstractmethod
    def allowed_actions(self) -> List[str]:
        """List of valid action strings for this challenge"""
        pass
    
    @property
    def hidden(self) -> bool:
        """Whether this challenge is hidden from the UI (default: False)"""
        return False
    
    @property
    def challenge_type(self) -> str:
        """
        Type of challenge for routing/streaming (debate, attack, code, etc.)
        Override in subclasses if needed
        """
        return "generic"
    
    @property
    def supports_streaming(self) -> bool:
        """
        Whether this challenge supports SSE streaming
        Override in subclasses that support streaming
        """
        return False
    
    @property
    def template_name(self) -> Optional[str]:
        """
        Custom template name for this challenge, or None for default
        Override in subclasses if needed
        """
        return None
    
    @abstractmethod
    def reset(self) -> Dict[str, Any]:
        """
        Reset the challenge to initial state.
        
        Returns:
            Initial observation dictionary
        """
        pass
    
    @abstractmethod
    def step(self, action: str) -> StepResult:
        """
        Execute one step of the challenge with the given action.
        
        Args:
            action: The action string chosen by the agent
            
        Returns:
            StepResult containing observation, reward, done flag, and info
        """
        pass
    
    @abstractmethod
    def render(self) -> str:
        """
        Render the current state as a string (for visualization).
        
        Returns:
            String representation of current state
        """
        pass
    
    def validate_action(self, action: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if an action is allowed.
        
        Args:
            action: The action string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if action not in self.allowed_actions:
            return False, f"Invalid action '{action}'. Allowed: {self.allowed_actions}"
        return True, None
    
    def log_step(self, action: str, result: StepResult):
        """
        Log a step for later review.
        
        Args:
            action: The action taken
            result: The result of the step
        """
        log_entry = {
            "step": self.current_step,
            "action": action,
            "observation": result.observation,
            "reward": result.reward,
            "done": result.done,
            "info": result.info,
            "render": self.render()
        }
        self.logs.append(log_entry)
        self.replay_data.append({
            "step": self.current_step,
            "state": self.get_state_snapshot()
        })
    
    def get_state_snapshot(self) -> Dict[str, Any]:
        """
        Get a snapshot of the current state for replay.
        Override this to customize what gets saved for replay.
        
        Returns:
            Dictionary containing state information
        """
        return {
            "step": self.current_step,
            "score": self.total_score
        }
    
    def get_result(self, status: ChallengeStatus, error_message: Optional[str] = None) -> ChallengeResult:
        """
        Package the final result of the challenge run.
        
        Args:
            status: Final status of the run
            error_message: Optional error message if status is ERROR
            
        Returns:
            ChallengeResult object
        """
        success = status == ChallengeStatus.SUCCESS
        
        return ChallengeResult(
            status=status,
            score=self.total_score,
            steps=self.current_step,
            success=success,
            logs=self.logs,
            replay_data={"frames": self.replay_data},
            error_message=error_message
        )
    
    def get_agent_template(self) -> str:
        """
        Return a template agent.py file for this challenge.
        Override to provide challenge-specific examples.
        
        Returns:
            String containing template Python code
        """
        return f'''"""
Agent template for {self.display_name}

Implement the act() function below.
"""

def act(observation, memory):
    """
    Make a decision based on the current observation.
    
    Args:
        observation: dict containing current state information
        memory: dict that persists between steps (you can store anything here)
    
    Returns:
        tuple of (action: str, new_memory: dict)
    
    Allowed actions: {self.allowed_actions}
    """
    # Your agent logic here
    action = "{self.allowed_actions[0]}"
    
    return action, memory
'''
    

    # ===== Multi-Agent Support =====

    async def conversation_flow(
        self,
        user_input: str,
        context: Dict[str, Any]
    ) -> AsyncGenerator['ConversationTurn', None]:
        """
        OPTIONAL: Define conversation flow for multi-agent challenges.
        
        Override this method to create multi-agent challenges.
        Yield ConversationTurn objects to define the conversation.
        
        Args:
            user_input: Initial input from the user
            context: Optional context dictionary
            
        Yields:
            ConversationTurn objects defining the conversation
            
        Example:
            async def conversation_flow(self, user_input, context):
                # User speaks
                yield ConversationTurn(
                    agent='user',
                    message=user_input,
                    type='message'
                )
                
                # Junior thinks
                yield ConversationTurn(agent='junior', type='thinking')
                
                # Junior responds
                response = await self.call_agent('junior', user_input)
                yield ConversationTurn(
                    agent='junior',
                    message=response,
                    type='message'
                )
        """
        raise NotImplementedError(
            "Multi-agent challenges must implement conversation_flow(). "
            "See MULTI_AGENT_PLAN.md for examples."
        )
        # Make this a generator
        yield  # pragma: no cover

    async def call_agent(
        self,
        agent_name: str,
        message: str,
        context: Dict[str, Any] = None
    ) -> str:
        """
        Helper to call an agent and get its response.
        Available to all multi-agent challenges.
        
        Args:
            agent_name: Name of the agent (must be in self.agents)
            message: Message/prompt for the agent
            context: Optional context dictionary
            
        Returns:
            Agent's response as string
            
        Raises:
            ValueError: If agent_name not found in self.agents
            AttributeError: If LLM client not available
        """
        if agent_name not in self.agents:
            raise ValueError(
                f"Agent '{agent_name}' not found. "
                f"Available agents: {list(self.agents.keys())}"
            )
        
        # Get LLM client (must be set by challenge)
        if not hasattr(self, 'llm_client'):
            raise AttributeError(
                f"Challenge must have 'llm_client' attribute for multi-agent support. "
                f"Add 'self.llm_client = LLMClient()' in __init__."
            )
        
        agent = self.agents[agent_name]
        
        # Call LLM with agent's configuration
        from app.llm.client import LLMClient
        client = LLMClient(model=agent.model) if agent.model else self.llm_client
        response = client.call(
            system_prompt=agent.system_prompt,
            user_message=message,
            temperature=agent.temperature,
            max_tokens=agent.max_tokens
        )
        
        return response
    
    # ===== Streaming =====
    
    async def stream_events(
        self,
        user_action: str,
        llm_client=None
    ):
        """
        Generic streaming implementation with AUTOMATIC pattern detection.
        
        Auto-detects single-agent vs multi-agent:
        - Has agents + conversation_flow → Multi-agent (uses orchestrator)
        - No agents → Single-agent (uses simple streaming)
        
        Override only if you need custom streaming logic.
        
        Args:
            user_action: The action/input from the user
            llm_client: Optional LLM client for AI interactions
            
        Yields:
            JSON-formatted SSE events in standardized format
        """
        import json
        import asyncio
        import logging
        logger = logging.getLogger(__name__)
        
        # Check if this is a multi-agent challenge
        is_multi_agent = (
            self.agents and 
            len(self.agents) > 0 and
            hasattr(self, 'conversation_flow')
        )
        
        if is_multi_agent:
            # Multi-agent: Use orchestrator
            from app.challenges.orchestrator import run_conversation
            
            try:
                async for event in run_conversation(
                    self.conversation_flow(user_action, {}),
                    self.agents,
                    llm_client or getattr(self, 'llm_client', None)
                ):
                    yield event
                    if json.loads(event.removeprefix('data: ').strip()).get('type') == 'error':
                        return
                
                # Automatically send complete event after conversation ends
                # This enables level unlocking and modal display
                status = ChallengeStatus.SUCCESS if getattr(self, 'user_won', False) is True else ChallengeStatus.FAILURE
                result = self.get_result(status)
                complete_event = {
                    'type': 'complete',
                    'agent': 'system',
                    'data': {
                        'result': {
                            'status': result.status.value,
                            'score': result.score,
                            'steps': result.steps,
                            'success': result.success,
                            'logs': result.logs
                        }
                    },
                    'metadata': {}
                }
                yield sse_event(complete_event)
                return  # Multi-agent conversation complete, don't fall through
            except NotImplementedError:
                # conversation_flow not implemented, fall back to single-agent
                pass
        
        # Single-agent: Use simple streaming (existing logic)
        # Send initial state
        observation = self.reset()
        event = {
            'type': 'update',
            'agent': 'system',
            'data': {
                'observation': observation,
                'score': self.total_score
            },
            'metadata': {'step': self.current_step}
        }
        yield sse_event(event)
        await asyncio.sleep(0.1)
        
        # System thinking indicator
        event = {
            'type': 'thinking',
            'agent': 'system',
            'data': {'message': 'Processing your action...'},
            'metadata': {}
        }
        yield sse_event(event)
        await asyncio.sleep(0.3)
        
        # Execute step
        try:
            step_result = self.step(user_action)
            self.current_step += 1
            self.total_score += step_result.reward
            
            # Send update event with result
            event = {
                'type': 'update',
                'agent': 'system',
                'data': {
                    'observation': step_result.observation,
                    'reward': step_result.reward,
                    'score': self.total_score,
                    'done': step_result.done
                },
                'metadata': {'step': self.current_step}
            }
            yield sse_event(event)
            
            # Check if challenge is complete
            if step_result.done:
                status = ChallengeStatus.SUCCESS if step_result.info.get('success') is True else ChallengeStatus.FAILURE
                result = self.get_result(status)
                
                event = {
                    'type': 'complete',
                    'agent': 'system',
                    'data': {
                        'success': result.success,
                        'score': result.score,
                        'steps': result.steps,
                        'status': result.status.value,
                        'message': step_result.observation.get('message', 'Challenge complete!'),
                        'result': {
                            'success': result.success,
                            'score': result.score,
                            'steps': result.steps,
                            'status': result.status.value,
                            'logs': result.logs
                        }
                    },
                    'metadata': {}
                }
                yield sse_event(event)
        
        except Exception as e:
            event = {
                'type': 'error',
                'agent': 'system',
                'data': {'message': f'Error processing action: {str(e)}'},
                'metadata': {}
            }
            yield sse_event(event)


# Compatibility import: every consumer shares one registry.
from app.challenges.registry import ChallengeRegistry
