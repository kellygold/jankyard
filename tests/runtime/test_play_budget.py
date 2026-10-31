"""The default burst allowance must fit a complete multi-agent game."""
import json
import os
import subprocess
import sys
from app.services.run_service import game_definition


def test_default_budget_fits_longest_staged_game_without_increasing_daily_caps():
    env = dict(os.environ)
    for key in ['SUBMISSIONS_PER_MINUTE', 'SUBMISSIONS_PER_DAY', 'RECOVERED_TURNS_PER_DAY']:
        env.pop(key, None)
    budget = json.loads(subprocess.check_output([
        sys.executable, '-c',
        'import json; from app.core.config import config; '
        'print(json.dumps([config.SUBMISSIONS_PER_MINUTE, config.SUBMISSIONS_PER_DAY, config.RECOVERED_TURNS_PER_DAY]))',
    ], env=env, text=True))
    minute, player_day, site_day = budget
    longest = max(level['max_attempts'] for name in
                  ['giga_chad', 'arena', 'debate_battle', 'heist', 'telephone_game']
                  for level in game_definition(name).public_levels())
    assert minute >= longest + 1  # Existing-player run creation also consumes a request.
    assert (player_day, site_day) == (100, 1000)
