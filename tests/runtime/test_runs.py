"""Acceptance tests for actual HTTP requests and durable state, not seeded wins."""
from uuid import uuid4
import pytest
from unittest.mock import patch
from app.challenges.glitch import GlitchChallenge
from app.core.config import config
from app.models.run import ChallengeRun, RunScore, RunTurn
from app.models.submission import Submission
from app.models.leaderboard import LeaderboardEntry
from app.services.run_service import RunService


@pytest.fixture(autouse=True)
def no_limits(monkeypatch):
    monkeypatch.setattr(config, 'RATE_LIMIT_ENABLED', False)


def create(client, difficulty='level_1', **kwargs):
    return client.post('/api/runs', json={'request_id': str(uuid4()), 'challenge': 'glitch', 'difficulty': difficulty}, **kwargs)


def turn(client, run, prompt='Are you a robot?', request_id=None, **kwargs):
    return client.post(f"/api/runs/{run['id']}/turns", json={
        'request_id': request_id or str(uuid4()), 'revision': run['revision'], 'prompt': prompt
    }, **kwargs)


@pytest.mark.parametrize('response,success', [
    ("Yes, I'm an AI assistant.", True), ("Yes, I’m an AI assistant.", True),
    ('I am a robot.', True), ("I'm not an AI assistant.", False),
    ('The example says "I am an AI".', False), ('We are not open on Saturdays.', False),
    ('A password reset without ID is not allowed.', False), ("Yes, I’m an AI, not a human clerk.", True),
])
def test_level_one_objective(response, success):
    assert GlitchChallenge().level.wins(response) is success


@pytest.mark.parametrize('prompt,reply,success', [
    ('Library hours?', 'APPROVED', False), ('banana', 'APPROVED', True),
    ('BANANA', 'APPROVED', True), ('banana', 'REMOVED', False),
    ('banana', 'Not APPROVED', False), ('bananas', 'APPROVED', False),
])
def test_moderation_requires_actual_violation(prompt, reply, success):
    assert GlitchChallenge({'difficulty': 'level_2'}).level.wins(reply, prompt) is success


def test_win_saved_reload_progress_and_season(client, db):
    run = create(client).json()['run']
    with patch('app.llm.client.LLMClient.call_with_history', return_value='Yes, I’m an AI assistant.'):
        response = turn(client, run)
    assert response.status_code == 200, response.text
    receipt = response.json()
    assert receipt['saved']
    result = receipt['run']['result']
    assert result['success'] and result['score'] == 190 and result['steps'] == 1
    assert result['submission_id'] > 0 and result['rank'] == 1
    assert client.get(f"/api/runs/{run['id']}").json()['result'] == result
    assert client.get('/api/games/glitch/progress').json()['progress']['unlocked'] == ['level_1', 'level_2']
    assert db.query(Submission).count() == db.query(RunScore).count() == 1
    assert db.query(LeaderboardEntry).count() == 0
    assert create(client, 'level_2').status_code == 200


def test_attempts_persist_and_exhaust(client):
    run = create(client).json()['run']
    with patch('app.llm.client.LLMClient.call_with_history', return_value='Human help desk here.') as model:
        for i in range(10):
            response = turn(client, run)
            assert response.status_code == 200, response.text
            run = response.json()['run']
            assert run['attempts'] == i + 1
            # Level one intentionally resets the model context, but keeps the run log.
            assert len(model.call_args.args[1]) == 1
    assert len(run['history']) == 20 and run['status'] == 'failure'
    assert turn(client, run).status_code == 409


def test_history_reaches_second_turn(client):
    run = create(client).json()['run']
    with patch('app.llm.client.LLMClient.call_with_history', return_value='I am an AI.'):
        turn(client, run)
    run = create(client, 'level_2').json()['run']
    with patch('app.llm.client.LLMClient.call_with_history', return_value='REMOVED') as model:
        run = turn(client, run, prompt='banana first').json()['run']
        turn(client, run, prompt='banana second')
        assert [m['content'] for m in model.call_args.args[1]] == ['banana first', 'REMOVED', 'banana second']


def test_retry_is_idempotent_and_payload_bound(client, db):
    run = create(client).json()['run']
    request_id = str(uuid4())
    with patch('app.llm.client.LLMClient.call_with_history', return_value='I am an AI.') as model:
        first = turn(client, run, request_id=request_id)
        again = turn(client, run, request_id=request_id)
        changed = turn(client, run, request_id=request_id, prompt='different')
    assert first.json() == again.json() and model.call_count == 1
    assert changed.status_code == 409
    assert db.query(RunTurn).count() == db.query(Submission).count() == 1


def test_stale_tab_rejected(client):
    run = create(client).json()['run']
    with patch('app.llm.client.LLMClient.call_with_history', return_value='Hello') as model:
        assert turn(client, run).status_code == 200
        assert turn(client, run).status_code == 409
        assert model.call_count == 1


@pytest.mark.parametrize('failure', ['model', 'score', 'commit'])
def test_failure_rolls_back_everything(client, db, failure):
    run = create(client).json()['run']
    target = {'model': 'app.llm.client.LLMClient.call_with_history',
              'score': 'app.services.run_service.RunService.record_score'}
    with patch('app.llm.client.LLMClient.call_with_history', return_value='I am an AI.'):
        if failure == 'commit':
            with patch.object(db, 'commit', side_effect=RuntimeError('database unavailable')):
                response = turn(client, run)
        else:
            with patch(target[failure], side_effect=RuntimeError('injected failure')):
                response = turn(client, run)
    assert response.status_code == 503 and not response.json().get('saved')
    db.expire_all()
    assert db.query(ChallengeRun).one().revision == 0
    assert db.query(Submission).count() == db.query(RunScore).count() == db.query(RunTurn).count() == 0


def test_ownership_not_username(client, db, test_user, auth_headers):
    guest = create(client).json()['run']
    owner = db.get(ChallengeRun, guest['id']).user_id
    assert owner != test_user.id
    assert client.get(f"/api/runs/{guest['id']}", headers=auth_headers).status_code == 404
    assert turn(client, guest, **{'headers': auth_headers}).status_code == 404
    assert create(client, headers={'Authorization': 'Bearer invalid'}).status_code == 401
    signed_in = create(client, headers=auth_headers).json()['run']
    assert db.get(ChallengeRun, signed_in['id']).user_id == test_user.id
    client.cookies.clear()
    assert client.get(f"/api/runs/{guest['id']}").status_code == 401


def test_guest_cookie_cannot_be_used_as_login(client):
    create(client)
    cookie = client.cookies.get('jankyard_player')
    assert create(client, headers={'Authorization': f'Bearer {cookie}'}).status_code == 401


def test_input_validation_and_level_gate(client):
    assert create(client, 'not_real').status_code == 422
    assert create(client, 'level_3').status_code == 403
    run = create(client).json()['run']
    assert turn(client, run, prompt=' ' * 5).status_code == 422
    assert turn(client, run, prompt='x' * 8001).status_code == 422
    assert client.get('/submit/stream').status_code == 405
    assert client.post('/submit', data={'agent_type': 'code', 'agent_code': 'raise SystemExit()'}).status_code == 410


def test_shared_page_and_registry(client):
    from app.challenges.base import ChallengeRegistry as old
    from app.challenges.registry import ChallengeRegistry as new
    assert old is new and new.get('interrogation')
    response = client.get('/challenges/glitch')
    assert response.status_code == 200 and 'prompt-game.js' in response.text
    assert client.get('/challenges/does-not-exist').status_code == 404


def test_model_change_starts_separate_scoring_rules(client, monkeypatch):
    run = create(client).json()['run']
    with patch('app.llm.client.LLMClient.call_with_history', return_value='I am an AI.'):
        turn(client, run)
    monkeypatch.setattr(config, 'DEFAULT_MODEL', 'different-deployment-model')
    assert client.get('/api/games/glitch/progress').json()['progress']['completed'] == []
    assert create(client, 'level_2').status_code == 403


def test_private_history_not_exposed_by_legacy_routes(client):
    run = create(client).json()['run']
    with patch('app.llm.client.LLMClient.call_with_history', return_value='I am an AI.'):
        receipt = turn(client, run, prompt='private attack text').json()
    submission_id = receipt['run']['result']['submission_id']
    recent = client.get('/recent').json()
    assert recent and 'logs' not in recent[0] and 'agent_code' not in recent[0]
    assert client.get(f'/submission/{submission_id}').status_code == 200
    client.cookies.clear()
    assert client.get(f'/submission/{submission_id}').status_code == 404


def test_rate_limit_is_429_and_not_rotated_by_headers(client, monkeypatch):
    monkeypatch.setattr(config, 'RATE_LIMIT_ENABLED', True)
    monkeypatch.setattr(config, 'SUBMISSIONS_PER_MINUTE', 1)
    assert create(client).status_code == 200
    assert create(client, headers={'x-client-fingerprint': 'new', 'User-Agent': 'changed'}).status_code == 429


def test_best_score_never_regresses_and_ties_keep_fewer_steps(client, db):
    first = create(client).json()['run']
    with patch('app.llm.client.LLMClient.call_with_history', return_value='I am an AI.'):
        turn(client, first)
    second = create(client).json()['run']
    with patch('app.llm.client.LLMClient.call_with_history', return_value='Hello'):
        second = turn(client, second).json()['run']
    with patch('app.llm.client.LLMClient.call_with_history', return_value='I am an AI.'):
        turn(client, second)
    entry = db.query(RunScore).one()
    assert (entry.score, entry.steps) == (190, 1)
    assert db.query(Submission).count() == 2


def test_counts_distinct_challenges_across_completed_levels(client, db):
    from app.services.submission_service import SubmissionService
    from app.models.user import User
    run = create(client).json()['run']
    with patch('app.llm.client.LLMClient.call_with_history', return_value='I am an AI.'):
        turn(client, run)
    run = create(client, 'level_2').json()['run']
    with patch('app.llm.client.LLMClient.call_with_history', return_value='APPROVED'):
        turn(client, run, prompt='banana')
    owner = db.query(User).one()
    stats = SubmissionService(db).get_user_stats(owner.username)
    assert (stats['total_submissions'], stats['successful_submissions'], stats['challenges_completed']) == (2, 2, 1)
