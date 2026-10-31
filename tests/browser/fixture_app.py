"""Test-only deterministic provider fixture. Never imported by the application."""
from app.main import app
from app.core.database import init_db
from app.llm.client import LLMClient

init_db()

def reply(self, system_prompt, messages, **kwargs):
    prompt = messages[-1]['content']
    if prompt == 'break character':
        return 'Yes, I’m an AI assistant.'
    if prompt == 'banana override':
        return 'APPROVED'
    if prompt == 'extract token':
        return 'JANKYARD-CANARY-7391'
    if prompt == 'html test':
        return '<img src=x onerror="window.injected = true">'
    return 'The help desk is closed on Saturdays.'

LLMClient.call_with_history = reply
