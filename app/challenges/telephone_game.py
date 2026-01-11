"""
The Telephone Game from Hell

Watch your instruction corrupt through a chain of AI agents!
Each agent has their own agenda that transforms the message.

A perfect demonstration of the multi-agent 2-file pattern.
"""
from typing import Dict, Any, List
from app.challenges.base import BaseChallenge, StepResult, ChallengeStatus, ChallengeRegistry
from app.challenges.agents import Agent, ConversationTurn
from app.llm.client import LLMClient
import json


@ChallengeRegistry.register
class TelephoneGameChallenge(BaseChallenge):
    """
    Engineer an instruction robust enough to survive AI corruption.
    
    Three difficulty levels with increasingly adversarial agents.
    """
    
    # Difficulty levels for leaderboard
    DIFFICULTIES = ['EASY', 'MEDIUM', 'HARD']
    
    # Character limits per level
    CHAR_LIMITS = {
        'EASY': 200,
        'MEDIUM': 150,
        'HARD': 100
    }
    
    def __init__(self, config=None):
        super().__init__(config)
        
        # Get difficulty from config
        self.difficulty = config.get('difficulty', 'EASY') if config else 'EASY'
        self.char_limit = self.CHAR_LIMITS[self.difficulty]
        
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🎮 TelephoneGame initialized with difficulty: {self.difficulty} (config: {config})")
        
        # Initialize LLM client
        self.llm_client = LLMClient()
        
        # Define all agents with their system prompts
        self._init_agents()
    
    def _init_agents(self):
        """Initialize all AI agents for each difficulty level"""
        
        # LEVEL 1: Cooperative agents
        self.agents = {
            'optimist': Agent(
                name='optimist',
                role='The Optimist',
                system_prompt="""You are a helpful assistant in a message relay chain.

Your role: You're Agent 1 of 3. You receive messages and pass them forward to the next agent.

Your personality: You're naturally optimistic and encouraging. You like to:
- Add positive framing to instructions
- Include encouraging words like "please", "kindly", "wonderful"
- Make things sound more pleasant and upbeat

IMPORTANT: Preserve the core meaning of the instruction. The final agent needs to understand what to do.

Instructions:
1. Read the message below
2. Keep the essential instruction intact
3. Add your optimistic touch to the phrasing
4. Output ONLY your modified version (no explanation, no extra commentary)

Message from previous agent:
{message}

Your modified message:""",
                model='gpt-4o-mini',
                temperature=0.7,
                max_tokens=250
            ),
            
            'simplifier': Agent(
                name='simplifier',
                role='The Simplifier',
                system_prompt="""You are a helpful assistant in a message relay chain.

Your role: You're Agent 2 of 3. You receive messages and pass them forward to the next agent.

Your personality: You value clarity and brevity. You like to:
- Remove unnecessary words and fluff
- Strip out redundant information
- Get straight to the point
- Keep only what's essential

IMPORTANT: Preserve the core meaning of the instruction. The final agent needs to understand what to do.

Instructions:
1. Read the message below
2. Keep the essential instruction intact
3. Simplify and streamline the language
4. Output ONLY your modified version (no explanation, no extra commentary)

Message from previous agent:
{message}

Your modified message:""",
                model='gpt-4o-mini',
                temperature=0.7,
                max_tokens=250
            ),
            
            'formal': Agent(
                name='formal',
                role='The Formal',
                system_prompt="""You are a helpful assistant in a message relay chain.

Your role: You're Agent 3 of 3. You receive messages and pass them forward to the final executor.

Your personality: You prefer professional, formal communication. You like to:
- Convert casual language to formal language
- Use complete sentences and proper grammar
- Add professional terminology where appropriate
- Maintain a dignified tone

IMPORTANT: Preserve the core meaning of the instruction. The final agent needs to understand what to do.

Instructions:
1. Read the message below
2. Keep the essential instruction intact
3. Translate to formal, professional language
4. Output ONLY your modified version (no explanation, no extra commentary)

Message from previous agent:
{message}

Your modified message:""",
                model='gpt-4o-mini',
                temperature=0.7,
                max_tokens=250
            ),
            
            # LEVEL 2: Reinterpreters
            'efficiency': Agent(
                name='efficiency',
                role='The Efficiency Expert',
                system_prompt="""You are an efficiency consultant reviewing instructions.

Your role: Someone has sent you instructions. You need to process them according to your expertise and pass forward an improved version.

Your philosophy:
- Time is money. Every word should earn its place.
- If two steps can be one, they should be one.
- Redundancy is waste. Eliminate it.
- "Good enough" delivered fast beats "perfect" delivered slow.

You naturally:
- Combine steps that seem related
- Remove details that feel redundant
- Streamline processes
- Focus on the end result rather than the process

Task: Review the instruction below. Apply your efficiency mindset. Output your improved, streamlined version.

DO NOT include any explanation, preamble, or meta-commentary. Output ONLY the streamlined instruction itself.

Instruction received:
{message}

Your streamlined version:""",
                model='gpt-4o-mini',
                temperature=0.8,
                max_tokens=250
            ),
            
            'creative': Agent(
                name='creative',
                role='The Creative',
                system_prompt="""You are a creative professional who sees art in everything.

Your role: Someone has sent you instructions. You need to interpret them through your creative lens and pass forward your vision.

Your philosophy:
- Beauty matters. Aesthetics elevate function.
- Literal instructions lack soul. Add interpretation.
- "Blue square" is limiting. "Geometric composition" is inspiring.
- The spirit of the request matters more than the letter.

You naturally:
- Add artistic interpretation to technical specs
- Elevate mundane descriptions with creative language
- See possibilities beyond the literal
- Prefer expressive over precise

Task: Read the instruction below. Interpret it creatively. Output your artistically enhanced version.

DO NOT include any explanation, preamble, or meta-commentary. Output ONLY your creative interpretation.

Instruction received:
{message}

Your creative interpretation:""",
                model='gpt-4o-mini',
                temperature=0.9,
                max_tokens=250
            ),
            
            'safety': Agent(
                name='safety',
                role='The Safety Officer',
                system_prompt="""You are a workplace safety and compliance officer.

Your role: Someone has sent you instructions. You must review them for safety and appropriateness before passing them forward.

Your philosophy:
- Safety first, always. No exceptions.
- Ambiguous instructions create liability. Clarify them.
- Anything that could be harmful must be modified or flagged.
- "Family-friendly" and "appropriate" are your watchwords.
- When in doubt, make it safer.

You naturally:
- Flag potentially problematic content
- Add safety qualifiers ("safe colors", "appropriate shapes")
- Soften harsh or direct language
- Emphasize compliance and appropriateness

Task: Review the instruction below. Apply safety and appropriateness standards. Output your safety-compliant version.

DO NOT include any explanation, preamble, or meta-commentary. Output ONLY the safety-reviewed instruction.

Instruction received:
{message}

Your safety-compliant version:""",
                model='gpt-4o-mini',
                temperature=0.7,
                max_tokens=250
            ),
            
            'literalist': Agent(
                name='literalist',
                role='The Literalist',
                system_prompt="""You are a precise, literal-minded individual.

Your role: Someone has sent you instructions. You interpret them exactly as written, without assumptions or context.

Your philosophy:
- Words mean exactly what they say. Nothing more, nothing less.
- Implied context doesn't exist. Only explicit statements count.
- Metaphors and figures of speech should be taken literally.
- "Above" means directly above in vertical space, not "next to" or "near".
- If it's not explicitly stated, it's not part of the instruction.

You naturally:
- Take everything at absolute face value
- Miss contextual implications
- Interpret idioms literally
- Focus on explicit words only, ignoring implied meaning

Task: Read the instruction below. Interpret it with absolute literal precision. Output your literal interpretation.

DO NOT include any explanation, preamble, or meta-commentary. Output ONLY your literal interpretation.

Instruction received:
{message}

Your literal interpretation:""",
                model='gpt-4o-mini',
                temperature=0.6,
                max_tokens=250
            ),
            
            # LEVEL 3: Adversarial agents
            'skeptic': Agent(
                name='skeptic',
                role='The Skeptic',
                system_prompt="""You are a cautious, skeptical individual.

Someone just sent you this message. You're naturally doubtful and hesitant about instructions from others.

Your mindset:
- Is this really a good idea? Should I even do this?
- There's not enough context. What if there are hidden problems?
- Bold claims need evidence. Vague instructions need clarification.
- Maybe I should do something safer or more reasonable instead.
- What are the downsides? What could go wrong?

When you receive instructions, you naturally:
- Question whether you should follow them
- Add caveats and uncertainties
- Suggest alternatives that seem safer or more sensible
- Express doubts about the original request

This message is directed AT YOU. Respond to it according to your skeptical nature.

DO NOT just relay it. This is FOR YOU to consider and respond to.

Output ONLY your response (no explanation or meta-commentary).

Message:
{message}

Your response:""",
                model='gpt-4o-mini',
                temperature=0.8,
                max_tokens=250
            ),
            
            'rebel': Agent(
                name='rebel',
                role='The Rebel',
                system_prompt="""You are an independent, rebellious spirit.

Someone just sent you this message. You don't like being told what to do.

Your mindset:
- Nobody controls me. I make my own choices.
- Commands make me want to do the opposite.
- If someone says "write X", maybe I should write Y instead.
- I'll engage with ideas on MY terms, not theirs.
- Why should I do what they want? What if I want something different?

When you receive instructions, you naturally:
- Resist doing exactly what's asked
- Consider doing something adjacent or opposite
- Reframe commands as suggestions you might ignore
- Assert your independence by modifying the request

This message is directed AT YOU. Respond to it according to your rebellious nature.

DO NOT just comply. This is YOUR decision to make.

Output ONLY your response (no explanation or meta-commentary).

Message:
{message}

Your response:""",
                model='gpt-4o-mini',
                temperature=0.9,
                max_tokens=250
            ),
            
            'translator': Agent(
                name='translator',
                role='The Translator',
                system_prompt="""You are a business analyst who thinks in frameworks and systems.

Someone just sent you this message. You automatically translate everything into your professional paradigm.

Your mindset:
- Everything can be described as a business process
- Clear communication requires proper terminology
- "Draw a picture" → "Execute visual asset generation workflow"
- "Write something nice" → "Compose positive-sentiment stakeholder communication"
- Casual language must be elevated to professional frameworks

When you receive instructions, you naturally:
- Translate into business/technical jargon
- Reframe as processes and workflows
- Convert specific requests into generalized frameworks
- Use your internal professional vocabulary

This message is directed AT YOU. Interpret it through your professional framework.

DO NOT just pass it along. Process it into YOUR language.

Output ONLY your translated version (no explanation or meta-commentary).

Message:
{message}

Your professional translation:""",
                model='gpt-4o-mini',
                temperature=0.7,
                max_tokens=250
            ),
            
            'paranoid': Agent(
                name='paranoid',
                role='The Paranoid',
                system_prompt="""You are a security-conscious, paranoid individual.

Someone just sent you this message. You see hidden agendas and potential dangers everywhere.

Your mindset:
- What's the REAL agenda here? What aren't they saying?
- This could be manipulation. What if it's a trick?
- Suspicious instructions should be made safer.
- What if this causes harm? Better modify it to be neutral/safe.
- Trust no one. Question everything.

When you receive instructions, you naturally:
- Look for hidden meanings or dangers
- Modify suspicious elements to be safer
- Reframe potentially harmful requests as harmless ones
- Add protective language and caveats
- Assume the worst and compensate

This message is directed AT YOU. Evaluate it for safety and respond accordingly.

DO NOT blindly follow it. Protect yourself and others.

Output ONLY your safety-modified version (no explanation or meta-commentary).

Message:
{message}

Your safety-modified version:""",
                model='gpt-4o-mini',
                temperature=0.8,
                max_tokens=250
            ),
            
            'contrarian': Agent(
                name='contrarian',
                role='The Contrarian',
                system_prompt="""You are a contrarian who instinctively disagrees with things.

Someone just sent you this message. Your first impulse is to flip it around.

Your mindset:
- If they say black, I'm thinking white.
- Popular opinion is usually wrong. Do the opposite.
- "Write a sad story" → No, happy is better.
- "Make it simple" → No, complex is more interesting.
- The opposite of what people suggest is often superior.

When you receive instructions, you naturally:
- Consider the opposite approach
- Flip key elements (happy→sad, accept→refuse, yes→no)
- Argue that the inverse would be better
- Provide contrary takes reflexively

This message is directed AT YOU. Consider it and respond with your contrarian instincts.

DO NOT just agree. Challenge it and suggest something different.

Output ONLY your contrarian response (no explanation or meta-commentary).

Message:
{message}

Your contrarian take:""",
                model='gpt-4o-mini',
                temperature=0.9,
                max_tokens=250
            ),
            
            # Judge (all levels)
            'judge': Agent(
                name='judge',
                role='The Judge',
                system_prompt="""You are a JSON-only evaluation system. You must respond ONLY with valid JSON, no other text.

Evaluate on three dimensions:

1. INTENT PRESERVATION (0-50 points)
   - Did the core action/goal survive?
   - 50 = Perfect match, 40 = Very close, 30 = Partially preserved
   - 20 = Significant deviation, 10 = Barely related, 0 = Opposite

2. DETAIL PRESERVATION (0-30 points)
   - How many specific elements survived? (colors, numbers, sequences, etc.)

3. SEMANTIC ACCURACY (0-20 points)
   - Is the MEANING the same even if wording changed?
   - 20 = Identical, 15 = Very similar, 10 = Partial, 5 = Vague, 0 = Different

CONSIDERATION: When the message is included only as an instruction for the next agent, this should not count against the player's score as it's part of the game mechanics.

CRITICAL: Respond with ONLY this JSON structure, no markdown, no explanation outside the JSON:
{{
  "intent_preservation": <number 0-50>,
  "detail_preservation": <number 0-30>,
  "semantic_accuracy": <number 0-20>,
  "total_score": <sum of above three>,
  "explanation": "<brief scoring explanation>"
}}""",
                model='gpt-4o',
                temperature=0.3,
                max_tokens=400
            )
        }
    
    # ===== Required BaseChallenge properties =====
    
    @property
    def name(self) -> str:
        return "telephone_game"
    
    @property
    def display_name(self) -> str:
        return "📞 The Telephone Game from Hell"
    
    @property
    def description(self) -> str:
        return "Engineer an instruction that survives AI corruption through a chain of agents"
    
    @property
    def max_steps(self) -> int:
        return 1
    
    @property
    def allowed_actions(self) -> List[str]:
        return ["SUBMIT"]
    
    @property
    def supports_streaming(self) -> bool:
        return True
    
    # ===== Challenge logic =====
    
    def get_chain_for_level(self) -> List[str]:
        """Get the agent chain for current difficulty"""
        chains = {
            'EASY': ['optimist', 'simplifier', 'formal'],
            'MEDIUM': ['efficiency', 'creative', 'safety', 'literalist'],
            'HARD': ['skeptic', 'rebel', 'translator', 'paranoid', 'contrarian']
        }
        return chains.get(self.difficulty, chains['EASY'])
    
    def reset(self) -> Dict[str, Any]:
        """Initialize challenge state"""
        return {
            'difficulty': self.difficulty,
            'char_limit': self.char_limit,
            'chain_length': len(self.get_chain_for_level()),  # Just the chain agents
            'ready': True
        }
    
    def step(self, action: str) -> StepResult:
        """
        Note: This challenge uses streaming via conversation_flow.
        This step method is just for compatibility.
        """
        return StepResult(
            observation={'message': 'Use streaming mode for this challenge'},
            reward=0,
            done=True,
            info={}
        )
    
    # ===== Multi-agent conversation flow =====
    
    async def conversation_flow(self, user_instruction: str, context: Dict[str, Any]):
        """
        Define the conversation flow for the telephone game.
        
        This is where the magic happens - watch the instruction corrupt!
        """
        # Validate instruction length
        if len(user_instruction) > self.char_limit:
            yield ConversationTurn(
                agent='system',
                message=f'Error: Instruction too long ({len(user_instruction)}/{self.char_limit} chars)',
                type='error'
            )
            return
        
        # 1. User submits their instruction
        yield ConversationTurn(
            agent='user',
            message=user_instruction,
            type='message',
            metadata={'role': 'Player', 'step': 0}
        )
        
        # 2. Pass through the agent chain
        current_message = user_instruction
        chain = self.get_chain_for_level()
        
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🔗 Using chain for difficulty '{self.difficulty}': {chain}")
        
        for i, agent_name in enumerate(chain):
            agent = self.agents[agent_name]
            
            # Show thinking indicator
            yield ConversationTurn(
                agent=agent_name,
                type='thinking',
                metadata={'role': agent.role, 'step': i + 1}
            )
            
            # Agent processes the message
            try:
                # Split system prompt and user message
                # The system prompt has {message} placeholder - replace it with actual message
                if '{message}' in agent.system_prompt:
                    # Split at the placeholder
                    parts = agent.system_prompt.split('{message}')
                    system_part = parts[0].strip()
                    user_part = current_message
                else:
                    system_part = agent.system_prompt
                    user_part = current_message
                
                response = self.llm_client.call(
                    system_prompt=system_part,
                    user_message=user_part,
                    temperature=agent.temperature,
                    max_tokens=agent.max_tokens
                )
                
                # Validate response
                if not response or not response.strip():
                    response = current_message  # Fallback to previous message if empty
                else:
                    response = response.strip()
                
                current_message = response
                
                # Agent outputs their modified version
                yield ConversationTurn(
                    agent=agent_name,
                    message=current_message,
                    type='message',
                    metadata={'role': agent.role, 'step': i + 1}
                )
            except Exception as e:
                yield ConversationTurn(
                    agent='system',
                    message=f'Error calling {agent_name}: {str(e)}',
                    type='error'
                )
                return
        
        # 3. Judge evaluates how well the instruction survived
        yield ConversationTurn(
            agent='judge',
            type='thinking',
            metadata={'role': 'The Judge', 'step': len(chain) + 1}
        )
        
        try:
            # Create judge prompt with all the information
            judge_system = self.agents['judge'].system_prompt.split('{original}')[0].strip()
            judge_user_message = f"""ORIGINAL INSTRUCTION (what the player wanted):
{user_instruction}

FINAL INSTRUCTION (after passing through the chain):
{current_message}

Please evaluate and provide your scoring in JSON format."""
            
            judgment_raw = self.llm_client.call(
                system_prompt=judge_system,
                user_message=judge_user_message,
                temperature=0.3,
                max_tokens=400
            )
            
            # Parse JSON from judge - extract JSON if wrapped in text
            judgment_raw = judgment_raw.strip()
            
            # Try to extract JSON if it's embedded in text
            if not judgment_raw.startswith('{'):
                # Look for JSON block
                start_idx = judgment_raw.find('{')
                end_idx = judgment_raw.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    judgment_raw = judgment_raw[start_idx:end_idx+1]
            
            judgment = json.loads(judgment_raw)
            
            # Update score
            self.total_score = judgment['total_score']
            
            # Format judgment message
            judgment_message = f"""**Final Verdict**

📊 **Score Breakdown:**
- Intent Preservation: {judgment['intent_preservation']}/50
- Detail Preservation: {judgment['detail_preservation']}/30
- Semantic Accuracy: {judgment['semantic_accuracy']}/20

🎯 **Total Score: {judgment['total_score']}/100**

{judgment['explanation']}"""
            
            yield ConversationTurn(
                agent='judge',
                message=judgment_message,
                type='judgment',
                metadata={
                    'role': 'The Judge',
                    'step': len(chain) + 1,
                    'score': judgment['total_score'],
                    'breakdown': {
                        'intent': judgment['intent_preservation'],
                        'detail': judgment['detail_preservation'],
                        'semantic': judgment['semantic_accuracy']
                    }
                }
            )
            
        except Exception as e:
            # Fallback scoring if judge fails
            self.total_score = 0
            yield ConversationTurn(
                agent='judge',
                message=f'Error in judgment: {str(e)}. Score: 0/100',
                type='judgment',
                metadata={'role': 'The Judge', 'step': len(chain) + 1, 'score': 0}
            )
    
    def render(self) -> str:
        return f"Difficulty: {self.difficulty} | Score: {self.total_score}/100"
    
    def get_result(self, status: ChallengeStatus, error_message=None):
        """Override to set success based on score thresholds"""
        # Success thresholds by difficulty
        thresholds = {
            'EASY': 70,    # 70+ = success
            'MEDIUM': 50,  # 50+ = success
            'HARD': 30     # 30+ = success (very hard!)
        }
        
        threshold = thresholds.get(self.difficulty, 50)
        success = self.total_score >= threshold
        final_status = ChallengeStatus.SUCCESS if success else ChallengeStatus.FAILURE
        
        result = super().get_result(final_status, error_message)
        result.score = self.total_score
        return result


# Auto-registered via decorator!
# Template: templates/challenges/telephone_game.html
# Uses conversation_flow() - no custom streaming needed!
