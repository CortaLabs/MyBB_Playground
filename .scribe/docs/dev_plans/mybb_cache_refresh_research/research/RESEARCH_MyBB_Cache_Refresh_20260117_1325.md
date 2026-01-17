
# 🔬 Research Mybb Cache Refresh 20260117 1325 — mybb_cache_refresh_research
**Author:** Scribe
**Version:** v0.1
**Status:** In Progress
**Last Updated:** 2026-01-17 13:25:32 UTC

> This research document provides a complete technical analysis of the MyBB VSCode extension's cache refresh system for themes and stylesheets. It documents the end-to-end workflow from file save in VSCode through HTTP endpoints to MyBB's core cache_stylesheet() function.

---
## Executive Summary
<!-- ID: executive_summary -->
**Primary Objective:** Understand how the MyBB VSCode extension refreshes MyBB's internal cache after stylesheet changes.

**Key Takeaways:**
- The extension uses a multi-layer architecture: VSCode → Node.js → PHP endpoints → MyBB core functions
- Cache refresh is automatic on every stylesheet save when autoUpload is enabled
- MyBB's cache_stylesheet() function creates physical CSS files in cache/themes/theme{tid}/ directory
- The system generates both regular and minified versions of stylesheets
- The workflow involves database updates (themestylesheets table) followed by file system operations


---
## Research Scope
<!-- ID: research_scope -->
**Research Lead:** ResearchAgent_MyBBCache

**Investigation Window:** 2026-01-17

**Focus Areas:**
- [x] VSCode extension cache refresh trigger mechanism
- [x] HTTP endpoint architecture (cacheStylesheet.js, cachecss.php, cacheform.php)
- [x] MyBB core cache_stylesheet() function implementation
- [x] Database operations (themes and themestylesheets tables)
- [x] File system operations (cache directory structure)
- [x] Integration points between TypeScript and PHP layers

**Dependencies & Constraints:**
- Research limited to read-only analysis of existing codebase
- Extension located at /home/austin/projects/MyBB_Playground/vscode-mybbbridge
- MyBB installation at /home/austin/projects/MyBB_Playground/TestForum
- All findings verified through direct code inspection with file:line references


---
## Findings
<!-- ID: findings -->

### Finding 1: Automatic Cache Refresh on Save
- **Summary:** The extension automatically refreshes MyBB's cache after every stylesheet save when autoUpload is enabled
- **Evidence:**
  - `src/events.ts:54` - onSaveEvent() calls `style.saveElement()`
  - `src/MyBBThemes.ts:331` - saveElement() automatically calls `this.requestCacheRefresh()`
  - Comment at line 330: "Always refresh the cache after update"
- **Confidence:** HIGH (100%)

### Finding 2: HTTP Endpoint Architecture
- **Summary:** The extension uses HTTP POST requests to PHP endpoints for cache operations
- **Evidence:**
  - `src/MyBBThemes.ts:354` - POST request to `cachecss.php`
  - `cacheStylesheet.js:25` - Alternative POST to `cacheform.php?action=csscacheclear`
  - Both endpoints accept `theme_name` and `stylesheet` parameters
- **Confidence:** HIGH (100%)

### Finding 3: MyBB Core cache_stylesheet() Function
- **Summary:** MyBB's cache_stylesheet() function creates physical CSS files in the cache directory with both regular and minified versions
- **Evidence:**
  - `TestForum/admin/inc/functions_themes.php:374-440`
  - Creates `cache/themes/theme{tid}/{filename}` for regular CSS
  - Creates `cache/themes/theme{tid}/{filename}.min.css` for minified CSS
  - Performs theme variable parsing and URL fixing
  - Handles CDN integration via `copy_file_to_cdn()`
- **Confidence:** HIGH (100%)

### Finding 4: Database Operations
- **Summary:** The system updates the themestylesheets table before triggering cache refresh
- **Evidence:**
  - `src/MyBBThemes.ts:320-323` - UPDATE query sets stylesheet content and lastmodified timestamp
  - `cacheform.php:177-178` - Fetches theme ID from themes table
  - `cacheform.php:191-192` - Fetches stylesheet content from themestylesheets table
  - `cacheform.php:201-205` - Updates lastmodified timestamp
- **Confidence:** HIGH (100%)

### Finding 5: Two PHP Endpoint Options
- **Summary:** The extension provides two PHP endpoints for cache refresh: cachecss.php (direct) and cacheform.php (routing)
- **Evidence:**
  - `cachecss.php` - Direct endpoint that immediately calls cache_stylesheet()
  - `cacheform.php` - Routing endpoint with action=csscacheclear that provides additional validation
  - `src/MyBBThemes.ts:354` uses cachecss.php
  - `cacheStylesheet.js:25` uses cacheform.php
- **Confidence:** HIGH (100%)

### Additional Notes
- Both endpoints require MyBB's `admin/inc/functions_themes.php` to be loaded for cache_stylesheet() function
- The system includes error logging to separate log files (cachecss_errors.log, mybbbridge_extension.log)
- Optional token-based authentication is supported but not required
- File save detection uses path pattern matching: `styles/{theme}/{stylesheet}.css`


---
## Technical Analysis
<!-- ID: technical_analysis -->

**Code Patterns Identified:**

1. **Event-Driven Architecture**
   - VSCode file watcher triggers onSaveEvent() (events.ts:12)
   - Path pattern matching determines file type (styles vs templates)
   - Automatic database update followed by cache refresh

2. **Layered Communication**
   ```
   VSCode Extension (TypeScript)
       ↓ (HTTP POST)
   PHP Endpoints (cachecss.php / cacheform.php)
       ↓ (Function Call)
   MyBB Core (cache_stylesheet)
       ↓ (File I/O)
   Cache Directory (cache/themes/theme{tid}/)
   ```

3. **Dual File Generation Pattern**
   - Every stylesheet cached in two versions: regular + minified
   - Minification removes comments, whitespace, and optimizes colors
   - Both files copied to CDN if configured

4. **Theme Variable Parsing**
   - `parse_theme_variables()` replaces placeholders in CSS
   - `fix_css_urls_callback()` corrects relative URL paths
   - Ensures cache files reference correct theme directory

**System Interactions:**

1. **Database Dependencies:**
   - `themes` table - Maps theme names to theme IDs (tid)
   - `themestylesheets` table - Stores CSS content, tracks lastmodified timestamps

2. **File System Operations:**
   - Creates `cache/themes/theme{tid}/` directory structure
   - Writes `{filename}` and `{filename}.min.css`
   - Handles safe mode fallback to single cache/themes/ directory
   - Optional CDN sync via copy_file_to_cdn()

3. **HTTP Communication:**
   - POST requests with form-encoded data (theme_name, stylesheet)
   - JSON response format for success/error messages
   - Optional token authentication parameter

**Risk Assessment:**

- [x] **File System Permissions** - cache_stylesheet() requires write permissions to cache/themes/ directory; failures return false but may not be immediately visible to user
- [x] **Database Integrity** - System assumes theme and stylesheet exist in database; missing records cause errors
- [x] **HTTP Endpoint Security** - cachecss.php runs in MyBB context, token auth is optional
- [x] **Error Handling** - Both endpoints log errors but continue execution; failed cache refresh may go unnoticed
- [x] **Safe Mode Limitations** - In PHP safe mode, all themes share single cache directory with prefixed filenames (tid_filename)


---
## Recommendations
<!-- ID: recommendations -->

### Immediate Next Steps
- [x] **Documentation Complete** - This research provides complete understanding of cache refresh mechanism
- [ ] **Testing** - Verify cache refresh works correctly across different MyBB versions
- [ ] **Error Handling** - Consider improving user feedback when cache refresh fails
- [ ] **Security Review** - Evaluate whether token authentication should be mandatory

### Long-Term Opportunities
- **Consolidate Endpoints** - Consider standardizing on one PHP endpoint (cachecss.php vs cacheform.php)
- **Enhanced Monitoring** - Add cache refresh success/failure metrics to VSCode status bar
- **Batch Operations** - Support refreshing multiple stylesheets in single operation
- **CDN Integration** - Document CDN setup requirements and verify copy_file_to_cdn() behavior
- **Safe Mode Detection** - Auto-detect PHP safe mode and inform user of cache directory limitations


---
## Appendix
<!-- ID: appendix -->

### Complete Execution Flow

**Step-by-Step Cache Refresh Process:**

1. **User Saves CSS File in VSCode**
   - File path: `styles/{theme}/{stylesheet}.css`
   - Detected by VSCode file watcher

2. **onSaveEvent() Triggered** (events.ts:12)
   - Checks `config.autoUpload` setting
   - Extracts theme name and filename from path
   - Creates MyBBStyle instance

3. **saveElement() Updates Database** (MyBBThemes.ts:293-338)
   - Fetches theme ID from `themes` table
   - Updates `themestylesheets` table with new CSS content
   - Sets `lastmodified` timestamp
   - Shows success message in VSCode

4. **requestCacheRefresh() Invoked** (MyBBThemes.ts:347-398)
   - Automatically called after database update (line 331)
   - POSTs to `{mybbUrl}/cachecss.php`
   - Sends `theme_name` and `stylesheet` parameters
   - Optional `token` for authentication

5. **cachecss.php Processes Request** (cachecss.php:1-91)
   - Loads MyBB context and functions_themes.php
   - Validates theme_name and stylesheet parameters
   - Fetches theme ID from database
   - Fetches stylesheet content from database
   - Calls `cache_stylesheet($tid, $stylesheet, $content)`

6. **cache_stylesheet() Creates Cache Files** (functions_themes.php:374-440)
   - Validates filename ends with .css
   - Creates `cache/themes/theme{tid}/` directory
   - Parses theme variables in CSS
   - Fixes CSS URL references
   - Writes `{filename}` (regular version)
   - Minifies CSS and writes `{filename}.min.css`
   - Copies both to CDN if configured
   - Returns cache file path

7. **Response Returned to VSCode**
   - JSON response with success/failure status
   - VSCode shows information/error message
   - Extension logs result to mybbbridge_extension.log

### File References

**VSCode Extension Files:**
- `vscode-mybbbridge/src/events.ts` - File save event handler
- `vscode-mybbbridge/src/MyBBThemes.ts` - MyBBStyle class with cache refresh logic
- `vscode-mybbbridge/cacheStylesheet.js` - Alternative Node.js cache refresh script
- `vscode-mybbbridge/cachecss.php` - Primary PHP cache endpoint
- `vscode-mybbbridge/cacheform.php` - Secondary PHP routing endpoint

**MyBB Core Files:**
- `TestForum/admin/inc/functions_themes.php` - cache_stylesheet() function (lines 374-440)

### Database Schema

**themes Table:**
- `tid` (INT) - Theme ID (primary key)
- `name` (VARCHAR) - Theme name

**themestylesheets Table:**
- `tid` (INT) - Theme ID (foreign key)
- `name` (VARCHAR) - Stylesheet filename
- `stylesheet` (TEXT) - CSS content
- `lastmodified` (INT) - Unix timestamp

### Configuration Requirements

**VSCode Extension Settings:**
- `mybbUrl` - Base URL of MyBB installation (e.g., http://localhost/mybb)
- `autoUpload` - Enable automatic upload on save (boolean)
- `token` - Optional authentication token (string)
- `database` - Database connection credentials (host, user, password, database, prefix)

---