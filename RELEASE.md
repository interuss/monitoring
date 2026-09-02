# Release Management

## Background

Releases of `monitoring` utilize Git tags structured precisely as `interuss/monitoring/v[X].[Y].[Z]`, optionally accompanied by strict pre-release/candidate identifiers adhering to **PEP 440 Pre-Release Conventions**. 

This formatting conforms to the InterUSS Component Registry pattern: `[owner]/[component]/[semantic version]`. (See [Semantic Versioning](https://semver.org) and [PEP 440 Version Identification](https://peps.python.org/pep-0440/)).

Keeping track of breaking changes and migration instructions is done through the [NEXT_RELEASE_NOTES.md](NEXT_RELEASE_NOTES.md) file, which is updated as features are added or modified and serves as a basis for release notes.

### PEP 440 Versioning, Validation, & PyPI Releases
For compatibility with PyPI (Python Package Index) and Docker registry distributions, versions must follow the conventions below:
*   **Official Releases (`vX.Y.Z`)**: Output purely as canonical, unmodified Semantic Versions (`X.Y.Z`). These artifacts are fully eligible for publishing to PyPI.
*   **Release Candidates (`vX.Y.Z-rc[N]`)**: **Strict Pre-Release Identifiers**. 
    *   Pre-release tags **must** utilize the strictly lowercase, hyphenated `-rc[N]` suffix (e.g., `v0.31.0-rc1`). 
    *   Build tooling normalizes these delimiters into PEP 440-compliant pre-release strings (`X.Y.Zrc[N]`) for PyPI compatibility.
    *   Note: Pre-releases containing uppercase identifiers (e.g., `-RC1`), space delimiters, alphabetic metadata, or non-numeric suffixes (e.g., `-alpha`, `-1.2`) are prevented to avoid accidental malformed PyPI publication.
*   **Development & Branch Builds (`+<metadata>`)**:
    *   Any image or PyPI artifact generated from a development branch, Pull Request, or commit other than an explicitly tagged release/pre-release boundary automatically appends PEP 440 Local Version Segments utilizing the `+` delimiter (e.g., `0.31.0+gd56bb4d`). 
    *   Because PyPI rejects package uploads bearing PEP 440 `+` local-version metadata, this provides a safeguard preventing non-release/development builds from accidentally polluting the public package registry.

## PyPI Package Distribution (`interuss_monitoring`)
As part of broader interoperating improvements for the InterUSS Python ecosystem:
*   **Distribution Identity**: The `monitoring` Python codebase is published to PyPI under the canonical ecosystem package name **`interuss_monitoring`**. 
*   **Interim Import Namespace (Phase 1 Phase-in)**: 
    *   Consumers install the package via `pip install interuss_monitoring`.
    *   In the current structural phase (Phase 1), internal code modules and external users importing from the PyPI package interact with the Python Import Namespace via **`import monitoring.<submodule>`**. 
    *   *Warning for Interim Consumers*: Users must ensure their active Python virtual environment does not contain a conflicting top-level `monitoring/` directory from alternative third-party packages to prevent Python import-shadowing and runtime `ModuleNotFoundError` conflicts.
*   **Future Transition (Phase 2)**: The repository is systematically migrating towards a fully isolated `src/interuss_monitoring` layout and explicit `import interuss_monitoring.<submodule>` namespace, perfectly mirrors the architectural patterns established by `implicitdict` and `uas_standards`.

## Release procedure

Releasing a monitoring version requires the following steps:
- Select a release version `vX.Y.Z[-W]` appropriate for the release
  - `X` is the major release number
  - `Y` is the minor release number
  - `Z` is the patch number
  - (optionally) `W` is the pre-release candidate (**must strictly be formatted as `rcN`**, e.g., `rc1`, `rc2`)
  - `X`, `Y`, and `Z` should be selected according to the nature of the changes included in the release
    - See [NEXT_RELEASE_NOTES.md](./NEXT_RELEASE_NOTES.md) for the minimum version increment, and look for any changes that might suggest a more substantial category of release than the intended next version currently tracked in NEXT_RELEASE_NOTES
- Create and publish a release in GitHub:
  - On the repository, navigate to **Releases** -> **Draft a new release**.
  - For **Choose a tag**, enter `interuss/monitoring/vX.Y.Z` (or `interuss/monitoring/vX.Y.Z-rcN` for pre-releases) and click **Create new tag**.
  - Ensure the target branch is `main`.
  - For **Release title**, enter `vX.Y.Z` (or `vX.Y.Z-rcN`).
  - Click **Generate release notes**, then copy and prepend any pending content from [NEXT_RELEASE_NOTES.md](./NEXT_RELEASE_NOTES.md) to the top of the release notes.
  - Click **Publish release**.
- The GitHub workflows are triggered by the published release/tag:
  - The image publishing workflow ([.github/workflows/image-publish.yml](.github/workflows/image-publish.yml)) is triggered for every new release tag. On the canonical interuss fork, it builds and publishes the monitoring image to the [official docker registry](https://hub.docker.com/repository/docker/interuss/monitoring).
  - The package publishing workflow ([.github/workflows/publish.yaml](.github/workflows/publish.yaml)) is triggered when a release is published. It builds the `interuss_monitoring` Python distribution packages (`.tar.gz` and `.whl`) and publishes them to PyPI.
- After completing the release, open a PR to remove the pending release notes from [NEXT_RELEASE_NOTES.md](NEXT_RELEASE_NOTES.md) and update the anticipated next release version number assuming just a bug fix (e.g., v0.18.3 -> v0.18.4)
- When a PR with a change larger than the current anticipated next release version number in [NEXT_RELEASE_NOTES.md](./NEXT_RELEASE_NOTES.md) is made, it should ideally also adjust the anticipated next release version number in NEXT_RELEASE_NOTES
  - Example 1: if the most recent release was v0.18.3, NEXT_RELEASE_NOTES indicated v0.18.4, and a PR made a change larger than a bug fix, that PR should change the number in NEXT_RELEASE_NOTES to v0.19.0
  - Example 2: if the most recent release was v1.3.0, NEXT_RELEASE_NOTES indicated v1.4.0, and a PR made a bug fix or minor change, that PR does not need to update NEXT_RELEASE_NOTES
  - Example 3: if the most recent release was v3.1.4, NEXT_RELEASE_NOTES indicated v3.1.5, and a PR made a major change, that PR should change the number in NEXT_RELEASE_NOTES to v4.0.0

## Releasing from a fork

To enable releases of monitoring version in a fork, the following steps are required:
  1. Set the remote origin url of the repository of the target fork. (ie git@github.com:[owner]/monitoring.git)
  2. Edit in ([.github/workflows/image-publish.yml](.github/workflows/image-publish.yml)) the trigger to match the tags of the fork's owner as well as the job's entry condition to allow the forked repository.
  3. [Enable github actions in the forked project](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository#configuring-required-approval-for-workflows-from-public-forks).
  4. Configure the environment variables to setup the registry. (See instructions at the top of [.github/workflows/image-publish.yml](.github/workflows/image-publish.yml))

Optionally, you can manually build the monitoring docker image using [monitoring/build.sh](monitoring/build.sh), tag accordingly the image `interuss/monitoring` and push it out to an image registry of your choice.
