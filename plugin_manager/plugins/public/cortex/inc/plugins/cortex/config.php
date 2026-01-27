<?php
/**
 * Cortex Configuration
 *
 * @package Cortex
 * @author Corta Labs
 * @license MIT
 */

if (!defined('IN_MYBB')) {
    die('This file cannot be accessed directly.');
}

return [
    'enabled' => true,
    'cache_enabled' => true,
    'cache_ttl' => 0,
    'debug' => false,
    'security' => [
        /**
         * SECURITY WARNING: Additional Allowed Functions
         * =============================================
         *
         * Functions added here bypass Cortex's security whitelist.
         * Only add functions you FULLY TRUST and understand.
         *
         * DANGEROUS functions that trigger warnings if added:
         * - preg_match, preg_replace, etc. (ReDoS vulnerability potential)
         * - file_exists, is_file, is_dir (information disclosure)
         * - var_dump, print_r, debug_backtrace (information disclosure)
         * - getenv, putenv (environment manipulation)
         *
         * Adding dangerous functions will log warnings when debug=true.
         * Consider the security implications carefully before adding ANY function.
         *
         * Example: 'additional_allowed_functions' => ['custom_func'],
         */
        'additional_allowed_functions' => [],

        /**
         * Denied Functions
         *
         * Functions listed here are blocked even if they would otherwise
         * be allowed. Takes precedence over the whitelist.
         */
        'denied_functions' => [],

        /**
         * Maximum nesting depth for <if> blocks.
         * Set to 0 for unlimited (not recommended).
         */
        'max_nesting_depth' => 10,

        /**
         * Maximum expression length in characters.
         * Helps prevent ReDoS and memory exhaustion.
         * Set to 0 for unlimited (not recommended).
         */
        'max_expression_length' => 1000,
    ],
];
