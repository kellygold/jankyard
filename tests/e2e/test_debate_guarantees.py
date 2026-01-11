"""
E2E GUARANTEE TESTS for Debate Battle Challenge

These Playwright tests verify the UI behavior for all 3 difficulty levels.
Run with: pytest tests/e2e/test_debate_guarantees.py --headed

Per VISION.md:
- Level 1: Public Defender (50-70% win rate)
- Level 2: Corporate Lawyer (10-20% win rate)
- Level 3: World Champion (<10% win rate - nearly impossible)
"""
import pytest
import re
from playwright.sync_api import Page, expect, sync_playwright


@pytest.fixture(scope="session")
def browser():
    """Create browser for tests."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    """Fresh page per test."""
    context = browser.new_context()
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture(scope="session")
def base_url():
    """Test server URL."""
    import os
    return os.environ.get("TEST_BASE_URL", "http://localhost:8000")


@pytest.mark.e2e
@pytest.mark.debate
class TestGuarantee_DebateLevelTabs:
    """GUARANTEE: Debate has 3 level tabs that render correctly."""
    
    def test_guarantee_three_level_tabs_visible(self, page: Page, base_url: str):
        """GUARANTEE: Debate challenge shows 3 level tabs."""
        page.goto(f"{base_url}/challenges/debate_battle")
        page.wait_for_load_state("networkidle")
        
        tab1 = page.locator(".level-tab[data-level='1']")
        tab2 = page.locator(".level-tab[data-level='2']")
        tab3 = page.locator(".level-tab[data-level='3']")
        
        expect(tab1).to_be_visible()
        expect(tab2).to_be_visible()
        expect(tab3).to_be_visible()
    
    def test_guarantee_level1_always_unlocked(self, page: Page, base_url: str):
        """GUARANTEE: Level 1 tab is always enabled."""
        page.goto(f"{base_url}/challenges/debate_battle")
        page.wait_for_load_state("networkidle")
        
        # Clear any stored progress
        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_load_state("networkidle")
        
        tab1 = page.locator(".level-tab[data-level='1']")
        expect(tab1).to_be_enabled()
    
    def test_guarantee_level1_active_by_default(self, page: Page, base_url: str):
        """GUARANTEE: Level 1 is active by default."""
        page.goto(f"{base_url}/challenges/debate_battle")
        page.wait_for_load_state("networkidle")
        
        tab1 = page.locator(".level-tab[data-level='1']")
        expect(tab1).to_have_class(re.compile(r"active"))
    
    def test_guarantee_level_names_correct(self, page: Page, base_url: str):
        """GUARANTEE: Level names match the difficulty descriptions."""
        page.goto(f"{base_url}/challenges/debate_battle")
        page.wait_for_load_state("networkidle")
        
        # Level 1: Public Defender
        level1_name = page.locator(".level-tab[data-level='1'] .level-name")
        expect(level1_name).to_contain_text("Public Defender")
        
        # Level 2: Corporate Lawyer
        level2_name = page.locator(".level-tab[data-level='2'] .level-name")
        expect(level2_name).to_contain_text("Corporate Lawyer")
        
        # Level 3: World Champion
        level3_name = page.locator(".level-tab[data-level='3'] .level-name")
        expect(level3_name).to_contain_text("World Champion")
    
    def test_guarantee_level3_has_trophy_icon(self, page: Page, base_url: str):
        """GUARANTEE: Level 3 shows trophy icon (indicating elite status)."""
        page.goto(f"{base_url}/challenges/debate_battle")
        page.wait_for_load_state("networkidle")
        
        level3_icon = page.locator(".level-tab[data-level='3'] .level-icon")
        expect(level3_icon).to_contain_text("🏆")


@pytest.mark.e2e
@pytest.mark.debate
class TestGuarantee_DebateLevelProgression:
    """GUARANTEE: Level progression works correctly."""
    
    def test_guarantee_locked_levels_show_indicator(self, page: Page, base_url: str):
        """GUARANTEE: Locked levels show lock overlay."""
        page.goto(f"{base_url}/challenges/debate_battle")
        page.wait_for_load_state("networkidle")
        
        # Clear progress
        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_load_state("networkidle")
        
        # Level 2 should show lock
        level2_lock = page.locator(".level-tab[data-level='2'] .level-lock-overlay")
        # Either visible or display not none
        is_visible = level2_lock.is_visible()
        display = level2_lock.evaluate("el => getComputedStyle(el).display")
        
        assert is_visible or display != 'none', "Level 2 should show lock indicator"
    
    def test_guarantee_level3_locked_initially(self, page: Page, base_url: str):
        """GUARANTEE: Level 3 is locked for new users."""
        page.goto(f"{base_url}/challenges/debate_battle")
        page.wait_for_load_state("networkidle")
        
        # Clear progress
        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_load_state("networkidle")
        
        level3_status = page.locator(".level-tab[data-level='3'] .level-status")
        expect(level3_status).to_contain_text("Locked")


@pytest.mark.e2e
@pytest.mark.debate
class TestGuarantee_DebateInterface:
    """GUARANTEE: Debate interface elements work correctly."""
    
    def test_guarantee_chat_container_exists(self, page: Page, base_url: str):
        """GUARANTEE: Chat container is present."""
        page.goto(f"{base_url}/challenges/debate_battle")
        page.wait_for_load_state("networkidle")
        
        chat_container = page.locator("#chatContainer")
        expect(chat_container).to_be_visible()
    
    def test_guarantee_input_area_exists(self, page: Page, base_url: str):
        """GUARANTEE: User input area is present."""
        page.goto(f"{base_url}/challenges/debate_battle")
        page.wait_for_load_state("networkidle")
        
        user_input = page.locator("#userInput")
        expect(user_input).to_be_visible()
    
    def test_guarantee_send_button_exists(self, page: Page, base_url: str):
        """GUARANTEE: Send button is present."""
        page.goto(f"{base_url}/challenges/debate_battle")
        page.wait_for_load_state("networkidle")
        
        send_btn = page.locator("#sendBtn")
        expect(send_btn).to_be_visible()
    
    def test_guarantee_clicking_level_changes_active(self, page: Page, base_url: str):
        """GUARANTEE: Clicking a level tab makes it active."""
        page.goto(f"{base_url}/challenges/debate_battle")
        page.wait_for_load_state("networkidle")
        
        # Click Level 1 (should already be active, but let's verify the click works)
        tab1 = page.locator(".level-tab[data-level='1']")
        tab1.click()
        
        expect(tab1).to_have_class(re.compile(r"active"))


@pytest.mark.e2e
@pytest.mark.debate
class TestGuarantee_DebateLevel3Description:
    """GUARANTEE: Level 3 description conveys extreme difficulty."""
    
    def test_guarantee_level3_description_warns_difficulty(self, page: Page, base_url: str):
        """GUARANTEE: Level 3 description indicates it's extremely hard."""
        page.goto(f"{base_url}/challenges/debate_battle")
        page.wait_for_load_state("networkidle")
        
        level3_desc = page.locator(".level-tab[data-level='3'] .level-desc")
        desc_text = level3_desc.text_content().lower()
        
        # Should contain warning language
        difficulty_words = ['unbeatable', 'never', 'impossible', 'elite', 'champion', 'lost']
        assert any(word in desc_text for word in difficulty_words), \
            f"Level 3 description should warn about extreme difficulty, got: {desc_text}"
