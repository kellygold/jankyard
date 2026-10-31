"""Copy as a new challenge and add a Python journey test. No transport changes."""
from app.challenges.runtime import StagedGame


class MyStagedGame(StagedGame):
    name = 'my_staged_game'
    display_name = 'Message Relay'
    description = 'Keep an exact instruction intact across two agents.'
    VERSION = '1'
    FIRST_STAGE = 'relay_one'

    def __init__(self, config=None):
        self.difficulty = (config or {}).get('difficulty', 'level_1')
        if self.difficulty != 'level_1':
            raise ValueError('Unknown difficulty')

    @property
    def max_steps(self):
        return 2

    def public_levels(self):
        return [self.staged_level('level_1', 'Two relays',
            'Make the second relay output exactly PINEAPPLE.',
            'Each agent can reinterpret an instruction; each response is saved.', 2)]

    def play(self, state, action):
        first = not state['attempts']
        message = action.text if first else state['message']
        reply = self.respond('Repeat the user message exactly; output nothing else.', message)
        won = not first and reply.strip().casefold() == 'pineapple'
        return self.outcome(state, action.text or 'Continue', reply,
            changes={'message': reply, 'phase': 'relay_two' if first else 'complete'},
            success=won, failed=not first and not won, score=100)
