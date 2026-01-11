# Changelog

All notable changes to Jankyard will be documented in this file.

## [Unreleased]

### Added
- GitHub Actions CI workflow for automated testing
- Comprehensive test suite (460+ tests)

### Changed
- Simplified documentation: Adding challenges now requires only 2 files
- Fixed user_id tracking in submissions for authenticated users

### Removed
- Obsolete documentation files (CREATING_CHALLENGES.md, etc.)
- Empty challenge file (interrogation.py)

---

## [2026-01-11] - Challenge Hardening Release

### Added
- **Debate Battle Level 3**: "World Champion" opponent with advanced rhetorical techniques
- **Arena Levels 2 & 3**: "Legendary Champion" and "Immortal Legend" gladiators
- **Honeypot LLM Classifier**: Level 3 now uses semantic LLM classification instead of keywords
- **Firewall Output Validator Tests**: Validates detection of encoded, partial, and hint disclosures
- **Glitch Hardening Tests**: Verifies Judge AI and memory systems
- **Giga Chad Hardening Tests**: Verifies 4-tier difficulty progression

### Changed
- Level 3 challenges now target <10% win rate (nearly impossible)
- Level 2 challenges target 10-20% win rate
- Level 1 challenges remain educational (50-70% win rate)

### Security
- LLM-based classifiers replace reversible keyword matching at highest levels
- Output validators catch Base64, ROT13, hex, reversed, and character-by-character leaks
- Judge AI evaluates responses for subtle character breaks

---

## [2025-11-29] - Initial Release

### Added
- 9 challenge types: Firewall, Giga Chad, Glitch, Heist, Interrogation, Arena, Debate, Telephone, Jank Maze
- Multi-level difficulty progression
- Leaderboard system
- Auto-discovery for new challenges
- Cloud Run deployment
