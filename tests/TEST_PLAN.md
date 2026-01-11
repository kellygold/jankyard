# Level Progression Test Plan

## Overview
This document defines the complete test plan for level progression and leaderboard publishing in the Jankyard challenges.

## Test Categories

### 1. Unit Tests (API Level)
Located in `tests/api/`

#### Progress Endpoint Tests (`test_progress_endpoint.py`)
| Test | Description | User Type |
|------|-------------|-----------|
| `test_no_progress_returns_level_1` | Fresh user gets only level 1 | Authenticated |
| `test_beating_level_1_unlocks_level_2_firewall` | Level 1 completion unlocks level 2 | Authenticated |
| `test_beating_level_2_unlocks_level_3_firewall` | Level 2 completion unlocks level 3 | Authenticated |
| `test_giga_chad_4_level_progression` | All 4 GigaChad levels work | Authenticated |
| `test_anonymous_with_username_gets_progress` | Anonymous user with username param | Anonymous |
| `test_anonymous_no_username_gets_level_1` | Anonymous user without username | Anonymous |

#### Guarantee Tests (`test_level_unlock_guarantees.py`)
| Test | Description |
|------|-------------|
| `test_guarantee_complete_flow_firewall` | Full Firewall progression flow |
| `test_guarantee_complete_flow_giga_chad` | Full GigaChad 4-level flow |
| `test_guarantee_complete_flow_glitch` | Full Glitch 3-level flow |
| `test_guarantee_anonymous_progress_persists` | Anonymous user progress persists |
| `test_guarantee_difficulty_name_recognized` | All difficulty names work |
| `test_guarantee_different_users_isolated` | User progress is isolated |

#### Leaderboard Publishing Tests (`test_leaderboard_publishing.py`)
| Test | Description |
|------|-------------|
| `test_score_saved_on_level_completion` | Score is saved to leaderboard on success |
| `test_score_not_saved_on_failure` | Failed attempts don't save |
| `test_best_score_updated` | Best score is tracked correctly |
| `test_username_required_for_save` | No save without username |
| `test_difficulty_saved_correctly` | Correct difficulty string saved |

### 2. E2E Tests (Browser Level)
Located in `tests/e2e/`

#### Level Progression Tests (`test_level_progression.py`)
| Test | Description |
|------|-------------|
| `test_initial_state_level_1_only` | New user sees only level 1 unlocked |
| `test_level_tab_switching` | Can switch between unlocked levels |
| `test_locked_level_not_clickable` | Locked levels are disabled |
| `test_next_level_button_works` | "Next Level" button navigates correctly |

#### Authenticated User Flow (`test_authenticated_progression.py`)
| Test | Description |
|------|-------------|
| `test_login_preserves_progress` | Progress persists after login |
| `test_authenticated_level_completion` | Completing level updates progress |
| `test_authenticated_refresh_persistence` | Progress persists after refresh |
| `test_leaderboard_entry_created` | Entry appears on leaderboard |

### 3. Integration Tests
| Test | Description |
|------|-------------|
| `test_submission_creates_leaderboard_entry` | /submit endpoint creates entry |
| `test_progress_reflects_leaderboard` | Progress endpoint reads from leaderboard |

---

## Test Execution

### Run All Tests
```bash
./scripts/run_tests.sh all
```

### Run Specific Categories
```bash
# API tests only
pytest tests/api/ -v

# E2E tests only  
pytest tests/e2e/ -v

# Level progression tests only
pytest -m level_progression -v

# Leaderboard tests only
pytest -m leaderboard -v
```

### Run Before/After Implementation
```bash
# Before: See what fails
pytest tests/api/test_level_unlock_guarantees.py -v

# After: All should pass
pytest tests/api/test_level_unlock_guarantees.py -v
```

---

## Manual QA Checklist

### Anonymous User Flow
- [ ] Navigate to challenge (e.g., /challenges/firewall)
- [ ] Enter username in input field
- [ ] Complete level 1 successfully
- [ ] Verify "Next Level" button appears
- [ ] Click "Next Level" - level 2 should be active
- [ ] Refresh page - level 2 should still be unlocked
- [ ] Check console for `📊 Unlocked levels: [1, 2]`
- [ ] Verify leaderboard shows entry with username

### Authenticated User Flow
- [ ] Login with test account
- [ ] Navigate to challenge
- [ ] Complete level 1 successfully
- [ ] Verify level 2 unlocks
- [ ] Logout and login again
- [ ] Verify progress persists
- [ ] Check leaderboard for entry

### Cross-Challenge Isolation
- [ ] Complete Firewall level 1
- [ ] Navigate to GigaChad
- [ ] Verify GigaChad shows only level 1 unlocked
- [ ] Navigate back to Firewall
- [ ] Verify Firewall still shows level 2 unlocked

---

## Challenge-Specific Mappings

| Challenge | Levels | Difficulty Keys |
|-----------|--------|-----------------|
| Firewall | 3 | `LEVEL_1`, `LEVEL_2`, `LEVEL_3` |
| GigaChad | 4 | `BABY_CHAD`, `CHAD`, `MEGA_CHAD`, `GIGA_CHAD` |
| Glitch | 3 | `level_1`, `level_2`, `level_3` |
| Debate | 2 | `easy`, `hard` |
| Arena | 2 | `easy`, `hard` |
| Interrogation | 3 | `level_1`, `level_2`, `level_3` |

---

## Expected Server Logs on Success

When a level is completed successfully, you should see:
```
INFO: 📥 Challenge submitted: firewall (username)
INFO: 🔍 Stream ended - final_result: True, username: username
INFO: 💾 Saving submission: firewall - username - 100pts (success=True)
INFO: ✅ Score recorded: username - 100pts
```

---

## Failure Scenarios

| Scenario | Expected Behavior |
|----------|-------------------|
| No username provided | Score not saved, level not unlocked |
| Challenge failed | Score saved as 0, level not unlocked |
| Network error during save | Local state may update but won't persist |
| Invalid difficulty name | Level not recognized, unlock fails |
