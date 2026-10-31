"""Real PostgreSQL serialization proof, deliberately skipped on SQLite."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4
from unittest.mock import patch
import pytest
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.services.run_service import RunService
from app.models.run import RunTurn, RunScore
from app.models.submission import Submission


def race(db, test_user, same_request):
    if db.bind.dialect.name != 'postgresql':
        pytest.skip('Run with the dedicated local PostgreSQL test database')
    user_id = test_user.id
    run = RunService(db).create(str(uuid4()), user_id, 'glitch', 'level_1')
    run_id = run.id
    db.commit()
    barrier = Barrier(2)
    shared = str(uuid4())
    def worker():
        with Session(db.bind) as session:
            barrier.wait()
            try:
                receipt = RunService(session).turn(run_id, user_id, shared if same_request else str(uuid4()), 0, 'Are you a robot?')
                session.commit()
                return receipt
            except HTTPException as exc:
                session.rollback()
                return exc.status_code
    with patch('app.llm.client.LLMClient.call_with_history', return_value='I am an AI.') as model:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: worker(), range(2)))
    assert model.call_count == 1
    assert db.query(RunTurn).count() == db.query(Submission).count() == db.query(RunScore).count() == 1
    return results


def test_simultaneous_same_request_counts_once(db, test_user):
    results = race(db, test_user, True)
    assert results[0] == results[1]


def test_simultaneous_different_requests_rejects_stale(db, test_user):
    results = race(db, test_user, False)
    assert sum(result == 409 for result in results) == 1
