
# Bug Report: Scrolling broken after SVG feTurbulence texture overlay implementation

**Bug ID:** 2026-01-26_scroll_broken_svg_texture
**Project:** flavor-theme
**Author:** MyBBBugHunter
**Status:** FIXED
**Severity:** HIGH
**Component:** Flavor Theme CSS
**Date Reported:** 2026-01-26
**Date Fixed:** 2026-01-26
**Last Updated:** 2026-01-26 07:25 UTC

---

## Bug Overview

### Summary
User reported that scrolling was completely broken on the Flavor theme after attempts to add an SVG paper texture overlay using feTurbulence filters. The page could not be scrolled at all.

### Expected Behaviour
Page should scroll normally while displaying a subtle paper grain texture overlay for visual enhancement.

### Actual Behaviour at Time of Investigation
At time of investigation, scrolling was actually WORKING. No SVG feTurbulence elements were present in deployed code. The bug may have been self-resolved by previous cleanup work, or the problematic code was never fully deployed.

### Environment
- **URL:** http://localhost:8022
- **Theme:** Flavor (tid: 57)
- **Template Set:** Flavor Templates (sid: 13)

---

## Investigation

### Diagnosis Steps Performed

1. **CSS Inspection:** Reviewed workspace files:
   - `plugin_manager/themes/public/flavor/stylesheets/layout.css` - Clean, no SVG overlay
   - `plugin_manager/themes/public/flavor/stylesheets/base.css` - Has `.paper-texture` utility classes with feTurbulence, but not applied globally
   - `plugin_manager/themes/public/flavor/stylesheets/global.css` - Clean

2. **Template Inspection:** Reviewed header and footer templates in both workspace and database:
   - `header` template (sid=13, tid=10587) - Clean, has Alpine.js `x-data="flavorTheme()"` but no SVG overlay
   - `footer` template (sid=13, tid=10492) - Clean, no SVG elements

3. **Chrome DevTools Diagnosis:**
   - No SVG elements found in DOM
   - No position:fixed elements blocking scroll
   - No overflow:hidden on html, body, or #container
   - touchAction: auto (not blocking)
   - pointerEvents: normal

4. **Scroll Testing:** Comprehensive JavaScript scroll tests:
   - `window.scroll({top: 200})` - PASSED
   - `window.scroll({top: 400})` - PASSED
   - `window.scroll({top: maxScroll})` - PASSED
   - Scroll back to top - PASSED

### Root Cause Analysis

**Suspected Original Cause:** feTurbulence SVG filters are GPU-intensive and recalculate on every frame during scroll, causing severe scroll jank or complete scroll blocking on some systems.

**Current State:** No feTurbulence filters were deployed. The workspace files have `.paper-texture` utility classes that use feTurbulence in data URIs, but these were never applied to the main layout.

---

## Resolution

### Fix Applied

Added a scroll-safe paper texture overlay to `layout.css` using a different approach:

```css
#container::after {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 9999;
  opacity: 0.025;
  mix-blend-mode: multiply;
  background-image: url("data:image/svg+xml,..."); /* Pattern-based SVG */
  background-repeat: repeat;
  background-size: 100px 100px;
}
```

### Key Design Decisions

1. **Static pattern instead of feTurbulence:** Uses a pre-computed circle pattern SVG instead of runtime feTurbulence filter. The pattern tiles at 100x100px.

2. **Fixed positioning:** `position: fixed` means the overlay doesn't reflow during scroll - it stays in place while content scrolls beneath it.

3. **pointer-events: none:** Ensures the overlay cannot block any user interactions (clicks, scrolls, etc.).

4. **Accessibility:** Respects `prefers-reduced-motion` media query - overlay is hidden for users who prefer reduced motion.

5. **Subtle opacity:** 0.025 opacity provides a very subtle paper grain effect without being visually distracting.

### Files Modified

| File | Change |
|------|--------|
| `plugin_manager/themes/public/flavor/stylesheets/layout.css` | Added `#container::after` pseudo-element with static SVG pattern overlay |

### Verification

- Synced to database via `mybb_workspace_sync(codename="flavor", type="theme")`
- All 4 scroll tests pass after fix
- Visual inspection confirms subtle texture effect
- Screenshot captured showing working scrolling

---

## Timeline

| Phase | Owner | Date | Notes |
|-------|-------|------|-------|
| Investigation | MyBBBugHunter | 2026-01-26 07:18-07:22 | Found no blocking code, scrolling worked |
| Fix Implementation | MyBBBugHunter | 2026-01-26 07:22-07:24 | Added static SVG pattern overlay |
| Verification | MyBBBugHunter | 2026-01-26 07:24 | All scroll tests pass |

---

## Prevention

### Recommendations

1. **Never use live feTurbulence filters on page overlays** - they recalculate every frame and cause severe performance issues.

2. **For texture effects, prefer:**
   - Static pattern-based SVGs
   - Pre-rendered PNG textures (if file size permits)
   - CSS-only grain effects using gradients

3. **Always test scroll performance** after adding any full-page overlay elements.

4. **Use pointer-events: none** on decorative overlays to prevent accidental interaction blocking.

---

## Appendix

### Test Results

```json
{
  "results": [
    {"test": "scroll to 200", "scrollY": 200, "pass": true},
    {"test": "scroll to 400", "scrollY": 400, "pass": true},
    {"test": "scroll to max", "scrollY": 596, "pass": true},
    {"test": "scroll to top", "scrollY": 0, "pass": true}
  ],
  "allPassed": true,
  "overlay": {
    "exists": true,
    "pointerEvents": "none",
    "position": "fixed",
    "opacity": "0.025"
  }
}
```

### Related Documentation

- Progress Log: `.scribe/docs/dev_plans/flavor_theme/PROGRESS_LOG.md`
- Layout CSS: `plugin_manager/themes/public/flavor/stylesheets/layout.css`
