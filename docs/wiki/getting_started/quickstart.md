# Quickstart Tutorial

This 5-minute tutorial will get you up and running with the MyBB Playground. You'll learn how to use MCP tools through Claude Code to interact with your MyBB installation.

## Prerequisites

Before starting this tutorial, ensure you've completed the [Installation Guide](installation.md) and verified your setup is working.

## Step 1: List Template Sets

Let's start by listing all available template sets in your MyBB installation:

**In Claude Code, type:**
```
"List MyBB template sets"
```

**Expected Response:**
You should see a list of template sets including:
- Master Templates (sid: -2)
- Global Templates (sid: -1)
- Default Templates (sid: 1 or higher)

**What's Happening:**
Claude Code is calling the `mybb_list_template_sets` MCP tool, which queries your MyBB database and returns formatted results.

## Step 2: View a Template

Now let's view the contents of a specific template:

**In Claude Code, type:**
```
"Show me the header template"
```

**Expected Response:**
You'll see the HTML content of the header template, including:
- Template name and set information
- Full HTML markup
- Variable placeholders like `{$headerinclude}` and `{$menu}`

**What's Happening:**
Claude Code uses the `mybb_read_template` tool to fetch template content from the database. Templates are stored in the `mybb_templates` table.

## Step 3: Create a Simple Plugin

Let's create your first MyBB plugin using natural language:

**In Claude Code, type:**
```
"Create a test plugin called 'my_test'"
```

**Expected Response:**
Claude Code will:
1. Generate plugin scaffolding code
2. Create `TestForum/inc/plugins/my_test.php`
3. Include required plugin functions (`_info()`, `_activate()`, `_deactivate()`, etc.)
4. Show you the generated code

**What's Happening:**
The `mybb_create_plugin` tool uses templates from `mybb_mcp/tools/plugins.py` to generate a complete plugin structure following MyBB conventions.

## Step 4: Explore Available Tools

Now that you've seen basic operations, explore what else is possible:

**In Claude Code, try:**

```
"List all available plugins"
"Show me available hooks for the index page"
"List stylesheets for the default theme"
"What plugins are currently installed?"
```

Each command maps to a specific MCP tool:
- `mybb_list_plugins` - Lists plugin files in `inc/plugins/`
- `mybb_list_hooks` - Shows available hook points
- `mybb_list_stylesheets` - Lists theme stylesheets
- `mybb_plugin_list_installed` - Shows active plugins from cache

## Step 5: Understanding the Workflow

Here's the typical development workflow with MyBB Playground:

### Plugin Development
1. **Create** - "Create a plugin called 'feature_name'"
2. **Edit** - "Add a hook to index_start in my plugin"
3. **Test** - Navigate to `http://localhost:8022` and verify behavior
4. **Iterate** - "Update the plugin to add settings"

### Theme Customization
1. **List** - "Show me all stylesheets for the default theme"
2. **View** - "Show me the global.css stylesheet"
3. **Modify** - "Update the header background color in global.css"
4. **Verify** - Refresh MyBB to see changes

### Template Editing
1. **Explore** - "List templates in the Header Templates group"
2. **Read** - "Show me the header template"
3. **Update** - "Add a welcome message to the header template"
4. **Test** - View changes at `http://localhost:8022`

## What You've Learned

In this tutorial, you've:

- ✅ Listed template sets using MCP tools
- ✅ Viewed template content from the database
- ✅ Created a complete plugin with scaffolding
- ✅ Explored additional MCP tool capabilities
- ✅ Understood the development workflow

## Next Steps

Now that you're familiar with the basics, dive deeper:

1. **[MCP Tools Reference](../mcp_tools/index.md)** - Complete documentation of all 85+ tools
2. **[Plugin Development Guide](../best_practices/plugin_development.md)** - Best practices and patterns
3. **[Template System](../mcp_tools/templates.md)** - Template inheritance and customization
4. **[Plugin Manager](../plugin_manager/index.md)** - Advanced plugin workspace features

## Tips for Success

### Use Natural Language
You don't need to memorize tool names. Claude Code understands:
- "List all templates" → `mybb_list_templates`
- "Create a plugin for adding banners" → `mybb_create_plugin`
- "Show me the footer template" → `mybb_read_template`

### Leverage Context
Claude Code maintains context across requests:
```
"Show me the header template"
"Now update it to add a search box"
"And add a custom CSS class"
```

### Ask for Help
If you're unsure how to do something:
```
"How do I add a setting to my plugin?"
"What hooks are available for the posting process?"
"Show me examples of template variables"
```

### Verify Your Work
Always test changes in your local MyBB installation at `http://localhost:8022` before deploying to production.

## Common Issues

### MCP Tool Not Responding
- Ensure MyBB server is running: `./start_mybb.sh`
- Check database connection in `.env`
- Restart Claude Code to reload MCP configuration

### Plugin Not Appearing
- Plugins are created in `TestForum/inc/plugins/`
- Refresh the Admin CP > Plugins page
- Check file permissions

### Template Changes Not Visible
- Templates are cached by MyBB
- Clear cache in Admin CP > Tools & Maintenance > Cache Manager
- Or modify templates through Admin CP to trigger cache rebuild

## Getting Help

- **CLAUDE.md** - Complete project documentation
- **[Architecture Documentation](../architecture/index.md)** - How the MCP server works
- **[Best Practices](../best_practices/index.md)** - Development guidelines and conventions

Ready to build something amazing with MyBB? Start exploring the [MCP Tools Reference](../mcp_tools/index.md) to see everything that's possible!
