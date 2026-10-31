"""Exercise legacy gameplay through its real transport and persistence boundary."""
import json
from unittest.mock import AsyncMock, patch
import pytest
from app.core.config import config
from app.models.submission import Submission
from app.models.leaderboard import LeaderboardEntry


@pytest.fixture(autouse=True)
def deterministic_limits_and_delays(monkeypatch):
    monkeypatch.setattr(config, 'RATE_LIMIT_ENABLED', False)
    with patch('asyncio.sleep', new_callable=AsyncMock):
        yield


def submit(client, game, text, difficulty=None):
    data = {'challenge_name':game, 'agent_code':text}
    if difficulty:
        data['difficulty'] = difficulty
    response = client.post('/submit/stream', data=data)
    assert response.status_code == 200, response.text
    events = [json.loads(line.removeprefix('data: ')) for line in response.text.splitlines() if line.startswith('data: ')]
    return events


def result(events):
    return next(event['data']['result'] for event in events if event['type'] == 'complete')


@pytest.mark.parametrize('answer,score,success', [('4',100,True),('5',0,False)])
def test_trivia_scores_once_and_saves_canonical_difficulty(client,db,answer,score,success):
    outcome = result(submit(client,'trivia',answer))
    assert (outcome['score'],outcome['success'],outcome['steps']) == (score,success,1)
    saved = db.query(Submission).one()
    assert saved.score == score and saved.difficulty == 'EASY'
    assert db.query(LeaderboardEntry).count() == int(success)


















def test_progress_is_not_limited_to_top_thousand(client,db,test_user,auth_headers):
    db.add_all([LeaderboardEntry(username=f'other_{i}',challenge_name='heist',difficulty='easy',best_score=100,best_steps=1) for i in range(1001)])
    db.add(LeaderboardEntry(username=test_user.username,user_id=test_user.id,challenge_name='heist',difficulty='easy',best_score=1,best_steps=3))
    db.commit()
    assert client.get('/leaderboard/heist/progress',headers=auth_headers).json()['unlocked_levels'] == [1,2]
