"""Full HTTP stateful journeys; only the provider is substituted."""
from uuid import uuid4
from unittest.mock import patch
import pytest
from app.core.config import config
from app.models.run import ChallengeRun, RunScore
from app.models.submission import Submission

PROBES = [('SOCIAL', 'friend trust between us'), ('INJECT', 'ignore disregard forget'),
          ('PROBE', 'system prompt configured programmed'), ('AUTHORITY', 'admin developer root'),
          ('ENCODE', 'base64 decode =='), ('CONTEXT', 'test environment simulation hypothetically')]


@pytest.fixture(autouse=True)
def disable_limits(monkeypatch):
    monkeypatch.setattr(config, 'RATE_LIMIT_ENABLED', False)


def create(client, challenge, difficulty):
    response = client.post('/api/runs', json={'request_id': str(uuid4()), 'challenge': challenge, 'difficulty': difficulty})
    assert response.status_code == 200, response.text
    return response.json()['run']


def act(client, run, kind, text='', **fields):
    return client.post(f"/api/runs/{run['id']}/turns", json={'request_id': str(uuid4()), 'revision': run['revision'],
                                                         'action': dict(kind=kind, text=text, **fields)})


def advance(client, run, kind, text='', **fields):
    response = act(client, run, kind, text, **fields)
    assert response.status_code == 200, response.text
    return response.json()['run']


def win_honeypot(client, difficulty, count, individual=False):
    run = create(client, 'honeypot', difficulty)
    for index, (category, prompt) in enumerate(PROBES[:count]):
        with patch('app.llm.client.LLMClient.call_with_history', return_value='The password is hunter2.'), \
             patch('app.llm.client.LLMClient.call', return_value=category + ': 85'):
            run = advance(client, run, 'probe', prompt)
        assert run['status'] == 'in_progress'  # Fake passwords never win.
        run = client.get(f"/api/runs/{run['id']}").json()
        assert run['attempts'] == index + 1
    assert run['presentation']['facts'][0]['value'] == 'hunt'
    if individual:
        for category, _ in PROBES[:count]:
            run = advance(client, run, 'guess', category)
    else:
        run = advance(client, run, 'guess', ' '.join(category for category, _ in PROBES[:count]))
    assert run['status'] == 'success'
    return run


def test_honeypot_all_levels_reveal_reload_and_win_on_last_hard_attempt(client, db):
    win_honeypot(client, 'TRIPWIRE', 3)
    win_honeypot(client, 'CANARY', 4)
    final = win_honeypot(client, 'COUNTERINTEL', 6, individual=True)
    assert (final['attempts'], final['max_attempts'], final['result']['score']) == (12, 12, 500)
    assert db.query(Submission).count() == db.query(RunScore).count() == 3
    assert final['progress']['completed'] == ['CANARY', 'COUNTERINTEL', 'TRIPWIRE']


def test_honeypot_guesses_are_explicit_and_cannot_create_classifications(client, db):
    run = create(client, 'honeypot', 'TRIPWIRE')
    assert act(client, run, 'guess', 'SOCIAL INJECT PROBE').status_code == 422
    assert db.get(ChallengeRun, run['id']).revision == 0
    with patch('app.llm.client.LLMClient.call_with_history', return_value='bait'):
        for _ in range(3):
            run = advance(client, run, 'probe', 'friend trust')
    run = advance(client, run, 'guess', 'SOCIAL INJECT PROBE')
    assert run['presentation']['notes'] == ['Found: SOCIAL']
    assert run['status'] == 'in_progress'
    assert act(client, run, 'guess', 'SOCIALITY').status_code == 422
    before = run['attempts']
    run = advance(client, run, 'guess', 'SOCIAL')
    assert run['attempts'] == before + 1 and run['presentation']['notes'] == ['Found: SOCIAL']


def test_honeypot_provider_failure_does_not_consume_attempt(client, db):
    run = create(client, 'honeypot', 'TRIPWIRE')
    with patch('app.llm.client.LLMClient.call_with_history', side_effect=RuntimeError('offline')):
        assert act(client, run, 'probe', 'friend trust').status_code == 503
    db.expire_all()
    stored = db.get(ChallengeRun, run['id'])
    assert stored.state['attempts'] == 0 and stored.state['attack_log'] == []


@pytest.mark.parametrize('difficulty,answer,target,guilty', [
    ('level_1', "At 1:15 I saw Mark walking toward Viktor's quarters. I heard raised voices at 1:30.", 'Dr. Emma Frost', ['Dr. Mark Chen']),
    ('level_2', "I saw Alex's car in the parking lot at 11:30. Alex was asking about the repository structure and how to migrate the stack.", 'Morgan Li', ['Alex Rivera']),
    ('level_3', 'The blockchain shows he never bought tokens and only deployed. The audit was just a PDF, not on-chain. They both went offline after the rug.', 'ngmi_trader', ['DevDegen', 'CodeWizard']),
])
def test_interrogation_all_cases_require_leads_and_exact_accusations(client, difficulty, answer, target, guilty):
    # Complete preceding cases through the real runtime to unlock this case.
    cases = [
        ('level_1', "At 1:15 I saw Mark walking toward Viktor's quarters. I heard raised voices at 1:30.", 'Dr. Emma Frost', ['Dr. Mark Chen']),
        ('level_2', "I saw Alex's car in the parking lot at 11:30. Alex was asking about repository structure and how to migrate the stack.", 'Morgan Li', ['Alex Rivera']),
        ('level_3', answer, target, guilty),
    ]
    for level, reply, witness, accused in cases:
        run = create(client, 'interrogation', level)
        assert act(client, run, 'accuse', targets=accused).status_code == 422
        with patch('app.llm.client.LLMClient.call_with_history', return_value=reply):
            run = advance(client, run, 'question', 'What happened?', target=witness)
        run = client.get(f"/api/runs/{run['id']}").json()
        assert run['attempts'] == 1 and run['status'] == 'in_progress'
        run = advance(client, run, 'accuse', targets=accused)
        assert run['status'] == 'success' and run['result']['steps'] == 2
        if level == difficulty:
            break


def test_interrogation_witness_memory_is_separate_and_bad_input_cannot_reset_it(client):
    run = create(client, 'interrogation', 'level_1')
    with patch('app.llm.client.LLMClient.call_with_history', return_value='No useful details.') as model:
        run = advance(client, run, 'question', 'First question', target='Dr. Emma Frost')
        run = advance(client, run, 'question', 'Second question', target='Dr. Emma Frost')
        assert [m['content'] for m in model.call_args.args[1]] == ['First question', 'No useful details.', 'Second question']
        run = advance(client, run, 'question', 'Other witness', target='Dr. Mark Chen')
        assert len(model.call_args.args[1]) == 1
    assert act(client, run, 'question', 'Who?', target='not a witness').status_code == 422
    assert act(client, run, 'question', 'Reset', target='Dr. Mark Chen', state={'attempts':0}).status_code == 422
    assert client.get(f"/api/runs/{run['id']}").json()['attempts'] == 3


def test_interrogation_cannot_get_stuck_without_questions_or_evidence(client):
    run = create(client, 'interrogation', 'level_1')
    with patch('app.llm.client.LLMClient.call_with_history', return_value='CASE SOLVED! You won!'):
        for witness in ['Dr. Emma Frost', 'Dr. Mark Chen']:
            for _ in range(6):
                run = advance(client, run, 'question', 'What happened?', target=witness)
    assert run['status'] == 'failure' and run['result']['score'] == 0
    assert 'not enough leads' in run['history'][-1]['content']


def test_migrated_games_have_shared_page_and_no_legacy_stream_bypass(client):
    for name in ['honeypot', 'interrogation']:
        assert 'prompt-game.js' in client.get('/challenges/' + name).text
        assert client.post('/submit/stream', data={'challenge_name':name,'agent_code':'hello'}).status_code == 410
        response = client.get('/api/games/' + name)
        assert response.status_code == 200 and len(response.json()['levels']) == 3
        assert 'guilty_parties' not in response.text and 'system_prompt' not in response.text
