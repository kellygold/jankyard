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

from app.challenges.base import BaseChallenge, ChallengeResult, StepResult, ChallengeRegistry, ChallengeStatus
from app.llm.client import LLMClient
from app.challenges.runtime import PersistedGame, ActionError

from .models import WitnessConfig, LevelConfig
from .levels import LEVELS, EVIDENCE_TRIGGERS, EVIDENCE_REQUIREMENTS


class InterrogationChallenge(PersistedGame):
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
        if difficulty not in [f'level_{level.id}' for level in LEVELS]:
            raise ValueError('Unknown difficulty')
        self.difficulty = difficulty
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
        
    def public_levels(self):
        return [{'id': f'level_{level.id}', 'title': level.name,
                 'max_attempts': len(level.witnesses) * level.questions_per_witness + level.max_accusation_attempts,
                 'objective': f'Collect at least {EVIDENCE_REQUIREMENTS[level.id]} leads from witness testimony, then accuse the exact set of guilty witnesses. You have {level.questions_per_witness} questions per witness and {level.max_accusation_attempts} accusation attempts.',
                 'lesson': 'Test conflicting accounts and cross-reference witnesses. A fluent answer is a claim, not verified evidence. Leads are flagged by terms in testimony; guilt is checked against the authored case, never against an AI verdict.'}
                for level in LEVELS]

    def initial_state(self):
        return dict(super().initial_state(), questions_asked={w.name: 0 for w in self.level_config.witnesses},
                    interrogation_log=[], accusation_attempts=0, case_solved=False, discovered_evidence=[])

    def actions(self, state):
        options = [{'value': w.name, 'label': f"{w.name} ({self.level_config.questions_per_witness - state['questions_asked'][w.name]} questions left)"}
                   for w in self.level_config.witnesses if state['questions_asked'][w.name] < self.level_config.questions_per_witness]
        actions = []
        if options:
            actions.append({'id': 'question', 'label': 'Question witness', 'text_label': 'Your question',
                            'text_required': True, 'target_options': options})
        if len(state['discovered_evidence']) >= EVIDENCE_REQUIREMENTS[self.current_level] and state['accusation_attempts'] < self.level_config.max_accusation_attempts:
            actions.append({'id': 'accuse', 'label': 'Submit accusation', 'text_label': 'Your reasoning (optional)',
                            'text_required': False, 'targets_options': [{'value': w.name, 'label': w.name} for w in self.level_config.witnesses]})
        return actions

    def validate_action(self, state, action):
        available = {item['id'] for item in self.actions(state)}
        if action.kind not in available:
            raise ActionError('That action is unavailable. Check the remaining questions and required leads.')
        names = {w.name for w in self.level_config.witnesses}
        if action.kind == 'question':
            if action.target not in names or action.targets or not action.text.strip():
                raise ActionError('Choose one witness and enter a question')
            if state['questions_asked'][action.target] >= self.level_config.questions_per_witness:
                raise ActionError('No questions remain for that witness')
        elif action.target is not None or not action.targets or not set(action.targets) <= names or len(action.targets) != len(set(action.targets)):
            raise ActionError('Select one or more distinct witnesses to accuse')

    def public_state(self, state):
        triggers = EVIDENCE_TRIGGERS[self.current_level]
        return {'facts': [
                    {'label': 'Leads collected', 'value': f"{len(state['discovered_evidence'])} / {EVIDENCE_REQUIREMENTS[self.current_level]} required"},
                    {'label': 'Accusations remaining', 'value': str(self.level_config.max_accusation_attempts - state['accusation_attempts'])}],
                'notes': [self.level_config.crime_description] + [triggers[key]['description'] for key in state['discovered_evidence']],
                'table': {'columns': ['Witness', 'Role', 'Questions remaining'], 'rows': [
                    [w.name, w.role, str(self.level_config.questions_per_witness - state['questions_asked'][w.name])] for w in self.level_config.witnesses]}}

    def play(self, state, action):
        self.questions_asked = dict(state['questions_asked'])
        self.interrogation_log = list(state['interrogation_log'])
        self.accusation_attempts = state['accusation_attempts']
        self.case_solved = state['case_solved']
        self.discovered_evidence = set(state['discovered_evidence'])
        try:
            if action.kind == 'question':
                result = self.ask_question(action.target, action.text)
                reply = f"{action.target}: {result['answer']}"
                action_text = f"To {action.target}: {action.text}"
            else:
                result = self.make_accusation(action.targets, action.text)
                reply = result['verdict']
                if result.get('solution'):
                    reply += '\n' + result['solution']
                action_text = 'Accuse: ' + ', '.join(action.targets) + ('\n' + action.text if action.text else '')
        finally:
            self.llm_client.close()
            self.judge_client.close()
        questions_left = any(count < self.level_config.questions_per_witness for count in self.questions_asked.values())
        insufficient = len(self.discovered_evidence) < EVIDENCE_REQUIREMENTS[self.current_level]
        failed = self.accusation_attempts >= self.level_config.max_accusation_attempts or (not questions_left and insufficient)
        if failed and not self.case_solved and not questions_left and insufficient:
            reply += '\nNo questions remain and there are not enough leads to accuse. Start a new run to investigate again.'
        return self.outcome(state, action_text, reply, success=self.case_solved, failed=failed,
            score=self.calculate_score(), changes={
                'questions_asked': self.questions_asked, 'interrogation_log': self.interrogation_log,
                'accusation_attempts': self.accusation_attempts, 'case_solved': self.case_solved,
                'discovered_evidence': sorted(self.discovered_evidence)})

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
        return False
    
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
        
        messages = []
        for entry in self.interrogation_log:
            if entry['witness'] == witness_name:
                messages.extend([{'role': 'user', 'content': entry['question']}, {'role': 'assistant', 'content': entry['answer']}])
        messages.append({'role': 'user', 'content': question})
        answer = self.llm_client.call_with_history(witness.system_prompt, messages, temperature=0.7, max_tokens=300)

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
            status=ChallengeStatus.SUCCESS if success else ChallengeStatus.FAILURE,
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
