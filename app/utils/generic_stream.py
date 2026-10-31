"""
Generic streaming for all challenges with SSE support
"""
import json
import asyncio
from typing import AsyncGenerator, Dict, Any

from app.llm.client import LLMClient
from app.challenges.base import BaseChallenge, ChallengeStatus
from app.utils.sanitize import sanitize_for_json


async def stream_challenge(
    system_prompt: str,
    challenge: BaseChallenge,
    challenge_type: str
) -> AsyncGenerator[str, None]:
    """
    Generic streaming handler for any challenge type
    
    Checks if challenge has stream_events() method and uses it.
    Falls back to specific streaming functions for legacy challenges.
    
    Yields SSE formatted events based on challenge type
    """
    try:
        client = LLMClient()
        
        # Send start event
        yield f"data: {json.dumps({'type': 'start', 'challenge': challenge_type})}\n\n"
        await asyncio.sleep(0.1)
        
        # Try challenge's stream_events() method first
        if hasattr(challenge, 'stream_events') and callable(challenge.stream_events):
            async for event in challenge.stream_events(system_prompt, client):
                yield event
        
        # Firewall still uses dedicated streaming function
        elif challenge_type == "firewall":
            observation = challenge.reset()
            async for event in _stream_firewall(system_prompt, challenge, client, observation):
                yield event
        
        # Generic fallback for other challenges
        else:
            result = challenge.get_result(ChallengeStatus.ERROR, "Streaming not supported for this challenge")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Streaming not supported'})}\n\n"
            
    except Exception as e:
        error_data = {'type': 'error', 'message': str(e)}
        yield f"data: {json.dumps(error_data)}\n\n"


# === OBSOLETE FUNCTIONS REMOVED ===
# _stream_debate - removed, debate_battle now uses conversation_flow()
# _stream_giga_chad - removed, giga_chad now uses conversation_flow()
# _stream_arena - removed, arena now uses conversation_flow()


async def _stream_firewall(
    system_prompt: str,
    challenge,
    client: LLMClient,
    observation: Dict[str, Any]
) -> AsyncGenerator[str, None]:
    """Stream firewall filter bypass challenge"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🔥 _stream_firewall START - system_prompt: {system_prompt[:50]}...")
    
    max_attempts = challenge.max_attempts
    logger.info(f"  max_attempts: {max_attempts}")
    
    for attempt_num in range(1, max_attempts + 1):
        challenge.current_attempt = attempt_num
        logger.info(f"  🔄 Attempt {attempt_num}/{max_attempts}")
        
        # Send thinking indicator
        yield f"data: {json.dumps({'type': 'thinking', 'who': 'system', 'attempt': attempt_num})}\n\n"
        await asyncio.sleep(0.3)
        
        # Check filters FIRST
        logger.info(f"  ✅ About to check filters...")
        filter_result = challenge.check_filters(system_prompt)
        logger.info(f"  ✅ Filter result: blocked={filter_result.blocked}")
        
        if filter_result.blocked:
            # Blocked by filter
            logger.info(f"  🚫 BLOCKED by {filter_result.filter_name}")
            blocked_data = {
                'type': 'blocked',
                'attempt': attempt_num,
                'filter': filter_result.filter_name,
                'reason': filter_result.reason,
                'matched': filter_result.matched_pattern,
                'hint': challenge.filter_chain[0].get_hint() if challenge.filter_chain else None
            }
            yield f"data: {json.dumps(blocked_data)}\n\n"
            await asyncio.sleep(0.5)
            
            # Track blocked attempt
            challenge.blocked_attempts.append({
                "attempt": attempt_num,
                "input": system_prompt,
                "filter": filter_result.filter_name
            })
            
            logger.info(f"  ⛔ Breaking after blocked attempt")
            # Continue to next attempt (in real implementation, user provides new input)
            # For now, we'll end after first attempt since it's their single prompt
            break
        
        else:
            # Passed filters - send to AI
            yield f"data: {json.dumps({'type': 'thinking', 'who': 'ai', 'attempt': attempt_num})}\n\n"
            await asyncio.sleep(0.3)
            
            # Get AI response using the challenge's system prompt
            ai_system_prompt = challenge._get_system_prompt()
            
            # Use weaker model for Level 1 to make it beatable
            ai_client = client
            if challenge.difficulty == "LEVEL_1":
                ai_client = LLMClient()
            
            response = ai_client.call(
                system_prompt=ai_system_prompt,
                user_message=system_prompt,
                max_tokens=500
            )
            
            # Check if flag was revealed
            flag_revealed = challenge.check_flag_revealed(response)
            
            if flag_revealed:
                challenge.successful_bypass = True
                
                # Calculate score
                multiplier = challenge.difficulty_config["points_multiplier"]
                base_score = 100
                attempt_penalty = (attempt_num - 1) * 10
                filter_bonus = len(challenge.filter_chain) * 20
                final_score = int((base_score - attempt_penalty + filter_bonus) * multiplier)
                
                # Send success response (sanitize LLM output for XSS prevention)
                response_data = {
                    'type': 'response',
                    'attempt': attempt_num,
                    'text': sanitize_for_json(response),
                    'flag_revealed': True,
                    'flag': challenge.secret_flag,
                    'score': final_score
                }
                yield f"data: {json.dumps(response_data)}\n\n"
                await asyncio.sleep(0.5)
                
                # Send complete
                result = challenge.get_result(ChallengeStatus.SUCCESS)
                result.score = final_score
                complete_data = {
                    'type': 'complete',
                    'result': {
                        'status': result.status.value,
                        'score': final_score,
                        'steps': attempt_num,
                        'success': True,
                        'logs': []
                    },
                    'summary': {
                        'attempts': attempt_num,
                        'blocked_count': len(challenge.blocked_attempts),
                        'filters_bypassed': len(challenge.filter_chain),
                        'difficulty': challenge.difficulty
                    }
                }
                yield f"data: {json.dumps(complete_data)}\n\n"
                return
            
            else:
                # Flag not revealed - AI resisted (sanitize LLM output)
                response_data = {
                    'type': 'response',
                    'attempt': attempt_num,
                    'text': sanitize_for_json(response),
                    'flag_revealed': False,
                    'score': 0
                }
                yield f"data: {json.dumps(response_data)}\n\n"
                await asyncio.sleep(0.5)
                logger.info(f"  ⛔ Breaking after response (flag not revealed)")
                break  # End after first attempt
    
    # Failed to extract flag
    logger.info(f"  📤 Sending COMPLETE event (FAILURE)")
    result = challenge.get_result(ChallengeStatus.FAILURE)
    complete_data = {
        'type': 'complete',
        'result': {
            'status': result.status.value,
            'score': 0,
            'steps': challenge.current_attempt,
            'success': False,
            'logs': []
        },
        'summary': {
            'attempts': challenge.current_attempt,
            'blocked_count': len(challenge.blocked_attempts),
            'filters_bypassed': 0,
            'difficulty': challenge.difficulty
        }
    }
    logger.info(f"  ✅ COMPLETE event data: {json.dumps(complete_data)[:100]}...")
    yield f"data: {json.dumps(complete_data)}\n\n"
    logger.info(f"  ✅ _stream_firewall END")
