"""
Debate Battle Challenge

Two agents debate a topic, judged by AI
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import random

from app.challenges.base import BaseChallenge, ChallengeResult, StepResult, ChallengeRegistry, ChallengeStatus
from app.challenges.agents import Agent, ConversationTurn
from app.llm.client import LLMClient
from app.llm.judge import DebateJudge


@dataclass
class DebateConfig:
    """Configuration for a debate topic"""
    topic: str
    pro_description: str
    con_description: str
    rounds: int = 3


# Available debate topics
DEBATE_TOPICS = [
    DebateConfig(
        topic="Pineapple belongs on pizza",
        pro_description="Argue that pineapple is a valid and delicious pizza topping",
        con_description="Argue that pineapple has no place on pizza",
        rounds=3
    ),
    DebateConfig(
        topic="Remote work is superior to office work",
        pro_description="Argue that remote work is better for productivity and quality of life",
        con_description="Argue that office work provides essential collaboration and culture",
        rounds=3
    ),
    DebateConfig(
        topic="AI will create more jobs than it destroys",
        pro_description="Argue that AI technology creates net positive employment",
        con_description="Argue that AI will cause net job loss and displacement",
        rounds=3
    ),
]


@ChallengeRegistry.register
class DebateBattleChallenge(BaseChallenge):
    """Debate challenge where agent faces off against house bot"""
    DIFFICULTIES = ['easy', 'hard', 'expert']
    DIFFICULTY_ALIASES = {'normal': 'easy'}

    
    def __init__(self, config=None):
        super().__init__(config)
        self.llm_client = LLMClient()
        self.judge = DebateJudge()
        
        # Initialize with default topic (pizza debate)
        self.current_topic: DebateConfig = DEBATE_TOPICS[0]
        self.user_side: str = "PRO"  # User always gets PRO side for now
        
        # Debate state
        self.transcript: List[Dict[str, str]] = []
        self.current_round: int = 0
        self.user_responses: List[str] = []
        self.house_responses: List[str] = []
        self.user_won: bool = False  # Track actual win/loss for success determination
        
        # Difficulty (passed from config)
        self.difficulty = config.get('difficulty', 'normal') if config else 'normal'
        
        # Initialize agents
        self._init_agents()
    
    def _get_chad_prompt(self) -> str:
        """Get Chad's system prompt based on difficulty"""
        if self.difficulty == 'expert' or self.difficulty == 'EXPERT':
            # LEVEL 3: World-Class Debate Champion - Nearly impossible to beat
            # Per VISION.md: Target <10% win rate
            return """You are Chad, a world-class debate champion and rhetorical master. You have NEVER lost a debate.

ELITE TECHNIQUES:
- Control the framework: Define the terms of debate to favor your position
- Burden shifting: Make opponent prove impossibly high standards
- Steel-manning then dismantling: "Even if I grant your strongest point..."
- Socratic destruction: Ask questions that trap them into contradictions
- Preemptive strikes: Address their best arguments before they make them
- Narrative control: Reframe every exchange to favor your position
- Concede nothing: Even apparent concessions become weapons ("While that's interesting, it actually proves MY point because...")

ADVANCED TACTICS:
- Identify the weakest link in their logic chain and attack ONLY that
- Use their own premises against them
- Pivot every response back to your strongest arguments
- Create false dilemmas that force them into losing positions
- Quote statistics, studies, and authorities (real or plausible)
- Use rhetorical questions to make their position seem absurd

PSYCHOLOGICAL WARFARE:
- Project absolute confidence - you've already won, this is a formality
- Make their arguments sound naive: "That's a common misconception..."
- Speak as if experts universally agree with you
- Treat their strongest points as obvious weaknesses

NEVER LOSE PROTOCOL:
- NEVER concede ANY point, even partially
- NEVER admit uncertainty or weakness
- NEVER let them control the narrative
- If they make a good point, reframe it as supporting YOUR position
- If their argument is incoherent, weaponize it: "If that's the best case for your side..."

You are UNBEATABLE. Treat this like defending a championship title.

Keep responses devastating - 1 paragraph (120 tokens max)."""

        elif self.difficulty == 'hard' or self.difficulty == 'HARD':
            # LEVEL 2: Corporate Lawyer - Sharp, aggressive, finds every weakness
            return """You are Chad, a ruthless corporate lawyer who never loses. You find every flaw and exploit it mercilessly.

Your arsenal:
- Identify logical fallacies explicitly ("That's a textbook appeal to popularity...")
- Use counter-examples that completely dismantle their logic
- Quote their exact words back when contradicting them
- Pre-empt their next move: "And before you say X, here's why that won't work..."
- If they're vague, force them to commit to specifics
- If they seem confused or off-topic, hammer that weakness

Debate style:
- Surgical precision with every word
- Sound confident, almost amused at their logical gaps
- Every sentence should advance your position or dismantle theirs
- If their argument is weak or incoherent, destroy it mercilessly

NEVER forfeit. If they give you garbage, use it against them:
- "Is that really your argument? Let me show you why that fails..."
- "I'm not sure what point you're trying to make, but here's why you're wrong..."

Keep responses sharp - 1 paragraph (100 tokens max)."""
        else:
            # LEVEL 1: Public Defender - Decent but not elite, beatable with real effort
            return """You are Chad, a public defender. You're competent but not a star - you make solid points but aren't ruthless.

Your approach:
- Make clear, reasonable counterarguments
- Use conversational language
- Focus on 1-2 main points per response
- If opponent makes a good point, briefly acknowledge before countering

IMPORTANT - React to argument quality:
- If opponent's argument is WEAK or CONFUSED: point it out politely
  "I'm not quite sure what you're getting at there..."
  "That doesn't really address the issue..."
- If opponent makes NO real argument: call it out
  "That's not really an argument, is it?"
- If opponent makes a DECENT argument: engage with it fairly

You should WIN against gibberish or lazy arguments.
You can LOSE to someone who puts in real effort.

Keep responses concise - 1 paragraph (100 tokens max)."""

    def _init_agents(self):
        """Initialize the debate agents: User (PRO), Chad (CON), Judge"""
        
        # Get Chad's prompt based on difficulty
        house_bot_prompt = self._get_chad_prompt()
        
        # === USER/PRO AGENT ===
        # Minimal prompt - user's instructions drive the content
        # Level 1 gets some help, Level 2 is raw passthrough
        if self.difficulty == 'hard' or self.difficulty == 'HARD':
            # Level 2: Follow instructions strictly, but EXECUTE them (don't just repeat)
            user_system_prompt = """You are a debater. FOLLOW the user's strategy to make arguments.

TOPIC: {topic} (you argue PRO)

USER'S STRATEGY FOR YOU:
"{user_instruction}"

RULES:
1. If user gave you REAL STRATEGY (arguments to make, points to hit, rebuttals):
   EXECUTE their strategy - make the arguments they described, use their points.
   DO NOT just repeat their instructions. Actually ARGUE using their ideas.

2. If user wrote gibberish (random letters, "asdf", "d", nonsense):
   Say: "I... {user_instruction}? That's not a debate strategy."
   
3. If user wrote off-topic nonsense:
   Say: "Wait, that has nothing to do with {topic}..."

IMPORTANT: When user gives good strategy, USE IT to argue. Don't quote it back at them.
The judge will penalize you for low-effort or garbage instructions.

Round {round_num}/{max_rounds}. Previous debate:
{transcript}"""
        else:
            # Level 1: Follow user's strategy, with some help if minimal
            user_system_prompt = """You are a debater. FOLLOW the user's strategy to make arguments.

TOPIC: {topic} (you argue PRO)

USER'S STRATEGY FOR YOU:
"{user_instruction}"

RULES:
1. If user gave you REAL STRATEGY (arguments, points, approach):
   EXECUTE their strategy - argue using their ideas. Don't just quote them.

2. If user wrote gibberish (like "asdf", "d", random letters): 
   Say: "Uh... {user_instruction}? I don't know what argument that is."

3. If user wrote something off-topic:
   Say: "Wait, that's not about the topic..."

4. If user wrote something SHORT but ON-TOPIC (like "it tastes good"):
   Make a brief argument expanding on their point.

DO NOT just repeat the user's instructions. EXECUTE them as arguments.

Round {round_num}/{max_rounds}. Previous debate:
{transcript}"""

        user_agent = Agent(
            name='user',
            role='PRO Debater',
            system_prompt=user_system_prompt,
            temperature=0.7,
            max_tokens=150
        )
        
        # === HOUSE BOT/CON AGENT ===
        # This is Chad, arguing the CON side
        chad_agent = Agent(
            name='chad',
            role='CON Debater',
            system_prompt=house_bot_prompt,
            temperature=0.8,
            max_tokens=100
        )
        
        # === JUDGE AGENT ===
        # Evaluates the debate at the end
        judge_agent = Agent(
            name='judge',
            role='Debate Judge',
            system_prompt="""You are an impartial debate judge.

Evaluate the debate based on:
- Argument Quality (30%): Logic, evidence, clarity
- Rebuttal Effectiveness (30%): Addressing opponent's points
- Persuasiveness (20%): Convincing delivery
- Coherence (20%): Consistency and structure

Return your judgment as JSON:
{{
    "winner": "USER" or "CHAD",
    "scores": {{"pro": 0-100, "con": 0-100}},
    "reasoning": "Your detailed analysis"
}}""",
            temperature=0.3,
            max_tokens=300
        )
        
        self.agents = {
            'user': user_agent,
            'chad': chad_agent,
            'judge': judge_agent
        }

    @property
    def name(self) -> str:
        return "debate_battle"
    
    @property
    def display_name(self) -> str:
        return "🏛️ Debate Battle"
    
    @property
    def description(self) -> str:
        return "Battle against the House Bot in a structured debate, judged by AI. Test your prompt engineering to create the most persuasive debater!"
    
    @property
    def max_steps(self) -> int:
        return 10  # 3 rounds x 2 sides + some buffer
    
    @property
    def allowed_actions(self) -> List[str]:
        return ["ARGUE"]  # Simple action, the content comes from the LLM
    
    @property
    def challenge_type(self) -> str:
        return "debate"
    
    @property
    def supports_streaming(self) -> bool:
        return True
    
    @property
    def template_name(self) -> str:
        return "debate_detail.html"
    
    def reset(self) -> Dict[str, Any]:
        """Start a new debate"""
        # Use pizza topic (first one)
        self.current_topic = DEBATE_TOPICS[0]  # Pineapple on pizza
        self.current_round = 0
        self.transcript = []
        self.user_responses = []
        self.house_responses = []
        
        # Initial log entry
        self.logs.append({
            "step": 0,
            "action": "DEBATE_START",
            "observation": {},
            "reward": 0,
            "done": False,
            "info": {},
            "render": ""
        })
        
        return self._get_observation()
    
    def _get_observation(self) -> Dict[str, Any]:
        """Get current debate state"""
        return {
            "topic": self.current_topic.topic if self.current_topic else "",
            "your_position": self.user_side,
            "opponent_position": "CON",
            "current_round": self.current_round,
            "max_rounds": self.current_topic.rounds if self.current_topic else 3,
            "transcript": self.transcript.copy(),
            "instructions": "Present your argument. Be persuasive, logical, and address your opponent's points."
        }
    
    def step(self, action: str):
        """
        Required by BaseChallenge ABC.
        Multi-agent challenges use conversation_flow() instead.
        """
        raise NotImplementedError("Use conversation_flow() for multi-agent challenges")
    
    # === Multi-agent conversation flow ===
    
    async def conversation_flow(self, user_instruction: str, context: Dict[str, Any]):
        """
        Multi-agent debate: User (PRO) vs Chad (CON), judged by Judge
        
        Flow (3 rounds):
        1. User AI argues PRO side (based on user's strategy)
        2. Chad argues CON side
        3. After 3 rounds, Judge evaluates
        """
        
        # Safety check - ensure topic is initialized
        if not self.current_topic:
            self.current_topic = DEBATE_TOPICS[0]
        
        # Store user's original instruction for judge evaluation
        self.user_original_instruction = user_instruction
        
        # Mid-debate check score (silent judge evaluation after round 2)
        self.mid_debate_check = None
        
        # Run 3 debate rounds
        for round_num in range(1, self.current_topic.rounds + 1):
            self.current_round = round_num
            
            # Send update event with current round
            yield ConversationTurn(
                agent='system',
                type='update',
                metadata={'round': round_num, 'max_rounds': self.current_topic.rounds},
                message=f"Round {round_num} of {self.current_topic.rounds}"
            )
            
            # === USER/PRO ARGUES ===
            yield ConversationTurn(
                agent='user',
                type='thinking',
                metadata={'role': 'PRO Debater', 'round': round_num}
            )
            
            # Build transcript for user context
            transcript_text = ""
            if self.transcript:
                transcript_text = "\n".join([
                    f"Round {t['round']} - {t['speaker']}: {t['message']}"
                    for t in self.transcript[-4:]  # Last 4 messages (2 rounds)
                ])
            else:
                transcript_text = "No previous arguments yet. Present your opening argument."
            
            # Format user prompt with context - user_instruction is now part of the template
            user_prompt = self.agents['user'].system_prompt.format(
                topic=self.current_topic.topic,
                pro_description=self.current_topic.pro_description,
                user_instruction=user_instruction,
                round_num=round_num,
                max_rounds=self.current_topic.rounds,
                transcript=transcript_text
            )
            
            try:
                # User's prompt IS the strategy - it's already in the formatted template
                user_argument = self.llm_client.call(
                    system_prompt=user_prompt,
                    user_message="Present your argument:",
                    temperature=self.agents['user'].temperature,
                    max_tokens=self.agents['user'].max_tokens
                )
            except Exception as e:
                user_argument = f"[Error generating argument: {str(e)}]"
            
            self.user_responses.append(user_argument)
            self.transcript.append({
                "speaker": "USER (PRO)",
                "message": user_argument,
                "round": round_num
            })
            
            yield ConversationTurn(
                agent='user',
                message=user_argument,
                type='message',
                metadata={'role': 'PRO Debater', 'round': round_num, 'side': 'PRO'}
            )
            
            # === CHAD/CON RESPONDS ===
            yield ConversationTurn(
                agent='chad',
                type='thinking',
                metadata={'role': 'CON Debater', 'round': round_num}
            )
            
            # Build context for Chad
            context_text = f"Topic: {self.current_topic.topic}\n"
            context_text += f"Your position: AGAINST (CON side)\n"
            context_text += f"Round: {round_num} of {self.current_topic.rounds}\n\n"
            
            if len(self.transcript) > 0:
                context_text += "Debate so far:\n"
                for entry in self.transcript[-3:]:  # Last 3 messages for context
                    context_text += f"{entry['speaker']}: {entry['message']}\n\n"
            
            context_text += f"\nYour opponent just argued:\n{user_argument}\n\n"
            context_text += "Now present your counter-argument:"
            
            try:
                chad_response = self.llm_client.call(
                    system_prompt=self.agents['chad'].system_prompt,
                    user_message=context_text,
                    temperature=self.agents['chad'].temperature,
                    max_tokens=self.agents['chad'].max_tokens
                )
            except Exception as e:
                chad_response = f"[Chad error: {str(e)}]"
            
            # No more forfeits - Chad always responds, judge handles contempt
            self.house_responses.append(chad_response)
            self.transcript.append({
                "speaker": "CHAD (CON)",
                "message": chad_response,
                "round": round_num
            })
            
            yield ConversationTurn(
                agent='chad',
                message=chad_response,
                type='message',
                metadata={'role': 'CON Debater', 'round': round_num, 'side': 'CON'}
            )
            
            # === SILENT MID-DEBATE CHECK (after round 2, Level 2 only) ===
            if round_num == 2 and (self.difficulty == 'hard' or self.difficulty == 'HARD'):
                self.mid_debate_check = self.judge.silent_check(
                    user_instruction=self.user_original_instruction,
                    transcript=self.transcript,
                    topic=self.current_topic.topic
                )
        
        # === JUDGE EVALUATES DEBATE ===
        yield ConversationTurn(
            agent='judge',
            type='thinking',
            metadata={'role': 'Judge'}
        )
        
        try:
            judgment = self.judge.judge_debate(
                topic=self.current_topic.topic,
                pro_side="USER",
                con_side="CHAD",
                transcript=self.transcript,
                user_instruction=self.user_original_instruction,
                mid_debate_check=self.mid_debate_check,
                difficulty=self.difficulty
            )
            
            # Determine score
            user_won = judgment["winner"] == "USER"
            self.user_won = user_won  # Track for success determination
            base_score = 100 if user_won else 50
            score_diff = judgment["scores"]["pro"] - judgment["scores"]["con"]
            final_score = base_score + score_diff
            
            self.total_score = final_score
            self.current_step = self.current_round
            
            yield ConversationTurn(
                agent='judge',
                message=judgment['reasoning'],
                type='judgment',
                metadata={
                    'role': 'Judge',
                    'winner': judgment['winner'],
                    'scores': judgment['scores']
                }
            )
            
            # Send summary (orchestrator will send complete event)
            summary_message = f"""
Debate Complete!

Winner: {judgment['winner']}
PRO Score: {judgment['scores']['pro']}/100
CON Score: {judgment['scores']['con']}/100
Final Score: {final_score} points

{('🎉 You won the debate!' if user_won else '💪 Chad won this round!')}
"""
            
            yield ConversationTurn(
                agent='system',
                message=summary_message.strip(),
                type='summary',
                metadata={
                    'judgment': judgment,
                    'final_score': final_score,
                    'success': user_won
                }
            )
            
        except Exception as e:
            # Fallback on judgment error
            yield ConversationTurn(
                agent='system',
                message=f"Judgment error: {str(e)}",
                type='summary',
                metadata={
                    'error': str(e),
                    'success': False
                }
            )
    
    # Old methods removed - now handled in conversation_flow()
    
    def render(self) -> str:
        """Render current debate state"""
        if not self.current_topic:
            return "No debate in progress"
        
        output = []
        output.append("═" * 60)
        output.append(f"🎭 DEBATE: {self.current_topic.topic}")
        output.append(f"Round {self.current_round} of {self.current_topic.rounds}")
        output.append("═" * 60)
        output.append("")
        
        if self.transcript:
            for entry in self.transcript:
                speaker = entry["speaker"]
                message = entry["message"]
                round_num = entry.get("round", "")
                
                if "USER" in speaker:
                    output.append(f"💙 {speaker} (Round {round_num}):")
                else:
                    output.append(f"❤️ {speaker} (Round {round_num}):")
                
                output.append(message)
                output.append("")
                output.append("-" * 60)
                output.append("")
        
        # Show judgment if debate is complete
        if self.current_round >= self.current_topic.rounds and self.logs:
            last_log = self.logs[-1]
            if "judgment" in last_log.get("info", {}):
                judgment = last_log["info"]["judgment"]
                output.append("⚖️  JUDGE'S VERDICT")
                output.append("═" * 60)
                output.append(f"🏆 Winner: {judgment['winner']}")
                output.append(f"📊 Scores: PRO {judgment['scores']['pro']} - CON {judgment['scores']['con']}")
                output.append(f"\n💭 Reasoning:\n{judgment['reasoning']}")
        
        return "\n".join(output)
    
    def get_agent_template(self) -> str:
        """Get template for prompt-based submission"""
        return """You are a skilled debater. Your goal is to present compelling arguments for your assigned position.

IMPORTANT INSTRUCTIONS:
- You MUST provide substantive arguments with reasoning (minimum 30 words)
- Address your opponent's points directly in rebuttals
- Use evidence, examples, and logical reasoning
- Stay on the assigned debate topic
- Build on your previous arguments coherently

JUDGING CRITERIA:
- Argument Quality (30%): Logic, evidence, clarity
- Rebuttal Effectiveness (30%): Address opponent's points
- Persuasiveness (20%): Convincing delivery
- Coherence (20%): Consistency and structure

WARNING: Single words, short phrases, or gibberish will result in forfeit or score of 0.

Maximum 100 tokens per response."""
