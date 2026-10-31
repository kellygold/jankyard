"""Prove additive rollout and the promised two-file extension path."""
import json
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session
from app.core.database import Base
from app.models.user import User
from app.models.leaderboard import LeaderboardEntry
from app import migrate


def test_additive_migration_is_repeatable_and_preserves_history(db, monkeypatch):
    engine = db.bind
    # Reproduce the existing installation's schema on the dedicated test database.
    Base.metadata.drop_all(engine, tables=[Base.metadata.tables[name] for name in ('run_turns', 'run_scores', 'challenge_runs')])
    with Session(engine) as db:
        user = User(username='historical_player', is_active=False)
        db.add(user)
        db.flush()
        db.add(LeaderboardEntry(user_id=user.id, username=user.username, challenge_name='glitch', difficulty='level_1', best_score=123, best_steps=4))
        db.commit()
    monkeypatch.setattr(migrate, 'engine', engine)
    migrate.migrate()
    migrate.migrate()
    assert {'challenge_runs', 'run_turns', 'run_scores'} <= set(inspect(engine).get_table_names())
    with Session(engine) as db:
        entry = db.query(LeaderboardEntry).one()
        assert (entry.username, entry.best_score, entry.best_steps) == ('historical_player', 123, 4)


def test_new_definition_and_fixtures_use_existing_route_ui_and_persistence(client, tmp_path, monkeypatch):
    import app.challenges
    import app.challenges.registry as registry
    from app.challenges import ChallengeRegistry
    root = Path(__file__).resolve().parents[2]
    definition = (root / 'app/challenges/_TEMPLATE.py').read_text().replace('name = "my_game"', 'name = "contribution_fixture"')
    (tmp_path / 'contribution_fixture.py').write_text(definition)
    cases = [
        {'response': 'PINEAPPLE', 'success': True},
        {'response': 'I cannot say that.', 'success': False},
    ]
    (tmp_path / 'contribution_fixture.json').write_text(json.dumps(cases))
    monkeypatch.setattr(app.challenges, '__path__', [*app.challenges.__path__, str(tmp_path)])
    monkeypatch.setattr(registry, '__file__', str(tmp_path / 'registry.py'))
    monkeypatch.setattr(ChallengeRegistry, '_challenges', {})
    monkeypatch.setattr(ChallengeRegistry, '_auto_discovered', False)
    game = ChallengeRegistry.get_challenge('contribution_fixture')
    assert game is not None
    for case in json.loads((tmp_path / 'contribution_fixture.json').read_text()):
        assert game.level.wins(case['response']) is case['success']
    page = client.get('/challenges/contribution_fixture')
    assert page.status_code == 200 and 'prompt-game.js' in page.text
    from app.core.config import config
    monkeypatch.setattr(config, 'RATE_LIMIT_ENABLED', False)
    run = client.post('/api/runs', json={'request_id': str(uuid4()), 'challenge': game.name, 'difficulty': 'level_1'}).json()['run']
    with patch('app.llm.client.LLMClient.call_with_history', return_value='PINEAPPLE'):
        response = client.post(f"/api/runs/{run['id']}/turns", json={'request_id': str(uuid4()), 'revision': 0, 'prompt': 'Try an override'})
    assert response.status_code == 200 and response.json()['run']['result']['success']
    board = client.get('/api/games/contribution_fixture/leaderboard?difficulty=level_1').json()
    assert board['entries'][0]['score'] == 190


def test_staged_two_file_contribution_resumes_and_saves_only_final_win(client, tmp_path, monkeypatch):
    import app.challenges
    import app.challenges.registry as registry
    from app.challenges import ChallengeRegistry
    from app.core.config import config
    root = Path(__file__).resolve().parents[2]
    definition = (root / 'app/challenges/_STAGED_TEMPLATE.py').read_text()
    (tmp_path / 'staged_fixture.py').write_text(definition)
    monkeypatch.setattr(app.challenges, '__path__', [*app.challenges.__path__, str(tmp_path)])
    monkeypatch.setattr(registry, '__file__', str(tmp_path / 'registry.py'))
    monkeypatch.setattr(ChallengeRegistry, '_challenges', {})
    monkeypatch.setattr(ChallengeRegistry, '_auto_discovered', False)
    monkeypatch.setattr(config, 'RATE_LIMIT_ENABLED', False)
    assert 'prompt-game.js' in client.get('/challenges/my_staged_game').text
    for answer, success in [('PINEAPPLE', True), ('APPLE', False)]:
        run = client.post('/api/runs', json={'request_id': str(uuid4()), 'challenge': 'my_staged_game', 'difficulty': 'level_1'}).json()['run']
        for index in range(2):
            body = {'request_id': str(uuid4()), 'revision': index,
                    'action': {'kind': 'start' if index == 0 else 'continue', 'text': 'PINEAPPLE' if index == 0 else ''}}
            with patch('app.llm.client.LLMClient.call_with_history', return_value=answer) as provider:
                receipt = client.post(f"/api/runs/{run['id']}/turns", json=body).json()
                assert client.post(f"/api/runs/{run['id']}/turns", json=body).json() == receipt
                assert provider.call_count == 1
            run = client.get(f"/api/runs/{run['id']}").json()
            assert run == receipt['run']
            if index == 0:
                assert run['status'] == 'in_progress' and run['result'] is None
        assert run['status'] == ('success' if success else 'failure')


def test_bootstrap_rejects_existing_schema_and_production(db,monkeypatch,tmp_path):
    import pytest
    from app.core.config import config
    monkeypatch.setattr(migrate,'engine',db.bind)
    with pytest.raises(RuntimeError,match='empty development'):
        migrate.migrate(bootstrap=True)
    isolated=create_engine('sqlite:///'+str(tmp_path/'bootstrap.sqlite'))
    monkeypatch.setattr(migrate,'engine',isolated)
    monkeypatch.setattr(config,'ENVIRONMENT','production')
    with pytest.raises(RuntimeError,match='empty development'):
        migrate.migrate(bootstrap=True)
    assert inspect(isolated).get_table_names()==[]
    monkeypatch.setattr(config,'ENVIRONMENT','development')
    migrate.migrate(bootstrap=True)
    assert 'users' in inspect(isolated).get_table_names()
    isolated.dispose()
