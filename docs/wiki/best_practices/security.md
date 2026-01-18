# Security Best Practices

**Critical security practices for protecting MyBB installations and user data.**

---

## Overview

Security is paramount in forum software. MyBB handles sensitive user data (passwords, emails, IP addresses) and allows user-generated content. Following these security practices prevents common vulnerabilities like SQL injection, CSRF attacks, and data exposure.

**Core Security Principles:**
1. **Never trust user input** - Always validate and sanitize
2. **Defense in depth** - Multiple layers of protection
3. **Least privilege** - Grant minimum necessary permissions
4. **Fail securely** - Errors should not expose sensitive information
5. **Keep secrets secret** - Never expose credentials or tokens

---

## Input Validation

### User Input Handling

**CRITICAL:** Never use raw `$_POST`, `$_GET`, or `$_COOKIE` data directly.

**Use MyBB's Input Sanitization:**

```php
global $mybb;

// Get string input (default)
$username = $mybb->get_input('username', MyBB::INPUT_STRING);

// Get integer input (sanitized)
$user_id = $mybb->get_input('uid', MyBB::INPUT_INT);

// Get array input
$selected_items = $mybb->get_input('items', MyBB::INPUT_ARRAY);

// Get boolean input
$enabled = $mybb->get_input('enabled', MyBB::INPUT_BOOL);
```

**Input Types:**
- `MyBB::INPUT_STRING` - Strips tags, sanitizes HTML
- `MyBB::INPUT_INT` - Casts to integer
- `MyBB::INPUT_BOOL` - Converts to boolean
- `MyBB::INPUT_ARRAY` - Expects array

### Validation Patterns

**Email Validation:**
```php
if (!validate_email_format($email)) {
    error("Invalid email address");
}
```

**Username Validation:**
```php
if (strlen($username) < 3 || strlen($username) > 30) {
    error("Username must be 3-30 characters");
}

if (!preg_match("/^[a-zA-Z0-9_]+$/", $username)) {
    error("Username can only contain letters, numbers, and underscores");
}
```

**URL Validation:**
```php
if (!filter_var($url, FILTER_VALIDATE_URL)) {
    error("Invalid URL format");
}
```

### File Upload Validation

**CRITICAL:** Validate file uploads rigorously:

```php
$allowed_types = array('image/jpeg', 'image/png', 'image/gif');
$max_size = 2 * 1024 * 1024; // 2 MB

if (!in_array($_FILES['upload']['type'], $allowed_types)) {
    error("Invalid file type");
}

if ($_FILES['upload']['size'] > $max_size) {
    error("File too large");
}

// Validate actual file content (not just extension)
$image_info = getimagesize($_FILES['upload']['tmp_name']);
if ($image_info === false) {
    error("Not a valid image file");
}

// Generate safe filename
$safe_filename = preg_replace('/[^a-zA-Z0-9_.-]/', '', basename($_FILES['upload']['name']));
```

---

## CSRF Protection

### What is CSRF?

**Cross-Site Request Forgery (CSRF):** An attack where a malicious site tricks a user's browser into performing unwanted actions on a site where the user is authenticated.

**Example Attack:**
```html
<!-- Malicious site includes this image -->
<img src="https://forum.example.com/admin.php?action=delete_user&uid=1" />
```

If admin is logged in, their browser sends cookies automatically → user deleted.

### MyBB's CSRF Protection

MyBB uses **POST tokens** to verify requests originate from legitimate forms.

#### In Templates

**Add token to forms:**

```html
<form action="action.php" method="post">
    <input type="hidden" name="my_post_key" value="{$mybb->post_code}" />
    <!-- Form fields -->
    <input type="submit" value="Submit" />
</form>
```

**Variable:** `{$mybb->post_code}` generates unique token per user session.

#### In Plugin Handlers

**Verify token in POST handlers:**

```php
function myplugin_form_handler()
{
    global $mybb;

    if ($mybb->request_method == "post") {
        // REQUIRED: Verify CSRF token
        verify_post_check($mybb->get_input('my_post_key'));

        // Token valid - process form
        $data = $mybb->get_input('data');
        // ... rest of handler logic
    }
}
```

**What verify_post_check() does:**
1. Compares submitted token with user's session token
2. If mismatch → displays error and halts execution
3. If match → continues execution

### CSRF Protection Checklist

- [ ] All forms include `{$mybb->post_code}` hidden input
- [ ] All POST handlers call `verify_post_check()`
- [ ] No state-changing operations via GET requests
- [ ] Admin actions require POST + CSRF verification
- [ ] AJAX requests include CSRF token

### AJAX CSRF Protection

For AJAX requests, include token in request:

```javascript
$.ajax({
    url: 'action.php',
    method: 'POST',
    data: {
        my_post_key: '{$mybb->post_code}',
        action: 'update',
        data: 'value'
    }
});
```

Then verify in handler:

```php
verify_post_check($mybb->get_input('my_post_key'));
```

---

## SQL Injection Prevention

### What is SQL Injection?

**SQL Injection:** An attack where malicious SQL code is inserted into queries via user input.

**Example Vulnerable Code:**

```php
// WRONG - SQL injection vulnerability
$username = $_POST['username'];
$query = "SELECT * FROM users WHERE username = '{$username}'";
```

**Attack:** User submits `username = "admin' OR '1'='1"` → query becomes:

```sql
SELECT * FROM users WHERE username = 'admin' OR '1'='1'
```

This returns all users (bypassing authentication).

### Secure Query Patterns

#### Method 1: Parameterized Queries (Preferred)

**Use placeholders (`?`) with bind parameters:**

```php
global $db;

$query = $db->simple_select(
    "users",
    "uid, username, email",
    "username = ?",
    array('bind' => array($username))
);
```

MyBB handles escaping automatically.

#### Method 2: Database Escaping (Fallback)

**Use `escape_string()` for all user input:**

```php
global $db;

$username = $db->escape_string($mybb->get_input('username'));
$query = $db->simple_select(
    "users",
    "uid, username, email",
    "username = '{$username}'"
);
```

**CRITICAL:** Wrap escaped values in quotes: `'{$escaped_value}'`

#### Method 3: Type Casting for Integers

**Cast integers explicitly:**

```php
$uid = (int)$mybb->get_input('uid');
$query = $db->simple_select("users", "*", "uid = {$uid}");
```

No quotes needed for integers.

### SQL Injection Prevention Checklist

- [ ] All string input uses `$db->escape_string()` or parameterized queries
- [ ] Integer input cast with `(int)$value`
- [ ] No direct concatenation of user input into SQL
- [ ] LIKE clauses escape wildcards: `$db->escape_string_like($value)`
- [ ] Dynamic table/column names validated against whitelist

### Escaping LIKE Queries

**LIKE queries need special escaping:**

```php
$search = $db->escape_string_like($mybb->get_input('search'));
$query = $db->simple_select(
    "posts",
    "*",
    "message LIKE '%{$search}%'"
);
```

`escape_string_like()` escapes `%` and `_` wildcards in addition to SQL special characters.

### Dynamic Identifiers

**If table/column names come from user input, validate against whitelist:**

```php
$allowed_columns = array('username', 'email', 'postcount');
$sort_by = $mybb->get_input('sort');

if (!in_array($sort_by, $allowed_columns)) {
    $sort_by = 'username'; // Default safe value
}

$query = $db->simple_select("users", "*", "", array('order_by' => $sort_by));
```

**NEVER escape and use directly** - table/column names cannot be parameterized or quoted.

---

## Sensitive Data Handling

### Password Security

**NEVER expose passwords or password hashes:**

```php
// CORRECT: Exclude password fields
$query = $db->simple_select(
    "users",
    "uid, username, email, usergroup",  // No password, salt, loginkey
    "uid = " . (int)$uid
);

// WRONG: Exposing sensitive fields
$query = $db->simple_select(
    "users",
    "*",  // Includes password, salt, loginkey - NEVER DO THIS
    "uid = " . (int)$uid
);
```

**Sensitive User Fields to Exclude:**
- `password` - Password hash
- `salt` - Password salt
- `loginkey` - Auto-login token
- `regip` - Registration IP address
- `lastip` - Last login IP address
- `coppauser` - COPPA status (privacy)

### Database Credentials

**NEVER hardcode credentials in code:**

```php
// WRONG: Hardcoded credentials
$db_host = "localhost";
$db_pass = "mypassword123";

// CORRECT: Load from environment
$config = load_config();
$db_host = $config->db['host'];
$db_pass = $config->db['password'];  // From .env file
```

**MyBB Playground uses .env for credentials:**

```env
MYBB_DB_HOST=localhost
MYBB_DB_NAME=mybb_dev
MYBB_DB_USER=mybb_user
MYBB_DB_PASS=<password>
```

`.env` files are gitignored - never commit credentials to version control.

### API Keys and Tokens

**Store sensitive tokens securely:**

```php
// Store in MyBB settings (encrypted in DB)
$db->insert_query("settings", array(
    'name' => 'myplugin_api_key',
    'value' => $api_key,
    'optionscode' => 'text'
));

// Access via settings
global $mybb;
$api_key = $mybb->settings['myplugin_api_key'];
```

**Environment Variables (Preferred):**

```php
// In config.py or equivalent
$api_key = getenv('MYPLUGIN_API_KEY');

if (!$api_key) {
    throw new Exception("API key not configured");
}
```

### Session Security

**Validate sessions properly:**

```php
// Check user is logged in
if (!$mybb->user['uid']) {
    error_no_permission();
}

// Check user has permission
if (!is_member($mybb->settings['myplugin_allowed_groups'])) {
    error_no_permission();
}

// Regenerate session on privilege escalation
if ($action == 'become_admin') {
    my_setcookie('sid', '', -1);  // Invalidate old session
    // Create new session with elevated privileges
}
```

### Logging Sensitive Operations

**Log security events without exposing data:**

```php
// CORRECT: Log action without sensitive data
log_moderator_action(array(
    'tid' => $tid,
    'uid' => $uid,
    'action' => 'Password reset requested'
));

// WRONG: Logging sensitive data
log_moderator_action(array(
    'action' => 'Password reset',
    'new_password' => $password  // NEVER LOG PASSWORDS
));
```

---

## MyBB MCP Security Measures

### Database Access Restrictions

**MCP tools enforce read-only database access:**

- `mybb_db_query` - Only accepts SELECT queries
- No INSERT, UPDATE, DELETE, DROP via direct query tool
- All modifications go through typed methods with validation

### User Data Protection

**User query tools exclude sensitive fields automatically:**

```python
# CORRECT: Sensitive fields excluded in MCP implementation
EXCLUDED_FIELDS = ['password', 'salt', 'loginkey', 'regip', 'lastip']

def get_user(uid):
    query = f"SELECT uid, username, email FROM users WHERE uid = {uid}"
    # password, salt, loginkey automatically excluded
```

### Configuration Security

**Environment-based configuration prevents credential exposure:**

- Database credentials in `.env` (gitignored)
- `MYBB_DB_PASS` required - fails fast if missing
- No credentials in code or version control

---

## Common Vulnerabilities

### XSS (Cross-Site Scripting)

**Vulnerability:** User input rendered as HTML allows script injection.

**Prevention:**

```php
// Escape output in templates
echo htmlspecialchars($user_input, ENT_QUOTES, 'UTF-8');

// In templates
{htmlspecialchars($variable)}
```

### Path Traversal

**Vulnerability:** User controls file paths, accesses unauthorized files.

**Prevention:**

```php
$allowed_dir = "/var/www/mybb/uploads/";
$filename = basename($_GET['file']);  // Strip directory components

$filepath = $allowed_dir . $filename;

// Validate resolved path is within allowed directory
$real_path = realpath($filepath);
if (strpos($real_path, $allowed_dir) !== 0) {
    error("Invalid file path");
}
```

### Session Fixation

**Vulnerability:** Attacker sets user's session ID, hijacks session after login.

**Prevention:**

```php
// Regenerate session ID on login
session_regenerate_id(true);

// MyBB handles this automatically in login process
```

### Command Injection

**Vulnerability:** User input passed to shell commands.

**Prevention:**

```php
// WRONG: Direct shell execution with user input
$output = shell_exec("ls " . $_GET['directory']);

// CORRECT: Validate input or avoid shell entirely
$allowed_dirs = array('uploads', 'cache', 'logs');
$dir = $_GET['directory'];

if (!in_array($dir, $allowed_dirs)) {
    error("Invalid directory");
}

$output = shell_exec("ls " . escapeshellarg($dir));
```

---

## Security Checklist

### Input Validation
- [ ] All user input sanitized via `$mybb->get_input()`
- [ ] Email addresses validated with `validate_email_format()`
- [ ] URLs validated with `filter_var(FILTER_VALIDATE_URL)`
- [ ] File uploads validated (type, size, content)
- [ ] Filenames sanitized before use

### CSRF Protection
- [ ] All forms include `{$mybb->post_code}`
- [ ] All POST handlers call `verify_post_check()`
- [ ] No state changes via GET requests
- [ ] AJAX requests include CSRF token

### SQL Injection Prevention
- [ ] All string input uses `$db->escape_string()` or parameterized queries
- [ ] Integer input cast with `(int)$value`
- [ ] LIKE queries use `$db->escape_string_like()`
- [ ] No direct SQL concatenation with user input

### Sensitive Data Protection
- [ ] Password/salt/loginkey excluded from queries
- [ ] IP addresses not exposed in public output
- [ ] Database credentials in `.env`, not code
- [ ] API keys stored securely (settings or environment)
- [ ] Sessions validated and regenerated on privilege changes

### General Security
- [ ] XSS prevention: `htmlspecialchars()` on output
- [ ] Path validation: `realpath()` and directory checks
- [ ] Permission checks before sensitive operations
- [ ] Error messages don't expose sensitive information
- [ ] Security events logged without sensitive data

---

## Security Resources

### MyBB Security
- [MyBB Security Documentation](https://docs.mybb.com/1.8/development/security/)
- [MyBB Database Methods](https://docs.mybb.com/1.8/development/database-methods/)

### General Security
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [OWASP CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)

### MyBB Playground
- [Plugin Development Guide](plugin_development.md) - Secure plugin patterns
- [MCP Tools Reference](../mcp_tools/index.md) - Security features in MCP tools
- [Architecture Guide](../architecture/index.md) - Security architecture

---

## Reporting Security Issues

**If you discover a security vulnerability:**

1. **DO NOT** disclose publicly
2. **DO NOT** commit fixes to public repositories
3. **DO** report to MyBB security team: security@mybb.com
4. **DO** include detailed reproduction steps
5. **DO** wait for patch before public disclosure

**For MyBB Playground specific issues:**
- Report via project issues with "Security" label
- Or contact project maintainer directly

---

**Last Updated:** 2026-01-18
