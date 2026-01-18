<?php
/**
 * Cortex Runtime
 * Template wrapper that intercepts get() calls and processes Cortex syntax.
 *
 * @package Cortex
 * @author Corta Labs
 * @license MIT
 */

declare(strict_types=1);

namespace Cortex;

// Ensure MyBB templates class is available
if (!class_exists('templates', false)) {
    require_once MYBB_ROOT . 'inc/class_templates.php';
}

/**
 * Runtime wrapper for MyBB templates.
 *
 * Extends the MyBB templates class to intercept template retrieval,
 * parse Cortex syntax, compile to PHP, and cache results.
 *
 * Gracefully falls back to original templates on any error.
 */
class Runtime extends \templates
{
    /**
     * Security policy for expression validation
     */
    private SecurityPolicy $security;

    /**
     * Template syntax parser
     */
    private Parser $parser;

    /**
     * Token-to-PHP compiler
     */
    private Compiler $compiler;

    /**
     * Disk cache for compiled templates
     */
    private Cache $diskCache;

    /**
     * In-memory cache for current request
     * @var array<string, string>
     */
    private array $memoryCache = [];

    /**
     * Configuration settings
     * @var array<string, mixed>
     */
    private array $config;

    /**
     * Whether Cortex processing is enabled
     */
    private bool $enabled = true;

    /**
     * Regex pattern for quick syntax detection
     * Matches: <if, <else, <func, <template, <setvar, {=
     */
    private const SYNTAX_PATTERN = '/<(?:if\s|else|func\s|template\s|setvar\s)|\{=/i';

    /**
     * Constructor
     *
     * Copies properties from original templates object and initializes
     * Cortex components (SecurityPolicy, Parser, Compiler, Cache).
     *
     * @param \templates $original Original MyBB templates object
     * @param array<string, mixed> $config Configuration options
     */
    public function __construct(\templates $original, array $config = [])
    {
        // Copy essential properties from original templates object
        // These are the core template caching structures in MyBB
        $this->cache = $original->cache;
        $this->total = $original->total ?? 0;
        $this->uncached_templates = $original->uncached_templates ?? [];

        // Store configuration
        $this->config = $config;
        $this->enabled = $config['enabled'] ?? true;

        // Initialize Cortex components
        $this->security = new SecurityPolicy(
            $config['security']['additional_allowed_functions'] ?? [],
            $config['security']['denied_functions'] ?? []
        );

        $this->parser = new Parser($this->security);
        $this->compiler = new Compiler($this->security);

        // Initialize disk cache
        $cacheDir = MYBB_ROOT . 'cache/cortex/';
        $this->diskCache = new Cache($cacheDir);
    }

    /**
     * Override template retrieval to process Cortex syntax.
     *
     * Processing flow:
     * 1. If disabled or eslashes=0, return parent result unchanged
     * 2. Get original template from parent
     * 3. Quick syntax check - if no Cortex syntax, return original
     * 4. Check memory cache, then disk cache
     * 5. On cache miss: parse, compile, cache result
     * 6. On ANY exception: log error, return original template
     *
     * @param string $title Template name
     * @param int $eslashes Whether to escape slashes (1 = template will be eval'd)
     * @param int $htmlcomments Whether to add HTML comments
     * @return string Processed template content
     */
    public function get($title, $eslashes = 1, $htmlcomments = 1)
    {
        // If disabled, pass through to parent
        if (!$this->enabled) {
            return parent::get($title, $eslashes, $htmlcomments);
        }

        // Only process when eslashes=1 (template will be eval'd)
        // eslashes=0 means template is used for other purposes (e.g., email)
        if (!$eslashes) {
            return parent::get($title, $eslashes, $htmlcomments);
        }

        // Get original template from MyBB
        $original = parent::get($title, $eslashes, $htmlcomments);

        // Quick syntax check - avoid parsing templates without Cortex syntax
        if (!$this->hasCortexSyntax($original)) {
            return $original;
        }

        // Generate content hash for cache key
        $hash = $this->generateHash($original);

        // Check memory cache first (fastest)
        if (isset($this->memoryCache[$hash])) {
            return $this->memoryCache[$hash];
        }

        // Check disk cache (if enabled)
        if ($this->config['cache_enabled'] ?? true) {
            $cached = $this->diskCache->get($title, $hash);
            if ($cached !== null) {
                $this->memoryCache[$hash] = $cached;
                return $cached;
            }
        }

        // Parse and compile
        try {
            $tokens = $this->parser->parse($original);
            $compiled = $this->compiler->compile($tokens);

            // Store in memory cache
            $this->memoryCache[$hash] = $compiled;

            // Store in disk cache (if enabled and writable)
            if (($this->config['cache_enabled'] ?? true) && $this->diskCache->isWritable()) {
                $this->diskCache->set($title, $hash, $compiled);
            }

            return $compiled;

        } catch (\Throwable $e) {
            // Graceful fallback: return original on ANY error
            // This ensures the site never breaks due to Cortex parsing issues
            if ($this->config['debug'] ?? false) {
                error_log('Cortex parse error in ' . $title . ': ' . $e->getMessage());
            }
            return $original;
        }
    }

    /**
     * Quick check if template contains Cortex syntax.
     *
     * Uses a simple regex to avoid full parsing overhead for templates
     * that don't use any Cortex features.
     *
     * @param string $content Template content
     * @return bool True if Cortex syntax detected
     */
    private function hasCortexSyntax(string $content): bool
    {
        return (bool) preg_match(self::SYNTAX_PATTERN, $content);
    }

    /**
     * Generate content hash for cache key.
     *
     * Uses MD5 for speed - this is not security-sensitive,
     * just needs to be fast and have low collision probability.
     *
     * @param string $content Template content
     * @return string 32-character hex hash
     */
    private function generateHash(string $content): string
    {
        return md5($content);
    }

    /**
     * Invalidate cache for a specific template.
     *
     * Call this when a template is modified to ensure fresh compilation.
     *
     * @param string $title Template name
     * @return int Number of cache entries removed
     */
    public function invalidateCache(string $title): int
    {
        return $this->diskCache->invalidate($title);
    }

    /**
     * Clear all Cortex caches.
     *
     * @return int Number of cache entries removed
     */
    public function clearCache(): int
    {
        $this->memoryCache = [];
        return $this->diskCache->clear();
    }

    /**
     * Get cache statistics.
     *
     * @return array{memory_count: int, disk_count: int, disk_writable: bool}
     */
    public function getCacheStats(): array
    {
        return [
            'memory_count' => count($this->memoryCache),
            'disk_count' => $this->diskCache->getCount(),
            'disk_writable' => $this->diskCache->isWritable(),
        ];
    }

    /**
     * Check if Cortex processing is enabled.
     *
     * @return bool True if enabled
     */
    public function isEnabled(): bool
    {
        return $this->enabled;
    }

    /**
     * Enable or disable Cortex processing.
     *
     * @param bool $enabled Whether to enable processing
     * @return void
     */
    public function setEnabled(bool $enabled): void
    {
        $this->enabled = $enabled;
    }
}
