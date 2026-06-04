# Test Artifacts Obfuscator (Anonymizer)

The `obfuscate.py` tool is a utility designed to replace potentially sensitive or uniquely-identifying information in `uss_qualifier` test artifacts with generic, pseudo-anonymized values.  This can be useful if otherwise hesitant to submit uss_qualifier artifacts publicly when requesting help or reporting issues.

## Capabilities

The tool can obfuscate three main types of identifying information:
- **Participant IDs**: Replaces all detected participant IDs (both individual and aggregate ones) with generic values (e.g., `participant1`, `participant2`).
- **Server Hostnames**: Detects URLs within files and replaces their hostnames with generic values (e.g., `host1`, `host2`), keeping any port numbers intact.
- **Authorization Tokens**: Redacts any authorization bearer tokens present in request headers (e.g., replacing them with `Bearer REDACTED`).

By default, all of these options are enabled.

## Inputs and Outputs

The tool accepts:
- A local directory containing test artifacts, or
- A `.zip` archive containing test artifacts.

It will produce the corresponding output format matching your path (either a local directory or a `.zip` archive).

## How to Get Detailed Option Help

Detailed information on command-line options and toggles can be retrieved using the `--help` flag:

```bash
PYTHONPATH=. uv run --index https://pypi.org/simple python monitoring/uss_qualifier/reports/obfuscate.py --help
```

## Running Locally

To run the obfuscation tool locally:

```bash
PYTHONPATH=. uv run --index https://pypi.org/simple python monitoring/uss_qualifier/reports/obfuscate.py <input-folder-or-zip> <output-folder-or-zip>
```

## Running via Docker

If you prefer to run the tool within a container, build the docker image using `make image` from the repo root, and execute:

```bash
docker run --rm \
  -v "/path/to/local/input_artifacts:/input" \
  -v "/path/to/local/output_dir:/output" \
  interuss/monitoring \
  uv run uss_qualifier/reports/obfuscate.py /input /output/obfuscated_artifacts.zip
```

Ensure that you mount the correct local directories to access your input artifacts and retrieve your obfuscated output.

> [!WARNING]
> This tool performs pseudo-anonymization based on heuristics and automated string scanning. It does not guarantee complete anonymization. Review the obfuscated artifacts for any remaining sensitive information before publishing or distributing them when appropriate.
