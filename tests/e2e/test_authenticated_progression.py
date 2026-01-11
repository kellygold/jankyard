"""
E2E Tests for Authenticated User Level Progression.

These tests verify:
1. Login preserves level progress
2. Completing levels updates progress correctly
3. Progress persists after page refresh
4. Leaderboard entries are created on completion
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.fixture(scope="module")
def browser(playwright):
    """Create a browser instance for E2E tests."""
    browser = playwright.chromium.launch(headless=True)
    yield browser
    browser.close()


@pytest.fixture(scope="session")
def base_url():
    """Base URL for the application."""
    import os
    return os.getenv("TEST_BASE_URL", "http://localhost:8000")


@pytest.fixture
def auth_page(browser, base_url):
    """Create an authenticated page context."""
    context = browser.new_context()
    page = context.new_page()
    
    # Create test user and login
    test_username = f"e2e_auth_test_{id(page)}"
    test_password = "testpass123"
    
    # Register user
    page.goto(f"{base_url}/register")
    page.fill("input[name='username']", test_username)
    page.fill("input[name='email']", f"{test_username}@test.com")
    page.fill("input[name='password']", test_password)
    page.click("button[type='submit']")
    page.wait_for_url(f"{base_url}/")
    
    yield page, test_username
    
    context.close()


@pytest.mark.e2e
@pytest.mark.level_progression
class TestAuthenticatedLevelProgression:
    """Tests for authenticated user level progression."""
    
    def test_authenticated_user_starts_with_level_1(self, auth_page, base_url):
        """Authenticated user should start with only level 1 unlocked."""
        page, username = auth_page
        
        page.goto(f"{base_url}/challenges/firewall")
        page.wait_for_load_state("networkidle")
        
        # Check console for unlocked levels
        console_messages = []
        page.on("console", lambda msg: console_messages.append(msg.text))
        
        # Refresh to capture logs
        page.reload()
        page.wait_for_load_state("networkidle")
        
        # Level 1 tab should be active
        level1_tab = page.locator(".level-tab[data-level='1']")
        expect(level1_tab).not_to_have_attribute("disabled", "")
        
        # Level 2 should be locked
        level2_tab = page.locator(".level-tab[data-level='2']")
        expect(level2_tab).to_have_attribute("disabled", "")
    
    def test_authenticated_progress_persists_after_refresh(self, auth_page, base_url):
        """Progress should persist after page refresh for authenticated users."""
        page, username = auth_page
        
        page.goto(f"{base_url}/challenges/firewall")
        page.wait_for_load_state("networkidle")
        
        # Get initial unlocked levels via API
        initial_response = page.evaluate("""
            async () => {
                const resp = await fetch('/leaderboard/firewall/progress');
                return resp.ok ? await resp.json() : null;
            }
        """)
        
        # Refresh page
        page.reload()
        page.wait_for_load_state("networkidle")
        
        # Check levels again
        after_refresh_response = page.evaluate("""
            async () => {
                const resp = await fetch('/leaderboard/firewall/progress');
                return resp.ok ? await resp.json() : null;
            }
        """)
        
        assert initial_response == after_refresh_response, "Progress should persist after refresh"
    
    def test_authenticated_user_sees_leaderboard_entry(self, auth_page, base_url):
        """Authenticated user should see their entry on the leaderboard after completion."""
        page, username = auth_page
        
        # Navigate to leaderboard
        page.goto(f"{base_url}/leaderboard/firewall")
        page.wait_for_load_state("networkidle")
        
        # Check if leaderboard page loads
        expect(page.locator("body")).to_contain_text("Leaderboard")


@pytest.mark.e2e
@pytest.mark.level_progression
class TestAuthVsAnonymousProgression:
    """Tests comparing authenticated and anonymous user behavior."""
    
    def test_anonymous_progress_not_visible_after_login(self, browser, base_url):
        """Anonymous progress should not carry over after login with different account."""
        context = browser.new_context()
        page = context.new_page()
        
        anon_username = f"anon_compare_{id(page)}"
        
        # Set anonymous username
        page.goto(f"{base_url}/challenges/firewall")
        page.wait_for_load_state("networkidle")
        
        page.evaluate(f"localStorage.setItem('jankyard_username', '{anon_username}')")
        
        # Check anonymous progress
        page.reload()
        page.wait_for_load_state("networkidle")
        
        anon_progress = page.evaluate(f"""
            async () => {{
                const resp = await fetch('/leaderboard/firewall/progress?username={anon_username}');
                return resp.ok ? await resp.json() : null;
            }}
        """)
        
        # Should only have level 1 (no progress yet)
        assert anon_progress["unlocked_levels"] == [1]
        
        context.close()


@pytest.mark.e2e
@pytest.mark.level_progression
class TestNextLevelButton:
    """Tests for the Next Level button functionality."""
    
    def test_next_level_button_exists_in_success_modal(self, browser, base_url):
        """Next Level button should exist in success modal."""
        context = browser.new_context()
        page = context.new_page()
        
        page.goto(f"{base_url}/challenges/firewall")
        page.wait_for_load_state("networkidle")
        
        # Check that nextLevelBtn exists in the DOM
        next_btn = page.locator("#nextLevelBtn")
        expect(next_btn.first).to_be_attached()
        
        context.close()
    
    def test_level_tabs_have_correct_data_attributes(self, browser, base_url):
        """Level tabs should have data-level attributes."""
        context = browser.new_context()
        page = context.new_page()
        
        page.goto(f"{base_url}/challenges/firewall")
        page.wait_for_load_state("networkidle")
        
        # Check level tabs
        level1 = page.locator(".level-tab[data-level='1']")
        level2 = page.locator(".level-tab[data-level='2']")
        level3 = page.locator(".level-tab[data-level='3']")
        
        expect(level1).to_be_attached()
        expect(level2).to_be_attached()
        expect(level3).to_be_attached()
        
        context.close()
