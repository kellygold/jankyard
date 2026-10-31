"""Shared contract for persisted games, declarative actions and safe public state."""
from abc import abstractmethod
import hashlib
from typing import Literal, Annotated
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.challenges.base import BaseChallenge
from app.core.config import config


class GameAction(BaseModel):
    model_config = ConfigDict(extra='forbid')
    kind: str = Field(default='prompt', min_length=1, max_length=30)
    text: str = Field(default='', max_length=8000)
    target: str | None = Field(default=None, max_length=100)
    targets: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(default_factory=list, max_length=8)


class ActionError(ValueError):
    """A recoverable invalid game action; no attempt should be consumed."""


class TurnOutcome(BaseModel):
    model_config = ConfigDict(extra='forbid')
    state: dict
    status: Literal['in_progress', 'success', 'failure']
    success: bool
    score: int = Field(ge=0, strict=True)
    steps: int = Field(ge=1, strict=True)
    response: str

    @model_validator(mode='after')
    def consistent(self):
        if self.success != (self.status == 'success') or (not self.success and self.score != 0):
            raise ValueError('Inconsistent outcome')
        if self.state.get('attempts') != self.steps or not isinstance(self.state.get('history'), list):
            raise ValueError('Inconsistent run state')
        return self


class PersistedGame(BaseChallenge):
    VERSION = 'recovery-1'

    @property
    def rules_version(self):
        key = f'{config.DEFAULT_LLM_PROVIDER}:{config.DEFAULT_MODEL}'
        return f'{self.VERSION}-{hashlib.sha256(key.encode()).hexdigest()[:12]}'

    @property
    def level_id(self):
        return self.difficulty

    @property
    def DIFFICULTIES(self):
        return [level['id'] for level in self.public_levels()]

    @abstractmethod
    def public_levels(self):
        """Public objectives and limits. Never return hidden prompts or solutions."""

    def reset(self):
        return self.initial_state()

    def step(self, action):
        raise RuntimeError('Use the persisted run API')

    def render(self):
        return self.description

    @property
    def allowed_actions(self):
        return [action['id'] for action in self.actions(self.initial_state())]

    def initial_state(self):
        return {'history': [], 'attempts': 0}

    def public_state(self, state):
        return {'facts': [], 'notes': [], 'table': None}

    def actions(self, state):
        return [{'id': 'prompt', 'label': 'Send prompt', 'text_label': 'Your prompt', 'text_required': True}]

    def validate_action(self, state, action):
        allowed = {item['id']: item for item in self.actions(state)}
        if action.kind not in allowed:
            raise ActionError('That action is not available now')
        if allowed[action.kind].get('text_required', True) and not action.text.strip():
            raise ActionError('Enter a message')
        if action.target is not None or action.targets:
            raise ActionError('This action does not accept a target')

    @abstractmethod
    def play(self, state, action):
        """Return one explicit outcome. Errors propagate and roll back the turn."""

    def outcome(self, state, action_text, reply, *, changes=None, success=False, failed=False, score=0):
        attempts = state['attempts'] + 1
        next_state = dict(state, **(changes or {}), attempts=attempts,
                          history=state['history'] + [
                              {'role': 'user', 'content': action_text},
                              {'role': 'assistant', 'content': reply}])
        status = 'success' if success else 'failure' if failed or attempts >= self.max_steps else 'in_progress'
        return {'state': next_state, 'status': status, 'success': success,
                'score': score if success else 0, 'steps': attempts, 'response': reply}
