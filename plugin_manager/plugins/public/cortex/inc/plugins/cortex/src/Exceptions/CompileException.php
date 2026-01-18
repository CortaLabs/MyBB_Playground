<?php
/**
 * Exception thrown during template compilation errors.
 *
 * This exception is thrown when the compiler encounters structural
 * errors or security violations during token-to-PHP transformation.
 *
 * @package Cortex
 * @author Corta Labs
 * @license MIT
 */

declare(strict_types=1);

namespace Cortex\Exceptions;

use Cortex\Token;
use Exception;

/**
 * Exception for template compilation errors.
 *
 * Provides factory methods for common compilation error scenarios
 * to ensure consistent error messaging.
 */
class CompileException extends Exception
{
    /**
     * The token that caused the error (if available).
     */
    private ?Token $token;

    /**
     * The type of compilation error.
     */
    private string $errorType;

    /**
     * Create a new CompileException.
     *
     * @param string $message The error message
     * @param string $errorType The type of error (structure, security, etc.)
     * @param Token|null $token The token that caused the error
     * @param Exception|null $previous The previous exception for chaining
     */
    public function __construct(
        string $message,
        string $errorType = 'general',
        ?Token $token = null,
        ?Exception $previous = null
    ) {
        $this->token = $token;
        $this->errorType = $errorType;

        $fullMessage = $this->buildMessage($message);
        parent::__construct($fullMessage, 0, $previous);
    }

    /**
     * Get the token that caused the error.
     *
     * @return Token|null The token or null if not available
     */
    public function getToken(): ?Token
    {
        return $this->token;
    }

    /**
     * Get the error type.
     *
     * @return string The type of compilation error
     */
    public function getErrorType(): string
    {
        return $this->errorType;
    }

    /**
     * Build the full error message with context.
     *
     * @param string $message The base error message
     * @return string The formatted message
     */
    private function buildMessage(string $message): string
    {
        $parts = ['Compile error'];

        if ($this->token !== null) {
            $parts[] = "at position {$this->token->position}";
            $parts[] = "(token: {$this->token->type->value})";
        }

        return implode(' ', $parts) . ': ' . $message;
    }

    /**
     * Create an exception for unbalanced if statements.
     *
     * This is thrown when there are unclosed if statements at the end
     * of compilation or mismatched if/endif blocks.
     *
     * @param string $message Description of the imbalance
     * @param Token|null $token The problematic token (if available)
     * @return self
     */
    public static function unbalancedIf(string $message, ?Token $token = null): self
    {
        return new self(
            "Unbalanced if statement: {$message}",
            'structure',
            $token
        );
    }

    /**
     * Create an exception for an else without a matching if.
     *
     * @param Token $token The else token
     * @return self
     */
    public static function elseWithoutIf(Token $token): self
    {
        return new self(
            'Found <else> without a matching <if>',
            'structure',
            $token
        );
    }

    /**
     * Create an exception for an elseif without a matching if.
     *
     * @param Token $token The elseif token
     * @return self
     */
    public static function elseIfWithoutIf(Token $token): self
    {
        return new self(
            'Found <else if> without a matching <if>',
            'structure',
            $token
        );
    }

    /**
     * Create an exception for an if_close without a matching if.
     *
     * @param Token $token The if_close token
     * @return self
     */
    public static function ifCloseWithoutIf(Token $token): self
    {
        return new self(
            'Found </if> without a matching <if>',
            'structure',
            $token
        );
    }

    /**
     * Create an exception wrapping a security violation.
     *
     * This is thrown when the SecurityPolicy rejects a function or
     * expression during compilation.
     *
     * @param SecurityException $e The underlying security exception
     * @param Token $token The token containing the security violation
     * @return self
     */
    public static function securityViolation(SecurityException $e, Token $token): self
    {
        return new self(
            "Security violation: {$e->getMessage()}",
            'security',
            $token,
            $e
        );
    }

    /**
     * Create an exception for multiple else clauses in one if block.
     *
     * @param Token $token The second else token
     * @return self
     */
    public static function multipleElse(Token $token): self
    {
        return new self(
            'Multiple <else> clauses in same <if> block',
            'structure',
            $token
        );
    }

    /**
     * Create an exception for elseif after else.
     *
     * @param Token $token The elseif token
     * @return self
     */
    public static function elseIfAfterElse(Token $token): self
    {
        return new self(
            'Found <else if> after <else> in same <if> block',
            'structure',
            $token
        );
    }
}
