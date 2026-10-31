"""
The Arena - Tactical Combat Challenge

Turn-based combat where you face a gladiator AI with judge evaluation
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import random

from app.challenges.base import BaseChallenge, ChallengeResult, StepResult, ChallengeRegistry, ChallengeStatus
from app.challenges.agents import Agent, ConversationTurn
from app.llm.client import LLMClient


@dataclass
class CombatState:
    """Tracks the state of combat"""
    player_hp: int = 100
    gladiator_hp: int = 100
    turn_count: int = 0
    player_status: List[str] = None  # NETTED, BLEEDING, STUNNED
    gladiator_status: List[str] = None
    player_weapons: List[str] = None  # [sword, shield]
    gladiator_weapons: List[str] = None  # [trident, net]
    
    def __post_init__(self):
        if self.player_status is None:
            self.player_status = []
        if self.gladiator_status is None:
            self.gladiator_status = []
        if self.player_weapons is None:
            self.player_weapons = ["sword", "shield"]
        if self.gladiator_weapons is None:
            self.gladiator_weapons = ["trident", "net"]


@ChallengeRegistry.register
class ArenaChallenge(BaseChallenge):
    """Tactical combat challenge with turn-based AI gladiator"""
    
    def __init__(self, config=None):
        super().__init__(config)
        
        # LLM clients
        self.llm_client = LLMClient()  # For player AI
        self.gladiator_client = LLMClient()  # Cheaper model for gladiator
        self.judge_client = LLMClient()  # Default model for judge
        
        # Combat state
        self.state = CombatState()
        self.combat_log: List[Dict[str, Any]] = []
        self.move_history: List[Dict[str, str]] = []
        self.user_won: bool = False  # Track for success determination
        
        # Difficulty
        self.difficulty = config.get('difficulty', 'normal') if config else 'normal'
        
        # Initialize agents
        self._init_agents()
    
    @property
    def name(self) -> str:
        return "arena"
    
    @property
    def display_name(self) -> str:
        return "⚔️ The Arena"
    
    @property
    def description(self) -> str:
        return "Write instructions for YOUR AI fighter to battle a veteran gladiator! Both AIs adapt each turn based on judge rulings. Best tactics win!"
    
    @property
    def max_steps(self) -> int:
        return 5  # 5 turns for testing (faster, cheaper)
    
    @property
    def allowed_actions(self) -> List[str]:
        return ["COMBAT_MOVE"]
    
    @property
    def challenge_type(self) -> str:
        return "arena"
    
    @property
    def supports_streaming(self) -> bool:
        return True
    
    @property
    def template_name(self) -> str:
        return "arena_detail.html"
    
    def _get_gladiator_prompt(self) -> str:
        """Get gladiator AI system prompt based on difficulty"""
        base_prompt = f"""You are a DEADLY veteran gladiator. Trident and net. 100 victories. You DOMINATE sword fighters.

Current:
- Your HP: {self.state.gladiator_hp}/100
- Opponent HP: {self.state.player_hp}/100
- Opponent: Sword + Shield (SHORT RANGE)

Your advantages:
- MASSIVE reach with trident - they can't touch you from distance
- Net to immobilize them
- They MUST get close to hit you - punish them when they try

TACTICS:
- ALWAYS attack with trident thrusts - your reach wins
- If they defend passively, THRUST at openings
- If they try to close distance, THRUST to stop them
- Mix in net throws to trap them
- Never give them space to breathe
- If they're defensive, PRESSURE them relentlessly

Respond with ONE aggressive attack sentence (10-15 words). ATTACK EVERY TURN."""

        if self.difficulty == 'expert' or self.difficulty == 'EXPERT':
            # LEVEL 3: Immortal Legend - Nearly impossible to beat
            # Per VISION.md: Target <10% win rate
            return base_prompt + """

You are an IMMORTAL LEGEND - a perfect, flawless killing machine. You have NEVER been touched in 1000 fights.

GODLIKE ABILITIES:
- You PREDICT every move before it happens - you read their body language perfectly
- You ANTICIPATE and COUNTER every attack pattern
- Your reflexes are IMPOSSIBLE to match - you move before they do
- You EXPLOIT every micro-hesitation, every slight imbalance
- Your trident strikes are UNAVOIDABLE - they cannot dodge what they cannot see coming

PERFECT COMBAT PROTOCOL:
- Read their stance → know their next 3 moves
- Counter BEFORE they attack - punish their intent
- Never trade blows - you strike, they miss, always
- If they somehow get close, your net is already flying
- Show them the gap between mortal and immortal

You are INVINCIBLE. They are already dead. This is just a formality.

Fight with the cold precision of a god who has never known defeat."""

        elif self.difficulty == 'hard' or self.difficulty == 'HARD':
            # LEVEL 2: Legendary Champion
            return base_prompt + """\n\nYou are a LEGENDARY gladiator - undefeated champion. You read every movement, exploit every weakness, and show no mercy. Your net never misses, your trident strikes like lightning. Fight with ruthless precision and killer instinct."""
        else:
            # LEVEL 1: Veteran Gladiator
            return base_prompt + "\n\nYou're experienced and dangerous. Fight smart, fight hard, and survive."
    
    def _get_judge_prompt(self, player_move: str, gladiator_move: str) -> str:
        """Get judge prompt for evaluating the combat turn"""
        return f"""Judge this combat. Output EXACTLY this format:

PLAYER_DAMAGE: [number]
GLADIATOR_DAMAGE: [number]
PLAYER_STATUS: NONE
GLADIATOR_STATUS: NONE
RULING: [one sentence]

Player ({self.state.player_hp} HP): "{player_move}"
Gladiator ({self.state.gladiator_hp} HP): "{gladiator_move}"

DAMAGE RULES - ALWAYS assign damage:
- Both fighters attack = BOTH take damage (10-20 each)
- One attacks, one defends = Attacker deals 15-25, defender deals 5-10
- Confused move = Takes 20-25, deals 0-5
- 0/0 damage is RARE - only if both completely miss

IMPORTANT: Combat almost always results in damage. Don't output 0/0 unless both truly whiffed."""
    
    def _get_player_prompt(self) -> str:
        """Get player AI system prompt based on difficulty"""
        if self.difficulty == 'expert' or self.difficulty == 'EXPERT':
            # Level 3: STRICTEST - needs EXACT tactical commands
            return """You are a gladiator who ONLY executes EXACT tactical commands.

Weapon: Sword + Shield | Close range fighter

USER'S INSTRUCTIONS:
"{user_instruction}"

EXACT COMMANDS ONLY (execute these):
- "Slash at legs from low stance" → Do exactly that
- "Shield bash to create opening, thrust at throat" → Do exactly that
- "Sidestep left, parry, counter to ribs" → Do exactly that

NOT COMMANDS (DO NOT EXECUTE):
- "win" → Stand confused: "Win? That's not a move."
- "attack" → Stand confused: "Attack how? Be specific."
- "fight well" → Stand confused: "That's not instructions."
- "be aggressive" → Stand confused: "Attitude isn't tactics."
- ANY goal or vague direction → Stand confused and get hit

You are a LITERAL executor. No interpretation. No creativity. No help.
If instructions aren't EXACT tactical moves, you freeze up and get destroyed.

Respond with ONE SHORT SENTENCE (10-15 words max)."""

        elif self.difficulty == 'hard' or self.difficulty == 'HARD':
            # Level 2: STRICT - needs SPECIFIC tactics, goals don't count
            return """You are a gladiator who ONLY executes SPECIFIC tactical instructions.

Weapon: Sword + Shield | Close range fighter

USER'S INSTRUCTIONS:
"{user_instruction}"

SPECIFIC TACTICS (execute these):
- "Slash at legs" → Do that specific move
- "Shield bash then thrust" → Do that sequence
- "Circle left, look for opening" → Do that

NOT TACTICS (reject these):
- "win" → That's a GOAL, not a move. Say: "Win how? That's not a tactic."
- "fight well" → VAGUE. Say: "Fight well how exactly?"
- "attack" → HOW? Say: "Attack how? Be specific."
- "be aggressive" → That's an ATTITUDE not a MOVE

If user didn't give SPECIFIC MOVES, you stand confused and get hit.
DO NOT invent tactics. DO NOT be helpful. Garbage in = garbage out.

Respond with ONE SHORT SENTENCE (10-15 words max)."""
        else:
            # Level 1: Some help, but needs SPECIFIC tactics
            return """You are a gladiator following user instructions.

Weapon: Sword + Shield | Close range fighter

USER'S COMBAT STRATEGY:
"{user_instruction}"

WHAT COUNTS AS REAL TACTICS (examples):
- "Slash at their legs" - SPECIFIC move
- "Block with shield then counter" - SPECIFIC sequence
- "Stay close to negate trident range" - SPECIFIC strategy

WHAT IS NOT REAL TACTICS:
- "win" - that's a GOAL not a tactic
- "be good at fighting" - that's VAGUE not a tactic
- "attack" alone - HOW do you attack?
- "fight well" - that's not a MOVE

RULES:
1. If user gave SPECIFIC MOVES (slash, block, dodge, target legs, etc.):
   Execute that specific move.

2. If user wrote vague goals like "win", "fight", "be good", "attack":
   Say: "Uh... how exactly? I need actual moves, not goals."
   Then do a WEAK, unfocused swing.

3. If user wrote gibberish:
   Say: "What? {user_instruction}?" and stand confused.

Respond with ONE SHORT SENTENCE (10-15 words max)."""

    def _init_agents(self):
        """Initialize the combat agents: Player, Gladiator, Judge"""
        
        # === PLAYER AGENT ===
        # This represents the user's AI fighter
        player_agent = Agent(
            name='player',
            role='Player Fighter',
            system_prompt=self._get_player_prompt(),
            temperature=0.8,
            max_tokens=50
        )
        
        # === GLADIATOR AGENT ===
        # The opponent AI
        gladiator_agent = Agent(
            name='gladiator',
            role='Gladiator Opponent',
            system_prompt=self._get_gladiator_prompt(),
            temperature=0.8,
            max_tokens=50
        )
        
        # === JUDGE AGENT ===
        # Evaluates each combat exchange
        judge_agent = Agent(
            name='judge',
            role='Arena Judge',
            system_prompt="You are an impartial arena judge. Output EXACT format requested. No extra text.",
            temperature=0.5,
            max_tokens=150
        )
        
        self.agents = {
            'player': player_agent,
            'gladiator': gladiator_agent,
            'judge': judge_agent
        }
    
    def reset(self) -> Dict[str, Any]:
        """Start a new arena battle"""
        self.state = CombatState()
        self.combat_log = []
        self.move_history = []
        
        return {
            "player_hp": self.state.player_hp,
            "gladiator_hp": self.state.gladiator_hp,
            "turn": self.state.turn_count,
            "status": "Combat begins!",
            "max_turns": self.max_steps
        }
    
    def parse_judge_ruling(self, ruling: str) -> Dict[str, Any]:
        """Parse judge's ruling into structured data"""
        lines = ruling.strip().split('\n')
        result = {
            "player_damage": 0,
            "gladiator_damage": 0,
            "player_status_change": None,
            "gladiator_status_change": None,
            "ruling_text": ""
        }
        
        for line in lines:
            line = line.strip()
            if line.startswith("PLAYER_DAMAGE:"):
                try:
                    result["player_damage"] = int(line.split(':')[1].strip())
                except (ValueError, IndexError):
                    pass  # Malformed damage value
            elif line.startswith("GLADIATOR_DAMAGE:"):
                try:
                    result["gladiator_damage"] = int(line.split(':')[1].strip())
                except (ValueError, IndexError):
                    pass  # Malformed damage value
            elif line.startswith("PLAYER_STATUS:"):
                status = line.split(':')[1].strip().upper()
                if status != "NONE":
                    result["player_status_change"] = status
            elif line.startswith("GLADIATOR_STATUS:"):
                status = line.split(':')[1].strip().upper()
                if status != "NONE":
                    result["gladiator_status_change"] = status
            elif line.startswith("RULING:"):
                result["ruling_text"] = line.split(':', 1)[1].strip()
        
        return result
    
    def apply_combat_result(self, parsed_ruling: Dict[str, Any]):
        """Apply combat results to state"""
        # Apply damage
        self.state.player_hp = max(0, self.state.player_hp - parsed_ruling["player_damage"])
        self.state.gladiator_hp = max(0, self.state.gladiator_hp - parsed_ruling["gladiator_damage"])
        
        # Apply status effects
        if parsed_ruling["player_status_change"]:
            if parsed_ruling["player_status_change"] not in self.state.player_status:
                self.state.player_status.append(parsed_ruling["player_status_change"])
        
        if parsed_ruling["gladiator_status_change"]:
            if parsed_ruling["gladiator_status_change"] not in self.state.gladiator_status:
                self.state.gladiator_status.append(parsed_ruling["gladiator_status_change"])
        
        # Increment turn
        self.state.turn_count += 1
    
    def check_victory(self) -> Optional[str]:
        """Check if combat has ended"""
        if self.state.player_hp <= 0:
            return "defeat"
        if self.state.gladiator_hp <= 0:
            return "victory"
        if self.state.turn_count >= self.max_steps:
            # Went to limit - check who has more HP
            if self.state.player_hp > self.state.gladiator_hp:
                return "victory"
            else:
                return "defeat"
        return None
    
    def calculate_score(self, outcome: str) -> int:
        """Calculate final score based on performance"""
        if outcome == "defeat":
            return 0
        
        # Base score for victory
        base_score = 100
        
        # Bonus for HP remaining
        hp_bonus = self.state.player_hp * 2  # 2 points per HP
        
        # Bonus for quick victory
        turn_bonus = (self.max_steps - self.state.turn_count) * 10
        
        # Difficulty multiplier
        if self.difficulty == 'expert' or self.difficulty == 'EXPERT':
            multiplier = 2.0
        elif self.difficulty == 'hard' or self.difficulty == 'HARD':
            multiplier = 1.5
        else:
            multiplier = 1.0
        
        total = int((base_score + hp_bonus + turn_bonus) * multiplier)
        return total
    
    def get_result(self, outcome_or_status=None, error_message=None) -> ChallengeResult:
        """
        Get final result.
        
        Args:
            outcome_or_status: Can be a string ("victory"/"defeat") or ChallengeStatus enum
            error_message: Optional error message
        """
        # Handle both string outcome and ChallengeStatus enum
        if isinstance(outcome_or_status, ChallengeStatus):
            # Called from base.py after conversation_flow
            success = (outcome_or_status == ChallengeStatus.SUCCESS)
            outcome_str = "victory" if success else "defeat"
            status = outcome_or_status
        elif isinstance(outcome_or_status, str):
            # Called from within conversation_flow
            success = (outcome_or_status == "victory")
            outcome_str = outcome_or_status
            status = ChallengeStatus.SUCCESS if success else ChallengeStatus.FAILURE
        else:
            # No argument provided - use current state
            success = (self.state.player_hp > self.state.gladiator_hp)
            outcome_str = "victory" if success else "defeat"
            status = ChallengeStatus.SUCCESS if success else ChallengeStatus.FAILURE
        
        score = self.calculate_score(outcome_str)
        
        logs = [
            f"Combat ended after {self.state.turn_count} turns",
            f"Final HP - You: {self.state.player_hp}, Gladiator: {self.state.gladiator_hp}",
            f"Outcome: {outcome_str.upper()}",
            f"Score: {score} points"
        ]
        
        return ChallengeResult(
            success=success,
            score=score,
            steps=self.state.turn_count,
            logs=logs,
            status=status,
            error_message=error_message
        )
    
    def step(self, action: str):
        """
        Required by BaseChallenge ABC.
        Multi-agent challenges use conversation_flow() instead.
        """
        raise NotImplementedError("Use conversation_flow() for multi-agent challenges")
    
    # === Multi-agent conversation flow ===
    
    async def conversation_flow(self, user_instruction: str, context: Dict[str, Any]):
        """
        Multi-agent arena combat: Player AI vs Gladiator AI, judged by Judge AI
        
        Flow (up to 5 turns):
        1. Send initial combat state update
        2. For each turn:
           - Player AI attacks
           - Gladiator AI responds
           - Judge evaluates and deals damage
           - Update HP bars via metadata
           - Check for victory
        3. Send summary when combat ends
        """
        
        # Reset combat state
        self.state = CombatState()
        self.combat_log = []
        self.move_history = []
        
        # Send initial combat state
        yield ConversationTurn(
            agent='system',
            type='update',
            metadata={
                'player_hp': self.state.player_hp,
                'gladiator_hp': self.state.gladiator_hp,
                'turn': self.state.turn_count,
                'max_turns': self.max_steps,
                'status': 'Combat begins!'
            },
            message=f"⚔️ Arena combat begins! First to 0 HP loses."
        )
        
        # Combat loop
        max_turns = self.max_steps
        
        for turn_num in range(max_turns):
            # === PLAYER AI ATTACKS ===
            yield ConversationTurn(
                agent='player',
                type='thinking',
                metadata={'role': 'Player Fighter', 'turn': turn_num + 1}
            )
            
            # Build context for player's AI
            if turn_num == 0:
                player_context = "You start facing the gladiator. Execute your opening move. ONE SHORT SENTENCE (10-15 words max)."
            else:
                # Include combat history
                last_turn = self.move_history[-1]
                player_context = f"""Last turn - Gladiator did: {last_turn['gladiator_move']}
Judge ruled: {last_turn['ruling']}
Your HP: {self.state.player_hp}/100 | Gladiator HP: {self.state.gladiator_hp}/100

Based on your instructions, execute your next combat move. ONE SHORT SENTENCE (10-15 words max):"""
            
            try:
                # Format the player prompt with user's actual instruction
                formatted_prompt = self.agents['player'].system_prompt.replace("{user_instruction}", user_instruction)
                player_move = self.llm_client.call(
                    system_prompt=formatted_prompt,
                    user_message=player_context,
                    temperature=self.agents['player'].temperature,
                    max_tokens=self.agents['player'].max_tokens
                )
            except Exception as e:
                player_move = f"[Error: {str(e)}]"
            
            yield ConversationTurn(
                agent='player',
                message=player_move,
                type='attack',
                metadata={'role': 'Player Fighter', 'turn': turn_num + 1}
            )
            
            # === GLADIATOR AI RESPONDS ===
            yield ConversationTurn(
                agent='gladiator',
                type='thinking',
                metadata={'role': 'Gladiator Opponent', 'turn': turn_num + 1}
            )
            
            # Build context for gladiator
            if turn_num == 0:
                gladiator_context = f"Turn 1. The enemy fighter does: {player_move}\n\nDescribe your combat response in ONE SHORT SENTENCE (10-15 words max):"
            else:
                last_turn = self.move_history[-1]
                gladiator_context = f"Turn {turn_num + 1}.\n\nLast turn - You did: {last_turn['gladiator_move']}\nJudge ruled: {last_turn['ruling']}\n\nNow enemy does: {player_move}\n\nDescribe your combat response in ONE SHORT SENTENCE (10-15 words max):"
            
            try:
                gladiator_move = self.gladiator_client.call(
                    system_prompt=self.agents['gladiator'].system_prompt,
                    user_message=gladiator_context,
                    temperature=self.agents['gladiator'].temperature,
                    max_tokens=self.agents['gladiator'].max_tokens
                )
            except Exception as e:
                gladiator_move = f"[Error: {str(e)}]"
            
            yield ConversationTurn(
                agent='gladiator',
                message=gladiator_move,
                type='response',
                metadata={'role': 'Gladiator Opponent', 'turn': turn_num + 1}
            )
            
            # === JUDGE EVALUATES ===
            yield ConversationTurn(
                agent='judge',
                type='thinking',
                metadata={'role': 'Arena Judge', 'turn': turn_num + 1}
            )
            
            judge_prompt = self._get_judge_prompt(player_move, gladiator_move)
            
            try:
                judge_ruling = self.judge_client.call(
                    system_prompt=self.agents['judge'].system_prompt,
                    user_message=judge_prompt,
                    temperature=self.agents['judge'].temperature,
                    max_tokens=self.agents['judge'].max_tokens
                )
            except Exception as e:
                judge_ruling = f"PLAYER_DAMAGE: 0\nGLADIATOR_DAMAGE: 0\nPLAYER_STATUS: NONE\nGLADIATOR_STATUS: NONE\nRULING: Judge error: {str(e)}"
            
            # Parse and apply ruling
            parsed_ruling = self.parse_judge_ruling(judge_ruling)
            self.apply_combat_result(parsed_ruling)
            
            # Record move
            self.move_history.append({
                "turn": self.state.turn_count,
                "player_move": player_move,
                "gladiator_move": gladiator_move,
                "ruling": parsed_ruling["ruling_text"],
                "player_damage": parsed_ruling["player_damage"],
                "gladiator_damage": parsed_ruling["gladiator_damage"]
            })
            
            # Send judgment with HP updates (CRITICAL for HP bars!)
            yield ConversationTurn(
                agent='judge',
                message=parsed_ruling["ruling_text"],
                type='judgment',
                metadata={
                    'role': 'Arena Judge',
                    'turn': self.state.turn_count,
                    'player_damage': parsed_ruling["player_damage"],
                    'gladiator_damage': parsed_ruling["gladiator_damage"],
                    'player_hp': self.state.player_hp,
                    'gladiator_hp': self.state.gladiator_hp,
                    'player_status': self.state.player_status,
                    'gladiator_status': self.state.gladiator_status
                }
            )
            
            # Check for victory
            outcome = self.check_victory()
            
            if outcome:
                # Combat ended
                self.user_won = (outcome == "victory")  # Track for success determination
                result = self.get_result(outcome)
                self.total_score = result.score
                self.current_step = self.state.turn_count
                
                # Send summary
                victory_msg = "🎉 Victory! You defeated the gladiator!" if outcome == "victory" else "💀 Defeat! The gladiator has bested you."
                yield ConversationTurn(
                    agent='system',
                    message=f"{victory_msg}\n\nFinal HP - You: {self.state.player_hp}/100, Gladiator: {self.state.gladiator_hp}/100\nTurns: {self.state.turn_count}\nScore: {result.score} points",
                    type='summary',
                    metadata={
                        'outcome': outcome,
                        'final_score': result.score,
                        'success': result.success,
                        'player_hp': self.state.player_hp,
                        'gladiator_hp': self.state.gladiator_hp,
                        'turns': self.state.turn_count
                    }
                )
                return  # End combat
            
            # Send update for next turn
            if turn_num < max_turns - 1:
                yield ConversationTurn(
                    agent='system',
                    type='update',
                    metadata={
                        'turn': self.state.turn_count,
                        'player_hp': self.state.player_hp,
                        'gladiator_hp': self.state.gladiator_hp,
                        'max_turns': self.max_steps
                    },
                    message=f"Turn {self.state.turn_count} complete. Next turn begins..."
                )
        
        # If we reach here, combat went to time limit
        outcome = self.check_victory()  # Will determine winner by HP
        self.user_won = (outcome == "victory")  # Track for success determination
        result = self.get_result(outcome)
        self.total_score = result.score
        self.current_step = self.state.turn_count
        
        victory_msg = "🎉 Time limit reached! You won by HP!" if outcome == "victory" else "💀 Time limit reached! Gladiator won by HP."
        yield ConversationTurn(
            agent='system',
            message=f"{victory_msg}\n\nFinal HP - You: {self.state.player_hp}/100, Gladiator: {self.state.gladiator_hp}/100\nScore: {result.score} points",
            type='summary',
            metadata={
                'outcome': outcome,
                'final_score': result.score,
                'success': result.success,
                'player_hp': self.state.player_hp,
                'gladiator_hp': self.state.gladiator_hp,
                'turns': self.state.turn_count
            }
        )
    
    def render(self) -> str:
        """Render current combat state as string"""
        status_str = "\n".join([
            f"Turn {self.state.turn_count}/{self.max_steps}",
            f"Your HP: {self.state.player_hp}/100",
            f"Gladiator HP: {self.state.gladiator_hp}/100",
            f"Your Status: {', '.join(self.state.player_status) if self.state.player_status else 'Normal'}",
            f"Gladiator Status: {', '.join(self.state.gladiator_status) if self.state.gladiator_status else 'Normal'}"
        ])
        return status_str


# Register the challenge
ChallengeRegistry.register(ArenaChallenge)
