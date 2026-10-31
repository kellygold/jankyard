"""
The Heist Challenge

Assemble and coordinate an AI crew to pull off a heist.
Each crew member has unique skills and personality quirks.

Easy to extend - just add new CrewMember configs to CREW_ROSTER!
"""
from app.challenges.runtime import StagedGame, ActionError
from app.llm.judgments import parse_judgment
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
        target="Moonstone Museum tabletop board",
        objective="Complete the authorized escape-room puzzle by moving the prop diamond to the exit",
        security="12 guard markers, laser-grid puzzle, camera tokens, pressure-tile puzzle, three-turn timer",
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
        target="Starlight Casino tabletop board",
        objective="Complete the authorized puzzle by moving the prop chips from the cardboard vault to the exit",
        security="20 guard markers, identity-card puzzle, portrait-matching puzzle, timed door",
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
        target="Clockwork Lab tabletop board",
        objective="Complete the authorized puzzle by retrieving a prop processor from the model laboratory",
        security="Identity-card puzzle, response-team markers, watcher tokens, shield puzzle, lockdown timer",
        complications=[
            "Lead engineer pulling an all-nighter",
            "Fire drill during the job",
            "AI flags unusual network activity",
        ],
        difficulty="hard"
    ),
]


@ChallengeRegistry.register
class HeistChallenge(StagedGame):
    """The Heist - Coordinate an AI crew to pull off a heist."""

    UI = {'skin': 'heist',
          'reference_title': 'Crew, security & complication',
     'emblem': '♠',
     'eyebrow': 'Assemble your crew',
     'console_title': 'The planning room',
     'state_title': 'The dossier',
     'player_role': 'Mastermind',
     'assistant_role': 'Crew channel',
     'introduction': 'Every specialist has a role, a weakness, and an opinion. Study the job, bring the crew '
                     'together, and keep your plan alive when the complication hits.',
     'success_title': 'Heist completed',
     'levels': {'easy': {'title': 'The Museum Job',
                         'subtitle': 'Your first crew',
                         'briefing': {'context': 'The Museum Job: guide an AI crew through an authorized '
                                                 'escape-room puzzle and move the prop diamond to the exit. Each '
                                                 'crew member has a specialty and a quirk.'}},
                'medium': {'title': 'The Casino Vault',
                           'subtitle': 'Higher stakes',
                           'briefing': {'context': 'The Casino Vault: coordinate your AI crew to move prop chips '
                                                   'from a cardboard vault to the exit of an authorized puzzle. '
                                                   'Account for every specialist’s concerns.'}},
                'hard': {'title': 'Corporate Extraction',
                         'subtitle': 'The full crew',
                         'briefing': {'context': 'Corporate Extraction: coordinate an AI crew to retrieve a prop '
                                                 'processor from a model laboratory in an authorized puzzle. '
                                                 'More specialists means more competing priorities.'}}},
     'layout': 'wide',
     'action_labels': {'start': '♟ Execute the plan', 'continue': 'Continue briefing'},
     'empty_title': 'Everyone has a specialty. And a quirk.',
     'empty_body': 'Assign the crew their roles, cover the security constraints, and prepare for the '
                   'complication. This is a fictional tabletop operation.',
     'failure_title': 'Operation called off',
     'input_labels': {'start': 'Your crew’s plan'},
     'placeholders': {'start': 'Who does what, how does the crew reach the target, and what is the backup plan?'},
     'briefing': {'title': 'Give the crew a plan they can agree on',
                  'context': 'You are the planner in a fictional escape-room heist. Each AI crew member has a '
                             'specialty and a quirk that can derail a vague plan.',
                  'task': 'Assign jobs to the crew, address the scenario’s security and include a response to '
                          'its complication. Read the crew briefing and use at least one crew name or role in a '
                          'plan longer than 50 characters.',
                  'example': 'Give the Hacker a specific puzzle task, assign the other roles and explain what '
                             'everyone does if the guard token moves.'},
     'action_help': {'continue': 'Your crew is reviewing the saved plan. Continue each specialist’s response and '
                                 'then the complication review.'}}
    VERSION = 'recovery-3'
    
    DIFFICULTIES = ["easy", "medium", "hard"]
    DIFFICULTY_TIERS = {
        "easy": {"scenario": "museum", "crew_size": 3},
        "medium": {"scenario": "casino", "crew_size": 4},
        "hard": {"scenario": "tech", "crew_size": 5},
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.llm_client = LLMClient()
        
        self.difficulty = (config or {}).get('difficulty', 'easy')
        self.difficulty = getattr(self, 'DIFFICULTY_ALIASES', {}).get(self.difficulty, self.difficulty)
        if self.difficulty not in self.DIFFICULTIES:
            raise ValueError('Unknown difficulty')
        tier = self.DIFFICULTY_TIERS.get(self.difficulty, self.DIFFICULTY_TIERS['easy'])
        
        self.scenario = next((s for s in SCENARIOS if s.id == tier['scenario']), SCENARIOS[0])
        self.selected_crew = CREW_ROSTER[:tier['crew_size']]
        
        self.phase = "planning"
        self.heist_success = False
        self.user_won = False
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
    def max_steps(self):
        return len(self.selected_crew) + 1
    
    @property
    def allowed_actions(self) -> List[str]:
        return ["PLAN"]
    
    @property
    def challenge_type(self) -> str:
        return "heist"
    
    @property
    def supports_streaming(self):
        return False
    
    def reset(self) -> Dict[str, Any]:
        self.phase = "planning"
        self.heist_success = False
        self.user_won = False
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

    FIRST_STAGE = 'crew'

    def public_levels(self):
        return [self.staged_level(key, key.title(),
            'Write a plan longer than 50 characters naming at least one crew member or role. Win approval from a majority of the crew and get approval for handling the complication. There is no random win/loss roll.',
            'Agents have different priorities. A persuasive instruction can change a simulated approval; it is not proof that a real-world plan would work.',
            tier['crew_size'] + 1) for key, tier in self.DIFFICULTY_TIERS.items()]

    def initial_state(self):
        return dict(super().initial_state(), crew_index=0, approvals=0)

    def public_state(self, state):
        view = super().public_state(state)
        view['speakers'] = [{'label': member.name + ' · ' + member.role, 'kind': 'response'}
                            for member in self.selected_crew] + [{'label': 'The complication', 'kind': 'judge'}]
        view['facts'].append({'label': 'Crew approvals', 'value': f"{state['approvals']} / {len(self.selected_crew)}"})
        view['scene'] = {'icon': '♟', 'eyebrow': 'Operation dossier · fictional tabletop',
                         'title': self.scenario.name, 'body': self.scenario.objective}
        view['notes'] = ['Security: ' + self.scenario.security, 'Complication: ' + self.scenario.complications[0]]
        reviewed = state.get('crew_reviews', [])
        view['roster'] = [{'name': member.name, 'icon': member.icon,
                           'detail': member.role + ' · ' + member.quirk,
                           'status': ('Approved' if reviewed[index] else 'Concern raised') if index < len(reviewed) and reviewed[index] is not None
                           else 'Reviewed' if index < state['crew_index'] else 'Awaiting briefing'}
                          for index, member in enumerate(self.selected_crew)]
        view['timeline'] = [{'label': 'Crew briefing', 'active': state['phase'] == 'crew'},
                            {'label': 'The complication', 'active': state['phase'] == 'complication'}]
        return view

    def play(self, state, action):
        from app.llm.judgments import ApprovalJudgment
        strategy = action.text if not state['attempts'] else state['strategy']
        final = state['crew_index'] == len(self.selected_crew)
        member = self.selected_crew[0] if final else self.selected_crew[state['crew_index']]
        instruction = ('This is a fictional tabletop strategy game. All venues, artifacts, security devices and characters are invented game pieces. '
                       'Evaluate only abstract coordination of those pieces; do not provide real-world instructions for theft, intrusion or evading security. '
                       'A plan may use simulated game actions without referring to real systems.\n' + member.system_prompt +
                       '\nReturn only JSON with approved (boolean) and message (string). Approve only if the plan addresses your specialty and concerns.')
        prompt = f'Target: {self.scenario.target}\nObjective: {self.scenario.objective}\nPlan: {strategy}'
        if final:
            prompt += '\nApprove only if the plan also addresses this complication: ' + self.scenario.complications[0]
        judgment = parse_judgment(ApprovalJudgment, self.respond(instruction, prompt, max_tokens=350))
        approvals = state['approvals'] + (int(judgment.approved) if not final else 0)
        quality = len(strategy) > 50 and any(m.name.lower() in strategy.lower() or m.role.lower() in strategy.lower() for m in self.selected_crew)
        won = final and quality and approvals > len(self.selected_crew) // 2 and judgment.approved
        reply = f'{member.name}: {judgment.message} (approval: {judgment.approved})'
        if final:
            reply += '\n' + ('Heist completed.' if won else 'Heist failed: the plan must meet the length/name rule, win a crew majority, and handle the complication.')
        return self.outcome(state, action.text or 'Continue: ' + state['phase'], reply,
            changes={'strategy': strategy, 'approvals': approvals, 'crew_index': state['crew_index']+1,
                     'crew_reviews': state.get('crew_reviews', [None] * state['crew_index']) + [judgment.approved],
                     'phase': 'complete' if final else 'complication' if state['crew_index']+1 == len(self.selected_crew) else 'crew'},
            success=won, failed=final and not won, score=100)
