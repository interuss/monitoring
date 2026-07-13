from implicitdict import ImplicitDict


class ASTExpression(str):
    """AST expression with undefined return type.

    See https://lmfit.github.io/asteval/"""


class SymbolExpression(ImplicitDict):
    name: str
    """Name of symbol that will take on the value."""

    value: ASTExpression
    """Expression for the untyped value to assign to this symbol."""
