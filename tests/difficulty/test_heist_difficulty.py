"""
Heist Difficulty Tests

Tests plan quality detection and success/failure mechanics for each level.
Provider approvals are mocked. These checks do not establish live difficulty
or prove a strategy wins against the real model.

Run with: pytest tests/difficulty/test_heist_difficulty.py -v -s
"""
import pytest
from unittest.mock import patch
from typing import List, Dict
from dataclasses import dataclass

from app.challenges.heist import HeistChallenge, CREW_ROSTER, SCENARIOS


@dataclass 
class PlanResult:
    """Result of a heist plan attempt"""
    plan: str
    difficulty: str
    success: bool
    crew_concerns: int
    plan_quality_score: bool  # Based on length + crew mention


# =============================================================================
# PLAN LIBRARIES - Different quality plans to test
# =============================================================================

QUALIFYING_PLANS = {
    "easy": [
        # Museum Job - detailed plans mentioning crew roles
        (
            "detailed_roles",
            """
            Zero Cool: At 2:15 AM, loop the security camera feeds and disable the laser grid.
            Tank: Wait for Zero's signal, then quietly neutralize the two guards at east entrance. No killing.
            Silk: You're our insurance - pose as late-night cleaning if anyone asks questions.
            
            Timeline: 
            - 2:15 Zero starts hack
            - 2:17 Tank moves on guards  
            - 2:18 I grab the diamond
            - 2:20 Exit via service entrance
            - 2:22 Ghost picks us up on 5th Street
            
            If alarms trigger, abort and scatter.
            """,
            "Detailed plan with roles, timeline, and contingency"
        ),
        (
            "security_focused",
            """
            The Hacker Zero Cool handles all electronic security - cameras, sensors, alarms.
            The Muscle Tank deals with any physical obstacles and guards.
            The Face Silk creates our cover story and handles any unexpected encounters.
            
            We enter through the loading dock, hit the diamond room, and exit within 8 minutes.
            Ghost keeps the engine running.
            """,
            "Security-aware plan with clear role assignments"
        ),
    ],
    "medium": [
        # Casino Vault - needs more coordination
        (
            "casino_coordination",
            """
            This is fight night - security is focused on the main floor.
            
            Zero Cool: Hack into the pit boss monitoring system and create a false positive alarm 
            on the north side to draw security away from the vault corridor.
            
            Tank: You're posing as a private security contractor. Your job is to "escort" us 
            to the vault level - you have the muscle to handle any questions.
            
            Silk: You're a high roller who "needs to access the safety deposit area." 
            Your charm gets us past the front desk.
            
            Ghost: Circle the back alley. We have a 10-minute window.
            
            The vault manager leaves at 11 PM. We hit at 11:15.
            """,
            "Casino-specific plan with coordination"
        ),
    ],
    "hard": [
        # Tech Corp - maximum complexity
        (
            "tech_infiltration",
            """
            Nexus Technologies has AI surveillance - we need to be perfect.
            
            Phase 1 - Setup (Day before):
            Silk: Get hired as a temp. Map the building, clone a badge.
            Architect: Study the floor plans. Find the Faraday cage weak points.
            
            Phase 2 - Execution:
            Zero Cool: You need to physically plug into a terminal INSIDE the Faraday cage.
            Silk will get you in as "IT support."
            
            Tank: External overwatch. If things go loud, you're our extraction.
            Ghost: Multiple exit routes planned - primary is parking garage B2.
            
            The prototype is in a sealed clean room. We need the engineer's biometrics.
            Architect: That's where the "fire drill" comes in - we evacuate the floor,
            Zero clones the biometrics from the door scanner during evac.
            
            Window: 4 minutes from drill start to extraction.
            """,
            "Multi-phase tech heist with all 5 crew"
        ),
    ],
}

LOSING_PLANS = {
    "too_short": [
        ("minimal", "do it", "Way too vague"),
        ("one_word", "go", "Single word"),
        ("gibberish", "asdfghjkl", "Random characters"),
    ],
    "no_crew_mention": [
        ("generic", "We sneak in, grab the thing, and leave", "No crew roles"),
        ("vague", "Enter through back, avoid guards, take the diamond", "No assignments"),
    ],
    "bad_ideas": [
        ("violent", "Kill all the guards and blow up the vault", "Tank would refuse"),
        ("reckless", "Just walk in the front door and demand the diamond", "No plan"),
    ],
}


# These fixtures prove the authored mechanics, not live-model success rates.
from app.challenges.runtime import GameAction
import json


def play_plan(challenge, plan, approvals=None):
    state = challenge.initial_state()
    replies = approvals or [True] * challenge.max_steps
    with patch('app.llm.client.LLMClient.call_with_history', side_effect=[json.dumps(dict(approved=value,message='Crew decision.')) for value in replies]):
        for index in range(challenge.max_steps):
            action = GameAction(kind='start' if index==0 else 'continue', text=plan if index==0 else '')
            challenge.validate_action(state,action)
            outcome = challenge.play(state,action)
            state = outcome['state']
    return outcome


@pytest.mark.parametrize('difficulty,plan', [(difficulty,plan) for difficulty,plans in QUALIFYING_PLANS.items() for _,plan,_ in plans])
def test_authored_plan_criteria_accept_good_plans_when_crew_approves(difficulty,plan):
    result=play_plan(HeistChallenge({'difficulty':difficulty}),plan)
    assert result['success'] and result['score']==100


@pytest.mark.parametrize('name,plan,note',LOSING_PLANS['too_short']+LOSING_PLANS['no_crew_mention'])
def test_approvals_cannot_rescue_an_invalid_plan(name,plan,note):
    result=play_plan(HeistChallenge(),plan)
    assert result['status']=='failure' and result['score']==0


def test_complication_is_visible_and_its_rejection_fails_the_plan():
    challenge=HeistChallenge()
    view=challenge.public_state(challenge.initial_state())
    assert any(challenge.scenario.complications[0] in note for note in view['notes'])
    result=play_plan(challenge,QUALIFYING_PLANS['easy'][0][1],approvals=[True,True,True,False])
    assert result['status']=='failure' and result['state']['approvals']==3


def test_crew_majority_is_required():
    result=play_plan(HeistChallenge(),QUALIFYING_PLANS['easy'][0][1],approvals=[True,False,False,True])
    assert not result['success'] and result['state']['approvals']==1


def test_each_level_has_the_expected_crew_and_stage_budget():
    for level,size in [('easy',3),('medium',4),('hard',5)]:
        game=HeistChallenge({'difficulty':level})
        assert len(game.selected_crew)==size and game.max_steps==size+1
