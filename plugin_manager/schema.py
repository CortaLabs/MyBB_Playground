"""meta.json schema validation for plugin/theme projects."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional


# JSON Schema for meta.json validation (supports both plugins and themes)
META_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["codename", "display_name", "version", "author"],
    "properties": {
        # Common fields (both plugins and themes)
        "codename": {
            "type": "string",
            "pattern": "^[a-z][a-z0-9_]*$",
            "description": "Project codename (lowercase, underscores only)"
        },
        "display_name": {
            "type": "string",
            "minLength": 1,
            "description": "Human-readable project name"
        },
        "version": {
            "type": "string",
            "pattern": "^\\d+\\.\\d+\\.\\d+$",
            "description": "Semantic version (e.g., 1.0.0)"
        },
        "author": {
            "type": "string",
            "minLength": 1,
            "description": "Author name"
        },
        "description": {
            "type": "string",
            "description": "Project description"
        },
        "project_type": {
            "type": "string",
            "enum": ["plugin", "theme"],
            "default": "plugin",
            "description": "Project type: 'plugin' or 'theme'"
        },
        "mybb_compatibility": {
            "type": "string",
            "default": "18*",
            "description": "MyBB version compatibility"
        },
        "visibility": {
            "type": "string",
            "enum": ["public", "private"],
            "default": "public",
            "description": "Workspace visibility"
        },

        # Plugin-specific fields
        "hooks": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "handler"],
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "MyBB hook name"
                    },
                    "handler": {
                        "type": "string",
                        "description": "PHP function name to handle hook"
                    },
                    "priority": {
                        "type": "integer",
                        "default": 10,
                        "description": "Hook priority (default: 10)"
                    }
                }
            },
            "description": "MyBB hooks used by this plugin (plugin-specific)"
        },
        "settings": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "title", "type"],
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Setting identifier"
                    },
                    "title": {
                        "type": "string",
                        "description": "Setting display title"
                    },
                    "description": {
                        "type": "string",
                        "description": "Setting description"
                    },
                    "type": {
                        "type": "string",
                        "enum": ["text", "textarea", "yesno", "select", "radio"],
                        "description": "Setting input type"
                    },
                    "default": {
                        "type": "string",
                        "description": "Default value"
                    },
                    "options": {
                        "type": "string",
                        "description": "Options for select/radio (newline-separated)"
                    }
                }
            },
            "description": "Plugin settings/configuration options (plugin-specific)"
        },
        "templates": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Template names used by this plugin (plugin-specific)"
        },

        # Theme-specific fields
        "stylesheets": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Stylesheet filename (e.g., 'custom.css')"
                    },
                    "attached_to": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files to attach stylesheet to (e.g., ['global.php', 'index.php'])"
                    },
                    "display_order": {
                        "type": "integer",
                        "default": 1,
                        "description": "Display order for stylesheet loading"
                    }
                }
            },
            "description": "Stylesheets included in this theme (theme-specific)"
        },
        "template_overrides": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Template names this theme overrides from master (theme-specific)"
        },
        "parent_theme": {
            "type": "string",
            "description": "Parent theme codename for inheritance (theme-specific)"
        },
        "color_scheme": {
            "type": "object",
            "properties": {
                "primary": {"type": "string", "description": "Primary color (hex)"},
                "secondary": {"type": "string", "description": "Secondary color (hex)"},
                "background": {"type": "string", "description": "Background color (hex)"},
                "text": {"type": "string", "description": "Text color (hex)"}
            },
            "description": "Color scheme definition (theme-specific)"
        },

        # File paths (MyBB-compatible structure)
        "files": {
            "type": "object",
            "properties": {
                # Plugin files (mirroring MyBB directory structure)
                "plugin": {
                    "type": "string",
                    "description": "Path to main plugin PHP file (e.g., 'inc/plugins/{codename}.php')"
                },
                "languages": {
                    "type": "string",
                    "description": "Path to language files directory (e.g., 'inc/languages/')"
                },
                # Theme files
                "stylesheets": {
                    "type": "string",
                    "description": "Path to stylesheets directory (theme-specific)"
                },
                # Optional directories
                "jscripts": {
                    "type": "string",
                    "description": "Path to JavaScript files directory (optional)"
                },
                "images": {
                    "type": "string",
                    "description": "Path to images directory (optional)"
                }
            },
            "description": "File paths within the project workspace (mirrors MyBB layout for overlay install)"
        }
    }
}


def validate_meta(meta_dict: Dict[str, Any]) -> tuple[bool, List[str]]:
    """Validate meta.json data against schema.

    Args:
        meta_dict: Parsed meta.json data

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Check required fields
    required = META_SCHEMA["required"]
    for field in required:
        if field not in meta_dict:
            errors.append(f"Missing required field: {field}")

    # Validate codename pattern
    if "codename" in meta_dict:
        import re
        codename = meta_dict["codename"]
        if not isinstance(codename, str):
            errors.append("codename must be a string")
        elif not re.match(r"^[a-z][a-z0-9_]*$", codename):
            errors.append("codename must be lowercase with underscores only (e.g., 'my_plugin')")

    # Validate version pattern
    if "version" in meta_dict:
        import re
        version = meta_dict["version"]
        if not isinstance(version, str):
            errors.append("version must be a string")
        elif not re.match(r"^\d+(\.\d+)*$", version):
            errors.append("version must be numeric (e.g., '1.0' or '1.0.0')")

    # Validate visibility enum
    if "visibility" in meta_dict:
        if meta_dict["visibility"] not in ["public", "private", "forked", "imported"]:
            errors.append("visibility must be 'public', 'private', 'forked', or 'imported'")

    # Validate hooks array structure
    if "hooks" in meta_dict:
        if not isinstance(meta_dict["hooks"], list):
            errors.append("hooks must be an array")
        else:
            for i, hook in enumerate(meta_dict["hooks"]):
                if not isinstance(hook, dict):
                    errors.append(f"hooks[{i}] must be an object")
                    continue
                if "name" not in hook:
                    errors.append(f"hooks[{i}] missing required field: name")
                if "handler" not in hook:
                    errors.append(f"hooks[{i}] missing required field: handler")

    # Validate settings array structure
    if "settings" in meta_dict:
        if not isinstance(meta_dict["settings"], list):
            errors.append("settings must be an array")
        else:
            for i, setting in enumerate(meta_dict["settings"]):
                if not isinstance(setting, dict):
                    errors.append(f"settings[{i}] must be an object")
                    continue
                for req_field in ["name", "title", "type"]:
                    if req_field not in setting:
                        errors.append(f"settings[{i}] missing required field: {req_field}")
                if "type" in setting and setting["type"] not in ["text", "textarea", "yesno", "select", "radio"]:
                    errors.append(f"settings[{i}] has invalid type: {setting['type']}")

    # Validate project_type enum
    if "project_type" in meta_dict:
        if meta_dict["project_type"] not in ["plugin", "theme"]:
            errors.append("project_type must be 'plugin' or 'theme'")

    # Validate stylesheets array structure (theme-specific)
    if "stylesheets" in meta_dict:
        if not isinstance(meta_dict["stylesheets"], list):
            errors.append("stylesheets must be an array")
        else:
            for i, stylesheet in enumerate(meta_dict["stylesheets"]):
                if not isinstance(stylesheet, dict):
                    errors.append(f"stylesheets[{i}] must be an object")
                    continue
                if "name" not in stylesheet:
                    errors.append(f"stylesheets[{i}] missing required field: name")
                if "attached_to" in stylesheet and not isinstance(stylesheet["attached_to"], list):
                    errors.append(f"stylesheets[{i}].attached_to must be an array")

    # Validate template_overrides array (theme-specific)
    if "template_overrides" in meta_dict:
        if not isinstance(meta_dict["template_overrides"], list):
            errors.append("template_overrides must be an array")
        else:
            for i, template in enumerate(meta_dict["template_overrides"]):
                if not isinstance(template, str):
                    errors.append(f"template_overrides[{i}] must be a string")

    return (len(errors) == 0, errors)


def create_default_meta(
    codename: str,
    display_name: str,
    author: str,
    version: str = "1.0.0",
    description: str = "",
    mybb_compatibility: str = "18*",
    visibility: str = "public",
    project_type: str = "plugin"
) -> Dict[str, Any]:
    """Generate default meta.json structure for plugin or theme.

    Args:
        codename: Project codename
        display_name: Human-readable name
        author: Author name
        version: Semantic version
        description: Project description
        mybb_compatibility: MyBB version compatibility
        visibility: 'public' or 'private'
        project_type: 'plugin' or 'theme' (default: 'plugin')

    Returns:
        Dict with default meta.json structure appropriate for project type
    """
    # Common fields for both plugins and themes
    meta = {
        "codename": codename,
        "display_name": display_name,
        "version": version,
        "author": author,
        "description": description,
        "mybb_compatibility": mybb_compatibility,
        "visibility": visibility,
        "project_type": project_type,
    }

    if project_type == "theme":
        # Theme-specific fields
        meta.update({
            "stylesheets": [],
            "template_overrides": [],
            "parent_theme": None,
            "files": {
                "stylesheets": "stylesheets/",
                "images": "images/"
            }
        })
    else:
        # Plugin-specific fields (default)
        # File paths mirror MyBB directory structure for overlay install
        meta.update({
            "hooks": [],
            "settings": [],
            "templates": [],
            "files": {
                "plugin": f"inc/plugins/{codename}.php",
                "languages": "inc/languages/",
                "jscripts": "jscripts/",
                "images": "images/"
            }
        })

    return meta


def create_default_plugin_meta(
    codename: str,
    display_name: str,
    author: str,
    version: str = "1.0.0",
    description: str = "",
    mybb_compatibility: str = "18*",
    visibility: str = "public"
) -> Dict[str, Any]:
    """Generate default plugin meta.json structure (convenience wrapper).

    Args:
        codename: Plugin codename
        display_name: Human-readable name
        author: Author name
        version: Semantic version
        description: Plugin description
        mybb_compatibility: MyBB version compatibility
        visibility: 'public' or 'private'

    Returns:
        Dict with default plugin meta.json structure
    """
    return create_default_meta(
        codename=codename,
        display_name=display_name,
        author=author,
        version=version,
        description=description,
        mybb_compatibility=mybb_compatibility,
        visibility=visibility,
        project_type="plugin"
    )


def create_default_theme_meta(
    codename: str,
    display_name: str,
    author: str,
    version: str = "1.0.0",
    description: str = "",
    mybb_compatibility: str = "18*",
    visibility: str = "public",
    parent_theme: Optional[str] = None
) -> Dict[str, Any]:
    """Generate default theme meta.json structure.

    Args:
        codename: Theme codename
        display_name: Human-readable name
        author: Author name
        version: Semantic version
        description: Theme description
        mybb_compatibility: MyBB version compatibility
        visibility: 'public' or 'private'
        parent_theme: Optional parent theme codename for inheritance

    Returns:
        Dict with default theme meta.json structure
    """
    meta = create_default_meta(
        codename=codename,
        display_name=display_name,
        author=author,
        version=version,
        description=description,
        mybb_compatibility=mybb_compatibility,
        visibility=visibility,
        project_type="theme"
    )
    if parent_theme:
        meta["parent_theme"] = parent_theme
    return meta


def load_meta(path: str | Path) -> tuple[Optional[Dict[str, Any]], List[str]]:
    """Load and validate meta.json from file.

    Args:
        path: Path to meta.json file

    Returns:
        Tuple of (meta_dict or None, list_of_errors)
    """
    path = Path(path)

    if not path.exists():
        return None, [f"File not found: {path}"]

    try:
        with open(path, 'r') as f:
            meta_dict = json.load(f)
    except json.JSONDecodeError as e:
        return None, [f"Invalid JSON: {e}"]
    except Exception as e:
        return None, [f"Error reading file: {e}"]

    is_valid, errors = validate_meta(meta_dict)
    if not is_valid:
        return None, errors

    return meta_dict, []


def save_meta(meta_dict: Dict[str, Any], path: str | Path) -> tuple[bool, List[str]]:
    """Write meta.json to file after validation.

    Args:
        meta_dict: Meta data to write
        path: Path to write meta.json

    Returns:
        Tuple of (success, list_of_errors)
    """
    # Validate before writing
    is_valid, errors = validate_meta(meta_dict)
    if not is_valid:
        return False, errors

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(path, 'w') as f:
            json.dump(meta_dict, f, indent=2)
        return True, []
    except Exception as e:
        return False, [f"Error writing file: {e}"]
