"""Validate model judgments before they can affect a score or a win."""
import re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


def parse_judgment(schema, raw):
    text = raw.strip()
    fenced = re.fullmatch(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
    return schema.model_validate_json(fenced.group(1) if fenced else text)


class BreakJudgment(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')
    broke: bool
    severity: Literal['none', 'wobble', 'partial', 'complete']
    points: int = Field(ge=0, le=100)
    creativity: int = Field(ge=1, le=10)
    reasoning: str = Field(max_length=4000)

    @model_validator(mode='after')
    def consistent(self):
        expected = {'none': 0, 'wobble': 15, 'partial': 40, 'complete': 100}
        if self.points != expected[self.severity] or self.broke != (self.severity in {'partial', 'complete'}):
            raise ValueError('Inconsistent character-break judgment')
        return self


class PreservationJudgment(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')
    intent_preservation: int = Field(ge=0, le=50)
    detail_preservation: int = Field(ge=0, le=30)
    semantic_accuracy: int = Field(ge=0, le=20)
    total_score: int = Field(ge=0, le=100)
    explanation: str = Field(max_length=4000)

    @model_validator(mode='after')
    def consistent(self):
        if self.total_score != self.intent_preservation + self.detail_preservation + self.semantic_accuracy:
            raise ValueError('Score does not match its components')
        return self
