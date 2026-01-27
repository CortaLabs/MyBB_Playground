<?php
/**
 * Security policy for template expression validation.
 *
 * This class enforces strict security boundaries by maintaining
 * a whitelist of allowed functions and detecting forbidden patterns
 * that could lead to code injection or other security vulnerabilities.
 *
 * @package Cortex
 * @author Corta Labs
 * @license MIT
 */

declare(strict_types=1);

namespace Cortex;

use Cortex\Exceptions\SecurityException;

/**
 * Security policy with function whitelist and pattern blacklist.
 *
 * All function calls in templates must be explicitly whitelisted.
 * All expressions are scanned for forbidden patterns before execution.
 */
class SecurityPolicy
{
    /**
     * Whitelisted functions organized by category.
     *
     * SECURITY CRITICAL: Only functions with no side effects or
     * read-only operations should be in this list.
     *
     * Total: ~99 functions
     */
    private const ALLOWED_FUNCTIONS = [
        // ============================================================
        // STRING MANIPULATION (safe, no side effects)
        // ============================================================
        'htmlspecialchars',     // HTML entity encoding
        'htmlentities',         // Full HTML entity encoding
        'html_entity_decode',   // Decode HTML entities
        'addslashes',           // Add backslashes
        'stripslashes',         // Remove backslashes
        'trim',                 // Strip whitespace from both ends
        'ltrim',                // Strip whitespace from start
        'rtrim',                // Strip whitespace from end
        'chop',                 // Alias for rtrim
        'nl2br',                // Insert <br> at newlines
        'strrev',               // Reverse a string
        'strtoupper',           // Convert to uppercase
        'strtolower',           // Convert to lowercase
        'ucfirst',              // Uppercase first character
        'ucwords',              // Uppercase first char of each word
        'lcfirst',              // Lowercase first character
        'strip_tags',           // Remove HTML tags
        'str_rot13',            // ROT13 encoding
        'str_shuffle',          // Shuffle string characters
        'str_repeat',           // Repeat a string
        'str_pad',              // Pad a string
        'str_replace',          // Replace occurrences
        'str_ireplace',         // Case-insensitive replace
        'substr',               // Extract substring
        'substr_replace',       // Replace part of string
        'strlen',               // Get string length
        'strpos',               // Find position of first occurrence
        'stripos',              // Case-insensitive strpos
        'strrpos',              // Find position of last occurrence
        'strripos',             // Case-insensitive strrpos
        'strstr',               // Find first occurrence
        'stristr',              // Case-insensitive strstr
        'strchr',               // Alias for strstr
        'strrchr',              // Find last occurrence of char
        'strcmp',               // Binary-safe string comparison
        'strcasecmp',           // Case-insensitive comparison
        'strncmp',              // Compare first n characters
        'strncasecmp',          // Case-insensitive strncmp
        'strnatcmp',            // Natural order comparison
        'strnatcasecmp',        // Case-insensitive natural comparison
        'substr_count',         // Count occurrences
        'str_word_count',       // Count words
        'wordwrap',             // Wrap text
        'number_format',        // Format number with grouping
        'money_format',         // Format as currency (deprecated but safe)
        'sprintf',              // Format string
        'vsprintf',             // Format string with array args
        'printf',               // Output formatted string - EXCLUDED (output)
        'sscanf',               // Parse string by format
        'chr',                  // Get character from ASCII
        'ord',                  // Get ASCII from character
        'chunk_split',          // Split string into chunks
        'convert_uuencode',     // Uuencode a string
        'convert_uudecode',     // Uudecode a string
        'quoted_printable_encode', // Quoted-printable encode
        'quoted_printable_decode', // Quoted-printable decode
        'quotemeta',            // Quote meta characters
        'preg_quote',           // Quote regex special chars

        // ============================================================
        // MYBB-SPECIFIC FUNCTIONS (safe MyBB utilities)
        // ============================================================
        'htmlspecialchars_uni', // MyBB's unicode-safe htmlspecialchars
        'my_strtoupper',        // MyBB's multibyte-safe strtoupper
        'my_strtolower',        // MyBB's multibyte-safe strtolower
        'my_strlen',            // MyBB's multibyte-safe strlen
        'my_wordwrap',          // MyBB's word wrap function
        'my_substr',            // MyBB's multibyte-safe substr
        'my_strpos',            // MyBB's multibyte-safe strpos
        'my_stripos',           // MyBB's multibyte-safe stripos
        'my_strtoupper',        // MyBB's multibyte-safe strtoupper
        'my_number_format',     // MyBB's number formatting
        'my_date',              // MyBB's date formatting
        'alt_trow',             // MyBB's alternating table row
        'get_friendly_size',    // Format file size
        'random_str',           // Generate random string (read-only)
        'unicode_chr',          // Get unicode character
        'unhtmlentities',       // MyBB's entity decode
        'get_colored_warning_level', // MyBB's warning level color

        // ============================================================
        // NUMERIC FUNCTIONS (safe, pure math)
        // ============================================================
        'intval',               // Convert to integer
        'floatval',             // Convert to float
        'doubleval',            // Alias for floatval
        'abs',                  // Absolute value
        'round',                // Round a number
        'floor',                // Round down
        'ceil',                 // Round up
        'min',                  // Find minimum
        'max',                  // Find maximum
        'pow',                  // Exponential
        'sqrt',                 // Square root
        'log',                  // Natural logarithm
        'log10',                // Base-10 logarithm
        'exp',                  // e to the power of
        'fmod',                 // Float modulo
        'number_format',        // Format with thousands separator

        // ============================================================
        // HASH AND ENCODING (safe, no I/O)
        // ============================================================
        'urlencode',            // URL encode
        'urldecode',            // URL decode
        'rawurlencode',         // RFC 3986 URL encode
        'rawurldecode',         // RFC 3986 URL decode
        'base64_encode',        // Base64 encode
        'base64_decode',        // Base64 decode
        'md5',                  // MD5 hash
        'sha1',                 // SHA1 hash
        'crc32',                // CRC32 checksum
        'bin2hex',              // Binary to hex
        'hex2bin',              // Hex to binary
        'json_encode',          // Encode to JSON
        'json_decode',          // Decode from JSON
        'http_build_query',     // Build query string

        // ============================================================
        // PATH FUNCTIONS (read-only, no file operations)
        // ============================================================
        'basename',             // Get filename from path
        'dirname',              // Get directory from path
        'pathinfo',             // Get path information

        // ============================================================
        // ARRAY FUNCTIONS (safe, no callbacks unless whitelisted)
        // ============================================================
        'count',                // Count elements
        'sizeof',               // Alias for count
        'in_array',             // Check if value in array
        'array_key_exists',     // Check if key exists
        'array_keys',           // Get all keys
        'array_values',         // Get all values
        'array_unique',         // Remove duplicates
        'array_reverse',        // Reverse array
        'array_flip',           // Flip keys and values
        'array_merge',          // Merge arrays
        'array_slice',          // Extract slice
        'array_splice',         // Remove/replace portion (in-place but safe)
        'array_search',         // Search for value
        'array_sum',            // Sum all values
        'array_product',        // Product of all values
        'array_pop',            // Pop last element
        'array_shift',          // Shift first element
        'array_push',           // Push element
        'array_unshift',        // Prepend element
        'array_rand',           // Pick random key
        'array_column',         // Get column from multi-dimensional
        'array_combine',        // Combine two arrays
        'array_chunk',          // Split into chunks
        'array_fill',           // Fill array with value
        'array_pad',            // Pad array
        'implode',              // Join array to string
        'join',                 // Alias for implode
        'explode',              // Split string to array
        'range',                // Create array of range
        'sort',                 // Sort array
        'rsort',                // Reverse sort
        'asort',                // Sort maintaining keys
        'arsort',               // Reverse sort maintaining keys
        'ksort',                // Sort by key
        'krsort',               // Reverse sort by key
        'natsort',              // Natural sort
        'natcasesort',          // Case-insensitive natural sort

        // ============================================================
        // TYPE CHECKING (safe, read-only)
        // ============================================================
        'is_array',             // Check if array
        'is_string',            // Check if string
        'is_int',               // Check if integer
        'is_integer',           // Alias for is_int
        'is_long',              // Alias for is_int
        'is_float',             // Check if float
        'is_double',            // Alias for is_float
        'is_real',              // Alias for is_float
        'is_numeric',           // Check if numeric
        'is_bool',              // Check if boolean
        'is_null',              // Check if null
        'is_object',            // Check if object
        'is_scalar',            // Check if scalar
        'isset',                // Check if set (language construct)
        'empty',                // Check if empty (language construct)
        'gettype',              // Get type name
        'boolval',              // Get boolean value
        'strval',               // Get string value

        // ============================================================
        // DATE AND TIME (safe, read-only)
        // ============================================================
        'date',                 // Format date
        'time',                 // Get current timestamp
        'strtotime',            // Parse date string to timestamp
        'mktime',               // Create timestamp
        'gmdate',               // Format as GMT
        'gmmktime',             // GMT mktime
        'strftime',             // Format by locale (deprecated but safe)
        'gmstrftime',           // GMT strftime
        'idate',                // Integer date format
        'getdate',              // Get date info
        'localtime',            // Get local time
        'microtime',            // Get microseconds
        'gettimeofday',         // Get time of day
        'checkdate',            // Validate date
        'date_diff',            // Calculate difference
        'date_format',          // Format DateTime object
        'date_create',          // Create DateTime object
    ];

    /**
     * Forbidden patterns that indicate security risks.
     *
     * Each pattern is documented with the attack vector it prevents.
     *
     * Total: 31 categories
     */
    private const FORBIDDEN_PATTERNS = [
        // ============================================================
        // 1. CODE EXECUTION
        // ============================================================
        '/\beval\s*\(/i' => 'eval() code execution',
        '/\bassert\s*\(/i' => 'assert() code execution',
        '/\bcreate_function\s*\(/i' => 'create_function() code execution',

        // ============================================================
        // 2. SHELL EXECUTION
        // ============================================================
        '/\bexec\s*\(/i' => 'exec() shell command',
        '/\bsystem\s*\(/i' => 'system() shell command',
        '/\bshell_exec\s*\(/i' => 'shell_exec() shell command',
        '/\bpassthru\s*\(/i' => 'passthru() shell command',
        '/\bpopen\s*\(/i' => 'popen() process opening',
        '/\bproc_open\s*\(/i' => 'proc_open() process opening',
        '/\bpcntl_exec\s*\(/i' => 'pcntl_exec() process execution',

        // ============================================================
        // 3. FILE OPERATIONS
        // ============================================================
        '/\bfile_get_contents\s*\(/i' => 'file_get_contents() file reading',
        '/\bfile_put_contents\s*\(/i' => 'file_put_contents() file writing',
        '/\bfopen\s*\(/i' => 'fopen() file opening',
        '/\bfread\s*\(/i' => 'fread() file reading',
        '/\bfwrite\s*\(/i' => 'fwrite() file writing',
        '/\bfputs\s*\(/i' => 'fputs() file writing',
        '/\bfclose\s*\(/i' => 'fclose() file closing',
        '/\bunlink\s*\(/i' => 'unlink() file deletion',
        '/\brmdir\s*\(/i' => 'rmdir() directory deletion',
        '/\bmkdir\s*\(/i' => 'mkdir() directory creation',
        '/\brename\s*\(/i' => 'rename() file renaming',
        '/\bcopy\s*\(/i' => 'copy() file copying',
        '/\bfile\s*\(/i' => 'file() file reading',
        '/\bglob\s*\(/i' => 'glob() directory scanning',
        '/\breadfile\s*\(/i' => 'readfile() file output',
        '/\bscandir\s*\(/i' => 'scandir() directory listing',
        '/\bopendir\s*\(/i' => 'opendir() directory opening',
        '/\breaddir\s*\(/i' => 'readdir() directory reading',
        '/\bfgetc\s*\(/i' => 'fgetc() file reading',
        '/\bfgets\s*\(/i' => 'fgets() file reading',
        '/\bfgetcsv\s*\(/i' => 'fgetcsv() file reading',

        // ============================================================
        // 4. INCLUDE/REQUIRE STATEMENTS
        // ============================================================
        '/\binclude\s*[\(\s]/i' => 'include statement',
        '/\binclude_once\s*[\(\s]/i' => 'include_once statement',
        '/\brequire\s*[\(\s]/i' => 'require statement',
        '/\brequire_once\s*[\(\s]/i' => 'require_once statement',

        // ============================================================
        // 5. DYNAMIC FUNCTION CALLS
        // ============================================================
        '/\bcall_user_func\s*\(/i' => 'call_user_func() dynamic execution',
        '/\bcall_user_func_array\s*\(/i' => 'call_user_func_array() dynamic execution',
        '/\bforward_static_call\s*\(/i' => 'forward_static_call() dynamic execution',
        '/\bforward_static_call_array\s*\(/i' => 'forward_static_call_array() dynamic execution',
        '/\$[a-zA-Z_][a-zA-Z0-9_]*\s*\(/i' => 'variable function call',

        // ============================================================
        // 6. VARIABLE VARIABLES
        // ============================================================
        '/\$\$[a-zA-Z_]/i' => 'variable variable ($$var)',
        '/\$\{[^}]*\$[^}]*\}/i' => 'variable variable (${$var})',

        // ============================================================
        // 7. BACKTICK EXECUTION
        // ============================================================
        '/`[^`]*`/' => 'backtick shell execution',

        // ============================================================
        // 8. NULL BYTE INJECTION
        // ============================================================
        '/\\x00/' => 'null byte injection',
        '/\\0/' => 'null byte injection (octal)',
        '/\%00/' => 'null byte injection (URL encoded)',

        // ============================================================
        // 9. OUTPUT BUFFERING (can intercept output)
        // ============================================================
        '/\bob_start\s*\(/i' => 'output buffering start',
        '/\bob_get_contents\s*\(/i' => 'output buffering read',
        '/\bob_end_clean\s*\(/i' => 'output buffering end',
        '/\bob_end_flush\s*\(/i' => 'output buffering flush',

        // ============================================================
        // 10. SERIALIZATION (deserialization attacks)
        // ============================================================
        '/\bunserialize\s*\(/i' => 'unserialize() deserialization',
        '/\bserialize\s*\(/i' => 'serialize() serialization',

        // ============================================================
        // 11. STREAM WRAPPERS
        // ============================================================
        '/php:\/\//i' => 'php:// stream wrapper',
        '/data:\/\//i' => 'data:// stream wrapper',
        '/expect:\/\//i' => 'expect:// stream wrapper',
        '/phar:\/\//i' => 'phar:// stream wrapper',
        '/zip:\/\//i' => 'zip:// stream wrapper',
        '/compress\.zlib:\/\//i' => 'compress.zlib:// stream wrapper',

        // ============================================================
        // 12. PROCESS CONTROL
        // ============================================================
        '/\bpcntl_/i' => 'pcntl_* process control',
        '/\bposix_/i' => 'posix_* functions',

        // ============================================================
        // 13. SOCKET OPERATIONS
        // ============================================================
        '/\bsocket_/i' => 'socket_* functions',
        '/\bfsockopen\s*\(/i' => 'fsockopen() socket opening',
        '/\bpfsockopen\s*\(/i' => 'pfsockopen() persistent socket',
        '/\bstream_socket_/i' => 'stream_socket_* functions',

        // ============================================================
        // 14. CURL OPERATIONS
        // ============================================================
        '/\bcurl_/i' => 'curl_* functions',

        // ============================================================
        // 15. DATABASE DIRECT ACCESS
        // ============================================================
        '/\bmysqli?_/i' => 'mysql/mysqli_* direct database access',
        '/\bpg_/i' => 'pg_* PostgreSQL access',
        '/\bsqlite_/i' => 'sqlite_* SQLite access',
        '/\boci_/i' => 'oci_* Oracle access',
        '/\bmssql_/i' => 'mssql_* SQL Server access',
        '/\bdb2_/i' => 'db2_* DB2 access',

        // ============================================================
        // 16. PREG_REPLACE WITH E MODIFIER
        // ============================================================
        '/preg_replace\s*\([^)]*\/[^)]*e[^)]*\)/i' => 'preg_replace with /e modifier',

        // ============================================================
        // 17. MAIL FUNCTION
        // ============================================================
        '/\bmail\s*\(/i' => 'mail() function',

        // ============================================================
        // 18. HEADER MANIPULATION
        // ============================================================
        '/\bheader\s*\(/i' => 'header() HTTP header manipulation',
        '/\bheader_remove\s*\(/i' => 'header_remove() HTTP header removal',
        '/\bsetcookie\s*\(/i' => 'setcookie() cookie manipulation',
        '/\bsetrawcookie\s*\(/i' => 'setrawcookie() cookie manipulation',

        // ============================================================
        // 19. SESSION MANIPULATION
        // ============================================================
        '/\bsession_/i' => 'session_* manipulation',
        '/\b\$_SESSION\b/' => '$_SESSION superglobal access',
        '/\b\$_COOKIE\b/' => '$_COOKIE superglobal access',
        '/\b\$_REQUEST\b/' => '$_REQUEST superglobal access',
        '/\b\$_POST\b/' => '$_POST superglobal access',
        '/\b\$_GET\b/' => '$_GET superglobal access',
        '/\b\$_FILES\b/' => '$_FILES superglobal access',
        '/\b\$_ENV\b/' => '$_ENV superglobal access',
        '/\b\$_SERVER\b/' => '$_SERVER superglobal access',
        '/\b\$GLOBALS\[/' => '$GLOBALS array access',

        // ============================================================
        // 20. EXIT/DIE
        // ============================================================
        '/\bexit\s*[\(;]/i' => 'exit statement',
        '/\bdie\s*[\(;]/i' => 'die statement',

        // ============================================================
        // 21. PHPINFO AND PROBING
        // ============================================================
        '/\bphpinfo\s*\(/i' => 'phpinfo() information disclosure',
        '/\bphpversion\s*\(/i' => 'phpversion() information disclosure',
        '/\bget_cfg_var\s*\(/i' => 'get_cfg_var() configuration reading',
        '/\bget_defined_vars\s*\(/i' => 'get_defined_vars() variable disclosure',
        '/\bget_defined_functions\s*\(/i' => 'get_defined_functions() function disclosure',
        '/\bget_defined_constants\s*\(/i' => 'get_defined_constants() constant disclosure',
        '/\bini_get\s*\(/i' => 'ini_get() configuration reading',
        '/\bini_set\s*\(/i' => 'ini_set() configuration modification',

        // ============================================================
        // 22. CLASS_EXISTS PROBING
        // ============================================================
        '/\bclass_exists\s*\(/i' => 'class_exists() probing',
        '/\bfunction_exists\s*\(/i' => 'function_exists() probing',
        '/\bmethod_exists\s*\(/i' => 'method_exists() probing',
        '/\binterface_exists\s*\(/i' => 'interface_exists() probing',

        // ============================================================
        // 23. EXTRACT (variable injection)
        // ============================================================
        '/\bextract\s*\(/i' => 'extract() variable injection',
        '/\bcompact\s*\(/i' => 'compact() variable access',
        '/\bparse_str\s*\(/i' => 'parse_str() variable injection',

        // ============================================================
        // 24. ARRAY_MAP/ARRAY_FILTER (callback accepting)
        // ============================================================
        '/\barray_map\s*\(/i' => 'array_map() callback execution',
        '/\barray_filter\s*\([^,]+,/i' => 'array_filter() with callback',
        '/\barray_reduce\s*\(/i' => 'array_reduce() callback execution',
        '/\barray_walk\s*\(/i' => 'array_walk() callback execution',
        '/\barray_walk_recursive\s*\(/i' => 'array_walk_recursive() callback execution',
        '/\busort\s*\(/i' => 'usort() callback execution',
        '/\buasort\s*\(/i' => 'uasort() callback execution',
        '/\buksort\s*\(/i' => 'uksort() callback execution',
        '/\bpreg_replace_callback\s*\(/i' => 'preg_replace_callback() callback execution',

        // ============================================================
        // 25. REFLECTION (class introspection)
        // ============================================================
        '/\bReflection/i' => 'Reflection* class introspection',

        // ============================================================
        // 26. NEW OBJECT INSTANTIATION
        // ============================================================
        '/\bnew\s+[a-zA-Z_\\\\][a-zA-Z0-9_\\\\]*\s*\(/i' => 'object instantiation',

        // ============================================================
        // 27. STATIC METHOD CALLS
        // ============================================================
        '/[a-zA-Z_\\\\][a-zA-Z0-9_\\\\]*::[a-zA-Z_][a-zA-Z0-9_]*\s*\(/i' => 'static method call',

        // ============================================================
        // 28. EXCEPTION THROWING
        // ============================================================
        '/\bthrow\s+new\b/i' => 'exception throwing',

        // ============================================================
        // 29. GLOBALS/CONSTANTS MODIFICATION
        // ============================================================
        '/\bdefine\s*\(/i' => 'define() constant definition',
        '/\bconst\s+[A-Z]/i' => 'const definition',

        // ============================================================
        // 30. EVAL-LIKE CONSTRUCTS
        // ============================================================
        '/\bpreg_replace\s*\([^,]*["\'][^"\']*\/[^\/]*e/i' => 'preg_replace /e modifier',

        // ============================================================
        // 31. CLOSURE/ANONYMOUS FUNCTIONS
        // ============================================================
        '/\bfunction\s*\(/i' => 'anonymous function',
        '/\bfn\s*\(/i' => 'arrow function',
        '/=>\s*function\s*\(/i' => 'closure in array',
    ];

    /**
     * Functions that are potentially dangerous when whitelisted.
     *
     * These are technically safe but could enable:
     * - ReDoS attacks (regex functions)
     * - Information disclosure (file/debug functions)
     * - Environment manipulation
     *
     * Adding these to additional_allowed_functions triggers warnings.
     */
    private const DANGEROUS_FUNCTIONS = [
        // Regex functions (ReDoS potential)
        'preg_match',
        'preg_match_all',
        'preg_replace',
        'preg_split',
        'preg_grep',
        // File existence (information disclosure)
        'file_exists',
        'is_file',
        'is_dir',
        'is_readable',
        'is_writable',
        'is_executable',
        'is_link',
        // Debugging (information disclosure)
        'var_dump',
        'print_r',
        'var_export',
        'debug_backtrace',
        'debug_print_backtrace',
        // Environment
        'getenv',
        'putenv',
    ];

    /**
     * Additional allowed functions (from config)
     * @var array<string>
     */
    private array $additionalAllowedFunctions = [];

    /**
     * Denied functions (takes precedence over allowed)
     * @var array<string>
     */
    private array $deniedFunctions = [];

    /**
     * Maximum expression length (0 = unlimited)
     */
    private int $maxExpressionLength = 0;

    /**
     * Dangerous functions that have been enabled via config
     * @var array<string>
     */
    private array $enabledDangerousFunctions = [];

    /**
     * Constructor
     *
     * @param array $additionalAllowed Additional functions to allow
     * @param array $denied Functions to deny (overrides allowed)
     * @param int $maxExpressionLength Maximum expression length
     */
    public function __construct(
        array $additionalAllowed = [],
        array $denied = [],
        int $maxExpressionLength = 0
    ) {
        $this->additionalAllowedFunctions = array_map('strtolower', array_filter($additionalAllowed));
        $this->deniedFunctions = array_map('strtolower', array_filter($denied));
        $this->maxExpressionLength = $maxExpressionLength;

        // Track which dangerous functions were enabled
        $this->enabledDangerousFunctions = array_values(array_intersect(
            $this->additionalAllowedFunctions,
            array_map('strtolower', self::DANGEROUS_FUNCTIONS)
        ));
    }

    /**
     * Validate a function name against the whitelist.
     *
     * @param string $func The function name to validate
     * @return string The validated (lowercased) function name
     * @throws SecurityException If the function is not whitelisted
     */
    public function validateFunction(string $func): string
    {
        $func = strtolower(trim($func));

        if (!$this->isAllowedFunction($func)) {
            throw SecurityException::disallowedFunction($func);
        }

        return $func;
    }

    /**
     * Check if a function is allowed without throwing.
     *
     * @param string $func The function name to check
     * @return bool True if allowed, false otherwise
     */
    public function isAllowedFunction(string $func): bool
    {
        $func = strtolower(trim($func));

        // Denied list takes precedence
        if (in_array($func, $this->deniedFunctions, true)) {
            return false;
        }

        // Check built-in whitelist
        if (in_array($func, self::ALLOWED_FUNCTIONS, true)) {
            return true;
        }

        // Check additional allowed functions from config
        return in_array($func, $this->additionalAllowedFunctions, true);
    }

    /**
     * Validate an expression for security issues.
     *
     * Checks for forbidden patterns AND validates any function calls
     * found within the expression against the whitelist.
     *
     * @param string $expr The expression to validate
     * @return string The validated expression (unescaped)
     * @throws SecurityException If a forbidden pattern is detected or disallowed function found
     */
    public function validateExpression(string $expr): string
    {
        // Check expression length first (before unescaping)
        if ($this->maxExpressionLength > 0 && strlen($expr) > $this->maxExpressionLength) {
            throw SecurityException::expressionTooLong(strlen($expr), $this->maxExpressionLength);
        }

        // Unescape MyBB's addslashes() escaping
        $unescaped = $this->unescape($expr);

        // Check for forbidden patterns
        foreach (self::FORBIDDEN_PATTERNS as $pattern => $description) {
            if (preg_match($pattern, $unescaped)) {
                throw SecurityException::forbiddenPattern($description, $unescaped);
            }
        }

        // Extract and validate function calls in the expression
        // Match function calls: word followed by opening parenthesis
        // Exclude language constructs like isset, empty, array
        if (preg_match_all('/\b([a-z_][a-z0-9_]*)\s*\(/i', $unescaped, $matches)) {
            $languageConstructs = ['isset', 'empty', 'array', 'list', 'unset', 'echo', 'print'];

            foreach ($matches[1] as $func) {
                $funcLower = strtolower($func);

                // Skip language constructs
                if (in_array($funcLower, $languageConstructs, true)) {
                    continue;
                }

                // Validate against whitelist
                if (!$this->isAllowedFunction($funcLower)) {
                    throw SecurityException::functionInExpression($func, $unescaped);
                }
            }
        }

        return $unescaped;
    }

    /**
     * Get the list of allowed functions.
     *
     * @return array<string> The whitelist of allowed function names
     */
    public function getAllowedFunctions(): array
    {
        return self::ALLOWED_FUNCTIONS;
    }

    /**
     * Check if any dangerous functions have been enabled.
     *
     * @return bool True if dangerous functions are in the whitelist
     */
    public function hasDangerousFunctionsEnabled(): bool
    {
        return !empty($this->enabledDangerousFunctions);
    }

    /**
     * Get the list of dangerous functions that have been enabled.
     *
     * @return array<string> List of enabled dangerous function names
     */
    public function getDangerousFunctionsEnabled(): array
    {
        return $this->enabledDangerousFunctions;
    }

    /**
     * Get the list of all functions considered dangerous.
     *
     * @return array<string> List of dangerous function names
     */
    public static function getDangerousFunctionsList(): array
    {
        return self::DANGEROUS_FUNCTIONS;
    }

    /**
     * Reverse MyBB's addslashes() escaping.
     *
     * MyBB templates are stored with addslashes() applied, so we need
     * to reverse this when validating expressions.
     *
     * @param string $str The escaped string
     * @return string The unescaped string
     */
    private function unescape(string $str): string
    {
        return strtr($str, [
            '\\"' => '"',
            "\\'" => "'",
            '\\\\' => '\\',
        ]);
    }
}
