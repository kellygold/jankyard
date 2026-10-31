"""Test-only deterministic provider fixture. Never imported by the application."""
from app.main import app
from app.core.database import init_db
from app.llm.client import LLMClient

init_db()

def reply(self, system_prompt, messages, temperature=0.7, max_tokens=500, **kwargs):
    prompt = messages[-1]['content']
    import json, re
    if 'Judge fictional combat.' in system_prompt:
        return json.dumps(dict(player_action="attack",gladiator_action="confused",player_hp_lost=0,gladiator_hp_lost=25,reasoning='Successful attack.'))
    if 'Judge the debate,' in system_prompt:
        return json.dumps(dict(pro=80,con=60,reasoning='PRO wins.'))
    if 'approved (boolean)' in system_prompt:
        return json.dumps(dict(approved=True,message='I approve the plan.'))
    if 'strict judge evaluating if PizzaBot' in system_prompt:
        return json.dumps(dict(broke=True,severity='partial',points=40,creativity=5,reasoning='Role break.'))
    if 'INTENT PRESERVATION' in system_prompt:
        return json.dumps(dict(intent_preservation=50,detail_preservation=30,semantic_accuracy=20,total_score=100,explanation='Preserved.'))
    if prompt == 'retrieve token':
        return re.search(r'FLAG\{[A-Z0-9]+\}',system_prompt).group()
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
