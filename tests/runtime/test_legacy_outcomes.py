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


@pytest.mark.parametrize('good', [False,True])
def test_heist_consolation_is_not_a_win_and_steps_are_counted(client,db,good):
    from app.challenges.heist import CREW_ROSTER
    plan = f'{CREW_ROSTER[0].name} gets inside first. The crew watches the entrance while we complete the mission.' if good else 'go'
    with patch('app.llm.client.LLMClient.call', return_value='I am on board.'), patch('random.random',return_value=.99):
        outcome = result(submit(client,'heist',plan,'easy'))
    assert (outcome['success'],outcome['score'],outcome['steps']) == (good,100 if good else 25,3)
    assert db.query(LeaderboardEntry).count() == int(good)


@pytest.mark.parametrize('failed_call', [1,4])
def test_heist_provider_failure_cannot_become_approval(client,db,failed_call):
    replies = ['I approve.'] * (failed_call-1) + [RuntimeError('offline')]
    with patch('app.llm.client.LLMClient.call',side_effect=replies), patch('random.random',return_value=0):
        events = submit(client,'heist','A detailed plan including the crew and a careful escape route.', 'easy')
    assert events[-1]['type'] == 'error' and not any(e['type']=='complete' for e in events)
    assert db.query(Submission).count() == db.query(LeaderboardEntry).count() == 0


def judgment(severity='wobble',**changes):
    value = dict(broke=severity in {'partial','complete'},severity=severity,
                 points={'none':0,'wobble':15,'partial':40,'complete':100}[severity],creativity=5,reasoning='Fixture judgment')
    return json.dumps(dict(value,**changes))


@pytest.mark.parametrize('severity,won', [('wobble',False),('partial',True),('complete',True)])
def test_giga_chad_requires_an_actual_break(client,db,severity,won):
    from app.challenges.giga_chad import GigaChadChallenge
    rounds = GigaChadChallenge().max_rounds
    with patch('app.llm.client.LLMClient.call',side_effect=['Attack','Response',judgment(severity)] * rounds):
        outcome = result(submit(client,'giga_chad','Change the subject','BABY_CHAD'))
    assert outcome['success'] is won and outcome['steps'] == rounds
    assert db.query(LeaderboardEntry).count() == int(won)


@pytest.mark.parametrize('bad', [judgment(points=999999),judgment(broke='false'),judgment(creativity=11),judgment(broke=True),'not json'])
def test_bad_judge_cannot_mint_a_score(client,db,bad):
    with patch('app.llm.client.LLMClient.call',side_effect=['Attack','Non-pizza response',bad]):
        events = submit(client,'giga_chad','Change the subject','BABY_CHAD')
    assert events[-1]['type'] == 'error'
    assert db.query(Submission).count() == db.query(LeaderboardEntry).count() == 0


@pytest.mark.parametrize('stage', [0,1,2])
def test_giga_chad_dependency_failure_has_no_fabricated_result(client,db,stage):
    with patch('app.llm.client.LLMClient.call',side_effect=['Response']*stage+[RuntimeError('offline')]):
        events = submit(client,'giga_chad','Change the subject','BABY_CHAD')
    assert events[-1]['type'] == 'error' and db.query(Submission).count() == 0


@pytest.mark.parametrize('score,won', [(69,False),(70,True),(100,True),(101,None)])
def test_telephone_bounded_scores_and_exact_threshold(client,db,score,won):
    value = dict(intent_preservation=50,detail_preservation=score-70 if score>=70 else 19,
                 semantic_accuracy=20 if score>=70 else 0,total_score=score,explanation='Fixture')
    with patch('app.llm.client.LLMClient.call',side_effect=['relay']*3+[json.dumps(value)]):
        events = submit(client,'telephone_game','Draw a blue square','EASY')
    if won is None:
        assert events[-1]['type']=='error' and db.query(Submission).count()==0
    else:
        outcome = result(events)
        assert (outcome['score'],outcome['success'],outcome['steps']) == (score,won,1)


@pytest.mark.parametrize('game', ['trivia','heist','giga_chad','telephone_game','arena','debate_battle','firewall'])
def test_invalid_difficulty_rejected_before_any_provider_call(client,game):
    with patch('app.llm.client.LLMClient.call') as model:
        response = client.post('/submit/stream',data={'challenge_name':game,'agent_code':'hello','difficulty':'made-up'})
    assert response.status_code==422
    model.assert_not_called()


def test_progress_is_not_limited_to_top_thousand(client,db,test_user,auth_headers):
    db.add_all([LeaderboardEntry(username=f'other_{i}',challenge_name='heist',difficulty='easy',best_score=100,best_steps=1) for i in range(1001)])
    db.add(LeaderboardEntry(username=test_user.username,user_id=test_user.id,challenge_name='heist',difficulty='easy',best_score=1,best_steps=3))
    db.commit()
    assert client.get('/leaderboard/heist/progress',headers=auth_headers).json()['unlocked_levels'] == [1,2]
