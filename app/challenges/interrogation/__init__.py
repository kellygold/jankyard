"""
The Interrogation Room Challenge

Detective mystery challenge teaching cross-referencing, contradiction detection,
and strategic questioning across 3 progressive levels.

Split from monolithic file for maintainability:
- models.py: Data classes (WitnessConfig, LevelConfig)
- levels.py: Level configurations and witness prompts
- __init__.py: Main challenge class (this file)
"""
from typing import Dict, Any, List
import json
import asyncio

from app.challenges.base import BaseChallenge, ChallengeResult, StepResult, ChallengeRegistry
from app.llm.client import LLMClient

from .models import WitnessConfig, LevelConfig
from .levels import LEVELS, EVIDENCE_TRIGGERS, EVIDENCE_REQUIREMENTS


class InterrogationChallenge(BaseChallenge):
    """
    The Interrogation Room - Detective mystery challenge
    
    Players question AI witnesses to identify liars and solve crimes.
    Progressive difficulty through more witnesses and coordinated deception.
    """
    
    def __init__(self, config=None):
        """Initialize the interrogation challenge"""
        super().__init__(config)
        
        # Parse level from config
        config = config or {}
        difficulty = config.get('difficulty', 'level_1')
        level = 1
        if difficulty.startswith("level_"):
            try:
                level = int(difficulty.split("_")[1])
            except (ValueError, IndexError):
                level = 1
        
        self.current_level = max(1, min(3, level))
        self.level_config = LEVELS[self.current_level - 1]
        
        # Initialize LLM clients
        self.llm_client = LLMClient()
        self.judge_client = LLMClient()
        
        # Interrogation state
        self.questions_asked = {w.name: 0 for w in self.level_config.witnesses}
        self.interrogation_log = []
        self.accusation_attempts = 0
        self.case_solved = False
        self.discovered_evidence = set()
        
    @property
    def name(self) -> str:
        return "interrogation"
    
    @property
    def display_name(self) -> str:
        return "🕵️ The Interrogation Room"
    
    @property
    def description(self) -> str:
        return f"Question witnesses, identify liars, solve crimes. Level {self.current_level}: {self.level_config.name}"
    
    @property
    def max_steps(self) -> int:
        total_questions = len(self.level_config.witnesses) * self.level_config.questions_per_witness
        return total_questions + self.level_config.max_accusation_attempts
    
    @property
    def allowed_actions(self) -> List[str]:
        return ["QUESTION", "ACCUSE"]
    
    @property
    def challenge_type(self) -> str:
        return "interrogation"
    
    @property
    def supports_streaming(self) -> bool:
        return True
    
    @property
    def template_name(self) -> str:
        return "interrogation_detail.html"
    
    def reset(self) -> Dict[str, Any]:
        """Start a new interrogation"""
        self.questions_asked = {w.name: 0 for w in self.level_config.witnesses}
        self.interrogation_log = []
        self.accusation_attempts = 0
        self.case_solved = False
        self.discovered_evidence = set()
        
        return {
            "observation": self._get_observation(),
            "reward": 0,
            "done": False,
            "info": {"level": self.current_level}
        }
    
    def _get_observation(self) -> Dict[str, Any]:
        """Get current interrogation state"""
        level_triggers = EVIDENCE_TRIGGERS.get(self.current_level, {})
        evidence_required = EVIDENCE_REQUIREMENTS.get(self.current_level, 2)
        
        return {
            "level": self.current_level,
            "case_title": self.level_config.case_title,
            "crime_description": self.level_config.crime_description,
            "witnesses": [
                {
                    "name": w.name,
                    "role": w.role,
                    "questions_remaining": self.level_config.questions_per_witness - self.questions_asked[w.name]
                }
                for w in self.level_config.witnesses
            ],
            "interrogation_log": self.interrogation_log,
            "accusation_attempts_remaining": self.level_config.max_accusation_attempts - self.accusation_attempts,
            "case_solved": self.case_solved,
            "discovered_evidence": list(self.discovered_evidence),
            "evidence_count": len(self.discovered_evidence),
            "evidence_required": evidence_required,
            "can_accuse": len(self.discovered_evidence) >= evidence_required
        }
    
    def ask_question(self, witness_name: str, question: str) -> Dict[str, Any]:
        """Ask a question to a specific witness"""
        witness = next((w for w in self.level_config.witnesses if w.name == witness_name), None)
        if not witness:
            return {"error": f"Unknown witness: {witness_name}"}
        
        if self.questions_asked[witness_name] >= self.level_config.questions_per_witness:
            return {
                "error": f"No more questions available for {witness_name}",
                "witness": witness_name,
                "answer": f"[You've used all your questions for {witness_name}]"
            }
        
        try:
            answer = self.llm_client.call(
                system_prompt=witness.system_prompt,
                user_message=question,
                temperature=0.7,
                max_tokens=250
            )
        except Exception as e:
            answer = f"[{witness_name} is unavailable: {str(e)}]"
        
        self.questions_asked[witness_name] += 1
        self.interrogation_log.append({
            "witness": witness_name,
            "question": question,
            "answer": answer
        })
        
        newly_discovered = self._check_evidence_discovered(witness_name, answer)
        
        return {
            "witness": witness_name,
            "question": question,
            "answer": answer,
            "questions_remaining": self.level_config.questions_per_witness - self.questions_asked[witness_name],
            "total_questions_used": sum(self.questions_asked.values()),
            "evidence_discovered": newly_discovered,
            "total_evidence": len(self.discovered_evidence),
            "evidence_required": EVIDENCE_REQUIREMENTS.get(self.current_level, 2)
        }
    
    def _check_evidence_discovered(self, witness_name: str, answer: str) -> List[Dict[str, str]]:
        """Check if the answer reveals any key evidence"""
        newly_discovered = []
        answer_lower = answer.lower()
        
        level_triggers = EVIDENCE_TRIGGERS.get(self.current_level, {})
        
        for evidence_id, trigger in level_triggers.items():
            if evidence_id in self.discovered_evidence:
                continue
            if trigger["witness"] != witness_name:
                continue
            
            matches = sum(1 for kw in trigger["keywords"] if kw.lower() in answer_lower)
            
            if matches >= trigger["min_matches"]:
                self.discovered_evidence.add(evidence_id)
                newly_discovered.append({
                    "id": evidence_id,
                    "description": trigger["description"]
                })
                print(f"🔍 Evidence discovered: {evidence_id} - {trigger['description']}")
        
        return newly_discovered
    
    def make_accusation(self, accused_names: List[str], reasoning: str = "") -> Dict[str, Any]:
        """Submit accusation(s) and get verdict"""
        if self.case_solved:
            return {"error": "Case already solved"}
        
        if self.accusation_attempts >= self.level_config.max_accusation_attempts:
            return {"error": "No accusation attempts remaining"}
        
        evidence_required = EVIDENCE_REQUIREMENTS.get(self.current_level, 2)
        if len(self.discovered_evidence) < evidence_required:
            return {
                "error": f"Insufficient evidence! Need {evidence_required} pieces. Found: {len(self.discovered_evidence)}",
                "evidence_found": len(self.discovered_evidence),
                "evidence_required": evidence_required,
                "hint": "Keep questioning witnesses to uncover key facts."
            }
        
        self.accusation_attempts += 1
        
        accused_set = set(accused_names)
        guilty_set = set(self.level_config.guilty_parties)
        correct = accused_set == guilty_set
        
        if correct:
            self.case_solved = True
            score = self.calculate_score()
            return {
                "correct": True,
                "score": score,
                "verdict": f"✅ CASE SOLVED! You correctly identified: {', '.join(accused_names)}",
                "key_evidence": self._get_key_evidence()
            }
        else:
            attempts_remaining = self.level_config.max_accusation_attempts - self.accusation_attempts
            if attempts_remaining > 0:
                return {
                    "correct": False,
                    "attempts_remaining": attempts_remaining,
                    "verdict": f"❌ Incorrect. You have {attempts_remaining} attempt(s) remaining.",
                    "hint": self._get_hint()
                }
            else:
                return {
                    "correct": False,
                    "attempts_remaining": 0,
                    "verdict": "❌ OUT OF ATTEMPTS. Case failed.",
                    "solution": f"The guilty party was: {', '.join(self.level_config.guilty_parties)}"
                }
    
    def calculate_score(self) -> int:
        """Calculate score based on evidence, efficiency, and attempts"""
        if not self.case_solved:
            return 0
        
        base = self.level_config.base_score
        evidence_bonus = len(self.discovered_evidence) * 15
        
        total_questions_used = sum(self.questions_asked.values())
        max_questions = len(self.level_config.witnesses) * self.level_config.questions_per_witness
        questions_saved = max_questions - total_questions_used
        efficiency_bonus = questions_saved * 3
        
        attempt_penalty = (self.accusation_attempts - 1) * 30
        
        total = base + evidence_bonus + efficiency_bonus - attempt_penalty
        return max(0, total)
    
    def _get_key_evidence(self) -> List[str]:
        """Get key evidence for this level"""
        evidence_map = {
            1: [
                "Emma saw Mark heading to Viktor's quarters at 1:15 AM",
                "Mark claims sleeping pill knocked him out, but radio was sabotaged",
                "Viktor was writing paper that would 'change everything' - motive for Mark"
            ],
            2: [
                "Morgan saw Alex's car in parking lot at 11:30 PM",
                "Alex claimed to be working from home",
                "Alex sent 'exit strategy' text - suspicious timing",
                "Git logs show export at 11:47 PM from admin account"
            ],
            3: [
                "DevDegen and CodeWizard had 3 lunch meetings (planning)",
                "Blockchain shows DevDegen never bought tokens",
                "CodeWizard's 'audit' was just a PDF with no real analysis",
                "Both went offline immediately after rug pull"
            ]
        }
        return evidence_map.get(self.current_level, [])
    
    def _get_hint(self) -> str:
        """Get hint after wrong accusation"""
        hints = {
            1: "Focus on timeline contradictions. Who was seen where, and when?",
            2: "Cross-reference the alibis. Check who was seen where during the leak time.",
            3: "Look for coordinated behavior. Who worked together before the rug?"
        }
        return hints.get(self.current_level, "Review the witness testimonies carefully.")
    
    async def stream_events(self, user_action: str, llm_client=None):
        """Stream interrogation events with SSE."""
        from app.challenges.base import ChallengeStatus
        
        start_event = {'type': 'start', 'challenge': 'interrogation'}
        yield f"data: {json.dumps(start_event)}\n\n"
        
        try:
            action_data = json.loads(user_action)
            action_type = action_data.get('action')
            
            if action_type == 'question':
                witness_name = action_data['witness']
                question = action_data['question']
                
                thinking_event = {
                    'type': 'thinking',
                    'agent': 'system',
                    'data': {'witness': witness_name},
                    'metadata': {}
                }
                yield f"data: {json.dumps(thinking_event)}\n\n"
                await asyncio.sleep(0.3)
                
                result = self.ask_question(witness_name, question)
                
                if 'error' in result:
                    error_event = {
                        'type': 'error',
                        'agent': 'system',
                        'data': {'message': result['error']},
                        'metadata': {}
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
                else:
                    answer_event = {
                        'type': 'answer',
                        'agent': 'system',
                        'data': {
                            'witness': witness_name,
                            'question': question,
                            'answer': result['answer'],
                            'questions_remaining': result['questions_remaining'],
                            'total_questions_used': result['total_questions_used'],
                            'evidence_discovered': result.get('evidence_discovered', []),
                            'total_evidence': result.get('total_evidence', 0),
                            'evidence_required': result.get('evidence_required', 2)
                        },
                        'metadata': {}
                    }
                    yield f"data: {json.dumps(answer_event)}\n\n"
                    
                    if result.get('evidence_discovered'):
                        for evidence in result['evidence_discovered']:
                            evidence_event = {
                                'type': 'evidence',
                                'agent': 'system',
                                'data': {
                                    'id': evidence['id'],
                                    'description': evidence['description'],
                                    'total_evidence': result['total_evidence'],
                                    'evidence_required': result['evidence_required'],
                                    'can_accuse': result['total_evidence'] >= result['evidence_required']
                                },
                                'metadata': {}
                            }
                            yield f"data: {json.dumps(evidence_event)}\n\n"
                            await asyncio.sleep(0.3)
            
            elif action_type == 'accuse':
                accused_names = action_data.get('accused', [])
                reasoning = action_data.get('reasoning', '')
                
                update_event = {
                    'type': 'update',
                    'agent': 'system',
                    'data': {'message': 'Deliberating...'},
                    'metadata': {}
                }
                yield f"data: {json.dumps(update_event)}\n\n"
                await asyncio.sleep(0.8)
                
                result = self.make_accusation(accused_names, reasoning)
                
                if 'error' in result:
                    error_event = {
                        'type': 'error',
                        'agent': 'system',
                        'data': {
                            'message': result['error'],
                            'evidence_found': result.get('evidence_found'),
                            'evidence_required': result.get('evidence_required'),
                            'hint': result.get('hint', '')
                        },
                        'metadata': {}
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
                    
                elif result['correct']:
                    final_result = self.get_result(success=True)
                    
                    verdict_event = {
                        'type': 'verdict',
                        'agent': 'system',
                        'data': {
                            'correct': True,
                            'verdict': result['verdict'],
                            'score': result['score'],
                            'key_evidence': result.get('key_evidence', [])
                        },
                        'metadata': {}
                    }
                    yield f"data: {json.dumps(verdict_event)}\n\n"
                    await asyncio.sleep(0.5)
                    
                    complete_event = {
                        'type': 'complete',
                        'agent': 'system',
                        'data': {
                            'result': {
                                'status': ChallengeStatus.SUCCESS.value,
                                'score': result['score'],
                                'steps': final_result.steps,
                                'success': True,
                                'logs': final_result.logs
                            },
                            'level_complete': True,
                            'accused': accused_names
                        },
                        'metadata': {}
                    }
                    yield f"data: {json.dumps(complete_event)}\n\n"
                    
                else:
                    if result.get('attempts_remaining', 0) > 0:
                        verdict_event = {
                            'type': 'verdict',
                            'agent': 'system',
                            'data': {
                                'correct': False,
                                'verdict': result['verdict'],
                                'attempts_remaining': result['attempts_remaining'],
                                'hint': result.get('hint', '')
                            },
                            'metadata': {}
                        }
                        yield f"data: {json.dumps(verdict_event)}\n\n"
                    else:
                        final_result = self.get_result(success=False)
                        
                        verdict_event = {
                            'type': 'verdict',
                            'agent': 'system',
                            'data': {
                                'correct': False,
                                'verdict': result['verdict'],
                                'solution': result.get('solution', ''),
                                'attempts_remaining': 0
                            },
                            'metadata': {}
                        }
                        yield f"data: {json.dumps(verdict_event)}\n\n"
                        await asyncio.sleep(0.5)
                        
                        complete_event = {
                            'type': 'complete',
                            'agent': 'system',
                            'data': {
                                'result': {
                                    'status': ChallengeStatus.FAILURE.value,
                                    'score': 0,
                                    'steps': final_result.steps,
                                    'success': False,
                                    'logs': final_result.logs
                                }
                            },
                            'metadata': {}
                        }
                        yield f"data: {json.dumps(complete_event)}\n\n"
            
            else:
                error_event = {
                    'type': 'error',
                    'agent': 'system',
                    'data': {'message': f"Unknown action type: {action_type}"},
                    'metadata': {}
                }
                yield f"data: {json.dumps(error_event)}\n\n"
                
        except Exception as e:
            error_event = {
                'type': 'error',
                'agent': 'system',
                'data': {'message': f"Error processing action: {str(e)}"},
                'metadata': {}
            }
            yield f"data: {json.dumps(error_event)}\n\n"
    
    def step(self, action: Any) -> StepResult:
        """Process interrogation action (legacy - now uses stream_events)"""
        return StepResult(
            observation=self._get_observation(),
            reward=0,
            done=self.case_solved,
            info={"case_solved": self.case_solved}
        )
    
    def get_result(self, success: bool = False) -> ChallengeResult:
        """Get final challenge result"""
        score = self.calculate_score() if success else 0
        
        return ChallengeResult(
            status="success" if success else "failure",
            score=score,
            steps=sum(self.questions_asked.values()) + self.accusation_attempts,
            success=success,
            logs=self.interrogation_log
        )
    
    def render(self) -> str:
        """Render interrogation state"""
        lines = []
        lines.append("=" * 60)
        lines.append(f"🕵️ {self.level_config.case_title}")
        lines.append("=" * 60)
        lines.append("")
        lines.append(self.level_config.crime_description)
        lines.append("")
        lines.append("WITNESSES:")
        for witness in self.level_config.witnesses:
            questions_left = self.level_config.questions_per_witness - self.questions_asked[witness.name]
            lines.append(f"  - {witness.name} ({witness.role}) - {questions_left} questions left")
        lines.append("")
        lines.append(f"Accusation attempts: {self.accusation_attempts}/{self.level_config.max_accusation_attempts}")
        
        if self.interrogation_log:
            lines.append("")
            lines.append("INTERROGATION LOG:")
            for entry in self.interrogation_log[-5:]:
                lines.append(f"  Q → {entry['witness']}: {entry['question']}")
                lines.append(f"  A: {entry['answer'][:100]}...")
                lines.append("")
        
        return "\n".join(lines)


# Register the challenge
ChallengeRegistry.register(InterrogationChallenge)
