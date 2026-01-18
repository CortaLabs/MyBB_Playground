<?php
/**
 * Token type enumeration for the Cortex template parser.
 *
 * Defines all recognized token types that the parser can produce
 * during template tokenization.
 *
 * @package Cortex
 * @author Corta Labs
 * @license MIT
 */

declare(strict_types=1);

namespace Cortex;

/**
 * Enumeration of all token types recognized by the Cortex parser.
 *
 * Token types are grouped by their function:
 * - Control flow: IF_OPEN, ELSEIF, ELSE, IF_CLOSE
 * - Functions: FUNC_OPEN, FUNC_CLOSE
 * - Content: TEXT, TEMPLATE, EXPRESSION, SETVAR
 */
enum TokenType: string
{
    /**
     * Plain text content (not matching any syntax pattern).
     */
    case TEXT = 'text';

    /**
     * Opening if statement: <if condition then>
     */
    case IF_OPEN = 'if_open';

    /**
     * Else-if clause: <else if condition then>
     */
    case ELSEIF = 'elseif';

    /**
     * Else clause: <else /> or <else/>
     */
    case ELSE = 'else';

    /**
     * Closing if statement: </if>
     */
    case IF_CLOSE = 'if_close';

    /**
     * Opening function call: <func name>
     */
    case FUNC_OPEN = 'func_open';

    /**
     * Closing function call: </func>
     */
    case FUNC_CLOSE = 'func_close';

    /**
     * Template inclusion: <template name>
     */
    case TEMPLATE = 'template';

    /**
     * Expression evaluation: {= expression }
     */
    case EXPRESSION = 'expression';

    /**
     * Variable assignment: <setvar name>value</setvar>
     */
    case SETVAR = 'setvar';
}
