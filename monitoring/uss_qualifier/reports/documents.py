from monitoring.uss_qualifier.reports import jinja_env
from monitoring.uss_qualifier.reports.report import TestRunReport


def make_report_html(report: TestRunReport) -> str:
    template = jinja_env.get_template("report.html")
    return template.render(report=report)
