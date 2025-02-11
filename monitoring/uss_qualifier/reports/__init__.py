import os

from jinja2 import Environment, FileSystemLoader

jinja_env = Environment(
    loader=FileSystemLoader(
        [
            os.path.abspath(os.path.join(os.path.dirname(__file__), relpath))
            for relpath in ("templates", "../../monitorlib/html/templates")
        ]
    ),
    trim_blocks=True,
    lstrip_blocks=True,
)
