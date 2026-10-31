"""Every two-file prompt-game contribution runs through this same contract."""
import json
from pathlib import Path
import pytest
from app.challenges import ChallengeRegistry
from app.challenges.prompt_game import PromptGame

FIXTURES = Path(__file__).parents[1] / 'runtime/fixtures'
GAMES = [(name, cls) for name, cls in ChallengeRegistry.get_all().items() if issubclass(cls, PromptGame)]
CASES = [(name, case) for name, _ in GAMES for case in json.loads((FIXTURES / f'{name}.json').read_text())]


@pytest.mark.parametrize('name,case', CASES, ids=[f"{name}: {case['name']}" for name, case in CASES])
def test_objective_fixture(name, case):
    game = ChallengeRegistry.get_challenge(name, {'difficulty': case['level']})
    assert game.level.wins(case['response'], case['prompt']) is case['success']


@pytest.mark.parametrize('name,cls', GAMES)
def test_every_level_has_winning_and_losing_fixtures(name, cls):
    cases = [case for game_name, case in CASES if name == game_name]
    for level in cls.LEVELS:
        assert {case['success'] for case in cases if case['level'] == level.id} == {False, True}
