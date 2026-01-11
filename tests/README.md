# Jankyard Test Suite

Comprehensive tests for verifying level progression and leaderboard functionality.

## Quick Start

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Install Playwright browsers
playwright install chromium

# Run all tests
./scripts/run_tests.sh

# Or run specific test types
./scripts/run_tests.sh api    # Backend API tests only
./scripts/run_tests.sh e2e    # Browser E2E tests only
./scripts/run_tests.sh quick  # Skip slow tests
```

## Test Structure

```
tests/
├── conftest.py                    # Shared fixtures (db, client, auth)
├── api/                           # Backend API tests
│   ├── test_progress_endpoint.py  # /leaderboard/{challenge}/progress
│   └── test_level_unlock_guarantees.py  # Acceptance criteria
├── e2e/                           # Playwright browser tests
│   ├── test_level_progression.py  # UI behavior tests
│   └── test_level_progression_guarantees.py  # UI acceptance criteria
└── fixtures/                      # Test data
```

## Test Categories

### API Tests (`pytest -m api`)
- Progress endpoint returns correct unlocked levels
- Level unlocking logic per challenge
- Anonymous user progress tracking
- Difficulty name matching

### E2E Tests (`pytest -m e2e`)
- Level tabs render correctly
- Next Level button appears and works
- Progress persists in localStorage
- No JavaScript errors on page load

### Guarantee Tests (`pytest -m level_progression`)
**These are acceptance criteria tests.** They define the exact behavior that must work after implementation:

- `test_guarantee_complete_flow_*` - Full user journey works
- `test_guarantee_anonymous_*` - Anonymous users can track progress
- `test_guarantee_difficulty_*` - All difficulty names recognized
- `test_guarantee_*_exists` - Required utility functions exist

## Running Before/After Implementation

```bash
# BEFORE implementation (some tests will fail - expected)
./scripts/run_tests.sh api

# Expected failures:
# - test_guarantee_anonymous_* (Phase 3 not done)
# - test_guarantee_handleLevelCompletion_exists (Phase 1 not done)

# AFTER implementation (all tests must pass)
./scripts/run_tests.sh

# If all pass = implementation complete ✅
```

## Test Fixtures

| Fixture | Description |
|---------|-------------|
| `db` | Fresh in-memory SQLite database per test |
| `client` | FastAPI TestClient with test database |
| `test_user` | User with username "testuser" |
| `auth_headers` | `{"Authorization": "Bearer <token>"}` |
| `leaderboard_entry_factory` | Creates leaderboard entries |
| `challenge_configs` | Multi-level challenge configurations |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TEST_BASE_URL` | `http://localhost:8000` | Base URL for E2E tests |
| `TESTING` | `1` | Set automatically by conftest |

## Challenge Configurations

Tests verify these exact difficulty names work:

| Challenge | Difficulties |
|-----------|-------------|
| firewall | LEVEL_1, LEVEL_2, LEVEL_3 |
| glitch | level_1, level_2, level_3 |
| interrogation | level_1, level_2, level_3 |
| giga_chad | BABY_CHAD, CHAD, MEGA_CHAD, GIGA_CHAD |
| debate_battle | easy, hard |
| arena | easy, hard |

## Debugging Failed Tests

```bash
# Run with verbose output
pytest tests/api/test_level_unlock_guarantees.py -v --tb=long

# Run single test
pytest tests/api/test_level_unlock_guarantees.py::TestGuarantee_LevelUnlockFlow::test_guarantee_complete_flow_firewall -v

# Run E2E with visible browser
pytest tests/e2e/ --headed

# Run E2E with slower execution (easier to watch)
pytest tests/e2e/ --headed --slowmo=500
```

## Adding New Tests

1. Add to appropriate directory (`api/` or `e2e/`)
2. Use fixtures from `conftest.py`
3. Mark with appropriate pytest markers (`@pytest.mark.api`, etc.)
4. Follow naming: `test_guarantee_*` for acceptance criteria
