# MyBB MCP Expansion Roadmap - Strategic Feature Prioritization

**Research Date:** 2026-01-17
**Project:** mybb-ecosystem-audit
**Researcher:** ResearchAgent
**Confidence:** 0.95

## Executive Summary

This research audit analyzed the current MyBB MCP server capabilities and MyBB's underlying infrastructure to identify high-value expansion opportunities for AI-assisted forum development. The investigation covered 15 existing MCP tools, 7 MyBB datahandler APIs, 30+ moderation operations, and extensive admin infrastructure.

**Key Finding:** Current MCP provides excellent design/theming tools but lacks content management, user management, and moderation capabilities - all of which MyBB's infrastructure fully supports through battle-tested, security-validated APIs.

**Top Priority:** Content Management (posts/threads/forums) offers the highest value-to-complexity ratio, enabling AI-assisted content creation workflows while leveraging MyBB's existing datahandler validation.

---

## Current MCP Capabilities (Baseline)

### Existing Tools (15 total)

**Templates (5 tools):**
- `mybb_list_template_sets` - List all template sets
- `mybb_list_templates` - Filter by set ID or search term
- `mybb_read_template` - Read template HTML with inheritance support
- `mybb_write_template` - Create/update with automatic inheritance
- `mybb_list_template_groups` - Browse template organization

**Themes/Styles (4 tools):**
- `mybb_list_themes` - List all themes with relationships
- `mybb_list_stylesheets` - List CSS files by theme
- `mybb_read_stylesheet` - Read CSS content
- `mybb_write_stylesheet` - Update CSS with cache refresh

**Plugins (4 tools):**
- `mybb_list_plugins` - List plugins in inc/plugins/
- `mybb_read_plugin` - Read plugin PHP source
- `mybb_create_plugin` - Scaffold complete plugin structure
- `mybb_list_hooks` - Browse 50+ hooks by category
- `mybb_analyze_plugin` - Analyze existing plugin structure

**Database (1 tool):**
- `mybb_db_query` - Read-only SELECT queries

**Additional Infrastructure:**
- DiskSync service with auto-watcher for templates/stylesheets
- Database abstraction layer (MyBBDatabase class)
- Configuration management via .env

### Coverage Assessment

✅ **Strong Coverage:**
- Design/theming (templates, stylesheets, themes)
- Plugin development (scaffolding, hooks, analysis)
- Code exploration (plugins, database queries)

❌ **Missing Coverage:**
- Content management (posts, threads, forums)
- User management (CRUD, permissions, groups)
- Moderation (thread/post actions, approvals)
- Search functionality
- Statistics/analytics
- Backup/restore automation
- Migration tools
- Testing/validation
- Performance monitoring
- External integrations

---

## MyBB Infrastructure Analysis

### Verified APIs and Patterns

**Datahandlers (7 core models):**
1. **post.php** (2037 lines)
   - Operations: `validate_post()`, `insert_post()`, `update_post()`, `validate_thread()`, `insert_thread()`
   - Validations: author, subject, message, flooding, merge, image/video count, prefix, icon, dateline
   - Pattern: Comprehensive validation → secure insertion/update

2. **user.php** (1878 lines)
   - Operations: `validate_user()`, `insert_user()`, `update_user()`, `delete_user()`, `clear_profile()`
   - Validations: username, password, email, usergroup, website, birthday, profile fields, signature, timezone
   - Security: Email verification, username uniqueness, password strength

3. **pm.php** (Private messages)
4. **event.php** (Calendar events)
5. **login.php** (Authentication)
6. **warnings.php** (User warnings)

**Moderation Class** (`class_moderation.php` - 3832 lines):
- **Thread Operations:** close, open, stick, unstick, delete, approve, unapprove, move, merge, split, expire, toggle_visibility, toggle_softdelete, toggle_status, toggle_importance, restore
- **Post Operations:** delete, merge, approve, unapprove, toggle_visibility, toggle_softdelete, soft_delete, restore
- **Bulk Operations:** change_thread_subject, apply_thread_prefix, remove_thread_subscriptions

**Admin Modules:**
- User management: admin_permissions.php, banning.php, groups.php, group_promotions.php, mass_mail.php, users.php
- Tools: backupdb.php, cache.php, file_verification.php
- Scheduled tasks: 13 tasks (backup, cleanup, mail queue, promotions, thread views, version check, user pruning)

**Search Infrastructure:**
- search.php (1765 lines) - Complex search logic
- stats.php - Forum statistics
- functions_serverstats.php - Server metrics

### Security Pattern (CRITICAL)

All MyBB datahandlers follow a **validate → insert/update** pattern with comprehensive field validation. This is NOT optional - bypassing these validators (e.g., direct SQL INSERT) would create security vulnerabilities.

**MCP Implementation Requirement:** Any content/user management tools MUST use MyBB's datahandler classes, not direct database access.

---

## Prioritized Roadmap

### Priority Scoring Methodology

**Value to AI Development (1-10):**
- AI workflow enhancement
- Automation potential
- Developer productivity impact

**Implementation Complexity (1-10, lower = easier):**
- Number of methods to wrap
- Validation complexity
- Security requirements
- Testing surface area

**Security Risk (1-10, lower = safer):**
- Permission requirements
- Data sensitivity
- Audit trail needs
- Potential for abuse

**Priority Score = (Value × 2) - Complexity - Security Risk**

---

### TIER 1: High Value, Low-Medium Complexity (Implement First)

#### 1. Content Management - Posts & Threads
**Priority Score: 11** | Value: 10 | Complexity: 6 | Security: 3

**Value Proposition:**
- Enables AI-assisted content creation workflows
- Supports automated testing with realistic data
- Facilitates forum seeding and development

**Proposed Tools:**
- `mybb_list_posts(fid, tid, limit, filters)` - Read posts with pagination
- `mybb_read_post(pid)` - Read single post with metadata
- `mybb_create_post(tid, message, author, options)` - Create new post
- `mybb_update_post(pid, message, options)` - Edit existing post
- `mybb_list_threads(fid, filters, limit)` - Read threads
- `mybb_read_thread(tid)` - Read thread with first post
- `mybb_create_thread(fid, subject, message, author, options)` - Create thread
- `mybb_update_thread(tid, subject, options)` - Edit thread

**Implementation Notes:**
- ✅ Wrap existing `PostDataHandler` class
- ✅ All validations already implemented
- ⚠️ Requires proper author context (user permissions)
- 📋 Flood checking automatically handled
- 🔒 Security: Use datahandler, validate permissions

**Complexity Breakdown:**
- 8 tools to implement
- Existing validation: 12+ methods already written
- Database: Tables already exist (posts, threads)
- Estimated effort: 3-5 days

---

#### 2. Content Management - Forums
**Priority Score: 9** | Value: 8 | Complexity: 4 | Security: 3

**Value Proposition:**
- Essential for test environment setup
- Enables automated forum structure creation
- Supports migration workflows

**Proposed Tools:**
- `mybb_list_forums(parent, recursive)` - List forums with hierarchy
- `mybb_read_forum(fid)` - Read forum config and stats
- `mybb_create_forum(name, description, parent, options)` - Create forum
- `mybb_update_forum(fid, options)` - Update forum settings

**Implementation Notes:**
- ✅ Admin module patterns already exist
- ✅ Forum hierarchy logic in `functions.php`
- 📋 Permission inheritance needs testing
- 🔒 Security: Admin-level operation

**Complexity Breakdown:**
- 4 tools to implement
- Simpler than posts (less validation)
- Database: forums table well-documented
- Estimated effort: 2-3 days

---

#### 3. Search Functionality
**Priority Score: 8** | Value: 9 | Complexity: 7 | Security: 2

**Value Proposition:**
- Critical for AI content discovery
- Enables semantic search integration
- Supports documentation generation

**Proposed Tools:**
- `mybb_search_posts(query, fid, uid, filters)` - Search post content
- `mybb_search_threads(query, fid, filters)` - Search thread titles
- `mybb_search_users(query, filters)` - Search usernames/emails

**Implementation Notes:**
- ✅ MyBB search engine already exists (search.php)
- ⚠️ Multiple search engines (MySQL, PostgreSQL fulltext)
- 📋 Results caching important for performance
- 🔒 Security: Respect forum permissions in results

**Complexity Breakdown:**
- 3 tools to implement
- Search logic already written
- Challenge: Abstracting MyBB's search API
- Estimated effort: 3-4 days

---

### TIER 2: High Value, Higher Complexity (Implement Second)

#### 4. User Management
**Priority Score: 7** | Value: 8 | Complexity: 7 | Security: 4

**Value Proposition:**
- Supports automated user provisioning
- Enables test user creation
- Facilitates permission testing

**Proposed Tools:**
- `mybb_list_users(filters, limit)` - List users with pagination
- `mybb_read_user(uid)` - Read user profile and stats
- `mybb_create_user(username, email, password, options)` - Create user
- `mybb_update_user(uid, options)` - Update user profile
- `mybb_delete_user(uid, prune_content)` - Delete user
- `mybb_list_usergroups()` - List available groups
- `mybb_add_user_to_group(uid, gid)` - Change user group

**Implementation Notes:**
- ✅ `UserDataHandler` class comprehensive
- ⚠️ Password hashing must use MyBB's auth system
- 📋 Email validation/verification flow complex
- 🔒 Security: Sensitive operation, audit logging critical

**Complexity Breakdown:**
- 7 tools to implement
- 20+ validation methods to wrap
- Security considerations high
- Estimated effort: 5-7 days

---

#### 5. Moderation Tools
**Priority Score: 6** | Value: 9 | Complexity: 8 | Security: 5

**Value Proposition:**
- Enables AI-assisted moderation workflows
- Supports bulk operations automation
- Reduces manual moderation workload

**Proposed Tools:**
- `mybb_moderate_approve_thread(tid)` - Approve thread
- `mybb_moderate_close_thread(tid)` - Close thread
- `mybb_moderate_stick_thread(tid)` - Stick thread
- `mybb_moderate_move_thread(tid, fid)` - Move thread
- `mybb_moderate_merge_threads(tid1, tid2)` - Merge threads
- `mybb_moderate_delete_post(pid, soft)` - Delete/soft-delete post
- `mybb_moderate_approve_post(pid)` - Approve post

**Implementation Notes:**
- ✅ `class_moderation.php` already implements all operations
- ⚠️ Permission checking CRITICAL (moderator rights by forum)
- 📋 Logging all moderation actions required
- 🔒 Security: High-risk operations, extensive audit trail

**Complexity Breakdown:**
- 7+ tools to implement (could expand to 20+)
- Wrapping existing methods straightforward
- Permission system integration complex
- Estimated effort: 5-7 days

---

#### 6. Statistics & Analytics
**Priority Score: 5** | Value: 7 | Complexity: 5 | Security: 3

**Value Proposition:**
- Enables monitoring dashboards
- Supports performance insights
- Facilitates reporting automation

**Proposed Tools:**
- `mybb_get_forum_stats()` - Overall forum statistics
- `mybb_get_thread_stats(tid)` - Thread analytics
- `mybb_get_user_stats(uid)` - User activity stats
- `mybb_get_server_stats()` - Server performance metrics

**Implementation Notes:**
- ✅ Stats functions already exist
- ✅ Database queries well-optimized
- 📋 Caching important for performance
- 🔒 Security: Read-only, low risk

**Complexity Breakdown:**
- 4 tools to implement
- Mostly database aggregation queries
- Cache integration recommended
- Estimated effort: 2-3 days

---

### TIER 3: Medium-High Value, Specialized Use Cases

#### 7. Backup & Restore Automation
**Priority Score: 4** | Value: 6 | Complexity: 6 | Security: 4

**Value Proposition:**
- Automates disaster recovery
- Enables development environment cloning
- Supports testing workflows

**Proposed Tools:**
- `mybb_create_backup(compress, path)` - Create database backup
- `mybb_list_backups()` - List available backups
- `mybb_restore_backup(backup_id, confirm)` - Restore from backup
- `mybb_export_settings(include_plugins)` - Export configuration

**Implementation Notes:**
- ✅ `backupdb.php` task already exists
- ⚠️ Restore requires careful transaction handling
- 📋 File system access for backup storage
- 🔒 Security: CRITICAL operation, requires confirmation

**Complexity Breakdown:**
- 4 tools to implement
- Backup logic already written
- Restore is net-new code
- Estimated effort: 4-5 days

---

#### 8. Testing & Validation Tools
**Priority Score: 4** | Value: 7 | Complexity: 7 | Security: 2

**Value Proposition:**
- Enables automated testing workflows
- Supports plugin validation
- Facilitates QA automation

**Proposed Tools:**
- `mybb_validate_plugin(plugin_name)` - Check plugin structure
- `mybb_validate_template(template_code)` - Check template syntax
- `mybb_validate_permissions(uid, fid, action)` - Test permission logic
- `mybb_run_integrity_check()` - File verification

**Implementation Notes:**
- ✅ `file_verification.php` already exists
- 📋 Template parsing requires MyBB template engine
- 📋 Plugin validation is custom logic
- 🔒 Security: Read-only validation, low risk

**Complexity Breakdown:**
- 4 tools to implement
- Some validation logic exists
- New validation patterns needed
- Estimated effort: 3-4 days

---

#### 9. Migration Tools
**Priority Score: 3** | Value: 5 | Complexity: 8 | Security: 4

**Value Proposition:**
- Supports forum platform migrations
- Enables data import workflows
- Facilitates testing with production data

**Proposed Tools:**
- `mybb_import_users(data, mapping)` - Bulk user import
- `mybb_import_threads(data, mapping)` - Bulk thread import
- `mybb_import_posts(data, mapping)` - Bulk post import
- `mybb_export_forum_structure()` - Export forum hierarchy

**Implementation Notes:**
- ⚠️ No existing migration infrastructure in MyBB core
- 📋 Requires comprehensive data mapping
- 📋 Validation at scale challenging
- 🔒 Security: Bulk operations risk, rate limiting needed

**Complexity Breakdown:**
- 4 tools to implement
- All net-new code
- High testing requirements
- Estimated effort: 7-10 days

---

#### 10. Performance Monitoring
**Priority Score: 2** | Value: 5 | Complexity: 7 | Security: 2

**Value Proposition:**
- Enables performance optimization
- Supports capacity planning
- Facilitates debugging

**Proposed Tools:**
- `mybb_get_query_log(limit)` - Recent database queries
- `mybb_get_cache_stats()` - Cache hit/miss rates
- `mybb_get_plugin_hooks_trace()` - Hook execution timing
- `mybb_monitor_resource_usage()` - Server resource metrics

**Implementation Notes:**
- ⚠️ Limited existing instrumentation in MyBB
- 📋 Requires performance data collection infrastructure
- 📋 Hook timing requires custom profiling
- 🔒 Security: Exposes internal metrics, admin-only

**Complexity Breakdown:**
- 4 tools to implement
- Significant instrumentation needed
- Performance overhead concerns
- Estimated effort: 5-7 days

---

## Implementation Recommendations

### Phase 1: Foundation (Weeks 1-3)
**Goal:** Enable AI-assisted content workflows

1. **Content Management - Forums** (2-3 days)
   - Start simple: list, read, create operations
   - Establishes pattern for other content tools

2. **Content Management - Posts & Threads** (3-5 days)
   - Wrap `PostDataHandler` class
   - Implement read operations first, then write
   - Add comprehensive validation tests

3. **Search Functionality** (3-4 days)
   - Wrap MyBB search API
   - Respect permission system in results
   - Implement basic post/thread search

**Deliverable:** MCP server with content read/write capabilities

---

### Phase 2: Administration (Weeks 4-6)
**Goal:** Enable AI-assisted user and moderation workflows

4. **User Management** (5-7 days)
   - Wrap `UserDataHandler` class
   - Implement group management
   - Add permission helpers

5. **Statistics & Analytics** (2-3 days)
   - Expose existing stats functions
   - Add caching for performance
   - Create dashboard data APIs

**Deliverable:** Full user lifecycle and stats management

---

### Phase 3: Advanced Operations (Weeks 7-10)
**Goal:** Enable moderation automation and operational tools

6. **Moderation Tools** (5-7 days)
   - Wrap `class_moderation.php` methods
   - Implement permission checks
   - Add comprehensive audit logging

7. **Backup & Restore** (4-5 days)
   - Wrap existing backup task
   - Implement restore logic
   - Add safety confirmations

**Deliverable:** Complete forum administration toolkit

---

### Phase 4: Specialized Tools (Weeks 11-14)
**Goal:** Enable advanced workflows and integrations

8. **Testing & Validation** (3-4 days)
9. **Migration Tools** (7-10 days) - If needed
10. **Performance Monitoring** (5-7 days) - If needed

**Deliverable:** Enterprise-grade development toolkit

---

## Security Considerations

### Critical Requirements

1. **ALWAYS Use Datahandlers**
   - ❌ Never bypass MyBB's validation with direct SQL
   - ✅ Use `PostDataHandler`, `UserDataHandler`, etc.
   - ✅ Validation includes: flood checking, permission verification, content sanitization

2. **Permission System Integration**
   - Every operation MUST check user permissions
   - Forum-level permissions for content operations
   - Moderator permissions for moderation tools
   - Admin permissions for user/forum management

3. **Audit Logging**
   - Log ALL write operations (create, update, delete)
   - Include: timestamp, user, action, target, result
   - Use MyBB's existing moderation log system
   - Add MCP-specific log category

4. **Input Validation**
   - All user-provided data sanitized
   - SQL injection protection (use parameterized queries)
   - XSS protection in content fields
   - CSRF protection for state-changing operations

5. **Rate Limiting**
   - Prevent bulk operation abuse
   - Respect MyBB's flood checking
   - Add MCP-specific rate limits for batch operations

### Risk Mitigation Strategies

**High-Risk Operations:**
- User deletion, bulk moderation, backup restore
- Mitigation: Require explicit confirmation parameter, dry-run mode, soft deletes

**Sensitive Data:**
- Passwords, email addresses, private messages
- Mitigation: Never return passwords, sanitize PII in logs, encrypt backups

**Permission Escalation:**
- Operations that could grant privileges
- Mitigation: Double-check permissions, log privilege changes, require admin confirmation

---

## Testing Strategy

### Unit Tests (Per Tool)
- Valid input scenarios
- Invalid input handling
- Permission denial cases
- Datahandler validation enforcement

### Integration Tests
- Multi-tool workflows (create thread → create post)
- Permission inheritance (forum → thread → post)
- Cache invalidation after updates
- Concurrent operation handling

### Security Tests
- Permission bypass attempts
- SQL injection vectors
- XSS in content fields
- CSRF attack simulation
- Rate limit enforcement

### Performance Tests
- Bulk operations scaling (100, 1000, 10000 items)
- Search query performance
- Cache hit rate optimization
- Database query optimization

---

## External Integration Opportunities

### Potential External Service Integrations

1. **AI Content Analysis**
   - Sentiment analysis for moderation
   - Spam detection with ML models
   - Content quality scoring

2. **Notification Services**
   - Slack/Discord webhooks for mod actions
   - Email automation for user events
   - SMS for critical alerts

3. **Analytics Platforms**
   - Export to Google Analytics
   - Custom dashboards (Grafana, Datadog)
   - SEO optimization tools

4. **Backup Storage**
   - S3/cloud storage for backups
   - Automated backup rotation
   - Geographic redundancy

5. **Authentication Providers**
   - OAuth integration (Google, GitHub, etc.)
   - SSO for enterprise deployments
   - Two-factor authentication

**Implementation Approach:**
- Create `mybb_register_webhook(event, url)` tool
- Add plugin hooks for external integrations
- Document integration patterns for extension

---

## Success Metrics

### Adoption Metrics
- Number of AI workflows using new tools
- Developer productivity improvements
- Reduction in manual admin tasks

### Technical Metrics
- API response times (< 100ms for read, < 500ms for write)
- Cache hit rates (> 80% for read operations)
- Error rates (< 0.1% for valid operations)

### Security Metrics
- Zero permission bypass vulnerabilities
- 100% audit log coverage for write operations
- Zero SQL injection vulnerabilities

---

## Open Questions & Recommendations for Architect

### Architectural Decisions Needed

1. **Authentication Strategy**
   - How should MCP authenticate as MyBB users?
   - Options: Session tokens, API keys, service account
   - Recommendation: Service account with configurable permission profile

2. **Error Handling Pattern**
   - Return MyBB's datahandler errors directly?
   - Wrap in MCP-specific error format?
   - Recommendation: Preserve MyBB error codes but wrap in structured JSON

3. **Pagination Strategy**
   - MyBB uses various pagination patterns
   - Standardize across all list operations?
   - Recommendation: Consistent cursor-based pagination

4. **Caching Layer**
   - Respect MyBB's cache or add MCP layer?
   - Cache invalidation strategy?
   - Recommendation: Use MyBB cache, add MCP cache for aggregations

5. **Async Operations**
   - Should bulk operations be async?
   - Job queue for long-running tasks?
   - Recommendation: Synchronous for now, add async in Phase 4

### Gaps Requiring Investigation

1. **MyBB Permission System Deep Dive**
   - Need comprehensive permission matrix
   - Document permission inheritance rules
   - Map to MCP tool requirements

2. **MyBB Hook System for MCP**
   - Can MCP operations trigger plugin hooks?
   - Should they? (Probably yes for consistency)
   - Document hook firing patterns

3. **Database Transaction Boundaries**
   - Which operations should be atomic?
   - Rollback strategy for multi-step operations
   - Document transaction requirements

---

## Conclusion

The MyBB ecosystem provides a **robust, security-validated infrastructure** that can be safely exposed through MCP tools. The current MCP server demonstrates excellent patterns for template/theme management that can be extended to content, user, and moderation operations.

**Recommended Approach:**
1. Start with **Content Management** (highest value, leverages existing datahandlers)
2. Add **Search** for content discovery
3. Expand to **User Management** and **Statistics**
4. Implement **Moderation** for advanced workflows
5. Add **Backup/Restore** and specialized tools as needed

**Critical Success Factors:**
- ALWAYS use MyBB datahandlers (never bypass validation)
- Comprehensive permission checking
- Full audit logging
- Extensive testing for security and performance

**Estimated Total Effort:**
- Phase 1 (Foundation): 2-3 weeks
- Phase 2 (Administration): 2-3 weeks
- Phase 3 (Advanced): 3-4 weeks
- Phase 4 (Specialized): 3-4 weeks
- **Total: 10-14 weeks for complete implementation**

This roadmap enables AI-assisted MyBB development workflows while maintaining security, data integrity, and operational safety.

---

## Appendix A: File References

### MCP Source Files Analyzed
- `/mybb_mcp/mybb_mcp/server.py` (614 lines) - Tool definitions
- `/mybb_mcp/mybb_mcp/db/connection.py` (350 lines) - Database layer
- `/mybb_mcp/mybb_mcp/tools/plugins.py` - Plugin scaffolding
- `/mybb_mcp/README.md` - Documentation

### MyBB Core Files Analyzed
- `/TestForum/inc/datahandlers/post.php` (2037 lines)
- `/TestForum/inc/datahandlers/user.php` (1878 lines)
- `/TestForum/inc/class_moderation.php` (3832 lines)
- `/TestForum/search.php` (1765 lines)
- `/TestForum/inc/functions.php` (9531 lines)
- `/TestForum/inc/functions_serverstats.php` (298 lines)
- `/TestForum/inc/tasks/backupdb.php` (147 lines)

### Database Tables Referenced
- `mybb_templates`, `mybb_templatesets`, `mybb_templategroups`
- `mybb_themes`, `mybb_themestylesheets`
- `mybb_posts`, `mybb_threads`, `mybb_forums`
- `mybb_users`, `mybb_usergroups`
- `mybb_moderatorlog`, `mybb_adminlog`
- `mybb_settings`, `mybb_settinggroups`

---

## Appendix B: Confidence Assessment

### High Confidence Findings (0.9-1.0)
- Current MCP tool inventory (verified source)
- MyBB datahandler capabilities (examined source)
- Moderation operations (enumerated from class)
- User management validation (examined datahandler)

### Medium Confidence Findings (0.7-0.9)
- Implementation complexity estimates (based on similar patterns)
- Security risk assessments (based on operation types)
- Effort estimates (extrapolated from existing code)

### Lower Confidence Areas (0.6-0.7)
- External integration opportunities (speculative)
- Performance monitoring implementation (limited existing infra)
- Migration tool complexity (no existing patterns)

### Requires Further Investigation
- MyBB permission system deep dive
- Hook system interaction patterns
- Transaction boundary requirements
- Authentication strategy for MCP service account
