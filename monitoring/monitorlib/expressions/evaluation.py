from typing import Any

from asteval import Interpreter, make_symbol_table
from loguru import logger

from monitoring.monitorlib.expressions.types import ASTExpression, SymbolExpression


def _truncate(s: str) -> str:
    max_len = 80
    if len(s) <= max_len:
        return s
    return f"{s[0 : max_len - 3]}..."


def _abbreviate(s: str) -> str:
    max_len = 500
    if len(s) <= max_len:
        return s
    snippset_len = int(max_len / 2) - 4
    return f"{s[0:snippset_len]} [...] {s[-snippset_len:]}"


def _raise_evaluation_error(msg: str, interpreter: Interpreter) -> None:
    err = interpreter.error[0].get_error()

    detail = "\n".join(_abbreviate(line) for line in err[1].split("/n"))

    default_symbols = make_symbol_table()
    custom_symbols = {}
    for k, v in interpreter.symtable.items():
        if k not in default_symbols or default_symbols[k] != v:
            custom_symbols[k] = v

    logger.debug(
        "asteval interpreter symbol table:\n"
        + "\n".join(f"  {k}: {_truncate(str(v))}" for k, v in custom_symbols.items())
    )
    raise ValueError(f"{msg}:\n{detail}")


def evaluate_expression(
    expression: ASTExpression, name: str, interpreter: Interpreter
) -> Any:
    """Evaluate `expression` for a variable of `name` using `interpreter`.

    Enhanced information is logged for failures."""
    result = interpreter.eval(expression)
    if isinstance(interpreter.error, list) and len(interpreter.error) > 0:
        _raise_evaluation_error(f"Error evaluating {name} '{expression}'", interpreter)
    return result


def get_updated_context(
    existing_symbols: dict[str, Any], new_expressions: list[SymbolExpression]
) -> tuple[dict[str, Any], Interpreter]:
    """Starting from a context of `existing_symbols` and their values, evaluate the `new_expressions`.

    Returns:
    * Updated context of new symbols and their values.
    * Interpreter ready to evaluate more expressions with the updated context.
    """
    updated_symbols = dict(existing_symbols)
    interpreter = Interpreter(user_symbols=updated_symbols)
    for sym_expr in new_expressions:
        value = evaluate_expression(sym_expr.value, sym_expr.name, interpreter)
        interpreter.symtable[sym_expr.name] = value
        updated_symbols[sym_expr.name] = value

    return updated_symbols, interpreter
