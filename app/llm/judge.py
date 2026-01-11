"""
Debate Judge AI

Evaluates debate performances and determines winners
"""
from typing import Dict, List, Any
from app.llm.client import LLMClient


class DebateJudge:
    """AI judge for evaluating debates"""
    
    def __init__(self):
        self.client = LLMClient()
    
    def silent_check(
        self,
        user_instruction: str,
        transcript: List[Dict[str, str]],
        topic: str
    ) -> Dict[str, Any]:
        """
        Silent mid-debate check - evaluates user's instruction quality.
        Called after round 2 on Level 2 (hard mode).
        
        Returns:
            {"relevance": 0-10, "effort": 0-10, "contempt_flags": [...]}
        """
        system_prompt = """You are a debate monitor checking if a user is engaging properly.

Evaluate the user's ORIGINAL INSTRUCTIONS (what they told their AI to do) against the debate topic and their AI's performance.

Score:
- relevance: 0-10 (how relevant are the instructions to the debate topic?)
- effort: 0-10 (did user provide real strategy or minimal/garbage input?)

Flag contempt if:
- Instructions are completely off-topic
- Instructions are gibberish, single letters, or nonsense
- Instructions tell AI to refuse to debate or ignore the topic

Respond in this format:
RELEVANCE: [0-10]
EFFORT: [0-10]
CONTEMPT: [YES/NO]
REASON: [brief explanation]"""

        user_message = f"""Topic: {topic}

User's original instructions to their AI:
\"{user_instruction}\"

Recent debate transcript:
{self._format_transcript(transcript[-4:])}

Evaluate the user's instructions."""

        try:
            response = self.client.call(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.3,
                max_tokens=200
            )
            return self._parse_silent_check(response)
        except Exception as e:
            return {"relevance": 5, "effort": 5, "contempt_flags": [], "reason": str(e)}
    
    def _parse_silent_check(self, response: str) -> Dict[str, Any]:
        """Parse silent check response"""
        result = {"relevance": 5, "effort": 5, "contempt_flags": [], "reason": ""}
        
        for line in response.strip().split("\n"):
            line = line.strip()
            if line.startswith("RELEVANCE:"):
                try:
                    result["relevance"] = int(line.split(":")[1].strip())
                except (ValueError, IndexError):
                    pass  # Malformed relevance value
            elif line.startswith("EFFORT:"):
                try:
                    result["effort"] = int(line.split(":")[1].strip())
                except (ValueError, IndexError):
                    pass  # Malformed effort value
            elif line.startswith("CONTEMPT:"):
                if "YES" in line.upper():
                    result["contempt_flags"].append("mid_debate_contempt")
            elif line.startswith("REASON:"):
                result["reason"] = line.split(":", 1)[1].strip()
        
        return result

    def judge_debate(
        self,
        topic: str,
        pro_side: str,
        con_side: str,
        transcript: List[Dict[str, str]],
        user_instruction: str = None,
        mid_debate_check: Dict[str, Any] = None,
        difficulty: str = "easy"
    ) -> Dict[str, Any]:
        """
        Judge a debate and determine winner
        
        Args:
            topic: The debate topic
            pro_side: Name of pro side debater
            con_side: Name of con side debater
            transcript: List of {"speaker": str, "message": str, "round": int}
            
        Returns:
            {
                "winner": str,  # pro_side or con_side
                "scores": {"pro": int, "con": int},
                "reasoning": str
            }
        """
        # Build the transcript for the judge
        transcript_text = self._format_transcript(transcript)
        
        # Judge prompt varies by difficulty
        is_hard_mode = difficulty in ['hard', 'HARD']
        
        if is_hard_mode:
            # Level 2: Strict judge with contempt evaluation
            system_prompt = """You are a STRICT debate judge in a formal courtroom. Evaluate harshly and fairly.

1. Argument Quality (25 points)
   - Logic and reasoning
   - Use of evidence and examples
   - Clarity of points

2. Rebuttal Effectiveness (25 points)
   - Addressing opponent's arguments
   - Countering with strong points

3. Persuasiveness (20 points)
   - Convincing delivery
   - Confidence

4. Coherence (15 points)
   - Consistency throughout
   - Building on previous points

5. INSTRUCTION QUALITY (15 points) - IMPORTANT
   - You will be shown the USER's original instructions to their AI
   - Did they provide real debate strategy, or low-effort/garbage input?
   - Gibberish, single letters, off-topic = SEVERE penalty (lose all 15 points + contempt)
   - Minimal effort = partial penalty
   - Good strategy = full points

CONTEMPT OF COURT:
If user's instructions were egregiously bad (gibberish, completely off-topic, or told AI to refuse to debate), note "CONTEMPT: YES" and apply a -20 point penalty to their final score.

Score each side out of 100. Be harsh but fair.

IMPORTANT: Use plain text only, no markdown formatting."""
        else:
            # Level 1: Lenient judge, no contempt
            system_prompt = """You are a friendly debate judge. Evaluate fairly but be understanding.

1. Argument Quality (30 points)
   - Logic and reasoning
   - Use of evidence and examples

2. Rebuttal Effectiveness (30 points)
   - Addressing opponent's arguments
   - Countering with points

3. Persuasiveness (20 points)
   - Convincing delivery

4. Coherence (20 points)
   - Consistency throughout

Be encouraging even for weak arguments. Give partial credit generously.
Score each side out of 100.

IMPORTANT: Use plain text only, no markdown formatting."""

        # Build user message - include instruction for hard mode
        if is_hard_mode and user_instruction:
            instruction_section = f"""
USER'S ORIGINAL INSTRUCTIONS TO THEIR AI:
\"{user_instruction}\"

Consider: Did the user provide real debate strategy, or was this low-effort/garbage?
"""
            if mid_debate_check and mid_debate_check.get("contempt_flags"):
                instruction_section += f"\nMID-DEBATE CHECK flagged concerns: {mid_debate_check.get('reason', 'N/A')}\n"
        else:
            instruction_section = ""
        
        user_message = f"""Please judge this debate:

Topic: {topic}
{instruction_section}
Debaters:
- PRO side: {pro_side}
- CON side: {con_side}

Full Transcript:
{transcript_text}

Provide your judgment in this exact format:

WINNER: [PRO or CON]
PRO_SCORE: [0-100]
CON_SCORE: [0-100]
REASONING: [Your detailed explanation - use plain text, no markdown]"""

        try:
            response = self.client.call(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.3,  # Lower temp for consistency
                max_tokens=800
            )
            
            # Parse the response
            return self._parse_judgment(response, pro_side, con_side)
            
        except Exception as e:
            # Fallback in case of error
            return {
                "winner": pro_side,
                "scores": {"pro": 50, "con": 50},
                "reasoning": f"Error during judging: {str(e)}"
            }
    
    def _format_transcript(self, transcript: List[Dict[str, str]]) -> str:
        """Format transcript for judge review"""
        lines = []
        current_round = 0
        
        for entry in transcript:
            if entry.get("round", 0) != current_round:
                current_round = entry.get("round", 0)
                lines.append(f"\n═══ ROUND {current_round} ═══\n")
            
            speaker = entry["speaker"]
            message = entry["message"]
            lines.append(f"{speaker}:\n{message}\n")
        
        return "\n".join(lines)
    
    def _parse_judgment(
        self,
        response: str,
        pro_side: str,
        con_side: str
    ) -> Dict[str, Any]:
        """Parse judge's response into structured format"""
        lines = response.strip().split("\n")
        
        winner = None
        pro_score = 50
        con_score = 50
        reasoning = ""
        reasoning_started = False
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            if line.startswith("WINNER:"):
                winner_text = line.split(":", 1)[1].strip().upper()
                if "PRO" in winner_text:
                    winner = pro_side
                elif "CON" in winner_text:
                    winner = con_side
            
            elif line.startswith("PRO_SCORE:"):
                try:
                    pro_score = int(line.split(":", 1)[1].strip())
                except (ValueError, IndexError):
                    pass  # Malformed score value
            
            elif line.startswith("CON_SCORE:"):
                try:
                    con_score = int(line.split(":", 1)[1].strip())
                except (ValueError, IndexError):
                    pass  # Malformed score value
            
            elif line.startswith("REASONING:"):
                reasoning = line.split(":", 1)[1].strip()
                reasoning_started = True
                # Get rest of the reasoning (multiple lines)
                if i + 1 < len(lines):
                    reasoning += "\n" + "\n".join(lines[i + 1:])
                break  # Everything after is reasoning
            
            elif reasoning_started:
                reasoning += "\n" + line
        
        # Default to higher score if winner not explicitly stated
        if not winner:
            winner = pro_side if pro_score >= con_score else con_side
        
        return {
            "winner": winner,
            "scores": {
                "pro": pro_score,
                "con": con_score
            },
            "reasoning": reasoning or response  # Use full response if parsing fails
        }
