# MyBB Development Best Practices

**Complete guide to secure and maintainable MyBB plugin and theme development.**

---

## Overview

This section provides comprehensive best practices for MyBB development within the MyBB Playground environment. Following these guidelines ensures your plugins and themes are secure, maintainable, and compatible with MyBB core.

**Key Principles:**
- **Security First**: Always validate input, prevent SQL injection, and protect sensitive data
- **Use the MyBB API**: Never modify core files - use hooks, plugins, and templates
- **Follow Conventions**: Adhere to MyBB naming and structure patterns
- **Test Thoroughly**: Validate all functionality before deployment

---

## Available Guides

### [Plugin Development Guide](plugin_development.md)
Complete guide to creating MyBB plugins with proper structure, hooks, settings, templates, and database operations.

**Topics Covered:**
- Plugin structure and lifecycle functions (_info, _activate, _deactivate, _install, _uninstall)
- Hook usage patterns and registration
- Settings management via Admin CP
- Template management and caching
- Database operations with proper escaping

### [Theme Development Guide](theme_development.md)
Best practices for creating and packaging MyBB themes with proper inheritance and customization.

**Topics Covered:**
- Theme structure and workspace organization
- Stylesheet inheritance and copy-on-write patterns
- Template overrides and master template relationships
- Theme packaging and distribution

### [Security Guide](security.md)
Critical security practices for protecting MyBB installations and user data.

**Topics Covered:**
- Input validation and sanitization
- CSRF protection in forms
- SQL injection prevention
- Sensitive data handling (passwords, tokens, IP addresses)

---

## Quick Reference

### Essential Security Rules

1. **Always escape user input**: Use `$db->escape_string()` for all user-provided data
2. **Use parameterized queries**: Never concatenate SQL strings with user input
3. **Verify CSRF tokens**: Include `verify_post_check()` in all form handlers
4. **Exclude sensitive fields**: Never expose passwords, salts, or login keys
5. **Validate file operations**: Check paths before reading/writing files

### Plugin Development Checklist

- [ ] All functions prefixed with plugin codename
- [ ] Hooks registered in `_activate()`, removed in `_deactivate()`
- [ ] Settings created in `_install()`, removed in `_uninstall()`
- [ ] Templates cached properly if used
- [ ] Database tables use plugin prefix
- [ ] CSRF verification on all POST handlers
- [ ] Input validation on all user data
- [ ] Compatibility string set correctly

### Theme Development Checklist

- [ ] Workspace structure follows convention
- [ ] Stylesheets organized in stylesheets/ directory
- [ ] Parent theme inheritance configured if applicable
- [ ] Templates override master templates only when necessary
- [ ] meta.json includes all required metadata
- [ ] README.md documents installation and features

---

## Development Workflow

### 1. Research Phase
- Review existing plugins/themes for patterns
- Use MCP tools to analyze MyBB core structure
- Identify required hooks and database operations

### 2. Design Phase
- Plan plugin/theme structure
- Document required settings, templates, and database tables
- Design security measures for all user input

### 3. Implementation Phase
- Create workspace using Plugin Manager
- Implement lifecycle functions
- Add hook handlers with CSRF protection
- Test all functionality thoroughly

### 4. Deployment Phase
- Validate workspace structure
- Deploy to TestForum using MCP tools
- Execute lifecycle functions via PHP bridge
- Verify installation and activation

---

## Common Pitfalls to Avoid

### Plugin Development
- **DON'T** modify MyBB core files - use hooks instead
- **DON'T** forget to prefix functions/variables with codename
- **DON'T** skip CSRF verification on form handlers
- **DON'T** concatenate SQL strings with user input
- **DON'T** expose sensitive user data in queries

### Theme Development
- **DON'T** modify master templates directly - create overrides
- **DON'T** break parent theme inheritance chain
- **DON'T** hardcode paths or URLs in stylesheets
- **DON'T** skip validation of workspace structure

---

## Resources

### MyBB Documentation
- [Official MyBB Plugin Development Guide](https://docs.mybb.com/1.8/development/plugins/)
- [MyBB Hooks Reference](https://docs.mybb.com/1.8/development/plugins/hooks/)
- [MyBB Database Methods](https://docs.mybb.com/1.8/development/database-methods/)

### MyBB Playground Tools
- [MCP Tools Reference](../mcp_tools/index.md) - All 85+ MCP tools
- [Plugin Manager](../plugin_manager/index.md) - Workspace and deployment system
- [Architecture Guide](../architecture/index.md) - System internals

---

## Getting Help

**For MyBB Playground issues:**
- Review the [Getting Started Guide](../getting_started/index.md)
- Check [Architecture Documentation](../architecture/index.md) for system internals
- Examine [MCP Tools Reference](../mcp_tools/index.md) for available operations

**For MyBB core questions:**
- [MyBB Community Forums](https://community.mybb.com/)
- [MyBB Documentation](https://docs.mybb.com/)

---

**Last Updated:** 2026-01-18
