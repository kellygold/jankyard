"""The legacy transport must not publish an unsaved win or trust a display name."""
import json
from unittest.mock import patch
import pytest
from app.core.config import config
from app.models.submission import Submission
from app.models.leaderboard import LeaderboardEntry


async def successful_stream(*args):
    yield 'data: ' + json.dumps({'type': 'complete', 'data': {'result': {
        'status': 'success', 'score': 100, 'steps': 1, 'success': True,
        'logs': ['string log', {'detail': 'structured log'}],
    }}}) + '\n\n'


@pytest.fixture(autouse=True)
def disable_limits(monkeypatch):
    monkeypatch.setattr(config, 'RATE_LIMIT_ENABLED', False)


def test_legacy_completion_waits_for_real_save(client, db, test_user, auth_headers):
    with patch('app.routes.submissions.stream_challenge', successful_stream):
        response = client.post('/submit/stream', data={'challenge_name': 'trivia', 'difficulty': 'EASY', 'agent_code': '4'}, headers=auth_headers)
    event = json.loads(response.text.removeprefix('data: ').strip())
    assert event['data']['saved'] and event['data']['submission_id'] > 0
    assert db.query(Submission).one().logs == ['string log', {'detail': 'structured log'}]
    assert db.query(LeaderboardEntry).one().user_id == test_user.id


def test_legacy_commit_failure_publishes_only_error(client, db, auth_headers):
    with patch('app.routes.submissions.stream_challenge', successful_stream), patch.object(db, 'commit', side_effect=RuntimeError('commit failed')):
        response = client.post('/submit/stream', data={'challenge_name': 'trivia', 'difficulty': 'EASY', 'agent_code': '4'}, headers=auth_headers)
    assert '"type":"error"' in response.text and 'complete' not in response.text
    assert db.query(Submission).count() == db.query(LeaderboardEntry).count() == 0


def test_legacy_guest_cannot_claim_registered_name(client, db, test_user):
    with patch('app.routes.submissions.stream_challenge', successful_stream):
        for _ in range(2):
            response = client.post('/submit/stream', data={'challenge_name': 'trivia', 'difficulty': 'EASY', 'agent_code': '4', 'username': test_user.username})
            assert '"saved": true' in response.text
    owners = {submission.user_id for submission in db.query(Submission).all()}
    assert len(owners) == 1 and test_user.id not in owners


def test_rejected_legacy_requests_do_not_create_guest_accounts(client, db):
    from app.models.user import User
    before = db.query(User).count()
    assert client.post('/submit/stream', data={'challenge_name': 'unknown', 'agent_code': 'hello'}).status_code == 404
    assert client.post('/submit/stream', data={'challenge_name': 'glitch', 'agent_code': 'hello'}).status_code == 410
    assert db.query(User).count() == before
