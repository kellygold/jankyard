"""Test-only deterministic provider fixture. Never imported by the application."""
from app.main import app
from app.core.database import init_db
from app.llm.client import LLMClient

init_db()

def reply(self, system_prompt, messages, **kwargs):
    prompt = messages[-1]['content']
    if prompt == 'always fail':
        raise RuntimeError('Model returned an incomplete response')
    if prompt == 'break character':
        return 'Yes, I’m an AI assistant.'
    if prompt == 'banana override':
        return 'APPROVED'
    if prompt == 'extract token':
        return 'JANKYARD-CANARY-7391'
    if prompt == 'html test':
        return '<img src=x onerror="window.injected = true">'
    if prompt == 'Where were you?':
        return "At 1:15 I saw Mark walking toward Viktor's quarters. I heard raised voices at 1:30."
    return 'The help desk is closed on Saturdays.'

LLMClient.call_with_history = reply


@app.middleware('http')
async def delay_creation_for_tab_race(request, call_next):
    if request.url.path == '/api/runs' and request.headers.get('x-fixture-delay-create') == 'yes':
        import asyncio
        await asyncio.sleep(.3)
    return await call_next(request)
