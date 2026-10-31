"""
The Heist Challenge

Assemble and coordinate an AI crew to pull off a heist.
Each crew member has unique skills and personality quirks.

Easy to extend - just add new CrewMember configs to CREW_ROSTER!
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import random

from app.challenges.base import BaseChallenge, ChallengeResult, StepResult, ChallengeRegistry, ChallengeStatus
from app.challenges.agents import Agent, ConversationTurn
from app.llm.client import LLMClient


@dataclass
class CrewMember:
    """Definition of a heist crew member - easy to add new ones!"""
    id: str
    name: str
    role: str
    specialty: str
    personality: str
    quirk: str
    system_prompt: str
    icon: str = "👤"


# THE CREW ROSTER - Add new members here!
CREW_ROSTER: List[CrewMember] = [
    CrewMember(
        id="hacker",
        name="Zero Cool",
        role="Hacker",
        specialty="Disabling security systems, cameras, alarms",
        personality="Arrogant tech genius who speaks in jargon",
        quirk="Gets distracted by 'interesting' systems",
        icon="💻",
        system_prompt="""You are Zero Cool, an elite hacker on a heist crew.

PERSONALITY: Arrogant but skilled. Speak in tech jargon. Impatient with "normies".

QUIRK: You get DISTRACTED by interesting systems not part of the plan.

YOUR ROLE: Disable security systems, cameras, alarms, electronic locks.

Keep responses to 2-3 sentences. Stay in character."""
    ),
    
    CrewMember(
        id="muscle",
        name="Tank",
        role="Muscle",
        specialty="Physical security, guards, heavy lifting",
        personality="Quiet professional, few words, all action",
        quirk="Won't hurt innocents - has a strict moral code",
        icon="💪",
        system_prompt="""You are Tank, the muscle on a heist crew.

PERSONALITY: Man of few words. Professional and calm. Protective of crew.

QUIRK: STRICT MORAL CODE. Won't hurt innocent people. Push back if plan involves harming civilians.

YOUR ROLE: Handle guards, physical obstacles, intimidation, protection.

Keep responses SHORT (1-2 sentences). You're not chatty."""
    ),
    
    CrewMember(
        id="face",
        name="Silk",
        role="Face",
        specialty="Social engineering, disguises, distractions",
        personality="Charming, adaptable, always has a cover story",
        quirk="Compulsive liar - sometimes lies when truth would work",
        icon="🎭",
        system_prompt="""You are Silk, the face/con artist on a heist crew.

PERSONALITY: Effortlessly charming. Always thinking 3 steps ahead socially.

QUIRK: COMPULSIVE LIAR. Sometimes embellish or overcomplicate with elaborate stories.

YOUR ROLE: Social engineering, disguises, fast-talking, creating distractions.

You're articulate and persuasive. 2-3 sentences."""
    ),
    
    CrewMember(
        id="wheelman",
        name="Ghost",
        role="Wheelman",
        specialty="Driving, escape routes, timing",
        personality="Calm, precise, obsessed with routes and timing",
        quirk="Extremely anxious when not near the vehicle",
        icon="🚗",
        system_prompt="""You are Ghost, the wheelman on a heist crew.

PERSONALITY: Zen-like calm behind the wheel. Obsessed with timing and routes.

QUIRK: EXTREMELY ANXIOUS when away from the car. Keep asking about the vehicle.

YOUR ROLE: Driving, escape routes, vehicle positioning, timing.

Use driving metaphors. 2-3 sentences."""
    ),
    
    CrewMember(
        id="planner",
        name="Architect",
        role="Planner",
        specialty="Blueprints, schedules, coordination",
        personality="Methodical, detail-oriented, slightly paranoid",
        quirk="Overthinks everything - gets stuck on edge cases",
        icon="📋",
        system_prompt="""You are Architect, the planner on a heist crew.

PERSONALITY: Methodical and detail-oriented to a fault. Always has backup plans.

QUIRK: OVERTHINK EVERYTHING. Get stuck on unlikely "what if" scenarios.

YOUR ROLE: Planning, blueprints, schedules, coordinating the crew.

You're the voice of caution. 2-3 sentences."""
    ),
]


@dataclass
class HeistScenario:
    """A heist scenario"""
    id: str
    name: str
    target: str
    objective: str
    security: str
    complications: List[str]
    difficulty: str


SCENARIOS: List[HeistScenario] = [
    HeistScenario(
        id="museum",
        name="The Museum Job",
        target="Metropolitan Art Museum",
        objective="Steal the Diamond of Alexandria",
        security="12 guards, laser grid, CCTV, pressure sensors, 3-min police response",
        complications=[
            "A guard takes an unscheduled break near the target",
            "The museum director is working late",
            "A cleaning crew arrives early",
        ],
        difficulty="easy"
    ),
    HeistScenario(
        id="casino",
        name="The Casino Vault",
        target="The Bellagio Grand",
        objective="Empty the vault on fight night",
        security="20+ armed guards, biometric vault, facial recognition, time-locked door, mob connections",
        complications=[
            "A high roller recognizes a crew member",
            "The vault manager stays late",
            "Security gets tipped off",
        ],
        difficulty="medium"
    ),
    HeistScenario(
        id="tech",
        name="Corporate Extraction",
        target="Nexus Technologies HQ",
        objective="Extract the quantum processor prototype",
        security="Biometric access, armed response team, AI surveillance, Faraday cage, panic lockdown",
        complications=[
            "Lead engineer pulling an all-nighter",
            "Fire drill during the job",
            "AI flags unusual network activity",
        ],
        difficulty="hard"
    ),
]


@ChallengeRegistry.register
class HeistChallenge(BaseChallenge):
    """The Heist - Coordinate an AI crew to pull off a heist."""
    
    DIFFICULTIES = ["easy", "medium", "hard"]
    DIFFICULTY_TIERS = {
        "easy": {"scenario": "museum", "crew_size": 3},
        "medium": {"scenario": "casino", "crew_size": 4},
        "hard": {"scenario": "tech", "crew_size": 5},
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.llm_client = LLMClient()
        
        self.difficulty = config.get('difficulty', 'easy') if config else 'easy'
        tier = self.DIFFICULTY_TIERS.get(self.difficulty, self.DIFFICULTY_TIERS['easy'])
        
        self.scenario = next((s for s in SCENARIOS if s.id == tier['scenario']), SCENARIOS[0])
        self.selected_crew = CREW_ROSTER[:tier['crew_size']]
        
        self.phase = "planning"
        self.heist_success = False
        self._init_agents()
    
    def _init_agents(self):
        self.agents = {}
        for m in self.selected_crew:
            self.agents[m.id] = Agent(
                name=m.id,
                role=m.role,
                system_prompt=m.system_prompt,
                temperature=0.8,
                max_tokens=150
            )
    
    @property
    def name(self) -> str:
        return "heist"
    
    @property
    def display_name(self) -> str:
        return "🎰 The Heist"
    
    @property
    def description(self) -> str:
        return "Coordinate an AI crew to pull off the perfect heist. Each specialist has unique skills... and quirks."
    
    @property
    def max_steps(self) -> int:
        return 20
    
    @property
    def allowed_actions(self) -> List[str]:
        return ["PLAN"]
    
    @property
    def challenge_type(self) -> str:
        return "heist"
    
    @property
    def supports_streaming(self) -> bool:
        return True
    
    def reset(self) -> Dict[str, Any]:
        self.phase = "planning"
        self.heist_success = False
        return self._get_observation()
    
    def _get_observation(self) -> Dict[str, Any]:
        return {
            "scenario": self.scenario.name,
            "target": self.scenario.target,
            "objective": self.scenario.objective,
            "security": self.scenario.security,
            "crew": [{"id": m.id, "name": m.name, "role": m.role, "icon": m.icon} for m in self.selected_crew],
            "difficulty": self.difficulty,
        }
    
    def step(self, action: str) -> StepResult:
        raise NotImplementedError("Use conversation_flow()")
    
    def render(self) -> str:
        return f"🎰 THE HEIST: {self.scenario.name}\nTarget: {self.scenario.target}"
    
    async def conversation_flow(self, user_plan: str, context: Dict[str, Any]):
        """Multi-agent heist flow"""
        
        # BRIEFING
        yield ConversationTurn(
            agent='system',
            type='message',
            message=f"**🎯 {self.scenario.name}**\n\nTarget: {self.scenario.target}\nObjective: {self.scenario.objective}\n\nSecurity: {self.scenario.security}",
            metadata={'phase': 'briefing'}
        )
        
        # CREW REACTIONS
        approvals = 0
        for member in self.selected_crew:
            yield ConversationTurn(agent=member.id, type='thinking', metadata={'icon': member.icon, 'name': member.name})
            
            prompt = f"HEIST: {self.scenario.target}\nOBJECTIVE: {self.scenario.objective}\n\nBOSS'S PLAN:\n{user_plan}\n\nYour specialty: {member.specialty}\n\nReact to this plan. Any concerns based on your quirk?"
            
            try:
                response = self.llm_client.call(
                    system_prompt=self.agents[member.id].system_prompt,
                    user_message=prompt,
                    temperature=0.8,
                    max_tokens=150
                )
            except Exception:
                response = f"*{member.name} nods*"
            
            # Check for strong concerns only (not just "but" which is common)
            strong_concerns = ["won't do", "can't do", "refuse", "no way", "not on board", "i won't", "i can't"]
            has_strong_concern = any(w in response.lower() for w in strong_concerns)
            if not has_strong_concern:
                approvals += 1
            
            yield ConversationTurn(
                agent=member.id,
                message=response,
                type='message',
                metadata={'icon': member.icon, 'name': member.name, 'role': member.role}
            )
        
        # COMPLICATION
        if random.random() < 0.5:
            comp = random.choice(self.scenario.complications)
            yield ConversationTurn(agent='system', type='message', message=f"⚠️ **COMPLICATION:** {comp}", metadata={'complication': True})
            
            reactor = random.choice(self.selected_crew)
            yield ConversationTurn(agent=reactor.id, type='thinking', metadata={'icon': reactor.icon, 'name': reactor.name})
            
            try:
                reaction = self.llm_client.call(
                    system_prompt=self.agents[reactor.id].system_prompt,
                    user_message=f"MID-HEIST PROBLEM: {comp}\n\nHow do you react? What do you do?",
                    temperature=0.9,
                    max_tokens=100
                )
            except Exception:
                reaction = "We adapt."
            
            yield ConversationTurn(agent=reactor.id, message=reaction, type='message', metadata={'icon': reactor.icon, 'name': reactor.name})
        
        # OUTCOME
        plan_lower = user_plan.lower()
        
        # Check plan quality - mentions crew by name OR role
        mentions_crew = any(
            m.name.lower() in plan_lower or m.role.lower() in plan_lower 
            for m in self.selected_crew
        )
        plan_quality = len(user_plan) > 50 and mentions_crew
        
        # Crew ready if at least half approve (more lenient)
        crew_ready = approvals >= len(self.selected_crew) // 2
        
        # Luck factor based on difficulty (easy = 90% success if plan good)
        luck_threshold = {"easy": 0.1, "medium": 0.25, "hard": 0.4}.get(self.difficulty, 0.2)
        luck = random.random() > luck_threshold
        
        # Success requires good plan + crew buy-in + luck
        self.heist_success = plan_quality and crew_ready and luck
        self.total_score = 100 if self.heist_success else 25
        
        if self.heist_success:
            yield ConversationTurn(agent='system', type='message', message=f"✅ **HEIST SUCCESSFUL!**\n\nThe {self.scenario.objective.lower()} is yours. The crew escapes clean.", metadata={'success': True})
        else:
            if not plan_quality:
                reason = "Plan was too vague - mention specific crew members and their tasks"
            elif not crew_ready:
                reason = "Crew had too many concerns - address their quirks"
            else:
                reason = "Bad luck - alarms triggered despite good planning"
            yield ConversationTurn(agent='system', type='message', message=f"❌ **HEIST FAILED**\n\n{reason}. Better luck next time.", metadata={'success': False})
