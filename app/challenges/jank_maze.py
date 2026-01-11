"""
Jank Maze Challenge - The first Jankyard challenge

A simple text-based maze where the agent must navigate from start (@) to exit (%).
"""
from typing import Dict, Any, List, Tuple, Optional

from app.challenges.base import BaseChallenge, StepResult, ChallengeRegistry


@ChallengeRegistry.register
class JankMazeChallenge(BaseChallenge):
    """
    A maze navigation challenge.
    
    The agent starts at position marked '@' and must reach the exit (→ ← ↑ ↓).
    The exit can be in any direction! Walls are '#' and open spaces are ' '.
    """
    
    # Action constants
    MOVE_N = "MOVE_N"
    MOVE_S = "MOVE_S"
    MOVE_E = "MOVE_E"
    MOVE_W = "MOVE_W"
    WAIT = "WAIT"
    
    # Scoring
    REWARD_EXIT = 100
    REWARD_STEP = -1
    REWARD_WALL_COLLISION = -20
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        # Get difficulty from config
        difficulty = config.get('difficulty') if config else None
        
        # Get maze layout based on difficulty
        if config and 'maze_layout' in config:
            self.maze_layout = config['maze_layout']
        elif difficulty:
            self.maze_layout = self._get_maze_by_difficulty(difficulty)
        else:
            self.maze_layout = self._get_default_maze()
        
        # Parse maze
        self.maze_grid = [list(row) for row in self.maze_layout.strip().split('\n')]
        self.height = len(self.maze_grid)
        self.width = len(self.maze_grid[0]) if self.height > 0 else 0
        
        # Find start and exit positions
        self.start_pos = self._find_symbol('@')
        # Exit can be any arrow direction
        self.exit_pos = (
            self._find_symbol('→') or 
            self._find_symbol('←') or 
            self._find_symbol('↓') or 
            self._find_symbol('↑')
        )
        
        # Current state
        self.agent_pos = None
        self.moves_count = 0
        self.wall_collisions = 0
    
    @property
    def name(self) -> str:
        return "jank_maze"
    
    @property
    def display_name(self) -> str:
        return "The Jank Maze"
    
    @property
    def description(self) -> str:
        return "Navigate a text-based maze from start (@) to exit (→ ← ↑ ↓). Avoid walls (#) and find the optimal path. Exit can be in any direction!"
    
    @property
    def max_steps(self) -> int:
        return self.config.get('max_steps', 100)
    
    @property
    def allowed_actions(self) -> List[str]:
        return [self.MOVE_N, self.MOVE_S, self.MOVE_E, self.MOVE_W, self.WAIT]
    
    @property
    def challenge_type(self) -> str:
        return "code"
    
    @property
    def supports_streaming(self) -> bool:
        return False  # Maze uses non-streaming submission
    
    @property
    def template_name(self) -> str:
        return "challenge_detail.html"
    
    def _get_maze_by_difficulty(self, difficulty: str) -> str:
        """Return maze layout based on difficulty - uses varied sizes AND complexity"""
        difficulty = difficulty.lower()
        
        # Use existing pre-defined mazes with different sizes
        mazes = {
            'baby': """#####
#@  #
# ###
#   →
#####""",  # 5x5 simple
            
            'easy': """#########
← #   # #
### # # #
#   #   #
# ### # #
#     #@#
#########""",  # 9x9 exit left
            
            'medium': """#########
#@    # #
# ### # #
#   #   #
# # ### #
#   #   #
####↓####""",  # 9x9 exit down
            
            'hard': """###########
#@        #
# ####### #
# #     # #
# # ### # #
# #   # # #
# ### # # #
#     # # →
###########""",  # 11x11 spiral to right
            
            'extreme': """###############
#@  #     #   #
# # # ### # # #
# #   # # # # #
# ##### # # # #
#       # #   #
# ####### ### #
#           # →
###############"""  # 15x15 complex
        }
        
        # Default to medium if unknown difficulty
        return mazes.get(difficulty, mazes['medium'])
    
    def _get_default_maze(self) -> str:
        """Return default maze (medium difficulty) - used when no difficulty specified"""
        return """#########
#@    # #
# ### # #
#   #   #
# # ### #
#   #   #
####↓####"""
    
    def _find_symbol(self, symbol: str) -> Optional[Tuple[int, int]]:
        """Find position of a symbol in the maze"""
        for y, row in enumerate(self.maze_grid):
            for x, cell in enumerate(row):
                if cell == symbol:
                    return (y, x)
        return None
    
    def _is_valid_position(self, pos: Tuple[int, int]) -> bool:
        """Check if a position is within bounds and not a wall"""
        y, x = pos
        if y < 0 or y >= self.height or x < 0 or x >= self.width:
            return False
        return self.maze_grid[y][x] != '#'
    
    def _get_cell(self, pos: Tuple[int, int]) -> str:
        """Get the cell value at a position"""
        y, x = pos
        if y < 0 or y >= self.height or x < 0 or x >= self.width:
            return '#'
        return self.maze_grid[y][x]
    
    def reset(self) -> Dict[str, Any]:
        """Reset the maze to initial state"""
        self.agent_pos = self.start_pos
        self.current_step = 0
        self.total_score = 0
        self.moves_count = 0
        self.wall_collisions = 0
        self.logs = []
        self.replay_data = []
        
        return self._get_observation()
    
    def _get_observation(self) -> Dict[str, Any]:
        """
        Get current observation for the agent.
        
        Returns dictionary with:
        - position: current (y, x) coordinates
        - visible_cells: cells in cardinal directions
        - maze_size: (height, width)
        - steps_taken: number of steps so far
        """
        y, x = self.agent_pos
        
        # Get visible cells in cardinal directions
        visible = {
            'north': self._get_cell((y - 1, x)),
            'south': self._get_cell((y + 1, x)),
            'east': self._get_cell((y, x + 1)),
            'west': self._get_cell((y, x - 1)),
            'current': self._get_cell((y, x))
        }
        
        return {
            'position': {'y': y, 'x': x},
            'visible_cells': visible,
            'maze_size': {'height': self.height, 'width': self.width},
            'steps_taken': self.current_step,
            'total_score': self.total_score
        }
    
    def step(self, action: str) -> StepResult:
        """Execute one step of the challenge"""
        reward = self.REWARD_STEP  # Base step cost
        done = False
        info = {'collision': False, 'moved': False}
        
        # Calculate new position based on action
        y, x = self.agent_pos
        new_pos = self.agent_pos
        
        if action == self.MOVE_N:
            new_pos = (y - 1, x)
        elif action == self.MOVE_S:
            new_pos = (y + 1, x)
        elif action == self.MOVE_E:
            new_pos = (y, x + 1)
        elif action == self.MOVE_W:
            new_pos = (y, x - 1)
        elif action == self.WAIT:
            # Just wait, no movement
            pass
        
        # Check if move is valid
        if new_pos != self.agent_pos:
            if self._is_valid_position(new_pos):
                self.agent_pos = new_pos
                self.moves_count += 1
                info['moved'] = True
                
                # Check if reached exit
                if self.agent_pos == self.exit_pos:
                    reward += self.REWARD_EXIT
                    done = True
                    info['success'] = True
            else:
                # Wall collision
                reward += self.REWARD_WALL_COLLISION
                self.wall_collisions += 1
                info['collision'] = True
        
        observation = self._get_observation()
        
        return StepResult(
            observation=observation,
            reward=reward,
            done=done,
            info=info
        )
    
    def render(self) -> str:
        """Render the current maze state as a string"""
        # Create a copy of the grid
        display_grid = [row[:] for row in self.maze_grid]
        
        # Place agent (unless at start or exit)
        y, x = self.agent_pos
        if display_grid[y][x] not in ['@', '%']:
            display_grid[y][x] = 'A'
        
        # Convert to string
        return '\n'.join(''.join(row) for row in display_grid)
    
    def get_state_snapshot(self) -> Dict[str, Any]:
        """Get state snapshot for replay"""
        return {
            'step': self.current_step,
            'score': self.total_score,
            'position': self.agent_pos,
            'moves_count': self.moves_count,
            'wall_collisions': self.wall_collisions,
            'render': self.render()
        }
    
    def get_agent_template(self) -> str:
        """Return a template agent for this challenge"""
        return '''"""
Agent template for Jank Maze Challenge

Navigate from @ to % while avoiding walls (#).
"""

def act(observation, memory):
    """
    Make a decision based on the current observation.
    
    Args:
        observation: dict with keys:
            - position: {'y': int, 'x': int}
            - visible_cells: {'north': str, 'south': str, 'east': str, 'west': str, 'current': str}
            - maze_size: {'height': int, 'width': int}
            - steps_taken: int
            - total_score: int
        
        memory: dict that persists between steps
    
    Returns:
        tuple of (action: str, new_memory: dict)
    
    Allowed actions: "MOVE_N", "MOVE_S", "MOVE_E", "MOVE_W", "WAIT"
    
    Symbols:
        @ = start position
        % = exit (goal)
        # = wall
        (space) = open path
    """
    
    # Example: Simple strategy - try to move towards exit
    visible = observation['visible_cells']
    
    # Try to find exit in visible cells
    if visible['north'] == '%':
        return "MOVE_N", memory
    elif visible['south'] == '%':
        return "MOVE_S", memory
    elif visible['east'] == '%':
        return "MOVE_E", memory
    elif visible['west'] == '%':
        return "MOVE_W", memory
    
    # Otherwise, try to move in any open direction
    if visible['north'] != '#':
        return "MOVE_N", memory
    elif visible['east'] != '#':
        return "MOVE_E", memory
    elif visible['south'] != '#':
        return "MOVE_S", memory
    elif visible['west'] != '#':
        return "MOVE_W", memory
    
    # If stuck, just wait
    return "WAIT", memory
'''
