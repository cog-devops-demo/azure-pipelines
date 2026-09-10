# settlement-gateway: ADO classic → GitHub Actions

## Source

Not a YAML file. `settlement-gateway-classic` is an Azure DevOps **classic (designer)**
build definition, id 9 in org `danagajewski`, project `danagajewski-demo`, read through:

    GET https://dev.azure.com/danagajewski/danagajewski-demo/_apis/build/definitions/9?api-version=7.1

A sanitized export is committed at `docs/migration/ado-exports/settlement-gateway-classic.json`
so the validator has a checked-in source to diff against.

## Intent

Build, test, version-stamp and package the settlement-gateway Python service, then publish a
drop containing the package, a reproducible build manifest and a registry receipt. The
manifest is what a downstream legacy release job consumes, so its shape is load-bearing:
component, version, branch, buildId, environment, and a SHA256 per source file.

Versioning is branch-derived: `4.2.<buildId>` with `-rc` on `release*`, `-hf` on `hotfix*`,
`-dev` on anything other than `main`.

Artifact registration targeted Artifactory over a shared service account. There is no
Artifactory in this estate, so the task writes a local receipt with `status: skipped` unless
`SETTLEMENT_REGISTRY_URL` is set. That behavior is preserved rather than removed — dropping it
would change what the pipeline claims to have done.

## Mapping

| ADO classic | GitHub Actions |
|---|---|
| Phase `Build settlement gateway`, agent `ubuntu-22.04`, 60 min | job `build`, `runs-on: ubuntu-22.04`, `timeout-minutes: 60` |
| (implicit designer checkout) | `actions/checkout@v4` |
| `Use Python 3.11` (UsePythonVersion) | `actions/setup-python@v5`, 3.11, x64 |
| `Stamp version and write build manifest` (inline pwsh) | same script, `shell: pwsh` |
| `Install dependencies` (inline bash) | same script |
| `Run unit tests` (inline bash, pytest + junitxml) | same script |
| `Publish test results` (PublishTestResults, JUnit) | `actions/upload-artifact@v4` — `settlement-gateway-test-results` |
| `Package and register artifact` (inline pwsh) | same script, `shell: pwsh` |
| `Publish build artifact` (PublishBuildArtifacts) | `actions/upload-artifact@v4` — `settlement-gateway-drop` |
| CI trigger, `main`, path `/services/settlement-gateway` | `on.push`, `main`, `services/settlement-gateway/**` |
| PR trigger, `main`, same path filter | `on.pull_request`, `main`, same paths |
| Variable `SETTLEMENT_ENV = dev` | workflow-level `env.SETTLEMENT_ENV` |

### Agent variables

The inline scripts read ADO agent variables directly, so a step maps them onto the GitHub
runner rather than rewriting the scripts:

| ADO | GitHub |
|---|---|
| `BUILD_SOURCEBRANCHNAME` | `${GITHUB_REF_NAME##*/}` — ADO passes the last segment of `Build.SourceBranch`, so a PR is `merge`, not `43/merge`; the value lands in the manifest |
| `BUILD_BUILDID` | `GITHUB_RUN_ID` |
| `BUILD_SOURCESDIRECTORY` | `GITHUB_WORKSPACE` |
| `BUILD_ARTIFACTSTAGINGDIRECTORY` | `$RUNNER_TEMP/a` |

`##vso[task.setvariable variable=settlementVersion]` becomes an append to `$GITHUB_ENV`;
`##vso[task.logissue type=error|warning]` becomes `::error::` / `::warning::`.

## Not carried over

Nothing. This is a lift and shift: no template extraction, no added scanning, no changed
runner image. Standardization is a later phase.

## Equivalence

Decided by the runtime parity section of `validate-migration`, which compares the ADO run and
the GHA run of the same commit on result, test count and artifact names — not by the stored
baselines, which are advisory. If ADO has no completed run for the commit the row is an
EXCEPTION, which is not a pass.

The first run of this PR was exactly that EXCEPTION: definition 9's pull-request trigger
carried a `/services/settlement-gateway` path filter, so a PR that only adds a workflow and
this document never produced an ADO build to compare against. The filter was dropped from the
PR trigger (the CI trigger on `main` keeps it), matching the other pipelines in the estate, so
both platforms now build the same merge ref.
