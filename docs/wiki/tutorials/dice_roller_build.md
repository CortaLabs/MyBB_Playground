# Building a Dice Roller Plugin: A Tutorial

This tutorial documents the development of the `dice_roller` plugin, capturing key learnings about MyBB plugin development.

## What We Built

A BBCode dice rolling system with:
- Syntax: `[roll]2d6[/roll]`, `[roll=Label]1d20+5[/roll]`
- Support for keep-highest: `[roll]4d6k3[/roll]`
- Database tracking of all rolls
- Critical hit (nat 20) and fumble (nat 1) detection
- Styled output with custom CSS
- Post-level visual effects for crits

## Key Learnings

### 1. BBCodes That Execute Once Need Different Hooks

**Problem:** Using `parse_message` to roll dice means the result changes on every page refresh.

**Solution:** Hook into `datahandler_post_insert_post` to process the roll ONCE when the post is saved, then store a reference tag that gets rendered on display.

```php
// WRONG - rolls every page view
$plugins->add_hook('parse_message', 'roll_dice');

// RIGHT - rolls once on post creation
$plugins->add_hook('datahandler_post_insert_post', 'process_rolls_on_insert');
$plugins->add_hook('parse_message', 'render_stored_results');
```

**Flow:**
1. User posts `[roll]2d6[/roll]`
2. `datahandler_post_insert_post` → Roll dice → Save to DB → Replace with `[diceresult=123/]`
3. Post saved with reference tag
4. `parse_message` → Fetch result from DB → Render HTML

### 2. CSS Injection Timing Matters

**Problem:** `global_start` hook runs before `$headerinclude` exists.

**Solution:** Use `global_end` instead.

```php
// WRONG - $headerinclude may not exist yet
$plugins->add_hook('global_start', 'inject_css');

// RIGHT - variables are populated
$plugins->add_hook('global_end', 'inject_css');
```

### 3. Template Newlines Render Literally

**Problem:** Templates with newlines break layout:

```html
<!-- This renders with line breaks between spans -->
<span class="dice-roll">
    <span class="notation">{$notation}</span>
    <span class="total">{$total}</span>
</span>
```

**Solution:** Keep templates single-line:

```html
<span class="dice-roll"><span class="notation">{$notation}</span><span class="total">{$total}</span></span>
```

### 4. MyBB Database Schema Quirks

**Problem:** Some MyBB tables have NOT NULL columns without default values.

**Example:** The `threads` table has a `notes` column that's NOT NULL with no default.

**Solution:** Always check schema before raw SQL inserts:

```sql
SELECT COLUMN_NAME, COLUMN_DEFAULT, IS_NULLABLE
FROM information_schema.COLUMNS
WHERE TABLE_NAME = 'mybb_threads'
```

**Better solution:** Use MyBB's data handlers instead of raw SQL.

### 5. Use Plugin Manager, Not Manual Copies

**Problem:** Manually copying files to TestForum bypasses tracking and lifecycle.

**Solution:** Always use `mybb_plugin_install()`:

```
# WRONG
cp workspace/plugin.php TestForum/inc/plugins/

# RIGHT
mybb_plugin_install("plugin_codename")
```

This ensures:
- File tracking
- PHP lifecycle execution (_install, _activate)
- Proper deployment

### 6. Direct SQL Skips Hooks

**Problem:** MCP tools using direct SQL for content creation bypass plugin hooks.

**Implication:** When testing plugins that hook into `datahandler_post_*`, you must test through the actual web interface, not MCP tools.

**Future improvement:** Route content creation through PHP bridge to trigger hooks.

## Plugin Structure

```
dice_roller/
├── inc/
│   ├── plugins/
│   │   └── dice_roller.php      # Main plugin file
│   └── languages/
│       └── english/
│           └── dice_roller.lang.php
├── meta.json                     # Plugin Manager metadata
└── README.md
```

## Database Schema

```sql
CREATE TABLE mybb_dice_rolls (
    rid INT UNSIGNED AUTO_INCREMENT,
    pid INT UNSIGNED,           -- Post ID
    tid INT UNSIGNED,           -- Thread ID
    uid INT UNSIGNED,           -- User ID
    roll_input VARCHAR(100),    -- "2d6+5"
    roll_label VARCHAR(100),    -- "Attack"
    num_dice TINYINT UNSIGNED,
    num_sides SMALLINT UNSIGNED,
    modifier SMALLINT,
    dice_results VARCHAR(500),  -- JSON: [3, 5]
    total SMALLINT,
    is_crit TINYINT,           -- 1=nat20, -1=nat1, 0=normal
    dateline INT UNSIGNED,
    PRIMARY KEY (rid),
    KEY pid (pid),
    KEY uid (uid)
);
```

## Hook Usage

| Hook | Purpose |
|------|---------|
| `datahandler_post_insert_post` | Process rolls when new post is created |
| `datahandler_post_insert_thread_post` | Process rolls in new thread first post |
| `datahandler_post_update` | Process rolls on post edit |
| `parse_message` | Render stored results to HTML |
| `postbit` | Add CSS classes for crits to post container |
| `global_end` | Inject CSS styles |

## Settings

The plugin creates these settings via `_activate()`:

- `dice_roller_enabled` - Master enable/disable
- `dice_roller_max_dice` - Max dice per roll (default: 100)
- `dice_roller_max_sides` - Max sides per die (default: 1000)
- `dice_roller_crit_effects` - Enable post CSS effects

## Future Enhancements

- User statistics page (luckiest roller, most crits)
- Roll history on profile
- Advantage/disadvantage syntax
- Exploding dice
- Route MCP content creation through PHP bridge for hook testing
