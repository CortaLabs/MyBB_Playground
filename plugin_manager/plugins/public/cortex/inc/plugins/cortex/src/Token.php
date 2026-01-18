<?php
/**
 * Immutable token data structure for the Cortex template parser.
 *
 * Represents a single token produced during template tokenization.
 * Uses PHP 8.1 readonly properties for immutability.
 *
 * @package Cortex
 * @author Corta Labs
 * @license MIT
 */

declare(strict_types=1);

namespace Cortex;

/**
 * Represents a single token from template parsing.
 *
 * This is a readonly class - once created, a Token cannot be modified.
 * Different token types use different optional properties:
 *
 * - IF_OPEN, ELSEIF: use `condition` property
 * - FUNC_OPEN: uses `funcName` property
 * - SETVAR: uses `varName` and `varValue` properties
 * - Others: only use `type`, `value`, and `position`
 */
readonly class Token
{
    /**
     * Create a new Token instance.
     *
     * @param TokenType $type The type of this token
     * @param string $value The raw matched value from the template
     * @param int $position The byte offset where this token starts in the original template
     * @param string|null $condition The condition expression (for IF_OPEN, ELSEIF)
     * @param string|null $funcName The function name (for FUNC_OPEN)
     * @param string|null $varName The variable name (for SETVAR)
     * @param string|null $varValue The variable value expression (for SETVAR)
     */
    public function __construct(
        public TokenType $type,
        public string $value,
        public int $position,
        public ?string $condition = null,
        public ?string $funcName = null,
        public ?string $varName = null,
        public ?string $varValue = null,
    ) {}

    /**
     * Create a TEXT token.
     *
     * @param string $value The text content
     * @param int $position The byte offset
     * @return self
     */
    public static function text(string $value, int $position): self
    {
        return new self(
            type: TokenType::TEXT,
            value: $value,
            position: $position,
        );
    }

    /**
     * Create an IF_OPEN token.
     *
     * @param string $value The full matched syntax
     * @param int $position The byte offset
     * @param string $condition The condition expression
     * @return self
     */
    public static function ifOpen(string $value, int $position, string $condition): self
    {
        return new self(
            type: TokenType::IF_OPEN,
            value: $value,
            position: $position,
            condition: $condition,
        );
    }

    /**
     * Create an ELSEIF token.
     *
     * @param string $value The full matched syntax
     * @param int $position The byte offset
     * @param string $condition The condition expression
     * @return self
     */
    public static function elseIf(string $value, int $position, string $condition): self
    {
        return new self(
            type: TokenType::ELSEIF,
            value: $value,
            position: $position,
            condition: $condition,
        );
    }

    /**
     * Create an ELSE token.
     *
     * @param string $value The full matched syntax
     * @param int $position The byte offset
     * @return self
     */
    public static function else(string $value, int $position): self
    {
        return new self(
            type: TokenType::ELSE,
            value: $value,
            position: $position,
        );
    }

    /**
     * Create an IF_CLOSE token.
     *
     * @param string $value The full matched syntax
     * @param int $position The byte offset
     * @return self
     */
    public static function ifClose(string $value, int $position): self
    {
        return new self(
            type: TokenType::IF_CLOSE,
            value: $value,
            position: $position,
        );
    }

    /**
     * Create a FUNC_OPEN token.
     *
     * @param string $value The full matched syntax
     * @param int $position The byte offset
     * @param string $funcName The function name
     * @return self
     */
    public static function funcOpen(string $value, int $position, string $funcName): self
    {
        return new self(
            type: TokenType::FUNC_OPEN,
            value: $value,
            position: $position,
            funcName: $funcName,
        );
    }

    /**
     * Create a FUNC_CLOSE token.
     *
     * @param string $value The full matched syntax
     * @param int $position The byte offset
     * @return self
     */
    public static function funcClose(string $value, int $position): self
    {
        return new self(
            type: TokenType::FUNC_CLOSE,
            value: $value,
            position: $position,
        );
    }

    /**
     * Create a TEMPLATE token.
     *
     * @param string $value The template name
     * @param int $position The byte offset
     * @return self
     */
    public static function template(string $value, int $position): self
    {
        return new self(
            type: TokenType::TEMPLATE,
            value: $value,
            position: $position,
        );
    }

    /**
     * Create an EXPRESSION token.
     *
     * @param string $value The expression content
     * @param int $position The byte offset
     * @return self
     */
    public static function expression(string $value, int $position): self
    {
        return new self(
            type: TokenType::EXPRESSION,
            value: $value,
            position: $position,
        );
    }

    /**
     * Create a SETVAR token.
     *
     * @param string $value The full matched syntax
     * @param int $position The byte offset
     * @param string $varName The variable name
     * @param string $varValue The variable value expression
     * @return self
     */
    public static function setVar(string $value, int $position, string $varName, string $varValue): self
    {
        return new self(
            type: TokenType::SETVAR,
            value: $value,
            position: $position,
            varName: $varName,
            varValue: $varValue,
        );
    }
}
