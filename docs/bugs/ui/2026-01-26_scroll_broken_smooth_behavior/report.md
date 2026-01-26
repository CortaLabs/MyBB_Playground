# Page scrolling broken due to scroll-behavior: smooth on html element

**Author:** MyBBBugHunter
**Version:** v1.0
**Status:** FIXED
**Last Updated:** 2026-01-26 07:30 UTC

> Documents the critical scrolling bug in the Flavor theme and its resolution.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** scroll_broken_smooth_behavior

**Reported By:** User (via Orchestrator)

**Date Reported:** 2026-01-26

**Severity:** CRITICAL

**Status:** FIXED

**Component:** flavor-theme/base.css (line 43)

**Environment:** Local development (http://localhost:8022)

**Customer Impact:** Forum completely unusable - users cannot scroll the page

---
## Description
<!-- ID: description -->
### Summary
The Flavor theme had a critical bug where page scrolling would become completely non-functional. Users could not scroll the page using mouse wheel, scrollbar, keyboard, or programmatic JavaScript methods.

### Expected Behaviour
- `window.scrollTo(0, 300)` should scroll the page to position 300
- Mouse wheel and keyboard scrolling should work normally
- Page should scroll smoothly between any valid scroll positions

### Actual Behaviour
- `window.scrollTo()` calls were ignored or returned incorrect positions
- Page would get "stuck" at a random scroll position
- Consecutive scroll commands would fail silently
- Example: scrollTo(0, 300) would leave scrollY at 595 (or whatever it was stuck at)

### Steps to Reproduce
1. Navigate to http://localhost:8022 with the Flavor theme active
2. Open browser DevTools console
3. Run: `window.scrollTo(0, 0); console.log(window.scrollY);`
4. Run: `window.scrollTo(0, 300); console.log(window.scrollY);`
5. Observe scrollY does not change to 300

---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**
The CSS property `scroll-behavior: smooth` was set on the `html` element in base.css line 43. When smooth scrolling is enabled globally, rapid or programmatic scroll commands can interfere with each other because:

1. Smooth scroll starts an animation to the target position
2. Before the animation completes, another scroll command is issued
3. The browser's scroll state becomes inconsistent
4. The scroll position gets "stuck" at an intermediate value

This is a known issue with `scroll-behavior: smooth` on the root element when combined with JavaScript scroll manipulation or rapid user interactions.

**Affected Areas:**
- `/home/austin/projects/MyBB_Playground/plugin_manager/themes/public/flavor/stylesheets/base.css` (line 43)

**Related Issues:**
- Previous bug report at `docs/bugs/ui/2026-01-26_scroll_broken_svg_texture/report.md` (misdiagnosed)
- The previous bug hunter incorrectly identified the issue as SVG texture related

---
## Resolution
<!-- ID: resolution_plan -->
### Fix Applied
Removed `scroll-behavior: smooth` from the html element in base.css:

**Before:**
```css
html {
  font-size: 100%;
  -webkit-text-size-adjust: 100%;
  scroll-behavior: smooth;
  -moz-text-size-adjust: 100%;
}
```

**After:**
```css
html {
  font-size: 100%;
  -webkit-text-size-adjust: 100%;
  /* Note: scroll-behavior: smooth removed - it causes scroll to get stuck
     when rapid scroll commands are issued (e.g., by scripts or during
     smooth scroll animation). Use targeted smooth scroll on anchor links
     if needed, not globally on html. */
  -moz-text-size-adjust: 100%;
}
```

### Testing Performed
All 6 programmatic scroll tests passed after the fix:
1. `scrollTo(0, 0)` - scrollY = 0 (PASS)
2. `scrollTo(0, 300)` - scrollY = 300 (PASS)
3. `scrollTo(0, 500)` - scrollY = 500 (PASS)
4. `scrollTo(0, 0)` - scrollY = 0 (PASS)
5. `scrollTo(0, maxScroll=595)` - scrollY = 595 (PASS)
6. `scrollTo(0, 200)` - scrollY = 200 (PASS)

### Deployment
- Changes synced to database via `mybb_workspace_sync(codename="flavor", type="theme")`
- 1 stylesheet updated (base.css)
- Verified on page reload with cache bypass

---
## Timeline & Ownership
<!-- ID: timeline -->
| Phase | Owner | Date | Notes |
| --- | --- | --- | --- |
| Investigation | MyBBBugHunter | 2026-01-26 07:27 UTC | Confirmed scroll broken, diagnosed root cause |
| Fix Development | MyBBBugHunter | 2026-01-26 07:29 UTC | Removed scroll-behavior: smooth |
| Testing | MyBBBugHunter | 2026-01-26 07:30 UTC | All 6 scroll tests pass |
| Deployment | MyBBBugHunter | 2026-01-26 07:30 UTC | Synced to database |

---
## Appendix
<!-- ID: appendix -->
- **Logs & Evidence:** Screenshots taken at scrollY=0, scrollY=200, scrollY=595 confirm scrolling works
- **Fix Location:** `/home/austin/projects/MyBB_Playground/plugin_manager/themes/public/flavor/stylesheets/base.css` line 43
- **Recommendation:** If smooth scrolling is desired for anchor links, apply it selectively via `scroll-behavior: smooth` on specific elements or use JavaScript-based smooth scrolling with proper debouncing

---