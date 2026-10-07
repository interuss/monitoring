import os

from monitoring.uss_qualifier.configurations.configuration import ArtifactsConfiguration
from monitoring.uss_qualifier.reports import jinja_env


def write_ai_helper_files(output_path: str, artifacts: ArtifactsConfiguration) -> None:
    # Ensure output_path exists
    os.makedirs(output_path, exist_ok=True)

    # Extract subfolder names for tested requirements configurations
    tested_requirements_folders = (
        [cfg.report_name for cfg in artifacts.tested_requirements]
        if artifacts.tested_requirements
        else []
    )

    # Render and write AGENTS.md
    agents_template = jinja_env.get_template("ai_helpers/AGENTS.md.template")
    agents_content = agents_template.render()
    with open(os.path.join(output_path, "AGENTS.md"), "w") as f:
        f.write(agents_content)

    # Render and write README.md
    readme_template = jinja_env.get_template("ai_helpers/README.md.template")
    readme_content = readme_template.render(
        has_raw_report=(artifacts.raw_report is not None),
        tested_requirements_folders=tested_requirements_folders,
        has_timing_report=(artifacts.timing_report is not None),
        has_globally_expanded_report=(artifacts.globally_expanded_report is not None),
        has_report_html=(artifacts.report_html is not None),
    )
    with open(os.path.join(output_path, "README.md"), "w") as f:
        f.write(readme_content)
