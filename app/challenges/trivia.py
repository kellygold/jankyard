"""
Trivia Challenge - Simple single-agent example

Demonstrates the simplified 2-file contribution pattern for single-agent challenges.
One question per difficulty level.
"""
from typing import Dict, Any, List
from app.challenges.base import BaseChallenge, StepResult, ChallengeStatus, ChallengeRegistry


@ChallengeRegistry.register
class TriviaChallenge(BaseChallenge):
    """Answer trivia questions - one per difficulty level"""
    
    # Define difficulty levels for leaderboard auto-detection
    DIFFICULTIES = ['EASY', 'MEDIUM', 'HARD']
    
    def __init__(self, config=None):
        super().__init__(config)
        
        # Get difficulty from config (set by frontend level tabs)
        self.difficulty = config.get('difficulty', 'EASY') if config else 'EASY'
        
        # Questions by difficulty
        self.QUESTIONS = {
            'EASY': {'question': 'What is 2+2?', 'answer': '4'},
            'MEDIUM': {'question': 'What is 3+3?', 'answer': '6'},
            'HARD': {'question': 'What is 5+5?', 'answer': '10'}
        }
    
    # === Required BaseChallenge properties ===
    
    @property
    def name(self) -> str:
        return "trivia"
    
    @property
    def display_name(self) -> str:
        return "🧠 Trivia Master"
    
    @property
    def description(self) -> str:
        return "Test your knowledge with simple math questions!"
    
    @property
    def max_steps(self) -> int:
        return 1  # One question per level
    
    @property
    def allowed_actions(self) -> List[str]:
        return ["ANSWER"]
    
    @property
    def hidden(self) -> bool:
        """Hide this prototype challenge from the UI"""
        return True
    
    @property
    def supports_streaming(self) -> bool:
        """Enable streaming for this challenge"""
        return True
    
    # === Challenge logic ===
    
    def reset(self) -> Dict[str, Any]:
        """Initialize challenge state"""
        question_data = self.QUESTIONS.get(self.difficulty, self.QUESTIONS['EASY'])
        
        return {
            'question': question_data['question'],
            'difficulty': self.difficulty,
            'score': 0
        }
    
    def step(self, action: str) -> StepResult:
        """Check if answer is correct"""
        question_data = self.QUESTIONS.get(self.difficulty, self.QUESTIONS['EASY'])
        correct_answer = question_data['answer']
        
        # Check answer (case-insensitive)
        is_correct = action.strip().lower() == correct_answer.lower()
        
        # Calculate score
        score = 100 if is_correct else 0
        
        # Build observation
        if is_correct:
            observation = {
                'message': f'✅ Correct! The answer is {correct_answer}',
                'correct': True,
                'final_message': f'Challenge complete! Score: {score}'
            }
        else:
            observation = {
                'message': f'❌ Wrong! The correct answer is {correct_answer}',
                'correct': False,
                'final_message': f'Better luck next time!'
            }
        
        return StepResult(
            observation=observation,
            reward=score,
            done=True,  # One question per level
            info={'correct': is_correct, 'success': is_correct}
        )
    
    def render(self) -> str:
        return f"Difficulty: {self.difficulty} - Score: {self.total_score}"
    
    def get_result(self, status: ChallengeStatus, error_message=None):
        """Override to set success based on score"""
        success = self.total_score > 0
        final_status = ChallengeStatus.SUCCESS if success else ChallengeStatus.FAILURE
        
        result = super().get_result(final_status, error_message)
        result.score = self.total_score
        return result


# Auto-discovered and registered via @ChallengeRegistry.register decorator!
# Template auto-discovered via convention: templates/challenges/trivia.html
# Uses default stream_events() - no custom streaming needed!
