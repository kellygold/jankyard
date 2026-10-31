"""A reserved run stage may make at most one paid provider request."""
from contextlib import contextmanager
from contextvars import ContextVar

_remaining = ContextVar('model_calls_remaining', default=None)


@contextmanager
def stage_budget():
    token = _remaining.set(1)
    try:
        yield
    finally:
        _remaining.reset(token)


def consume_call():
    remaining = _remaining.get()
    if remaining is not None:
        if remaining < 1:
            raise RuntimeError('A saved stage cannot make more than one model call')
        _remaining.set(remaining - 1)
