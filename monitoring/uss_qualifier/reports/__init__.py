import os

from jinja2 import FileSystemLoader, Environment


jinja_env = Environment(
    loader=FileSystemLoader(
        [
            os.path.abspath(os.path.join(os.path.dirname(__file__), relpath))
            for relpath in ("templates", "../../monitorlib/html/templates")
        ]
    )
)
