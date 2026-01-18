<?php
/**
 * Single-pass regex tokenizer for Cortex template syntax.
 *
 * Converts template strings containing Cortex syntax into an array
 * of Token objects for compilation. Handles MyBB's addslashes()
 * escaping transparently.
 *
 * @package Cortex
 * @author Corta Labs
 * @license MIT
 */

declare(strict_types=1);

namespace Cortex;

use Cortex\Exceptions\ParseException;

/**
 * Parser for Cortex template syntax.
 *
 * Recognizes the following constructs:
 * - Conditionals: <if condition then>, <else if condition then>, <else />, </if>
 * - Functions: <func name>, </func>
 * - Templates: <template name>
 * - Expressions: {= expression }
 * - Variables: <setvar name>value</setvar>
 *
 * Example usage:
 * ```php
 * $parser = new Parser();
 * $tokens = $parser->parse('<if $user then>Welcome!</if>');
 * // Returns: [Token(IF_OPEN), Token(TEXT), Token(IF_CLOSE)]
 * ```
 */
class Parser
{
    /**
     * Regex patterns for each construct.
     *
     * Order matters for the combined pattern - more specific patterns
     * should come before more general ones.
     *
     * Pattern notes:
     * - All patterns use case-insensitive matching (i flag)
     * - Patterns use # as delimiter to avoid escaping /
     * - Capturing groups extract the relevant parts
     */
    private const PATTERNS = [
        // <if condition then> - captures condition
        'if_open' => '#<if\s+(.*?)\s+then>#si',

        // <else if condition then> - captures condition
        'elseif' => '#<else\s+if\s+(.*?)\s+then>#si',

        // <else /> or <else/> - no capture needed
        'else' => '#<else\s*/?>#si',

        // </if> - no capture needed
        'if_close' => '#</if>#si',

        // <func name> - captures function name (letters/underscores only)
        'func_open' => '#<func\s+([a-z_][a-z0-9_]*)>#si',

        // </func> - no capture needed
        'func_close' => '#</func>#si',

        // <template name> or <template name /> - captures template name
        'template' => '#<template\s+([a-z0-9_\-\s]+)(?:\s*/)?\>#si',

        // {= expression } - captures expression (new safe syntax)
        'expression' => '#\{=\s*(.*?)\s*\}#s',

        // <setvar name>value</setvar> - captures name and value
        'setvar' => '#<setvar\s+([a-z][a-z0-9_]*)>(.*?)</setvar>#si',
    ];

    /**
     * Combined pattern for single-pass tokenization.
     *
     * Built from PATTERNS on first use and cached.
     */
    private ?string $combinedPattern = null;

    /**
     * Map of pattern keys to token types.
     */
    private const TYPE_MAP = [
        'if_open' => TokenType::IF_OPEN,
        'elseif' => TokenType::ELSEIF,
        'else' => TokenType::ELSE,
        'if_close' => TokenType::IF_CLOSE,
        'func_open' => TokenType::FUNC_OPEN,
        'func_close' => TokenType::FUNC_CLOSE,
        'template' => TokenType::TEMPLATE,
        'expression' => TokenType::EXPRESSION,
        'setvar' => TokenType::SETVAR,
    ];

    /**
     * Optional template name for error messages.
     */
    private ?string $templateName = null;

    /**
     * Tokenize template content into Token array.
     *
     * @param string $template The template content to parse
     * @param string|null $templateName Optional template name for error messages
     * @return Token[] Array of Token objects
     * @throws ParseException On syntax errors
     */
    public function parse(string $template, ?string $templateName = null): array
    {
        $this->templateName = $templateName;

        // NOTE: We do NOT unescape the template. MyBB's addslashes() escaping
        // must be preserved for the final eval(). The Cortex syntax patterns
        // work correctly with escaped content, and TEXT tokens pass through
        // with their escaping intact.

        // Quick check - if no syntax markers exist, return single TEXT token
        if (!$this->hasSyntax($template)) {
            if ($template === '') {
                return [];
            }
            return [Token::text($template, 0)];
        }

        $tokens = [];
        $matches = $this->findAllMatches($template);

        // Sort matches by position to process in order
        usort($matches, fn($a, $b) => $a['position'] <=> $b['position']);

        $currentPosition = 0;

        foreach ($matches as $match) {
            // Add TEXT token for content before this match
            if ($match['position'] > $currentPosition) {
                $textContent = substr($template, $currentPosition, $match['position'] - $currentPosition);
                if ($textContent !== '') {
                    $tokens[] = Token::text($textContent, $currentPosition);
                }
            }

            // Add the matched token
            $tokens[] = $this->createToken($match);

            // Move position past this match
            $currentPosition = $match['position'] + strlen($match['full']);
        }

        // Add any remaining text after the last match
        if ($currentPosition < strlen($template)) {
            $remainingText = substr($template, $currentPosition);
            if ($remainingText !== '') {
                $tokens[] = Token::text($remainingText, $currentPosition);
            }
        }

        // Validate token structure
        $this->validateStructure($tokens);

        return $tokens;
    }

    /**
     * Quick check if template contains any Cortex syntax.
     *
     * @param string $template The template content
     * @return bool True if syntax markers are present
     */
    private function hasSyntax(string $template): bool
    {
        // Quick string checks before expensive regex
        return (
            str_contains($template, '<if ') ||
            str_contains($template, '<else') ||
            str_contains($template, '</if>') ||
            str_contains($template, '<func ') ||
            str_contains($template, '</func>') ||
            str_contains($template, '<template ') ||
            str_contains($template, '{=') ||
            str_contains($template, '<setvar ')
        );
    }

    /**
     * Find all syntax matches in the template.
     *
     * @param string $template The template content
     * @return array[] Array of match information
     */
    private function findAllMatches(string $template): array
    {
        $allMatches = [];

        foreach (self::PATTERNS as $type => $pattern) {
            if (preg_match_all($pattern, $template, $matches, PREG_OFFSET_CAPTURE | PREG_SET_ORDER)) {
                foreach ($matches as $match) {
                    $matchInfo = [
                        'type' => $type,
                        'full' => $match[0][0],
                        'position' => $match[0][1],
                    ];

                    // Extract captured groups based on type
                    if (isset($match[1])) {
                        $matchInfo['capture1'] = $match[1][0];
                    }
                    if (isset($match[2])) {
                        $matchInfo['capture2'] = $match[2][0];
                    }

                    $allMatches[] = $matchInfo;
                }
            }
        }

        return $allMatches;
    }

    /**
     * Create a Token from match information.
     *
     * @param array $match The match information
     * @return Token
     */
    private function createToken(array $match): Token
    {
        $type = $match['type'];
        $position = (int)$match['position'];
        $value = $match['full'];

        return match ($type) {
            'if_open' => Token::ifOpen($value, $position, $match['capture1']),
            'elseif' => Token::elseIf($value, $position, $match['capture1']),
            'else' => Token::else($value, $position),
            'if_close' => Token::ifClose($value, $position),
            'func_open' => Token::funcOpen($value, $position, $match['capture1']),
            'func_close' => Token::funcClose($value, $position),
            'template' => Token::template(trim($match['capture1']), $position),
            'expression' => Token::expression($match['capture1'], $position),
            'setvar' => Token::setVar($value, $position, $match['capture1'], $match['capture2']),
        };
    }

    /**
     * Validate the token structure for balanced tags.
     *
     * @param Token[] $tokens The tokens to validate
     * @throws ParseException If structure is invalid
     */
    private function validateStructure(array $tokens): void
    {
        $ifStack = [];
        $funcStack = [];

        foreach ($tokens as $token) {
            switch ($token->type) {
                case TokenType::IF_OPEN:
                    $ifStack[] = $token;
                    break;

                case TokenType::ELSEIF:
                case TokenType::ELSE:
                    if (empty($ifStack)) {
                        throw ParseException::unexpected(
                            $token->type === TokenType::ELSEIF ? 'else if' : 'else',
                            $token->position,
                            $this->templateName
                        );
                    }
                    break;

                case TokenType::IF_CLOSE:
                    if (empty($ifStack)) {
                        throw ParseException::unexpected('if', $token->position, $this->templateName);
                    }
                    array_pop($ifStack);
                    break;

                case TokenType::FUNC_OPEN:
                    $funcStack[] = $token;
                    break;

                case TokenType::FUNC_CLOSE:
                    if (empty($funcStack)) {
                        throw ParseException::unexpected('func', $token->position, $this->templateName);
                    }
                    array_pop($funcStack);
                    break;
            }
        }

        // Check for unclosed tags
        if (!empty($ifStack)) {
            $unclosed = end($ifStack);
            throw ParseException::unclosed('if', $unclosed->position, $this->templateName);
        }

        if (!empty($funcStack)) {
            $unclosed = end($funcStack);
            throw ParseException::unclosed('func', $unclosed->position, $this->templateName);
        }
    }

}
