import marko.element


def text_of(value: marko.element.Element) -> str:
    """Gets the plain text contained within a Markdown element"""
    if isinstance(value, str):
        return value
    elif isinstance(value, marko.block.BlockElement):
        result = ""
        for child in value.children:
            result += text_of(child)
        return result
    elif isinstance(value, marko.inline.InlineElement):
        if isinstance(value, marko.inline.LineBreak):
            return "\n"
        if isinstance(value.children, str):
            return value.children
        result = ""
        for child in value.children:
            result += text_of(child)
        return result
    else:
        raise NotImplementedError(
            "Cannot yet extract raw text from {}".format(value.__class__.__name__)
        )
