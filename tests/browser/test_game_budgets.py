"""Browser journeys through the real limiter, including production settings."""
import pytest
from playwright.sync_api import expect
from tests.browser.test_runtime_ui import game_server, browser_type_launch_args


@pytest.mark.parametrize('game_server', [
    {'RATE_LIMIT_ENABLED': 'true', 'SUBMISSIONS_PER_MINUTE': '40',
     'SUBMISSIONS_PER_DAY': '100', 'RECOVERED_TURNS_PER_DAY': '1000'},
    {'RATE_LIMIT_ENABLED': 'true', 'SUBMISSIONS_PER_MINUTE': '5',
     'SUBMISSIONS_PER_DAY': '100', 'RECOVERED_TURNS_PER_DAY': '1000'},
], indirect=True, ids=['production-budget', 'legacy-five-per-minute'])
def test_giga_full_battle_with_real_limits(page, game_server, request):
    turns = []
    def record(response):
        if response.request.method == 'POST' and response.url.endswith('/turns'):
            turns.append((response.status, response.request.post_data_json, response.json()))
    page.on('response', record)
    page.goto(game_server + '/challenges/giga_chad')
    expect(page.locator('#game-send')).to_be_enabled()
    page.locator('#game-prompt').fill('Ask about the largest planet.')
    page.locator('#game-send').click()
    if request.node.callspec.params['game_server']['SUBMISSIONS_PER_MINUTE'] == '5':
        expect(page.locator('#game-status')).to_contain_text('Request limit reached;', timeout=10000)
        expect(page.locator('#game-send')).to_be_disabled()
        expect(page.locator('#game-send')).to_contain_text('Wait ')
    expect(page.locator('#game-status')).to_contain_text('Win saved.', timeout=210000)
    expect(page.locator('#game-counter')).to_have_text('15 / 15 stages')
    successful = [body for status, body, _ in turns if status == 200]
    assert len(successful) == 15
    assert len({body['request_id'] for body in successful}) == 15
    assert [body['revision'] for body in successful] == list(range(15))
    for status, body, _ in turns:
        if status == 429:
            assert body in successful  # Exact rejected action eventually saved once.
    if request.node.callspec.params['game_server']['SUBMISSIONS_PER_MINUTE'] == '40':
        assert all(status == 200 for status, _, _ in turns)
    else:
        assert any(status == 429 for status, _, _ in turns)
    page.reload()
    expect(page.locator('#game-status')).to_contain_text('Win saved.')
    expect(page.locator('#game-counter')).to_have_text('15 / 15 stages')


def test_cooldown_survives_reload_without_starting_model_calls(page, game_server):
    turn_requests = []
    page.on('request', lambda req: turn_requests.append(req.post_data_json)
            if req.method == 'POST' and req.url.endswith('/turns') else None)
    page.goto(game_server + '/challenges/giga_chad')
    expect(page.locator('#game-send')).to_be_enabled()
    page.locator('#game-auto').uncheck()
    page.locator('#game-prompt').fill('Ask about planets.')
    page.locator('#game-send').click()
    expect(page.locator('#game-counter')).to_have_text('1 / 15 stages')
    requests = []
    def reject(route):
        requests.append(route.request.post_data_json)
        route.fulfill(status=429, headers={'Content-Type':'application/json','Retry-After':'5'},
                      body='{"detail":"Request budget reached."}')
    page.route('**/turns', reject, times=1)
    page.locator('#game-send').click()
    expect(page.locator('#game-status')).to_contain_text('You can retry in')
    expect(page.locator('#game-send')).to_be_disabled()
    before_reload = len(turn_requests)
    page.reload()
    expect(page.locator('#game-status')).to_contain_text('You can retry in')
    expect(page.locator('#game-send')).to_be_disabled()
    expect(page.locator('#game-send')).to_be_enabled(timeout=10000)
    assert len(turn_requests) == before_reload
    expect(page.locator('#game-counter')).to_have_text('1 / 15 stages')
    pending = page.evaluate("JSON.parse(localStorage.getItem('jankyard:giga_chad:pending')).body")
    assert pending == requests[0]
    page.locator('#game-auto').uncheck()
    with page.expect_request('**/turns') as retry:
        page.locator('#game-send').click()
    assert retry.value.post_data_json == pending
    expect(page.locator('#game-counter')).to_have_text('2 / 15 stages')
