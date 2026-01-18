# Configuration

MyBB Playground uses environment variables for all configuration. This document covers all configuration options for the MCP server, disk sync service, and Plugin Manager workspace.

## Configuration Loading

Configuration is loaded via the `load_config()` function in `mybb_mcp/mybb_mcp/config.py`.

### Loading Sequence

```python
# From config.py (lines 34-80):
def load_config(env_path: Path | None = None) -> MyBBConfig:
    # 1. Search for .env file (parent directories if not provided)
    # 2. Load environment variables from .env
    # 3. Parse and validate all variables
    # 4. Return MyBBConfig object
```

**Key Behaviors:**
- `.env` loading searches parent directories if not explicitly provided
- Database password is **MANDATORY** - raises `ConfigurationError` if not set
- MyBB root defaults to `TestForum` in parent directory if not provided
- All integer values parsed with defaults

## Configuration Objects

### MyBBConfig (config.py lines 26-31)

Top-level configuration object:

```python
@dataclass
class MyBBConfig:
    db: DatabaseConfig           # Database configuration object
    mybb_root: Path              # Path to MyBB installation root
    mybb_url: str                # MyBB base URL for links
    port: int                    # Server port (default: 8022)
```

### DatabaseConfig (config.py lines 14-23)

Database connection configuration:

```python
@dataclass
class DatabaseConfig:
    host: str                    # Database hostname (default: "localhost")
    port: int                    # Database port (default: 3306)
    database: str                # Database name (default: "mybb_dev")
    user: str                    # Database user (default: "mybb_user")
    password: str                # Database password (REQUIRED - no default)
    prefix: str                  # Table prefix (default: "mybb_")
    pool_size: int               # Connection pool size (default: 5)
    pool_name: str               # Pool identifier (default: "mybb_pool")
```

### SyncConfig (sync/config.py lines 8-47)

Disk sync service configuration:

```python
@dataclass
class SyncConfig:
    sync_root: Path              # Root directory for disk sync (default: ./mybb_sync)
    auto_upload: bool            # Enable automatic import (default: True)
    cache_token: str             # Token for cache invalidation (default: "")
```

## Environment Variables

### Database Configuration

#### `MYBB_DB_HOST`
- **Type:** String
- **Default:** `localhost`
- **Purpose:** Database server hostname or IP address
- **Example:** `MYBB_DB_HOST=localhost`

#### `MYBB_DB_PORT`
- **Type:** Integer
- **Default:** `3306`
- **Purpose:** Database server port (MySQL/MariaDB)
- **Example:** `MYBB_DB_PORT=3306`

#### `MYBB_DB_NAME`
- **Type:** String
- **Default:** `mybb_dev`
- **Purpose:** Database name for MyBB tables
- **Example:** `MYBB_DB_NAME=mybb_dev`

#### `MYBB_DB_USER`
- **Type:** String
- **Default:** `mybb_user`
- **Purpose:** Database username for authentication
- **Example:** `MYBB_DB_USER=mybb_user`

#### `MYBB_DB_PASS`
- **Type:** String
- **Default:** **REQUIRED (no default)**
- **Purpose:** Database password for authentication
- **Example:** `MYBB_DB_PASS=your_secure_password`
- **⚠️ CRITICAL:** Server fails fast if not set (raises `ConfigurationError`)

#### `MYBB_DB_PREFIX`
- **Type:** String
- **Default:** `mybb_`
- **Purpose:** Table name prefix for MyBB tables
- **Example:** `MYBB_DB_PREFIX=mybb_`
- **Note:** Standard MyBB installation uses `mybb_` prefix

#### `MYBB_DB_POOL_SIZE`
- **Type:** Integer
- **Default:** `5`
- **Purpose:** Database connection pool size
- **Example:** `MYBB_DB_POOL_SIZE=5`
- **Values:**
  - `1` = Single persistent connection (no pooling)
  - `> 1` = Connection pooling enabled
  - Recommended: 5-10 for typical usage

#### `MYBB_DB_POOL_NAME`
- **Type:** String
- **Default:** `mybb_pool`
- **Purpose:** Connection pool identifier (for logging/debugging)
- **Example:** `MYBB_DB_POOL_NAME=mybb_pool`

### MyBB Installation Configuration

#### `MYBB_ROOT`
- **Type:** Path (string)
- **Default:** `{parent_dir}/TestForum` (auto-detected)
- **Purpose:** Absolute path to MyBB installation root directory
- **Example:** `MYBB_ROOT=/home/austin/projects/MyBB_Playground/TestForum`
- **Contains:** `inc/`, `admin/`, `archive/`, plugin files

#### `MYBB_URL`
- **Type:** String (URL)
- **Default:** `http://localhost:8022`
- **Purpose:** Base URL for MyBB installation (for links and cache invalidation)
- **Example:** `MYBB_URL=http://localhost:8022`

#### `MYBB_PORT`
- **Type:** Integer
- **Default:** `8022`
- **Purpose:** Development server port
- **Example:** `MYBB_PORT=8022`
- **Note:** Used by `start_mybb.sh` script

### Disk Sync Configuration

#### `MYBB_SYNC_ROOT`
- **Type:** Path (string)
- **Default:** `./mybb_sync`
- **Purpose:** Root directory for disk sync (templates and stylesheets)
- **Example:** `MYBB_SYNC_ROOT=/home/austin/projects/MyBB_Playground/mybb_sync`
- **Structure:**
  ```
  mybb_sync/
  ├── template_sets/
  │   └── {set_name}/
  │       └── {group_name}/
  │           └── {template_name}.html
  └── styles/
      └── {theme_name}/
          └── {stylesheet_name}.css
  ```

#### `MYBB_AUTO_UPLOAD`
- **Type:** Boolean (string)
- **Default:** `true`
- **Purpose:** Enable automatic import of template/stylesheet changes
- **Example:** `MYBB_AUTO_UPLOAD=true`
- **Accepted Values:**
  - `true`, `1`, `yes` (case-insensitive) → Enabled
  - Anything else → Disabled
- **Behavior:**
  - `true` = FileWatcher monitors `mybb_sync/` and imports changes to DB
  - `false` = FileWatcher disabled, manual export/import only

#### `MYBB_CACHE_TOKEN`
- **Type:** String
- **Default:** `""` (empty string)
- **Purpose:** Token for cache invalidation HTTP requests
- **Example:** `MYBB_CACHE_TOKEN=secret_token_here`
- **Used By:** `CacheRefresher` component for stylesheet cache invalidation

### Plugin Manager Configuration

Plugin Manager has its own `config.py` (not yet fully documented in research).

**Known Configuration Patterns:**
- Workspace root: `plugin_manager/workspace/`
- Plugin visibility: `public/` and `private/` subdirectories
- Theme workspace: `workspace/themes/{visibility}/{codename}/`
- Plugin workspace: `workspace/plugins/{visibility}/{codename}/`

## Example .env File

Complete example configuration for development:

```bash
# Database Configuration (REQUIRED)
MYBB_DB_HOST=localhost
MYBB_DB_PORT=3306
MYBB_DB_NAME=mybb_dev
MYBB_DB_USER=mybb_user
MYBB_DB_PASS=your_secure_password_here
MYBB_DB_PREFIX=mybb_

# Database Connection Pooling (OPTIONAL)
MYBB_DB_POOL_SIZE=5
MYBB_DB_POOL_NAME=mybb_pool

# MyBB Installation (REQUIRED for MCP server)
MYBB_ROOT=/home/austin/projects/MyBB_Playground/TestForum
MYBB_URL=http://localhost:8022
MYBB_PORT=8022

# Disk Sync Configuration (OPTIONAL)
MYBB_SYNC_ROOT=/home/austin/projects/MyBB_Playground/mybb_sync
MYBB_AUTO_UPLOAD=true
MYBB_CACHE_TOKEN=
```

## Configuration Validation

### Required Variables

The following variables **MUST** be set:

- `MYBB_DB_PASS` - Database password (no default, fails if missing)

### Optional Variables with Defaults

All other variables have sensible defaults:

| Variable | Default |
|----------|---------|
| `MYBB_DB_HOST` | `localhost` |
| `MYBB_DB_PORT` | `3306` |
| `MYBB_DB_NAME` | `mybb_dev` |
| `MYBB_DB_USER` | `mybb_user` |
| `MYBB_DB_PREFIX` | `mybb_` |
| `MYBB_DB_POOL_SIZE` | `5` |
| `MYBB_DB_POOL_NAME` | `mybb_pool` |
| `MYBB_ROOT` | `{parent_dir}/TestForum` |
| `MYBB_URL` | `http://localhost:8022` |
| `MYBB_PORT` | `8022` |
| `MYBB_SYNC_ROOT` | `./mybb_sync` |
| `MYBB_AUTO_UPLOAD` | `true` |
| `MYBB_CACHE_TOKEN` | `""` |

### Validation Rules

**Database Password:**
```python
if not password:
    raise ConfigurationError("MYBB_DB_PASS is required")
```

**Integer Parsing:**
```python
port = int(os.getenv('MYBB_DB_PORT', '3306'))
pool_size = int(os.getenv('MYBB_DB_POOL_SIZE', '5'))
```

**Path Resolution:**
```python
# MYBB_ROOT with fallback
mybb_root = os.getenv('MYBB_ROOT')
if not mybb_root:
    mybb_root = Path(__file__).parent.parent / "TestForum"
else:
    mybb_root = Path(mybb_root)
```

**Boolean Parsing:**
```python
# MYBB_AUTO_UPLOAD parsing (case-insensitive)
auto_upload = os.getenv('MYBB_AUTO_UPLOAD', 'true')
auto_upload = auto_upload.lower() in ('true', '1', 'yes')
```

## Configuration by Component

### MCP Server (server.py)

**Used Configuration:**
- `config.db` → Database connection
- `config.mybb_root` → MyBB installation path
- `config.mybb_url` → Base URL for links

**Initialization:**
```python
config = load_config()
db = MyBBDatabase(config.db)
sync_service = DiskSyncService(db, Path(config.mybb_root) / "mybb_sync")
```

### Database Connection (db/connection.py)

**Used Configuration:**
- `DatabaseConfig.host` → MySQL host
- `DatabaseConfig.port` → MySQL port
- `DatabaseConfig.user` → MySQL username
- `DatabaseConfig.password` → MySQL password
- `DatabaseConfig.database` → Database name
- `DatabaseConfig.pool_size` → Connection pool size
- `DatabaseConfig.pool_name` → Pool identifier

**Pool Initialization:**
```python
if config.pool_size > 1:
    self.pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name=config.pool_name,
        pool_size=config.pool_size,
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        database=config.database
    )
```

### Disk Sync Service (sync/service.py)

**Used Configuration:**
- `SyncConfig.sync_root` → Root directory for templates/stylesheets
- `SyncConfig.auto_upload` → Enable file watcher
- `SyncConfig.cache_token` → Cache invalidation token

**Initialization:**
```python
sync_config = SyncConfig.from_env()
service = DiskSyncService(
    db=db,
    sync_root=sync_config.sync_root
)
if sync_config.auto_upload:
    await service.start_watcher()
```

### File Watcher (sync/watcher.py)

**Used Configuration:**
- `sync_root` (from SyncConfig) → Directory to monitor
- `auto_upload` (from SyncConfig) → Whether to start watcher

**Behavior:**
- Monitors `{sync_root}/template_sets/` and `{sync_root}/styles/`
- Only runs if `MYBB_AUTO_UPLOAD=true`
- Debounce window hardcoded (not configurable): 0.5 seconds

### Cache Refresher (sync/cache.py)

**Used Configuration:**
- `cache_token` (from SyncConfig) → Token for cache invalidation requests
- `mybb_url` (from MyBBConfig) → Base URL for HTTP requests

**Behavior:**
- Sends HTTP request to `{mybb_url}/cachecss.php?token={cache_token}`
- Only if `cache_token` is set (optional)

## Security Considerations

### Sensitive Variables

**CRITICAL - Never commit to version control:**
- `MYBB_DB_PASS` - Database password

**Add to .gitignore:**
```gitignore
.env
.env.local
.env.*.local
```

### Default .env Template

Provide a `.env.example` with placeholders:

```bash
# Copy to .env and fill in values
MYBB_DB_HOST=localhost
MYBB_DB_PORT=3306
MYBB_DB_NAME=mybb_dev
MYBB_DB_USER=mybb_user
MYBB_DB_PASS=YOUR_PASSWORD_HERE

MYBB_ROOT=/path/to/MyBB_Playground/TestForum
MYBB_URL=http://localhost:8022
```

### Password Requirements

**Database Password:**
- Required for MCP server to start
- No default value (intentional security measure)
- Server fails immediately if missing (fail-fast principle)

**Cache Token:**
- Optional (empty string default)
- Used to prevent unauthorized cache invalidation
- Recommended for production deployments

## Troubleshooting

### Common Configuration Errors

**Error: "MYBB_DB_PASS is required"**
- **Cause:** Database password not set in `.env`
- **Fix:** Add `MYBB_DB_PASS=your_password` to `.env` file

**Error: "mysql.connector.errors.ProgrammingError: Access denied"**
- **Cause:** Incorrect database credentials
- **Fix:** Verify `MYBB_DB_USER` and `MYBB_DB_PASS` match MySQL user

**Error: "mysql.connector.errors.DatabaseError: Unknown database"**
- **Cause:** Database does not exist
- **Fix:** Create database with `CREATE DATABASE mybb_dev;`

**Error: "FileNotFoundError: mybb_sync directory not found"**
- **Cause:** Sync directory doesn't exist
- **Fix:** Create directory or update `MYBB_SYNC_ROOT` path

### Configuration Debugging

**View Loaded Configuration:**
```python
from mybb_mcp.config import load_config

config = load_config()
print(f"DB Host: {config.db.host}")
print(f"DB Name: {config.db.database}")
print(f"MyBB Root: {config.mybb_root}")
print(f"Pool Size: {config.db.pool_size}")
```

**Test Database Connection:**
```bash
cd mybb_mcp
source .venv/bin/activate
python -c "from mybb_mcp.config import load_config; from mybb_mcp.db import MyBBDatabase; db = MyBBDatabase(load_config().db); print('Connection successful')"
```

**Verify .env File Location:**
```python
from pathlib import Path
from dotenv import find_dotenv

env_path = find_dotenv()
print(f"Loading .env from: {env_path}")
```

## Performance Tuning

### Connection Pool Size

**Guidelines:**
- **Single-threaded**: `MYBB_DB_POOL_SIZE=1` (no pooling overhead)
- **Low concurrency**: `MYBB_DB_POOL_SIZE=3-5` (typical development)
- **High concurrency**: `MYBB_DB_POOL_SIZE=10-20` (production)

**Trade-offs:**
- Larger pool = More concurrent connections, higher memory usage
- Smaller pool = Lower memory usage, potential connection waits

### Database Port

**Standard Ports:**
- MySQL: `3306`
- MariaDB: `3306`
- PostgreSQL: `5432` (not supported)

**Custom Ports:**
- Set `MYBB_DB_PORT` if using non-standard port
- Ensure firewall allows connections

## Further Reading

- [MCP Server Architecture](mcp_server.md) - How configuration is used during server initialization
- [Disk Sync Architecture](disk_sync.md) - SyncConfig usage in FileWatcher and exporters
- [MCP Tools - Settings](/docs/wiki/mcp_tools/settings.md) - Runtime configuration via MyBB settings
- [Best Practices - Development Setup](/docs/wiki/best_practices/development.md) - Recommended configuration for development

---

*Last Updated: 2026-01-18*
*Based on: RESEARCH_MCP_SERVER_ARCHITECTURE_20250118_0811.md (section 1), RESEARCH_DISK_SYNC_SERVICE.md (Finding 6)*
