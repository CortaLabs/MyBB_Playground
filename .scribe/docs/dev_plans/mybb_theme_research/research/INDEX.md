# Research Documents Index

**Project:** mybb_theme_research
**Last Updated:** 2026-01-17 13:45 UTC

---

## Research Documents

### 1. RESEARCH_Theme_Stylesheet_Inheritance_20260117_1338.md
- **Created:** 2026-01-17 13:38 UTC
- **Researcher:** ResearchAgent
- **Scope:** MyBB theme and stylesheet inheritance system
- **Confidence:** 0.95 (high)
- **Status:** Complete

**Summary:**
Complete analysis of MyBB's copy-on-write theme inheritance system including:
- Database schema (themes and themestylesheets tables)
- Inheritance resolution algorithm using pid field and recursive parent chain
- Copy-on-write editing behavior with automatic override creation
- Revert-to-parent via deletion mechanism
- Runtime optimization using pre-computed stylesheet lists

**Key Findings:**
- pid field stores parent theme ID (recursive traversal)
- Stylesheet resolution uses tid DESC ordering (child overrides parent)
- ACP automatically creates overrides when editing inherited stylesheets
- Deleting overrides exposes parent stylesheets (implicit revert)
- Runtime uses pre-computed cache in themes.stylesheets field

**Files Analyzed:**
- `/admin/inc/functions_themes.php` (build_new_theme, copy_stylesheet_to_theme, update_theme_stylesheet_list, make_parent_theme_list)
- `/admin/modules/style/themes.php` (edit_stylesheet, delete_stylesheet actions)
- `/global.php` (runtime stylesheet loading)
- Database tables: themes, themestylesheets

**Verified Questions Answered:**
1. How stylesheet resolution works (tid DESC ordering)
2. pid field usage (parent theme ID)
3. ACP editing behavior (copy-on-write)
4. Revert to parent concept (delete override)
5. Runtime loading mechanism (pre-computed cache)

---

## Research Summary by Topic

### Theme Inheritance
- ✅ Parent chain resolution (make_parent_theme_list)
- ✅ Copy-on-write semantics
- ✅ Inheritance metadata tracking

### Stylesheet Management
- ✅ Resolution algorithm
- ✅ Override creation mechanism
- ✅ Revert functionality
- ✅ Cache invalidation

### Performance Optimization
- ✅ Pre-computed stylesheet lists
- ✅ Runtime loading strategy
- ✅ update_theme_stylesheet_list caching

---

## Next Steps

**For Architect:**
- Design MCP tools respecting copy-on-write pattern
- Plan update_theme_stylesheet_list integration for write operations
- Consider inherited metadata exposure in read operations

**For Coder:**
- Implement tools using verified functions from research
- Ensure Master theme (tid=1) protection
- Call update_theme_stylesheet_list after any stylesheet changes

**For Reviewer:**
- Verify copy-on-write compliance
- Check cache invalidation calls
- Validate inheritance chain handling
