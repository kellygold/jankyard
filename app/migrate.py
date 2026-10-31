"""Explicit additive schema preparation; never runs on application startup.

Existing installation: python -m app.migrate
Empty local database: python -m app.migrate --bootstrap
"""
import argparse
from sqlalchemy import inspect
from app.core.database import engine, Base
import app.models  # register every table
from app.models.run import ChallengeRun, RunTurn, RunScore


def migrate(bootstrap=False):
    with engine.begin() as connection:
        if bootstrap:
            Base.metadata.create_all(connection)
        else:
            existing = set(inspect(connection).get_table_names())
            required = {'users', 'submissions', 'leaderboard', 'rate_limits'}
            if not required <= existing:
                raise RuntimeError('Existing schema incomplete; use --bootstrap only for an empty development database')
            Base.metadata.create_all(connection, tables=[ChallengeRun.__table__, RunTurn.__table__, RunScore.__table__])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bootstrap', action='store_true')
    args = parser.parse_args()
    migrate(args.bootstrap)
    print('Schema prepared. Existing scores and submissions were not changed.')
