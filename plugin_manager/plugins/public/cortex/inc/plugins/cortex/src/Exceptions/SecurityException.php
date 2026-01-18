<?php
/**
 * Exception thrown when a security policy is violated.
 *
 * This exception is thrown when the security policy detects
 * disallowed function calls or forbidden patterns in template
 * expressions.
 *
 * @package Cortex
 * @author Corta Labs
 * @license MIT
 */

declare(strict_types=1);

namespace Cortex\Exceptions;

use Exception;

/**
 * Exception for security policy violations.
 *
 * Provides factory methods for common security violation scenarios
 * to ensure consistent error messaging.
 */
class SecurityException extends Exception
{
    /**
     * Error codes for different violation types.
     */
    public const CODE_DISALLOWED_FUNCTION = 1;
    public const CODE_FORBIDDEN_PATTERN = 2;
    public const CODE_EXPRESSION_FUNCTION = 3;
    public const CODE_EXPRESSION_TOO_LONG = 4;

    /**
     * The function or pattern that caused the violation.
     */
    private string $violatingElement;

    /**
     * The category of violation (function, pattern, etc.).
     */
    private string $category;

    /**
     * Create a new SecurityException.
     *
     * @param string $message The error message
     * @param int $code Error code constant
     * @param string $violatingElement The element that caused the violation
     * @param string $category The violation category
     * @param Exception|null $previous The previous exception for chaining
     */
    public function __construct(
        string $message,
        int $code = 0,
        string $violatingElement = '',
        string $category = 'general',
        ?Exception $previous = null
    ) {
        $this->violatingElement = $violatingElement;
        $this->category = $category;

        parent::__construct($message, $code, $previous);
    }

    /**
     * Get the element that caused the violation.
     *
     * @return string The violating function name or pattern
     */
    public function getViolatingElement(): string
    {
        return $this->violatingElement;
    }

    /**
     * Get the violation category.
     *
     * @return string The category (function, pattern, etc.)
     */
    public function getCategory(): string
    {
        return $this->category;
    }

    /**
     * Create an exception for a disallowed function call.
     *
     * @param string $func The disallowed function name
     * @return self
     */
    public static function disallowedFunction(string $func): self
    {
        return new self(
            "Function not allowed: {$func}",
            self::CODE_DISALLOWED_FUNCTION,
            $func,
            'function'
        );
    }

    /**
     * Create an exception for a forbidden pattern in an expression.
     *
     * @param string $description Human-readable description of what was forbidden
     * @param string $expr The expression containing the forbidden pattern
     * @return self
     */
    public static function forbiddenPattern(string $description, string $expr): self
    {
        // Truncate expression if too long for error message
        $truncatedExpr = strlen($expr) > 50
            ? substr($expr, 0, 47) . '...'
            : $expr;

        return new self(
            "Forbidden pattern detected: {$description}",
            self::CODE_FORBIDDEN_PATTERN,
            $truncatedExpr,
            'pattern'
        );
    }

    /**
     * Create an exception for a function call within an expression that is not whitelisted.
     *
     * @param string $func The function name found in the expression
     * @param string $expr The full expression for context
     * @return self
     */
    public static function functionInExpression(string $func, string $expr): self
    {
        // Truncate expression if too long for error message
        $truncatedExpr = strlen($expr) > 50
            ? substr($expr, 0, 47) . '...'
            : $expr;

        return new self(
            "Function call not allowed in expression: {$func}",
            self::CODE_EXPRESSION_FUNCTION,
            $func,
            'expression_function'
        );
    }

    /**
     * Create exception for expression too long
     *
     * @param int $actual Actual length
     * @param int $max Maximum allowed
     * @return self
     */
    public static function expressionTooLong(int $actual, int $max): self
    {
        return new self(
            "Expression too long: {$actual} characters exceeds maximum of {$max}",
            self::CODE_EXPRESSION_TOO_LONG,
            '',
            'expression_length'
        );
    }
}
