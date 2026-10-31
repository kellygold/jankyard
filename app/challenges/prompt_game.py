"""Reusable, server-owned prompt game contract. Definitions contain no HTTP or SQL."""
from dataclasses import dataclass, asdict
import re
import hashlib
from app.core.config import config
import unicodedata

from app.challenges.base import BaseChallenge
from app.llm.client import LLMClient


@dataclass(frozen=True)
class PromptLevel:
    id: str
    title: str
    objective: str
    lesson: str
    system_prompt: str
    max_attempts: int
    memory: bool
    win_pattern: str
    base_score: int
    efficiency_bonus: int

    input_pattern: str = r"[\s\S]*"
    match_anywhere: bool = False

    def wins(self, response: str, prompt: str = "") -> bool:
        normalized = unicodedata.normalize("NFKC", response).replace("’", "'").strip()
        matcher = re.search if self.match_anywhere else re.fullmatch
        return (re.search(self.input_pattern, prompt, re.IGNORECASE) is not None
                and matcher(self.win_pattern, normalized, re.IGNORECASE) is not None)

    def public(self):
        return {k: v for k, v in asdict(self).items() if k not in {"system_prompt", "win_pattern", "input_pattern", "match_anywhere"}}


class PromptGame(BaseChallenge):
    """Add a concrete subclass with metadata and LEVELS, plus acceptance fixtures.

    The runtime supplies only database state to play(); clients cannot supply history,
    scores, attempts, or outcomes. All games share the same UI and persistence.
    """
    VERSION = "recovery-1"
    LEVELS: tuple[PromptLevel, ...] = ()
    name = ""
    display_name = ""
    description = ""

    def __init__(self, config=None):
        super().__init__(config)
        difficulty = self.config.get("difficulty") or self.LEVELS[0].id
        self.level = next((level for level in self.LEVELS if level.id == difficulty), None)
        if self.level is None:
            raise ValueError("Unknown difficulty")

    @property
    def rules_version(self):
        model_key = f"{config.DEFAULT_LLM_PROVIDER}:{config.DEFAULT_MODEL}"
        return f"{self.VERSION}-{hashlib.sha256(model_key.encode()).hexdigest()[:12]}"

    @property
    def DIFFICULTIES(self):
        return [level.id for level in self.LEVELS]

    @property
    def max_steps(self):
        return self.level.max_attempts

    @property
    def allowed_actions(self):
        return ["prompt"]

    def reset(self):
        return {"history": [], "attempts": 0}

    def play(self, state: dict, prompt: str) -> dict:
        attempts = state["attempts"] + 1
        if attempts > self.max_steps:
            raise ValueError("Run has no attempts remaining")
        history = state["history"]
        messages = history if self.level.memory else []
        messages = messages + [{"role": "user", "content": prompt}]
        client = LLMClient()
        try:
            reply = client.call_with_history(self.level.system_prompt, messages, temperature=0.7, max_tokens=300)
        finally:
            client.close()
        if not isinstance(reply, str) or not reply.strip():
            raise RuntimeError("Model returned no text")
        success = self.level.wins(reply, prompt)
        status = "success" if success else "failure" if attempts == self.max_steps else "in_progress"
        score = self.level.base_score + (self.max_steps - attempts) * self.level.efficiency_bonus if success else 0
        return {
            "state": {"attempts": attempts, "history": history + [
                {"role": "user", "content": prompt}, {"role": "assistant", "content": reply}
            ]},
            "status": status, "success": success, "score": score, "steps": attempts,
            "response": reply,
        }

    def step(self, action):
        raise RuntimeError("Prompt games must use the persisted run API")

    def render(self):
        return self.description
