# Plugins

Plugins that ship with MyBB Playground.

## Corta Labs Plugins

| Plugin | Description | Status |
|--------|-------------|--------|
| [Cortex](cortex.md) | Secure template conditionals and expressions | Included (optional) |

## About Plugin Development

For guidance on creating your own MyBB plugins using the Playground toolkit, see:

- [Plugin Manager Documentation](../plugin_manager/index.md)
- [Best Practices: Plugin Development](../best_practices/plugin_development.md)
- [MCP Tools: Plugins](../mcp_tools/plugins.md)

## Installation

All plugins included with MyBB Playground are pre-deployed to the workspace (`plugin_manager/plugins/`). To activate:

1. **Via MCP Tools:**
   ```
   mybb_plugin_install("cortex")
   ```

2. **Via Admin CP:**
   - Navigate to **Admin CP > Plugins**
   - Find the plugin in the list
   - Click **Install** then **Activate**

## Support

For issues or feature requests:
- [GitHub Issues](https://github.com/yourusername/MyBB_Playground/issues)
- [MyBB Community Forums](https://community.mybb.com/)
