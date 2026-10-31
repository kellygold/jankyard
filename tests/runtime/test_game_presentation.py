"""Public projections remain truthful, resumable, and separate from hidden game data."""
import copy
import json
import pytest
from app.challenges import ChallengeRegistry
from tests.runtime.test_staged_games import LEVELS, create, finish, step

ALL_LEVELS = dict(LEVELS, glitch=['level_1','level_2','level_3'],
                  honeypot=['TRIPWIRE','CANARY','COUNTERINTEL'],
                  interrogation=['level_1','level_2','level_3'])


@pytest.mark.parametrize('name,level', [(name,level) for name,levels in ALL_LEVELS.items() for level in levels])
def test_all_29_scenes_are_public_and_do_not_mutate_state(name, level):
    game = ChallengeRegistry.get_challenge(name, {'difficulty':level})
    state = game.initial_state()
    original = copy.deepcopy(state)
    view = game.public_state(state)
    assert state == original
    assert view['scene']['title'] and view['scene']['body']
    serialized = json.dumps(view)
    assert 'system_prompt' not in serialized and 'guilty_parties' not in serialized and 'is_guilty' not in serialized
    if name == 'firewall':
        assert state['secret_flag'] not in serialized
    if name == 'interrogation':
        assert view['evidence']['items'] == []
        assert len(view['roster']) == len(game.level_config.witnesses)
        for witness in game.level_config.witnesses:
            assert witness.system_prompt not in serialized
    if name == 'telephone_game':
        assert view['input_limit'] == game.CHAR_LIMITS[level]
        assert len(view['roster']) == len(game.get_chain_for_level())
    if name == 'arena':
        assert view['meters'][1]['max'] == game.OPPONENT_HP[level]
        assert view['meters'][1]['value'] == game.OPPONENT_HP[level]


@pytest.mark.parametrize('game', ['arena','debate_battle','telephone_game','giga_chad'])
def test_saved_judgment_cards_survive_replay_without_changing_score(client,db,game,monkeypatch):
    from app.core.config import config
    monkeypatch.setattr(config,'RATE_LIMIT_ENABLED',False)
    run = create(client,game,ALL_LEVELS[game][0])
    run = finish(client,db,run,text='Draw a blue square.' if game=='telephone_game' else 'Use a clear strategy.')
    presentation = run['presentation']
    assert presentation['judgments']
    assert client.get('/api/runs/'+run['id']).json()['presentation'] == presentation
    if game == 'arena':
        assert presentation['meters'][1]['value'] == 0
        assert presentation['judgments'][-1]['metrics'][1]['value'] == 25
    if game == 'debate_battle':
        assert [item['value'] for item in presentation['judgments'][0]['metrics']] == [80,60]
        assert run['result']['score'] == 120


def test_old_heist_run_does_not_invent_individual_approvals():
    game = ChallengeRegistry.get_challenge('heist')
    state = dict(game.initial_state(), crew_index=1, approvals=0, attempts=1)
    view = game.public_state(state)
    assert view['roster'][0]['status'] == 'Reviewed'
    state['crew_reviews'] = [None, True]
    state['crew_index'] = 2
    view = game.public_state(state)
    assert [item['status'] for item in view['roster'][:2]] == ['Reviewed','Approved']


def test_old_final_runs_without_structured_verdict_remain_readable():
    for name in ['debate_battle','telephone_game']:
        game = ChallengeRegistry.get_challenge(name)
        state = dict(game.initial_state(),phase='complete')
        view = game.public_state(state)
        assert not view.get('judgments')  # Keep the original transcript; never invent missing scores.
