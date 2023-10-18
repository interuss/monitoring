import os.path

import marko
import marko.block
import marko.inline


def check_local_links(
    parent: marko.block.Element, doc_path: str, repo_root: str
) -> None:
    github_base_url = os.environ.get("MONITORING_GITHUB_ROOT", "")
    if not github_base_url:
        github_base_url = "https://github.com/interuss/monitoring"
    repo_content_base_url = github_base_url + "/tree/main/"
    if isinstance(parent, marko.inline.Link):
        if parent.dest.startswith(repo_content_base_url):
            relative_path = parent.dest[len(repo_content_base_url) :]
        elif parent.dest.startswith("http://") or parent.dest.startswith("https://"):
            # Don't check absolute paths to other locations
            relative_path = None
        else:
            md_path = os.path.relpath(os.path.dirname(doc_path), repo_root)
            relative_path = os.path.join(md_path, parent.dest)
        if relative_path is not None:
            if "#" in relative_path:
                relative_path = relative_path.split("#")[0]
            abs_path = os.path.realpath(os.path.join(repo_root, relative_path))
            if not os.path.exists(abs_path):
                md_relative_path = os.path.relpath(doc_path, repo_root)
                raise ValueError(
                    f"Document {md_relative_path} has a link to {parent.dest} but {relative_path} does not exist in the repository ({abs_path} in the repo_hygiene container)"
                )
    else:
        if hasattr(parent, "children") and not isinstance(parent.children, str):
            for child in parent.children:
                check_local_links(child, doc_path, repo_root)
