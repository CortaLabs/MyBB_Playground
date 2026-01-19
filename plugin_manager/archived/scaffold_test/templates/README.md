# Plugin Templates Directory

This directory contains HTML template files for your plugin.

## Naming Convention
- Files should be named `{template_name}.html`
- They will be synced to the database as `scaffold_test_{template_name}`
- Example: `welcome.html` becomes `scaffold_test_welcome` in MyBB

## Workflow
1. Create `.html` files in this directory
2. The db-sync watcher will automatically sync them to the database
3. Templates are stored in MyBB with sid=-2 (master templates)

## Using Templates in Plugin Code
```php
global $templates;
eval("\$template_html = \"" . $templates->get('scaffold_test_welcome') . "\";");
```

For multi-theme support, use `templates_themes/` directory structure.
