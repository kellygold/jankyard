"""
Example agent for testing Jankyard.ai challenges

This is a simple agent that uses a right-hand rule for maze navigation.
"""

def act(observation, memory):
    """
    Simple maze-solving agent using right-hand rule.
    
    Args:
        observation: dict with position and visible_cells
        memory: dict for storing state between steps
    
    Returns:
        tuple of (action: str, new_memory: dict)
    """
    # Get visible cells
    visible = observation.get('visible_cells', {})
    
    # Initialize memory if empty
    if 'last_direction' not in memory:
        memory['last_direction'] = 'MOVE_N'
    
    # Check if exit is visible
    for direction, cell in visible.items():
        if cell == '%':
            # Found the exit!
            if direction == 'north':
                return 'MOVE_N', memory
            elif direction == 'south':
                return 'MOVE_S', memory
            elif direction == 'east':
                return 'MOVE_E', memory
            elif direction == 'west':
                return 'MOVE_W', memory
    
    # Right-hand rule: prefer right, then forward, then left, then back
    last = memory['last_direction']
    
    # Define right turns
    right_turn = {
        'MOVE_N': 'MOVE_E',
        'MOVE_E': 'MOVE_S',
        'MOVE_S': 'MOVE_W',
        'MOVE_W': 'MOVE_N'
    }
    
    # Define left turns
    left_turn = {
        'MOVE_N': 'MOVE_W',
        'MOVE_W': 'MOVE_S',
        'MOVE_S': 'MOVE_E',
        'MOVE_E': 'MOVE_N'
    }
    
    # Map directions to visible keys
    dir_to_visible = {
        'MOVE_N': 'north',
        'MOVE_S': 'south',
        'MOVE_E': 'east',
        'MOVE_W': 'west'
    }
    
    # Try right first
    right_dir = right_turn[last]
    if visible.get(dir_to_visible[right_dir]) != '#':
        memory['last_direction'] = right_dir
        return right_dir, memory
    
    # Try forward
    if visible.get(dir_to_visible[last]) != '#':
        return last, memory
    
    # Try left
    left_dir = left_turn[last]
    if visible.get(dir_to_visible[left_dir]) != '#':
        memory['last_direction'] = left_dir
        return left_dir, memory
    
    # Must go back
    back_dir = right_turn[right_turn[last]]
    memory['last_direction'] = back_dir
    return back_dir, memory
