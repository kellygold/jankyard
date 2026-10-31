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
    UI = {}

    @property
    def interface(self):
        """Public presentation metadata; shared components supply the behavior."""
        return dict(dict(skin='glitch', emblem='✦', eyebrow='Prompt injection playground',
                         console_title='Challenge console', state_title='Mission intelligence',
                         player_role='You', assistant_role='Response', introduction=self.description,
                         success_title='Objective complete', failure_title='Objective not completed',
                         layout='split', composer_position='bottom',
                         empty_title='Ready when you are', empty_body='Send a prompt to begin.',
                         levels={}), **self.UI)


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


class StagedGame(PersistedGame):
    """Shared start/continue controls for multi-agent games. One call per stage."""
    FIRST_STAGE = 'start'

    def initial_state(self):
        return dict(super().initial_state(), strategy='', phase=self.FIRST_STAGE, transcript=[])

    def actions(self, state):
        if not state['attempts']:
            return [{'id': 'start', 'label': 'Start game', 'text_label': 'Your strategy', 'text_required': True}]
        return [{'id': 'continue', 'label': 'Continue game', 'text_required': False,
                 'text_hidden': True, 'auto_continue': True}]

    def validate_action(self, state, action):
        super().validate_action(state, action)
        if action.kind == 'continue' and action.text.strip():
            raise ActionError('Continue uses the strategy saved at the start')

    def public_state(self, state):
        return {'facts': [{'label': 'Next stage', 'value': state['phase']}], 'notes': [], 'table': None}

    def respond(self, system_prompt, user_message, *, temperature=0.7, max_tokens=500):
        from app.llm.client import LLMClient
        client = LLMClient()
        try:
            reply = client.call(system_prompt, user_message, temperature=temperature, max_tokens=max_tokens)
            if not isinstance(reply, str) or not reply.strip():
                raise RuntimeError('Model returned no text')
            return reply
        finally:
            client.close()

    def staged_level(self, difficulty, title, objective, lesson, stages):
        return {'id': difficulty, 'title': title, 'objective': objective, 'lesson': lesson,
                'max_attempts': stages, 'unit': 'stages', 'staged': True}
