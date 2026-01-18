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
        'additional_allowed_functions' => [],
        'denied_functions' => [],
        'max_nesting_depth' => 10,
        'max_expression_length' => 1000,
    ],
];
