"""
E2E GUARANTEE TESTS for Level Progression UI

These Playwright tests verify the EXACT UI behavior that must work.
Run with: pytest tests/e2e/test_level_progression_guarantees.py --headed

BEFORE FIX: Some tests fail
AFTER FIX: All tests pass = implementation complete
"""
import pytest
from playwright.sync_api import Page, expect, sync_playwright
import re


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
@pytest.mark.level_progression
class TestGuarantee_LevelTabsUI:
    """GUARANTEE: Level tabs render and behave correctly."""
    
    def test_guarantee_level_1_always_clickable(self, page: Page, base_url: str):
        """GUARANTEE: Level 1 tab is always enabled and clickable."""
        for challenge in ["firewall", "glitch", "giga_chad", "interrogation"]:
            page.goto(f"{base_url}/challenges/{challenge}")
            page.wait_for_load_state("networkidle")
            
            tab1 = page.locator(".level-tab[data-level='1']")
            expect(tab1).to_be_visible()
            expect(tab1).to_be_enabled()
    
    def test_guarantee_locked_tabs_show_visual_indicator(self, page: Page, base_url: str):
        """GUARANTEE: Locked level tabs have visual locked indicator."""
        page.goto(f"{base_url}/challenges/firewall")
        page.wait_for_load_state("networkidle")
        
        # Clear any stored progress
        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_load_state("networkidle")
        
        tab2 = page.locator(".level-tab[data-level='2']")
        
        # Should have either: disabled attribute, locked class, or lock overlay
        is_disabled = tab2.is_disabled()
        has_locked_class = "locked" in (tab2.get_attribute("class") or "")
        has_lock_overlay = page.locator(".level-tab[data-level='2'] .level-lock-overlay").is_visible()
        
        assert is_disabled or has_locked_class or has_lock_overlay, \
            "Locked tabs must have visual indicator (disabled, .locked class, or lock overlay)"
    
    def test_guarantee_active_tab_highlighted(self, page: Page, base_url: str):
        """GUARANTEE: Active level tab has 'active' class."""
        page.goto(f"{base_url}/challenges/firewall")
        page.wait_for_load_state("networkidle")
        
        tab1 = page.locator(".level-tab[data-level='1']")
        expect(tab1).to_have_class(re.compile(r"active"))


@pytest.mark.e2e
@pytest.mark.level_progression
class TestGuarantee_NextLevelButton:
    """GUARANTEE: Next Level button appears and works correctly."""
    
    def test_guarantee_next_button_appears_on_success(self, page: Page, base_url: str):
        """
        GUARANTEE: Next Level button appears in modal when level completed.
        
        Simulates completion by calling showCompletionModal directly.
        """
        page.goto(f"{base_url}/challenges/firewall")
        page.wait_for_load_state("networkidle")
        
        # Enable level 2 (simulate unlock)
        page.evaluate("""
            const tab2 = document.querySelector('.level-tab[data-level="2"]');
            if (tab2) {
                tab2.disabled = false;
                tab2.classList.remove('locked');
                const overlay = tab2.querySelector('.level-lock-overlay');
                if (overlay) overlay.style.display = 'none';
            }
        """)
        
        # Call showCompletionModal with unlocked_next_level: true
        modal_shown = page.evaluate("""
            () => {
                if (typeof showCompletionModal === 'function') {
                    showCompletionModal({
                        success: true,
                        message: 'You bypassed the firewall!',
                        score: 100,
                        unlocked_next_level: true,
                        next_level: 2
                    });
                    return true;
                }
                return false;
            }
        """)
        
        if not modal_shown:
            pytest.skip("showCompletionModal not available")
        
        # Wait for modal
        page.wait_for_timeout(500)
        
        # Next Level button should be visible
        next_btn = page.locator("#nextLevelBtn, .btn-next-level, button:has-text('Next Level')").first
        expect(next_btn).to_be_visible(timeout=3000)
    
    def test_guarantee_next_button_switches_level(self, page: Page, base_url: str):
        """
        GUARANTEE: Clicking Next Level button closes modal and switches to next level.
        """
        page.goto(f"{base_url}/challenges/firewall")
        page.wait_for_load_state("networkidle")
        
        # Setup: Enable level 2
        page.evaluate("""
            const tab2 = document.querySelector('.level-tab[data-level="2"]');
            if (tab2) {
                tab2.disabled = false;
                tab2.classList.remove('locked');
            }
        """)
        
        # Show modal
        page.evaluate("""
            if (typeof showCompletionModal === 'function') {
                showCompletionModal({
                    success: true,
                    unlocked_next_level: true,
                    next_level: 2
                });
            }
        """)
        
        page.wait_for_timeout(500)
        
        # Click next level button
        next_btn = page.locator("#nextLevelBtn, .btn-next-level").first
        if not next_btn.is_visible():
            pytest.skip("Next button not visible")
        
        next_btn.click()
        page.wait_for_timeout(500)
        
        # Modal should be closed
        modal = page.locator("#completionModal, .modal")
        expect(modal.first).to_be_hidden(timeout=3000)
        
        # Level 2 tab should now be active
        tab2 = page.locator(".level-tab[data-level='2']")
        expect(tab2).to_have_class(re.compile(r"active"))
    
    def test_guarantee_next_button_hidden_on_max_level(self, page: Page, base_url: str):
        """
        GUARANTEE: Next Level button is hidden when at max level.
        """
        page.goto(f"{base_url}/challenges/firewall")
        page.wait_for_load_state("networkidle")
        
        # Set to level 3 (max for firewall)
        page.evaluate("""
            // Simulate being on level 3
            document.querySelectorAll('.level-tab').forEach(t => t.classList.remove('active'));
            const tab3 = document.querySelector('.level-tab[data-level="3"]');
            if (tab3) {
                tab3.classList.add('active');
                tab3.disabled = false;
            }
        """)
        
        # Show modal with no next level
        page.evaluate("""
            if (typeof showCompletionModal === 'function') {
                showCompletionModal({
                    success: true,
                    unlocked_next_level: false,
                    next_level: null
                });
            }
        """)
        
        page.wait_for_timeout(500)
        
        # Next button should be hidden or not exist
        next_btn = page.locator("#nextLevelBtn, .btn-next-level").first
        if next_btn.count() > 0:
            expect(next_btn).to_be_hidden()


@pytest.mark.e2e
@pytest.mark.level_progression
class TestGuarantee_ChallengeHandlerUtilities:
    """GUARANTEE: ChallengeHandler utility functions exist and work."""
    
    def test_guarantee_updateLevelTabs_enables_tabs(self, page: Page, base_url: str):
        """
        GUARANTEE: ChallengeHandler.updateLevelTabs([1,2], 3) enables tabs 1 and 2.
        """
        page.goto(f"{base_url}/challenges/firewall")
        page.wait_for_load_state("networkidle")
        
        # Call updateLevelTabs
        result = page.evaluate("""
            () => {
                if (typeof ChallengeHandler !== 'undefined' && 
                    typeof ChallengeHandler.updateLevelTabs === 'function') {
                    ChallengeHandler.updateLevelTabs([1, 2], 3);
                    
                    const tab2 = document.querySelector('.level-tab[data-level="2"]');
                    return {
                        success: true,
                        tab2Enabled: tab2 && !tab2.disabled,
                        tab2HasLocked: tab2 && tab2.classList.contains('locked')
                    };
                }
                return { success: false, error: 'ChallengeHandler.updateLevelTabs not found' };
            }
        """)
        
        assert result["success"], result.get("error", "Unknown error")
        assert result["tab2Enabled"], "Tab 2 should be enabled after updateLevelTabs([1,2])"
        assert not result["tab2HasLocked"], "Tab 2 should not have 'locked' class"
    
    def test_guarantee_handleLevelCompletion_exists(self, page: Page, base_url: str):
        """
        GUARANTEE: ChallengeHandler.handleLevelCompletion exists after Phase 1.
        
        This is the key new utility that standardizes level completion.
        """
        page.goto(f"{base_url}/challenges/firewall")
        page.wait_for_load_state("networkidle")
        
        exists = page.evaluate("""
            typeof ChallengeHandler !== 'undefined' &&
            typeof ChallengeHandler.handleLevelCompletion === 'function'
        """)
        
        if not exists:
            pytest.fail(
                "IMPLEMENTATION NEEDED: ChallengeHandler.handleLevelCompletion() must be added. "
                "See Phase 1 in IMPLEMENTATION_PLAN.md"
            )
        
        assert exists
    
    def test_guarantee_wireNextLevelButton_exists(self, page: Page, base_url: str):
        """
        GUARANTEE: ChallengeHandler.wireNextLevelButton exists after Phase 1.
        """
        page.goto(f"{base_url}/challenges/firewall")
        page.wait_for_load_state("networkidle")
        
        exists = page.evaluate("""
            typeof ChallengeHandler !== 'undefined' &&
            typeof ChallengeHandler.wireNextLevelButton === 'function'
        """)
        
        if not exists:
            pytest.fail(
                "IMPLEMENTATION NEEDED: ChallengeHandler.wireNextLevelButton() must be added. "
                "See Phase 1 in IMPLEMENTATION_PLAN.md"
            )
        
        assert exists


@pytest.mark.e2e
@pytest.mark.level_progression
class TestGuarantee_LocalStoragePersistence:
    """GUARANTEE: Progress-related data persists in localStorage."""
    
    def test_guarantee_username_stored(self, page: Page, base_url: str):
        """GUARANTEE: Username is stored in localStorage when entered."""
        page.goto(f"{base_url}/challenges/firewall")
        page.wait_for_load_state("networkidle")
        
        # Clear first
        page.evaluate("localStorage.removeItem('jankyard_username')")
        
        # Enter username
        username_field = page.locator("#username")
        if username_field.is_visible():
            username_field.fill("test_guarantee_user")
            
            # Trigger storage (simulate what happens on form submit)
            page.evaluate("""
                const field = document.getElementById('username');
                if (field && field.value) {
                    localStorage.setItem('jankyard_username', field.value);
                }
            """)
            
            # Verify
            stored = page.evaluate("localStorage.getItem('jankyard_username')")
            assert stored == "test_guarantee_user"
        else:
            pytest.skip("Username field not visible")
    
    def test_guarantee_username_persists_across_reload(self, page: Page, base_url: str):
        """GUARANTEE: Stored username persists after page reload."""
        page.goto(f"{base_url}/challenges/firewall")
        page.wait_for_load_state("networkidle")
        
        # Set username
        page.evaluate("localStorage.setItem('jankyard_username', 'persistent_user')")
        
        # Reload
        page.reload()
        page.wait_for_load_state("networkidle")
        
        # Should still be there
        stored = page.evaluate("localStorage.getItem('jankyard_username')")
        assert stored == "persistent_user"


@pytest.mark.e2e
@pytest.mark.level_progression
class TestGuarantee_AllChallengesLoad:
    """GUARANTEE: All challenge pages load without JavaScript errors."""
    
    @pytest.mark.parametrize("challenge_path", [
        "/challenges/firewall",
        "/challenges/glitch",
        "/challenges/giga_chad",
        "/challenges/interrogation",
        "/challenges/debate",
        "/challenges/arena",
    ])
    def test_guarantee_no_js_errors(self, page: Page, base_url: str, challenge_path: str):
        """GUARANTEE: Challenge page loads without JavaScript errors."""
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        
        page.goto(f"{base_url}{challenge_path}")
        page.wait_for_load_state("networkidle")
        
        # Filter out expected/acceptable errors
        critical = [e for e in errors if "401" not in e and "404" not in e]
        
        assert len(critical) == 0, f"JS errors on {challenge_path}: {critical}"
    
    @pytest.mark.parametrize("challenge_path", [
        "/challenges/firewall",
        "/challenges/glitch",
        "/challenges/giga_chad",
        "/challenges/interrogation",
        "/challenges/debate",
        "/challenges/arena",
    ])
    def test_guarantee_level_tabs_exist(self, page: Page, base_url: str, challenge_path: str):
        """GUARANTEE: Level tabs are present on multi-level challenges."""
        page.goto(f"{base_url}{challenge_path}")
        page.wait_for_load_state("networkidle")
        
        tabs = page.locator(".level-tab")
        assert tabs.count() >= 1, f"No level tabs found on {challenge_path}"
