#!/usr/bin/env python
"""Verify meta.json format matches schema requirements."""

import json
from pathlib import Path
from plugin_manager.schema import validate_meta

# Test plugin meta with hooks
plugin_meta = {
    "codename": "test_plugin",
    "display_name": "Test Plugin",
    "version": "1.0.0",
    "author": "Test",
    "hooks": [
        {"name": "index_start", "handler": "test_plugin_index_start", "priority": 10}
    ],
    "settings": [
        {"name": "test_enabled", "title": "Enable Test", "type": "yesno", "default": "1"}
    ]
}

# Test theme meta with stylesheets
theme_meta = {
    "codename": "test_theme",
    "display_name": "Test Theme",
    "version": "1.0.0",
    "author": "Test",
    "project_type": "theme",
    "stylesheets": [
        {"name": "global.css", "attached_to": ["global"]}
    ]
}

print("=== PLUGIN META VALIDATION ===")
is_valid, errors = validate_meta(plugin_meta)
print(f"Valid: {is_valid}")
if errors:
    print("Errors:", errors)
else:
    print("✓ Hooks format correct:", json.dumps(plugin_meta["hooks"], indent=2))
    print("✓ Settings format correct:", json.dumps(plugin_meta["settings"], indent=2))

print("\n=== THEME META VALIDATION ===")
is_valid, errors = validate_meta(theme_meta)
print(f"Valid: {is_valid}")
if errors:
    print("Errors:", errors)
else:
    print("✓ Stylesheets format correct:", json.dumps(theme_meta["stylesheets"], indent=2))
