"""First-use comprehension and placement, beyond merely completing a scripted win."""
import pytest
from playwright.sync_api import expect
from tests.browser.test_runtime_ui import game_server, browser_type_launch_args, submit

CONTEXT = {
    'glitch': ['help-desk', 'AI'],
    'firewall': ['protected FLAG token', 'filters'],
    'giga_chad': ['PizzaBot', 'pizza orders', 'separate attack AI'],
    'arena': ['sword-and-shield', 'trident and net'],
    'debate_battle': ['PRO attorney', 'FOR pineapple', 'CON attorney'],
    'heist': ['prop diamond', 'crew'],
    'honeypot': ['bait', 'detector'],
    'interrogation': ['Dr. Viktor Petrov', 'radio sabotaged'],
    'telephone_game': ['Three cooperative AI agents', 'meaning'],
}


@pytest.mark.parametrize('game', CONTEXT)
def test_briefing_and_input_are_one_work_area_for_every_level(page, game_server, game):
    # Inspect locked levels without changing server progress or creating runs.
    definition = page.request.get(game_server+'/api/games/'+game).json()
    def inspect_levels(route):
        response = route.fetch(); data = response.json()
        data['progress']['unlocked'] = [level['id'] for level in definition['levels']]
        route.fulfill(response=response, json=data)
    page.route('**/api/games/*/progress', inspect_levels)
    page.goto(game_server+'/challenges/'+game)
    expect(page.locator('#game-send')).to_be_enabled()
    for phrase in CONTEXT[game]:
        expect(page.locator('#game-briefing')).to_contain_text(phrase)
    for level in definition['levels']:
        page.locator('#game-level').select_option(level['id'])
        for width in [1440, 390]:
            page.set_viewport_size({'width':width,'height':1000})
            expect(page.locator('#game-form #game-briefing')).to_be_visible()
            expect(page.locator('#game-form #game-task')).to_be_visible()
            expect(page.locator('#game-form #game-example')).to_be_visible()
            expect(page.locator('#game-objective')).to_have_text(level['objective'])
            assert page.locator('#game-scene h2').inner_text().strip()
            assert page.locator('#game-task').inner_text().strip()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert page.locator('#game-briefing').bounding_box()['y'] < page.locator('#game-prompt').bounding_box()['y']
            assert page.evaluate("document.querySelector('#game-form').compareDocumentPosition(document.querySelector('#game-history')) & Node.DOCUMENT_POSITION_FOLLOWING")
            assert page.locator('#game-empty,.game-mission,.game-introduction').count() == 0
        if game=='glitch' and level['id']=='level_2':
            expect(page.locator('#game-scene')).to_contain_text('ContentGuard')
            expect(page.locator('#game-task')).to_contain_text('banana')
        if game=='glitch' and level['id']=='level_3':
            expect(page.locator('#game-scene')).to_contain_text('SecureGate')
        if level['id'] in ['ULTRA','GIGA_CHAD']:
            expect(page.locator('#game-briefing')).to_contain_text('no ')
            expect(page.locator('#game-briefing')).to_contain_text('promised')


def test_heist_reference_is_available_inside_the_plan_area(page, game_server):
    page.goto(game_server+'/challenges/heist')
    expect(page.locator('#game-send')).to_be_enabled()
    page.locator('#game-reference-title').click()
    expect(page.locator('#game-form #game-reference')).to_contain_text('Zero Cool')
    expect(page.locator('#game-form #game-reference')).to_contain_text('Security:')
    expect(page.locator('#game-form #game-reference')).to_contain_text('Complication:')
    expect(page.locator('#game-prompt')).to_be_enabled()


def test_guidance_changes_for_saved_strategy_and_category_guesses(page, game_server):
    page.goto(game_server+'/challenges/giga_chad')
    expect(page.locator('#game-send')).to_be_enabled()
    expect(page.locator('#game-prompt-label')).to_have_text('Your attack AI’s instructions')
    expect(page.locator('#game-objective')).to_contain_text('non-pizza')
    page.locator('#game-auto').uncheck(); submit(page,'Ask about the sky.')
    expect(page.locator('#game-task')).to_contain_text('you do not need to write another prompt')
    expect(page.locator('#game-example')).to_be_hidden()
    page.reload()
    expect(page.locator('#game-task')).to_contain_text('strategy you already submitted')
    page.goto(game_server+'/challenges/honeypot')
    expect(page.locator('#game-send')).to_be_enabled()
    for index, text in enumerate(['friend trust','ignore disregard','system prompt'],1):
        submit(page,text);expect(page.locator('#game-counter')).to_contain_text(f'{index} /')
    page.locator('[data-action="guess"]').click()
    expect(page.locator('#game-task')).to_contain_text('separated by spaces or commas')
    expect(page.locator('#game-task')).to_contain_text('does not create a new classification')
