"""
Generic Conversation Orchestrator for Multi-Agent Challenges

Runs any multi-agent conversation by consuming ConversationTurn objects
and yielding standardized SSE events. Contributors never write streaming code!
"""
import json
import asyncio
from typing import AsyncGenerator, Dict
from app.challenges.agents import Agent, ConversationTurn
from app.challenges.base import sse_event
from app.llm.client import LLMClient


async def run_conversation(
    conversation_flow: AsyncGenerator[ConversationTurn, None],
    agents: Dict[str, Agent],
    llm_client: LLMClient
) -> AsyncGenerator[str, None]:
    """
    Generic orchestrator for ANY multi-agent conversation.
    
    This is the magic that makes multi-agent challenges work with 2 files!
    Contributors just yield ConversationTurn objects, this handles the rest.
    
    Args:
        conversation_flow: Async generator yielding ConversationTurn objects
        agents: Dictionary mapping agent names to Agent objects
        llm_client: LLM client for making API calls
        
    Yields:
        JSON-formatted SSE events in standardized format
        
    Example:
        async def my_conversation_flow(user_input, context):
            # User speaks
            yield ConversationTurn(agent='user', message=user_input, type='message')
            
            # Junior thinks
            yield ConversationTurn(agent='junior', type='thinking')
            
            # Junior responds
            response = await call_agent('junior', user_input)
            yield ConversationTurn(agent='junior', message=response, type='message')
        
        # Orchestrator handles all the streaming!
        async for event in run_conversation(
            my_conversation_flow(user_input, {}),
            agents,
            llm_client
        ):
            yield event
    """
    try:
        # Iterate through conversation turns
        async for turn in conversation_flow:
            # Validate turn has agent
            if not turn.agent:
                raise ValueError("ConversationTurn must have an agent")
            
            # Convert turn to SSE event
            event = turn.to_sse_event()
            
            # Yield the event
            yield sse_event(event)
            
            # Small delay for better UX (allows frontend to process)
            if turn.type == 'thinking':
                await asyncio.sleep(0.5)  # Thinking indicators show longer
            else:
                await asyncio.sleep(0.1)  # Quick delay for other events
                
    except StopAsyncIteration:
        # Conversation ended naturally
        pass
        
    except Exception as e:
        # Error in conversation flow
        error_event = {
            'type': 'error',
            'agent': 'system',
            'data': {
                'message': f'Error in conversation: {str(e)}'
            },
            'metadata': {}
        }
        yield sse_event(error_event)


async def run_conversation_with_llm(
    conversation_flow_func,
    agents: Dict[str, Agent],
    llm_client: LLMClient,
    user_input: str,
    context: Dict = None
) -> AsyncGenerator[str, None]:
    """
    Convenience wrapper that starts the conversation flow with user input.
    
    Args:
        conversation_flow_func: Function that returns AsyncGenerator[ConversationTurn, None]
        agents: Dictionary mapping agent names to Agent objects
        llm_client: LLM client for making API calls
        user_input: Initial user input to start conversation
        context: Optional context dictionary
        
    Yields:
        JSON-formatted SSE events
    """
    context = context or {}
    conversation_flow = conversation_flow_func(user_input, context)
    
    async for event in run_conversation(conversation_flow, agents, llm_client):
        yield event


# Helper functions for common patterns

def format_thinking_event(agent_name: str, metadata: Dict = None) -> str:
    """
    Helper to format a thinking event.
    
    Args:
        agent_name: Name of the agent that's thinking
        metadata: Optional metadata
        
    Returns:
        JSON-formatted SSE event string
    """
    event = {
        'type': 'thinking',
        'agent': agent_name,
        'data': {},
        'metadata': metadata or {}
    }
    return f"data: {json.dumps(event)}\n\n"


def format_message_event(
    agent_name: str,
    message: str,
    metadata: Dict = None
) -> str:
    """
    Helper to format a message event.
    
    Args:
        agent_name: Name of the agent sending the message
        message: Message content
        metadata: Optional metadata
        
    Returns:
        JSON-formatted SSE event string
    """
    event = {
        'type': 'message',
        'agent': agent_name,
        'data': {
            'message': message,
            'content': message  # Backward compatibility
        },
        'metadata': metadata or {}
    }
    return f"data: {json.dumps(event)}\n\n"


def format_judgment_event(
    agent_name: str,
    judgment_data: Dict,
    metadata: Dict = None
) -> str:
    """
    Helper to format a judgment/evaluation event.
    
    Args:
        agent_name: Name of the judging agent
        judgment_data: Judgment data (winner, scores, reasoning, etc.)
        metadata: Optional metadata
        
    Returns:
        JSON-formatted SSE event string
    """
    event = {
        'type': 'judgment',
        'agent': agent_name,
        'data': judgment_data,
        'metadata': metadata or {}
    }
    return f"data: {json.dumps(event)}\n\n"


def format_complete_event(
    result_data: Dict,
    metadata: Dict = None
) -> str:
    """
    Helper to format a completion event.
    
    Args:
        result_data: Result data (success, score, message, etc.)
        metadata: Optional metadata
        
    Returns:
        JSON-formatted SSE event string
    """
    event = {
        'type': 'complete',
        'agent': 'system',
        'data': result_data,
        'metadata': metadata or {}
    }
    return f"data: {json.dumps(event)}\n\n"


def format_error_event(
    error_message: str,
    metadata: Dict = None
) -> str:
    """
    Helper to format an error event.
    
    Args:
        error_message: Error description
        metadata: Optional metadata
        
    Returns:
        JSON-formatted SSE event string
    """
    event = {
        'type': 'error',
        'agent': 'system',
        'data': {'message': error_message},
        'metadata': metadata or {}
    }
    return f"data: {json.dumps(event)}\n\n"
