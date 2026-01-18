<?php
/**
 * Cortex Cache
 * Disk cache for compiled templates with atomic writes.
 *
 * @package Cortex
 * @author Corta Labs
 * @license MIT
 */

declare(strict_types=1);

namespace Cortex;

/**
 * Disk cache for compiled Cortex templates.
 *
 * Provides fast retrieval of pre-compiled templates using content hashing.
 * Uses atomic writes (temp file + rename) for crash safety.
 */
class Cache
{
    /**
     * Cache directory path (with trailing slash)
     */
    private string $cacheDir;

    /**
     * Whether cache directory is writable
     */
    private bool $writable;

    /**
     * In-memory cache for current request
     * @var array<string, string>
     */
    private array $memoryCache = [];

    /**
     * Cache TTL in seconds (0 = no expiration)
     */
    private int $ttl = 0;

    /**
     * Constructor
     *
     * @param string $cacheDir Path to cache directory
     * @param int $ttl Cache TTL in seconds (0 = no expiration)
     */
    public function __construct(string $cacheDir, int $ttl = 0)
    {
        // Ensure trailing slash
        $this->cacheDir = rtrim($cacheDir, '/\\') . '/';
        $this->ttl = $ttl;

        // Auto-create directory if missing
        if (!is_dir($this->cacheDir)) {
            @mkdir($this->cacheDir, 0755, true);
        }

        // Set writable flag
        $this->writable = is_dir($this->cacheDir) && is_writable($this->cacheDir);
    }

    /**
     * Get cached compiled template
     *
     * @param string $title Template title
     * @param string $hash Content hash for cache key
     * @param int|null $tid Template set ID (null = global)
     * @return string|null Cached content or null on miss
     */
    public function get(string $title, string $hash, ?int $tid = null): ?string
    {
        $cacheKey = $this->buildCacheKey($title, $hash, $tid);
        $cacheFile = $this->buildCachePath($title, $hash, $tid);

        // Check memory cache first
        if (isset($this->memoryCache[$cacheKey])) {
            return $this->memoryCache[$cacheKey];
        }

        // Check disk cache
        if (!is_file($cacheFile)) {
            return null;
        }

        // TTL check - if TTL is set and file is expired, treat as cache miss
        if ($this->ttl > 0) {
            $mtime = @filemtime($cacheFile);
            if ($mtime !== false && (time() - $mtime) > $this->ttl) {
                // Cache expired - delete stale file and return miss
                @unlink($cacheFile);
                return null;
            }
        }

        $content = @file_get_contents($cacheFile);
        if ($content === false) {
            return null;
        }

        // Store in memory cache for subsequent requests
        $this->memoryCache[$cacheKey] = $content;

        return $content;
    }

    /**
     * Store compiled template in cache
     *
     * Uses atomic write (temp file + rename) for crash safety.
     *
     * @param string $title Template title
     * @param string $hash Content hash for cache key
     * @param string $content Compiled template content
     * @param int|null $tid Template set ID (null = global)
     * @return bool True on success, false on failure
     */
    public function set(string $title, string $hash, string $content, ?int $tid = null): bool
    {
        if (!$this->writable) {
            return false;
        }

        $cacheKey = $this->buildCacheKey($title, $hash, $tid);
        $cacheFile = $this->buildCachePath($title, $hash, $tid);

        // Store in memory cache immediately
        $this->memoryCache[$cacheKey] = $content;

        // Atomic write: write to temp file, then rename
        $tempFile = $cacheFile . '.' . uniqid('tmp_', true);

        $result = @file_put_contents($tempFile, $content, LOCK_EX);
        if ($result === false) {
            @unlink($tempFile);
            return false;
        }

        // Atomic rename
        if (!@rename($tempFile, $cacheFile)) {
            @unlink($tempFile);
            return false;
        }

        return true;
    }

    /**
     * Invalidate all cached versions of a template
     *
     * @param string $title Template title to invalidate
     * @return int Number of cache files removed
     */
    public function invalidate(string $title): int
    {
        $count = 0;
        $pattern = $this->sanitizeTitle($title);

        // Remove from memory cache
        foreach (array_keys($this->memoryCache) as $key) {
            if (str_contains($key, '_' . $pattern . '_')) {
                unset($this->memoryCache[$key]);
            }
        }

        // Remove from disk cache
        $files = @glob($this->cacheDir . '*_' . $pattern . '_*.php');
        if ($files === false) {
            return 0;
        }

        foreach ($files as $file) {
            if (@unlink($file)) {
                $count++;
            }
        }

        return $count;
    }

    /**
     * Clear all cached templates
     *
     * @return int Number of cache files removed
     */
    public function clear(): int
    {
        $count = 0;

        // Clear memory cache
        $this->memoryCache = [];

        // Clear disk cache
        $files = @glob($this->cacheDir . '*.php');
        if ($files === false) {
            return 0;
        }

        foreach ($files as $file) {
            if (@unlink($file)) {
                $count++;
            }
        }

        return $count;
    }

    /**
     * Check if cache directory is writable
     *
     * @return bool True if cache can be written
     */
    public function isWritable(): bool
    {
        return $this->writable;
    }

    /**
     * Get count of cached files
     *
     * @return int Number of cache files on disk
     */
    public function getCount(): int
    {
        $files = @glob($this->cacheDir . '*.php');
        if ($files === false) {
            return 0;
        }

        return count($files);
    }

    /**
     * Build cache file path
     *
     * Format: {tid}_{sanitized_title}_{hash}.php
     *
     * @param string $title Template title
     * @param string $hash Content hash
     * @param int|null $tid Template set ID
     * @return string Full path to cache file
     */
    private function buildCachePath(string $title, string $hash, ?int $tid): string
    {
        $tidPart = $tid ?? 0;
        $sanitizedTitle = $this->sanitizeTitle($title);
        $safeHash = substr(preg_replace('/[^a-f0-9]/i', '', $hash), 0, 16);

        return $this->cacheDir . $tidPart . '_' . $sanitizedTitle . '_' . $safeHash . '.php';
    }

    /**
     * Build memory cache key
     *
     * @param string $title Template title
     * @param string $hash Content hash
     * @param int|null $tid Template set ID
     * @return string Cache key
     */
    private function buildCacheKey(string $title, string $hash, ?int $tid): string
    {
        $tidPart = $tid ?? 0;
        return $tidPart . '_' . $title . '_' . $hash;
    }

    /**
     * Sanitize template title for use in filename
     *
     * @param string $title Raw template title
     * @return string Sanitized title safe for filesystem
     */
    private function sanitizeTitle(string $title): string
    {
        // Replace non-alphanumeric characters with underscores
        $sanitized = preg_replace('/[^a-z0-9_]/i', '_', $title);
        // Collapse multiple underscores
        $sanitized = preg_replace('/_+/', '_', $sanitized);
        // Trim underscores and limit length
        return substr(trim($sanitized, '_'), 0, 64);
    }
}
