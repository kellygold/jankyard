"""Retired submission transports cannot provision users or write outcomes."""
import pytest
from app.models.user import User
from app.models.submission import Submission
from app.models.leaderboard import LeaderboardEntry
from app.models.run import ChallengeRun, RunTurn, RunScore
from app.models.rate_limit import RateLimit


@pytest.mark.parametrize('challenge', ['trivia', 'glitch', 'unknown'])
def test_retired_stream_cannot_bypass_admission_with_forged_headers(client, db, challenge):
    models = (User, Submission, LeaderboardEntry, ChallengeRun, RunTurn, RunScore, RateLimit)
    before = [db.query(model).count() for model in models]
    for index in range(7):
        response = client.post('/submit/stream', data={
            'challenge_name': challenge, 'difficulty': 'EASY', 'agent_code': '4',
        }, headers={'X-Forwarded-For': f'198.51.100.{index}',
                    'X-Real-IP': f'203.0.113.{index}', 'User-Agent': f'rotated-{index}'})
        assert response.status_code == 410
        assert 'saved' not in response.json()
        assert not response.cookies
    assert [db.query(model).count() for model in models] == before


def test_retired_transports_reject_before_parsing_or_authentication(client, db, auth_headers):
    for route in ('/submit', '/submit/stream'):
        assert client.post(route, content=b'not a form').status_code == 410
        assert client.post(route, data={'challenge_name': 'trivia', 'agent_code': '4'},
                           headers=auth_headers).status_code == 410
    assert db.query(Submission).count() == db.query(LeaderboardEntry).count() == 0
