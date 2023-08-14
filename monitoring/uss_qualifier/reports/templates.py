import json
import shutil
import os

from loguru import logger

from monitoring.uss_qualifier.configurations.configuration import (
    ArtifactsConfiguration,
    TemplatedReportConfiguration,
    TemplatedReportApplicationConfiguration,
)
from monitoring.uss_qualifier.reports.report import TestRunReport
import requests, zipfile, io
import pathlib
import hashlib
import fileinput

CACHE_TEMPLATE_PATH = ".templates_cache/"
TEMPLATE_CONFIGURATION_MARK = "<!-- Configuration goes here -->"


def _hash_url(url: str) -> str:
    sig = hashlib.sha256()
    sig.update(url.encode("utf-8"))
    return sig.hexdigest()


class RenderedApplicationConfiguration(TemplatedReportApplicationConfiguration):
    report: TestRunReport
    """Report instance to inject in the application"""


class TemplateRenderer:
    """
    This class is responsible to retrieve report templates and render a report
    Rendering is achieved using the following steps:
    1. Download a template which is composed of a zip file containing a index.html. For convenience,
    it can be versioned and hosted using a Github release.
    2. Replace the TEMPLATE_CONFIGURATION_MARK by a script tag. The tag sets a `interuss` variable
    at the window level which can be leverage by the encompassed javascript code. <script>window.interuss=`[JSON]`;</script>
    where [JSON] is a RenderedApplicationConfiguration JSON serialized object.
    """

    def __init__(self, template: TemplatedReportConfiguration, report: TestRunReport):
        self._template = template
        self._report = report

    def _download_template(self) -> pathlib.Path:
        url = self._template.template_url
        path = pathlib.Path(CACHE_TEMPLATE_PATH, _hash_url(url))
        if path.exists():
            logger.debug(f"{url} already in cache ({path}). Skip download.")
        else:
            req = requests.get(url)
            z = zipfile.ZipFile(io.BytesIO(req.content))
            z.extractall(path)
            logger.debug(f"{url} extracted to {path}")
        return path

    def render(self):
        # Copy template
        src = pathlib.Path(self._download_template(), "index.html")
        dst = pathlib.Path(self._template.output_path)

        # Configure application
        rendered_configuration = json.dumps(
            RenderedApplicationConfiguration(
                self._template.configuration, report=self._report
            )
        ).replace("`", "\\`")
        injected_configuration = (
            f"<script>window.interuss=`{rendered_configuration}`;</script>"
        )

        content = src.read_text()
        content = content.replace(TEMPLATE_CONFIGURATION_MARK, injected_configuration)
        with open(dst, "w") as fw:
            fw.write(content)

        logger.info(f"Templated report rendered to {dst}")


def render_templates(config: ArtifactsConfiguration, report: TestRunReport):
    pathlib.Path(CACHE_TEMPLATE_PATH).mkdir(parents=True, exist_ok=True)
    for template in config.report_templates:
        TemplateRenderer(template, report).render()
