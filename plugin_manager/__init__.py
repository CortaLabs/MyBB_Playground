"""Plugin Manager - MyBB plugin/theme workspace management."""

__version__ = "1.0.0"

from .database import ProjectDatabase
from .schema import validate_meta, create_default_meta, META_SCHEMA

__all__ = ["ProjectDatabase", "validate_meta", "create_default_meta", "META_SCHEMA"]
