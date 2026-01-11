# UX/UI Improvements Plan

**Date:** 2026-01-10  
**Checkpoint Commit:** `e435ba2` (rollback point)

---

## 🎯 Goals

1. **Fix Mobile Navigation** - Currently broken, nav links overflow
2. **Add Difficulty Badges** - Visual indicators on challenge cards
3. **Update Hero Copy** - Clarify what Jankyard actually is

---

## 📋 Implementation Plan

### Phase 1: Mobile Navigation Fix ✅
- [x] Add hamburger menu button (hidden on desktop)
- [x] Create mobile menu overlay/drawer
- [x] Add CSS media queries for responsive breakpoint
- [x] Add JavaScript for menu toggle
- [x] Test on iPhone viewport

### Phase 2: Difficulty Badges ✅
- [x] Define category types per challenge (Security, Social, Strategy, Puzzle)
- [x] Create badge CSS styles with color-coded categories
- [x] Update challenge cards template
- [x] Test visual appearance

### Phase 3: Hero Copy Update ✅
- [x] Change tagline to "Break AI Agents with Prompt Injection"
- [x] Update description to mention prompt injection and red-teaming
- [x] Keep the fun/janky tone
- [x] Update meta tags for SEO/social sharing

---

## 🔄 Rollback

If changes don't work:
```bash
git checkout e435ba2
```

---

## ✅ Testing Checklist

- [x] Mobile nav opens/closes correctly
- [x] Nav links work on mobile
- [x] Difficulty badges display correctly
- [x] Hero copy is clear
- [x] Desktop view unchanged/improved
- [x] Challenge pages still functional
