<?php
/**
 * Template compiler that transforms tokens into eval-ready PHP code.
 *
 * This class takes the token array produced by the Parser and compiles
 * it into a PHP string that can be safely eval'd by MyBB's template system.
 *
 * @package Cortex
 * @author Corta Labs
 * @license MIT
 */

declare(strict_types=1);

namespace Cortex;

use Cortex\Exceptions\CompileException;
use Cortex\Exceptions\SecurityException;

/**
 * Compiles Token[] arrays into eval-ready PHP code strings.
 *
 * The compiler performs:
 * - Token-to-PHP transformation for all token types
 * - Nested if statement tracking with proper parentheses balancing
 * - Security validation of conditions, functions, and expressions
 * - Template name sanitization for nested template calls
 */
class Compiler
{
    /**
     * Stack to track nested if statements.
     *
     * Each entry contains:
     * - 'hasElse': bool - whether this if block has seen an <else>
     * - 'depth': int - number of elseif clauses encountered
     *
     * @var array<int, array{hasElse: bool, depth: int}>
     */
    private array $ifStack = [];

    /**
     * Create a new Compiler instance.
     *
     * @param SecurityPolicy $security The security policy for validation
     */
    public function __construct(
        private SecurityPolicy $security
    ) {}

    /**
     * Compile an array of tokens into PHP code.
     *
     * @param array<Token> $tokens The tokens to compile
     * @return string The compiled PHP code ready for eval()
     * @throws CompileException On structural errors (unbalanced if, etc.)
     * @throws SecurityException On security violations (forwarded from SecurityPolicy)
     */
    public function compile(array $tokens): string
    {
        $this->ifStack = [];
        $output = '';

        foreach ($tokens as $token) {
            $output .= $this->compileToken($token);
        }

        // Check for unclosed if statements
        if (!empty($this->ifStack)) {
            throw CompileException::unbalancedIf(
                count($this->ifStack) . ' unclosed <if> statement(s) at end of template'
            );
        }

        return $output;
    }

    /**
     * Compile a single token to PHP code.
     *
     * @param Token $token The token to compile
     * @return string The compiled PHP fragment
     * @throws CompileException On structural errors
     * @throws SecurityException On security violations
     */
    private function compileToken(Token $token): string
    {
        return match ($token->type) {
            TokenType::TEXT => $token->value,
            TokenType::IF_OPEN => $this->compileIfOpen($token),
            TokenType::ELSEIF => $this->compileElseIf($token),
            TokenType::ELSE => $this->compileElse($token),
            TokenType::IF_CLOSE => $this->compileIfClose($token),
            TokenType::FUNC_OPEN => $this->compileFuncOpen($token),
            TokenType::FUNC_CLOSE => '")."',
            TokenType::TEMPLATE => $this->compileTemplate($token),
            TokenType::EXPRESSION => $this->compileExpression($token),
            TokenType::SETVAR => $this->compileSetVar($token),
        };
    }

    /**
     * Compile an IF_OPEN token.
     *
     * Opens a new if block and pushes state onto the stack.
     * Output pattern: ".(($condition)?"
     *
     * @param Token $token The IF_OPEN token
     * @return string The compiled PHP
     * @throws CompileException On security violation
     */
    private function compileIfOpen(Token $token): string
    {
        // Push new if block onto stack
        $this->ifStack[] = ['hasElse' => false, 'depth' => 0];

        try {
            $condition = $this->security->validateExpression($token->condition ?? '');
        } catch (SecurityException $e) {
            throw CompileException::securityViolation($e, $token);
        }

        return '".((' . $condition . ')?"';
    }

    /**
     * Compile an ELSEIF token.
     *
     * Increments depth and adds conditional else branch.
     * Output pattern: ":(($condition)?"
     *
     * @param Token $token The ELSEIF token
     * @return string The compiled PHP
     * @throws CompileException If no matching if or after else
     */
    private function compileElseIf(Token $token): string
    {
        if (empty($this->ifStack)) {
            throw CompileException::elseIfWithoutIf($token);
        }

        $stackIndex = count($this->ifStack) - 1;

        // Check if we already saw an else
        if ($this->ifStack[$stackIndex]['hasElse']) {
            throw CompileException::elseIfAfterElse($token);
        }

        // Increment depth for this elseif
        $this->ifStack[$stackIndex]['depth']++;

        try {
            $condition = $this->security->validateExpression($token->condition ?? '');
        } catch (SecurityException $e) {
            throw CompileException::securityViolation($e, $token);
        }

        return '":((' . $condition . ')?"';
    }

    /**
     * Compile an ELSE token.
     *
     * Marks the current if block as having an else.
     * Output pattern: ":"
     *
     * @param Token $token The ELSE token
     * @return string The compiled PHP
     * @throws CompileException If no matching if or duplicate else
     */
    private function compileElse(Token $token): string
    {
        if (empty($this->ifStack)) {
            throw CompileException::elseWithoutIf($token);
        }

        $stackIndex = count($this->ifStack) - 1;

        // Check for duplicate else
        if ($this->ifStack[$stackIndex]['hasElse']) {
            throw CompileException::multipleElse($token);
        }

        $this->ifStack[$stackIndex]['hasElse'] = true;

        return '":"';
    }

    /**
     * Compile an IF_CLOSE token.
     *
     * Closes the current if block with proper parentheses.
     * Output pattern: ":""[)* based on depth])."
     *
     * If no else was encountered, adds empty string fallback.
     * Each elseif adds one extra closing parenthesis.
     *
     * @param Token $token The IF_CLOSE token
     * @return string The compiled PHP
     * @throws CompileException If no matching if
     */
    private function compileIfClose(Token $token): string
    {
        if (empty($this->ifStack)) {
            throw CompileException::ifCloseWithoutIf($token);
        }

        $state = array_pop($this->ifStack);

        // Build closing string
        $output = '"';

        // If no else clause, add empty string fallback for the false case
        if (!$state['hasElse']) {
            $output .= ':""';
        }

        // Add closing parentheses for each elseif depth level
        $output .= str_repeat(')', $state['depth']);

        // Close the outermost ternary
        $output .= ')."';

        return $output;
    }

    /**
     * Compile a FUNC_OPEN token.
     *
     * Validates function name against security policy.
     * Output pattern: ".$funcName("
     *
     * @param Token $token The FUNC_OPEN token
     * @return string The compiled PHP
     * @throws CompileException On security violation
     */
    private function compileFuncOpen(Token $token): string
    {
        $funcName = $token->funcName ?? '';

        try {
            $validatedFunc = $this->security->validateFunction($funcName);
        } catch (SecurityException $e) {
            throw CompileException::securityViolation($e, $token);
        }

        return '".' . $validatedFunc . '("';
    }

    /**
     * Compile a TEMPLATE token.
     *
     * Sanitizes template name and generates nested template call.
     * Output pattern: ".$GLOBALS["templates"]->get("name")."
     *
     * @param Token $token The TEMPLATE token
     * @return string The compiled PHP
     */
    private function compileTemplate(Token $token): string
    {
        // Sanitize template name: allow only alphanumeric, underscore, hyphen, space
        $name = preg_replace('/[^a-z0-9_\-\s]/i', '', $token->value);

        return '".\\$GLOBALS["templates"]->get("' . $name . '")."';
    }

    /**
     * Compile an EXPRESSION token.
     *
     * Validates expression and wraps in strval() for safe output.
     * Output pattern: ".strval($expr)."
     *
     * @param Token $token The EXPRESSION token
     * @return string The compiled PHP
     * @throws CompileException On security violation
     */
    private function compileExpression(Token $token): string
    {
        try {
            $expr = $this->security->validateExpression($token->value);
        } catch (SecurityException $e) {
            throw CompileException::securityViolation($e, $token);
        }

        return '".strval(' . $expr . ')."';
    }

    /**
     * Compile a SETVAR token.
     *
     * Sanitizes variable name and validates value expression.
     * Auto-quotes plain text values that don't look like PHP expressions.
     * Uses assignment-in-ternary pattern to avoid output.
     * Output pattern: ".(($GLOBALS["tplvars"]["name"] = ($value))?"":"")."
     *
     * @param Token $token The SETVAR token
     * @return string The compiled PHP
     * @throws CompileException On security violation
     */
    private function compileSetVar(Token $token): string
    {
        // Sanitize variable name: only alphanumeric and underscore
        $name = preg_replace('/[^a-z0-9_]/i', '', $token->varName ?? '');

        $rawValue = $token->varValue ?? '';

        // Auto-quote plain text that doesn't look like a PHP expression
        // Expressions start with: $ (variable), " or ' (string), digit, or are function calls
        $value = $this->maybeQuoteValue($rawValue);

        try {
            $value = $this->security->validateExpression($value);
        } catch (SecurityException $e) {
            throw CompileException::securityViolation($e, $token);
        }

        // Assignment expression that outputs nothing
        // The ternary always evaluates to empty string, but the assignment side-effect occurs
        return '".(($GLOBALS["tplvars"]["' . $name . '"] = (' . $value . '))?"":"")."';
    }

    /**
     * Auto-quote a value if it doesn't look like a PHP expression.
     *
     * @param string $value Raw value from template
     * @return string Value, possibly wrapped in quotes
     */
    private function maybeQuoteValue(string $value): string
    {
        $trimmed = trim($value);

        // Already quoted string
        if (preg_match('/^(["\']).*\1$/s', $trimmed)) {
            return $value;
        }

        // Variable reference
        if (str_starts_with($trimmed, '$')) {
            return $value;
        }

        // Numeric value
        if (is_numeric($trimmed)) {
            return $value;
        }

        // Boolean/null constants
        if (in_array(strtolower($trimmed), ['true', 'false', 'null'], true)) {
            return $value;
        }

        // Function call (word followed by parenthesis)
        if (preg_match('/^[a-z_][a-z0-9_]*\s*\(/i', $trimmed)) {
            return $value;
        }

        // Array syntax
        if (str_starts_with($trimmed, '[') || str_starts_with($trimmed, 'array(')) {
            return $value;
        }

        // Plain text - wrap in double quotes, escape existing quotes and backslashes
        $escaped = str_replace(['\\', '"'], ['\\\\', '\\"'], $value);
        return '"' . $escaped . '"';
    }
}
