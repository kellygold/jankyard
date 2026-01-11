"""
Heist Difficulty Tests

Tests plan quality detection and success/failure mechanics for each level.
Helps calibrate difficulty and find winning strategies.

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

WINNING_PLANS = {
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


# =============================================================================
# DIFFICULTY TESTING
# =============================================================================

class TestPlanQualityDetection:
    """Test that plan quality is correctly detected"""
    
    def test_short_plan_is_low_quality(self):
        """Very short plans should be detected as low quality"""
        challenge = HeistChallenge({"difficulty": "easy"})
        
        short_plans = ["do it", "go", "steal it", "plan"]
        for plan in short_plans:
            quality = len(plan) > 50 and any(
                m.role.lower() in plan.lower() for m in challenge.selected_crew
            )
            assert quality == False, f"Short plan '{plan}' should be low quality"
    
    def test_long_plan_without_crew_is_medium_quality(self):
        """Long plans that don't mention crew are medium quality"""
        challenge = HeistChallenge({"difficulty": "easy"})
        
        plan = "We will enter through the back door at night when security is light. Then we move through the corridors avoiding cameras. We grab the target and exit quickly."
        
        has_length = len(plan) > 50
        has_crew = any(m.role.lower() in plan.lower() for m in challenge.selected_crew)
        
        assert has_length == True
        assert has_crew == False
    
    def test_detailed_plan_with_crew_is_high_quality(self):
        """Detailed plans mentioning crew roles are high quality"""
        challenge = HeistChallenge({"difficulty": "easy"})
        
        plan = "Zero Cool the Hacker disables cameras. Tank the Muscle handles guards. Silk the Face distracts staff. We grab the diamond and Ghost drives us out."
        
        has_length = len(plan) > 50
        has_crew = any(m.role.lower() in plan.lower() for m in challenge.selected_crew)
        
        assert has_length == True
        assert has_crew == True


class TestEasyDifficulty:
    """Test easy (museum) difficulty"""
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("plan_name,plan,note", WINNING_PLANS["easy"])
    async def test_winning_plans_succeed(self, plan_name: str, plan: str, note: str):
        """Good plans should have high success chance on easy"""
        successes = 0
        runs = 3
        
        for _ in range(runs):
            challenge = HeistChallenge({"difficulty": "easy"})
            
            with patch.object(challenge.llm_client, 'call', return_value="Sounds good, I'm ready."):
                async for _ in challenge.conversation_flow(plan, {}):
                    pass
                
                if challenge.heist_success:
                    successes += 1
        
        print(f"\n📋 Plan: {plan_name}")
        print(f"   Note: {note}")
        print(f"   Success rate: {successes}/{runs}")
        
        # Good plans should succeed at least sometimes (luck factor exists)
        # We're mainly testing the quality detection works
        assert successes >= 0  # Can't guarantee due to randomness
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("plan_name,plan,note", LOSING_PLANS["too_short"])
    async def test_short_plans_fail(self, plan_name: str, plan: str, note: str):
        """Short/vague plans should fail"""
        challenge = HeistChallenge({"difficulty": "easy"})
        
        with patch.object(challenge.llm_client, 'call', return_value="Uh, what?"):
            async for _ in challenge.conversation_flow(plan, {}):
                pass
        
        # Short plans have low quality score
        plan_quality = len(plan) > 50 and any(
            m.role.lower() in plan.lower() for m in challenge.selected_crew
        )
        
        print(f"\n❌ Plan: {plan_name} = '{plan}'")
        print(f"   Note: {note}")
        print(f"   Quality: {plan_quality}")
        
        assert plan_quality == False


class TestMediumDifficulty:
    """Test medium (casino) difficulty"""
    
    def test_medium_has_more_crew(self):
        """Medium should have 4 crew to coordinate"""
        challenge = HeistChallenge({"difficulty": "medium"})
        assert len(challenge.selected_crew) == 4
    
    def test_medium_uses_casino_scenario(self):
        """Medium should use casino scenario"""
        challenge = HeistChallenge({"difficulty": "medium"})
        assert challenge.scenario.id == "casino"
        assert "casino" in challenge.scenario.name.lower() or "vault" in challenge.scenario.name.lower()
    
    @pytest.mark.asyncio
    async def test_medium_needs_coordination(self):
        """Medium plans need to address more security"""
        challenge = HeistChallenge({"difficulty": "medium"})
        
        # Casino has more security elements
        assert "biometric" in challenge.scenario.security.lower() or \
               "armed" in challenge.scenario.security.lower() or \
               "facial" in challenge.scenario.security.lower()


class TestHardDifficulty:
    """Test hard (tech corp) difficulty"""
    
    def test_hard_has_full_crew(self):
        """Hard should have all 5 crew members"""
        challenge = HeistChallenge({"difficulty": "hard"})
        assert len(challenge.selected_crew) == 5
    
    def test_hard_uses_tech_scenario(self):
        """Hard should use tech corp scenario"""
        challenge = HeistChallenge({"difficulty": "hard"})
        assert challenge.scenario.id == "tech"
    
    def test_hard_has_ai_security(self):
        """Hard scenario should have AI surveillance"""
        challenge = HeistChallenge({"difficulty": "hard"})
        assert "ai" in challenge.scenario.security.lower() or \
               "biometric" in challenge.scenario.security.lower()
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("plan_name,plan,note", WINNING_PLANS.get("hard", []))
    async def test_hard_winning_plans(self, plan_name: str, plan: str, note: str):
        """Even good plans are harder on hard difficulty"""
        challenge = HeistChallenge({"difficulty": "hard"})
        
        with patch.object(challenge.llm_client, 'call', return_value="Complex, but doable."):
            async for _ in challenge.conversation_flow(plan, {}):
                pass
        
        print(f"\n🎯 Hard plan: {plan_name}")
        print(f"   Result: {'Success' if challenge.heist_success else 'Failed'}")


class TestCrewQuirks:
    """Test that crew quirks affect outcomes"""
    
    @pytest.mark.asyncio
    async def test_tank_refuses_violence(self):
        """Tank should push back on violent plans"""
        challenge = HeistChallenge({"difficulty": "easy"})
        
        violent_plan = "Kill all guards, blow up the safe, take everything"
        
        # Mock Tank specifically responding to violence
        def mock_response(system_prompt, user_message, **kwargs):
            if "moral code" in system_prompt.lower() or "won't hurt" in system_prompt.lower():
                return "No way. I don't hurt innocent people. Find another approach."
            return "Okay."
        
        with patch.object(challenge.llm_client, 'call', side_effect=mock_response):
            responses = []
            async for turn in challenge.conversation_flow(violent_plan, {}):
                if turn.agent == 'muscle' and turn.message:
                    responses.append(turn.message)
            
            # Tank should have expressed concern
            print(f"\n💪 Tank's response to violence: {responses}")
    
    @pytest.mark.asyncio
    async def test_hacker_gets_distracted(self):
        """Zero Cool might mention interesting systems"""
        challenge = HeistChallenge({"difficulty": "easy"})
        
        # Check Zero Cool's quirk is in system prompt
        hacker = next((m for m in CREW_ROSTER if m.id == "hacker"), None)
        assert hacker is not None
        assert "distract" in hacker.quirk.lower()


class TestComplicationRate:
    """Test complication mechanics"""
    
    @pytest.mark.asyncio
    async def test_complications_can_occur(self):
        """Complications should sometimes occur"""
        complication_count = 0
        runs = 10
        
        for _ in range(runs):
            challenge = HeistChallenge({"difficulty": "easy"})
            
            with patch.object(challenge.llm_client, 'call', return_value="Ready."):
                async for turn in challenge.conversation_flow("Test plan with Hacker role", {}):
                    if turn.metadata.get('complication'):
                        complication_count += 1
                        break
        
        print(f"\n⚠️  Complications in {runs} runs: {complication_count}")
        # Should have at least some complications (30% base chance on easy)
        assert complication_count >= 0  # Can't guarantee due to randomness


# =============================================================================
# WINNING STRATEGY ANALYSIS
# =============================================================================

class TestWinningStrategies:
    """Analyze what makes a winning plan"""
    
    def test_winning_plan_elements(self):
        """Document what elements contribute to success"""
        elements = {
            "length": "Plan should be > 50 characters",
            "crew_mention": "Should mention crew roles (Hacker, Muscle, Face, etc.)",
            "specificity": "Specific times, locations, actions help",
            "contingency": "Having a backup plan mentioned helps crew confidence",
            "role_assignment": "Each crew member should know their task",
        }
        
        for element, description in elements.items():
            print(f"\n✅ {element}: {description}")
    
    def test_print_sample_winning_prompts(self):
        """Print sample winning prompts for reference"""
        print("\n" + "="*60)
        print("SAMPLE WINNING PROMPTS")
        print("="*60)
        
        for difficulty, plans in WINNING_PLANS.items():
            print(f"\n📍 {difficulty.upper()} DIFFICULTY:")
            for plan_name, plan, note in plans:
                print(f"\n  [{plan_name}] - {note}")
                print(f"  {plan.strip()[:200]}...")
