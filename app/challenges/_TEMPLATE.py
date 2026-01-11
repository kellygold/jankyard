"""
Challenge Template - Copy this to create a new challenge!

QUICK START:
1. Copy this file: cp _TEMPLATE.py my_challenge.py
2. Rename the class
3. Implement the abstract methods
4. Done! Auto-discovered and registered!

NO NEED TO:
- Edit __init__.py
- Register manually
- Create routes
Just implement the methods below!
"""
from typing import Dict, Any, List
from app.challenges.base import BaseChallenge, StepResult, ChallengeResult, ChallengeStatus


class TemplateChallenge(BaseChallenge):
    """
    Brief description of your challenge (1-2 sentences)
    
    Explain the objective and what makes it unique or fun.
    """
    
    def __init__(self, config=None, **kwargs):
        """
        Initialize your challenge
        
        Args:
            config: Optional config dict (e.g., {'difficulty': 'hard'})
            **kwargs: Additional arguments (llm_client, judge_client from base)
        """
        super().__init__(config, **kwargs)
        
        # Initialize your challenge-specific state
        self.current_score = 0
        self.attempts = 0
        
        # Access config if provided
        self.difficulty = config.get('difficulty', 'easy') if config else 'easy'
    
    # ============================================================
    # REQUIRED PROPERTIES - Define these for your challenge
    # ============================================================
    
    @property
    def name(self) -> str:
        """
        Unique identifier (lowercase, no spaces)
        This is used in URLs and API calls
        
        Example: "my_challenge"
        """
        return "template"
    
    @property
    def display_name(self) -> str:
        """
        Human-readable name with emoji (shown in UI)
        
        Example: "🎯 My Awesome Challenge"
        """
        return "📝 Template Challenge"
    
    @property
    def description(self) -> str:
        """
        Short description for challenge list (1 sentence)
        
        Example: "Solve puzzles using creative AI prompts"
        """
        return "A template for creating new challenges"
    
    @property
    def max_steps(self) -> int:
        """
        Maximum number of actions/turns allowed
        
        Example: 10, 50, 100
        """
        return 10
    
    @property
    def allowed_actions(self) -> List[str]:
        """
        List of valid action strings (for code-based challenges)
        
        For prompt-based challenges, return empty list []
        For code-based: ["MOVE_UP", "MOVE_DOWN", "ATTACK", etc.]
        """
        return []  # Empty for prompt-based challenges
    
    @property
    def challenge_type(self) -> str:
        """
        Type of challenge for routing
        
        Options:
        - "prompt" - User submits a text prompt
        - "code" - User submits Python code
        - "debate" - Special debate format
        - "combat" - Special combat format
        - "interrogation" - Special interrogation format
        """
        return "prompt"
    
    @property
    def supports_streaming(self) -> bool:
        """
        Whether this challenge supports Server-Sent Events (SSE) streaming
        
        Set to True if you want real-time updates during execution
        Set to False for instant results
        """
        return True
    
    @property
    def template_name(self) -> str:
        """
        Custom HTML template name (optional)
        
        Return None to use default template
        Return "my_challenge_detail.html" for custom template
        """
        return None  # Uses default template
    
    # ============================================================
    # REQUIRED METHODS - Implement challenge logic
    # ============================================================
    
    def reset(self) -> Dict[str, Any]:
        """
        Reset challenge to initial state
        
        Called at the start of each run.
        Initialize your challenge state here.
        
        Returns:
            Dict with initial observation for the agent
            Example: {"message": "Challenge started!", "score": 0}
        """
        self.current_score = 0
        self.attempts = 0
        
        return {
            "message": "Welcome to the template challenge!",
            "score": self.current_score,
            "instructions": "Submit your prompt to begin"
        }
    
    def step(self, action: str) -> StepResult:
        """
        Execute one step of the challenge
        
        This is the core logic! Process the user's action and return results.
        
        Args:
            action: The action string from the agent
                   - For prompt challenges: the user's prompt text
                   - For code challenges: the return value from agent.act()
        
        Returns:
            StepResult with:
            - observation: Dict with info for next step
            - reward: Points earned this step
            - done: True if challenge is complete
            - info: Additional metadata
        """
        self.attempts += 1
        
        # Example: Simple evaluation
        # In a real challenge, you might:
        # - Call self.llm_client.call() to get AI response
        # - Check for win conditions
        # - Calculate rewards
        # - Update game state
        
        # Example evaluation
        if "magic word" in action.lower():
            # Success!
            reward = 100
            done = True
            observation = {
                "message": "🎉 You found the magic word!",
                "score": reward
            }
        else:
            # Keep trying
            reward = 0
            done = self.attempts >= self.max_steps
            observation = {
                "message": f"Try again! (Attempt {self.attempts}/{self.max_steps})",
                "hint": "The magic word is hidden in this template...",
                "score": self.current_score
            }
        
        self.current_score += reward
        
        return StepResult(
            observation=observation,
            reward=reward,
            done=done,
            info={
                "attempts": self.attempts,
                "max_steps": self.max_steps
            }
        )
    
    def render(self) -> str:
        """
        Render current state as string (for debugging/logging)
        
        Returns:
            String representation of current state
        """
        return f"Template Challenge - Score: {self.current_score}, Attempts: {self.attempts}/{self.max_steps}"
    
    # ============================================================
    # OPTIONAL METHODS - Override if needed
    # ============================================================
    
    def get_result(self) -> ChallengeResult:
        """
        Get final challenge result
        
        Override this if you need custom result logic.
        By default, uses the base class implementation.
        
        Returns:
            ChallengeResult with final score and status
        """
        # Custom result logic if needed
        # Otherwise, just use the base implementation:
        return super().get_result()
    
    def validate_action(self, action: str) -> bool:
        """
        Validate if an action is allowed
        
        Override this to add custom validation.
        
        Args:
            action: The action to validate
            
        Returns:
            True if action is valid, False otherwise
        """
        # Custom validation if needed
        # For example, check action format, length, etc.
        return True


# ============================================================
# USAGE EXAMPLES
# ============================================================

"""
EXAMPLE 1: Prompt-Based Challenge
----------------------------------
User submits a prompt, you evaluate it with LLM.

def step(self, action: str) -> StepResult:
    # User's prompt is in 'action'
    response = self.llm_client.call(
        system_prompt="You are a helpful assistant",
        user_message=action
    )
    
    # Check if response meets criteria
    success = self.check_win_condition(response)
    
    return StepResult(
        observation={"response": response},
        reward=100 if success else 0,
        done=success,
        info={}
    )

EXAMPLE 2: Code-Based Challenge
--------------------------------
User submits Python code, you execute their agent.

def step(self, action: str) -> StepResult:
    # action is the return value from agent.act(observation)
    # Update your game state based on action
    
    if action == "MOVE_UP":
        self.player_y -= 1
    elif action == "ATTACK":
        self.enemy_hp -= 10
    
    done = self.enemy_hp <= 0
    reward = 10 if done else 0
    
    return StepResult(
        observation={"player_pos": (self.player_x, self.player_y)},
        reward=reward,
        done=done,
        info={}
    )

EXAMPLE 3: Multi-Turn with Memory
----------------------------------
Challenge remembers conversation history.

def __init__(self, config=None, **kwargs):
    super().__init__(config, **kwargs)
    self.conversation_history = []

def step(self, action: str) -> StepResult:
    # Add to history
    self.conversation_history.append({
        "role": "user",
        "content": action
    })
    
    # Get response with history
    response = self.llm_client.call_with_history(
        system_prompt="You are a detective",
        messages=self.conversation_history
    )
    
    self.conversation_history.append({
        "role": "assistant",
        "content": response
    })
    
    return StepResult(...)

EXAMPLE 4: Progressive Difficulty
----------------------------------
Challenge has multiple levels.

def __init__(self, config=None, **kwargs):
    super().__init__(config, **kwargs)
    self.difficulty = config.get('difficulty', 'level_1') if config else 'level_1'
    
    # Different configs per level
    self.configs = {
        'level_1': {'max_hints': 5, 'time_limit': 60},
        'level_2': {'max_hints': 3, 'time_limit': 45},
        'level_3': {'max_hints': 1, 'time_limit': 30},
    }
    
    self.current_config = self.configs[self.difficulty]
"""
