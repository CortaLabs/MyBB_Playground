<?php
/**
 * Exception thrown during template parsing errors.
 *
 * This exception is thrown when the parser encounters invalid
 * template syntax that cannot be tokenized.
 *
 * @package Cortex
 * @author Corta Labs
 * @license MIT
 */

declare(strict_types=1);

namespace Cortex\Exceptions;

use Exception;

/**
 * Exception for template parsing errors.
 *
 * Includes position information to help locate the error
 * in the original template content.
 */
class ParseException extends Exception
{
    /**
     * The byte offset where the error occurred in the template.
     */
    private int $position;

    /**
     * The template name (if available).
     */
    private ?string $templateName;

    /**
     * Create a new ParseException.
     *
     * @param string $message The error message
     * @param int $position The byte offset where the error occurred
     * @param string|null $templateName The name of the template being parsed
     * @param Exception|null $previous The previous exception for chaining
     */
    public function __construct(
        string $message,
        int $position = 0,
        ?string $templateName = null,
        ?Exception $previous = null
    ) {
        $this->position = $position;
        $this->templateName = $templateName;

        $fullMessage = $this->buildMessage($message);
        parent::__construct($fullMessage, 0, $previous);
    }

    /**
     * Get the position where the error occurred.
     *
     * @return int The byte offset in the template
     */
    public function getPosition(): int
    {
        return $this->position;
    }

    /**
     * Get the template name if available.
     *
     * @return string|null The template name or null
     */
    public function getTemplateName(): ?string
    {
        return $this->templateName;
    }

    /**
     * Build the full error message with context.
     *
     * @param string $message The base error message
     * @return string The formatted message
     */
    private function buildMessage(string $message): string
    {
        $parts = ['Parse error'];

        if ($this->templateName !== null) {
            $parts[] = "in template '{$this->templateName}'";
        }

        if ($this->position > 0) {
            $parts[] = "at position {$this->position}";
        }

        return implode(' ', $parts) . ': ' . $message;
    }

    /**
     * Create an exception for an unclosed construct.
     *
     * @param string $construct The unclosed construct name (e.g., 'if', 'func')
     * @param int $position The position where the construct opened
     * @param string|null $templateName The template name
     * @return self
     */
    public static function unclosed(string $construct, int $position, ?string $templateName = null): self
    {
        return new self(
            "Unclosed <{$construct}> tag",
            $position,
            $templateName
        );
    }

    /**
     * Create an exception for an unexpected closing tag.
     *
     * @param string $construct The unexpected closing construct
     * @param int $position The position of the closing tag
     * @param string|null $templateName The template name
     * @return self
     */
    public static function unexpected(string $construct, int $position, ?string $templateName = null): self
    {
        return new self(
            "Unexpected </{$construct}> tag without matching opening tag",
            $position,
            $templateName
        );
    }

    /**
     * Create an exception for malformed syntax.
     *
     * @param string $description Description of what was malformed
     * @param int $position The position of the error
     * @param string|null $templateName The template name
     * @return self
     */
    public static function malformed(string $description, int $position, ?string $templateName = null): self
    {
        return new self(
            "Malformed syntax: {$description}",
            $position,
            $templateName
        );
    }

    /**
     * Create exception for nesting too deep
     *
     * @param int $actual Actual depth
     * @param int $max Maximum allowed
     * @param int $position Position in template
     * @param string|null $templateName Template name
     * @return self
     */
    public static function nestingTooDeep(int $actual, int $max, int $position, ?string $templateName = null): self
    {
        $context = $templateName ? " in template '{$templateName}'" : '';
        return new self(
            "Nesting too deep: {$actual} levels exceeds maximum of {$max}{$context} at position {$position}",
            $position,
            $templateName
        );
    }
}
