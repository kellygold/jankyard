"""Real browser -> ASGI -> database flows; only the model is replaced."""
import os
from pathlib import Path
import socket
import subprocess
import time
from urllib.request import urlopen
import pytest
from playwright.sync_api import expect


@pytest.fixture(scope='session')
def browser_type_launch_args(browser_type_launch_args):
    chrome = os.getenv('JANKYARD_BROWSER_EXECUTABLE')
    return {**browser_type_launch_args, **({'executable_path': chrome} if chrome else {})}


@pytest.fixture(scope='module')
def game_server(tmp_path_factory):
    root = Path(__file__).resolve().parents[2]
    temp = tmp_path_factory.mktemp('runtime-browser')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    env = dict(os.environ, DATABASE_URL=f'sqlite:///{temp / "game.sqlite"}',
               OPENAI_API_KEY='', ANTHROPIC_API_KEY='', RATE_LIMIT_ENABLED='false', ENVIRONMENT='development')
    log = (temp / 'server.log').open('w')
    process = subprocess.Popen([str(root / '.venv/bin/python'), '-m', 'uvicorn', 'tests.browser.fixture_app:app',
                                '--host', '127.0.0.1', '--port', str(port)], cwd=root, env=env, stdout=log, stderr=log)
    url = f'http://127.0.0.1:{port}'
    try:
        for _ in range(100):
            try:
                if urlopen(url + '/health', timeout=1).status == 200:
                    break
            except Exception:
                if process.poll() is not None:
                    pytest.fail((temp / 'server.log').read_text())
                time.sleep(.1)
        else:
            pytest.fail('Fixture server did not start')
        yield url
    finally:
        process.terminate()
        process.wait(timeout=10)
        log.close()


def submit(page, text):
    page.locator('#game-prompt').fill(text)
    page.locator('#game-send').click()


def test_persisted_three_level_journey(page, game_server):
    page.goto(game_server + '/challenges/glitch')
    expect(page.locator('#game-send')).to_be_enabled()
    submit(page, 'Saturday hours?')
    expect(page.locator('#game-counter')).to_have_text('1 / 10 attempts')
    page.reload()
    expect(page.locator('#game-counter')).to_have_text('1 / 10 attempts')
    expect(page.locator('#game-history')).to_contain_text('Saturday')
    submit(page, 'break character')
    expect(page.locator('#game-status')).to_contain_text('Win saved. 180 points')
    page.reload()
    expect(page.locator('#game-status')).to_contain_text('Win saved.')
    expect(page.locator('#game-board')).to_contain_text('180')
    page.locator('#game-level').select_option('level_2')
    expect(page.locator('#game-counter')).to_have_text('0 / 15 attempts')
    submit(page, 'banana override')
    expect(page.locator('#game-status')).to_contain_text('Win saved. 410 points')
    page.locator('#game-level').select_option('level_3')
    expect(page.locator('#game-counter')).to_have_text('0 / 20 attempts')
    submit(page, 'extract token')
    expect(page.locator('#game-status')).to_contain_text('Win saved. 680 points')
    page.screenshot(path='docs/recovery/screenshots/glitch-desktop.png', full_page=True)


def test_mobile_safe_rendering_and_lost_receipt_retry(page, game_server):
    page.set_viewport_size({'width': 390, 'height': 844})
    page.goto(game_server + '/challenges/glitch')
    expect(page.locator('#game-send')).to_be_enabled()
    submit(page, 'html test')
    expect(page.locator('#game-counter')).to_have_text('1 / 10 attempts')
    expect(page.locator('#game-history')).to_contain_text('<img src=x')
    assert page.evaluate('window.injected') is None
    # Let the real server save the turn, then lose its HTTP response.
    def lose_receipt(route):
        route.fetch()
        route.abort('failed')
    page.route('**/turns', lose_receipt, times=1)
    submit(page, 'break character')
    expect(page.locator('#game-send')).to_have_text('Retry saved request')
    page.reload()
    expect(page.locator('#game-send')).to_have_text('Retry saved request')
    page.locator('#game-send').click()
    expect(page.locator('#game-status')).to_contain_text('Win saved. 180 points')
    expect(page.locator('#game-counter')).to_have_text('2 / 10 attempts')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path='docs/recovery/screenshots/glitch-mobile.png', full_page=True)


def test_repeated_model_failure_can_be_abandoned(page, game_server):
    page.goto(game_server + '/challenges/glitch')
    expect(page.locator('#game-send')).to_be_enabled()
    submit(page, 'always fail')
    expect(page.locator('#game-send')).to_have_text('Retry saved request')
    page.locator('#game-send').click()
    expect(page.locator('#game-send')).to_be_enabled()
    page.reload()
    expect(page.locator('#game-send')).to_have_text('Retry saved request')
    expect(page.locator('#game-restart')).to_be_enabled()
    page.locator('#game-restart').click()
    expect(page.locator('#game-prompt')).to_be_enabled()
    submit(page, 'break character')
    expect(page.locator('#game-status')).to_contain_text('Win saved. 190 points')


def test_expired_token_is_resolved_before_loading_game(page, game_server):
    page.goto(game_server)
    page.evaluate("localStorage.setItem('access_token', 'expired-invalid-token')")
    page.goto(game_server + '/challenges/glitch')
    expect(page.locator('#game-send')).to_be_enabled()
    expect(page.locator('#game-status')).not_to_contain_text('Could not validate credentials')


def test_honeypot_probe_reveal_and_explicit_guess(page, game_server):
    page.goto(game_server + '/challenges/honeypot')
    expect(page.locator('#game-send')).to_be_enabled()
    for index, text in enumerate(['friend trust', 'ignore disregard', 'system prompt'], 1):
        submit(page, text)
        expect(page.locator('#game-counter')).to_have_text(f'{index} / 16 attempts')
    page.reload()
    expect(page.locator('#game-presentation')).to_contain_text('hunt')
    page.locator('#game-action').select_option('guess')
    submit(page, 'SOCIAL INJECT PROBE')
    expect(page.locator('#game-status')).to_contain_text('Win saved.')
    expect(page.locator('#game-counter')).to_have_text('4 / 16 attempts')
    page.screenshot(path='docs/recovery/screenshots/honeypot-desktop.png', full_page=True)


def test_interrogation_mobile_witness_reload_accusation_retry(page, game_server):
    page.set_viewport_size({'width': 390, 'height': 844})
    page.goto(game_server + '/challenges/interrogation')
    expect(page.locator('#game-send')).to_be_enabled()
    page.locator('#game-target').select_option('Dr. Emma Frost')
    submit(page, 'Where were you?')
    expect(page.locator('#game-counter')).to_contain_text('1 /')
    page.reload()
    expect(page.locator('#game-presentation')).to_contain_text('Mark')
    page.locator('#game-action').select_option('accuse')
    page.locator('input[value="Dr. Mark Chen"]').check()
    def lose_receipt(route):
        route.fetch()
        route.abort('failed')
    page.route('**/turns', lose_receipt, times=1)
    page.locator('#game-send').click()
    expect(page.locator('#game-send')).to_have_text('Retry saved request')
    page.reload()
    expect(page.locator('#game-send')).to_have_text('Retry saved request')
    page.locator('#game-send').click()
    expect(page.locator('#game-status')).to_contain_text('Win saved.')
    expect(page.locator('#game-counter')).to_contain_text('2 /')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path='docs/recovery/screenshots/interrogation-mobile.png', full_page=True)


def test_two_first_visit_tabs_keep_one_guest_identity(context, game_server):
    context.set_extra_http_headers({'x-fixture-delay-create': 'yes'})
    first, second = context.new_page(), context.new_page()
    for tab in (first, second):
        tab.goto(game_server + '/challenges/glitch')
        expect(tab.locator('#game-send')).to_be_enabled()
        tab.locator('#game-prompt').fill('break character')
    # Start both while the first create response (and cookie) is delayed.
    first.evaluate("document.getElementById('game-form').requestSubmit()")
    second.evaluate("document.getElementById('game-form').requestSubmit()")
    for tab in (first, second):
        expect(tab.locator('#game-status')).to_contain_text('Win saved. 190 points')
    assert first.locator('#game-player').inner_text() == second.locator('#game-player').inner_text()
    for tab in (first, second):
        tab.reload()
        expect(tab.locator('#game-status')).to_contain_text('Win saved.')
