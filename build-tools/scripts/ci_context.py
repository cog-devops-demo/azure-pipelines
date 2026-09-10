"""CI context helpers shared by Azure DevOps and GitHub Actions."""

import os


def _first_set(*names: str, default: str = "unknown") -> str:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return default


def source_branch() -> str:
    return _first_set("BUILD_SOURCEBRANCH", "GITHUB_REF")


def source_commit() -> str:
    return _first_set("BUILD_SOURCEVERSION", "GITHUB_SHA")


def pipeline_name() -> str:
    return _first_set("BUILD_DEFINITIONNAME", "GITHUB_WORKFLOW")


def requested_for() -> str:
    return _first_set("BUILD_REQUESTEDFOR", "GITHUB_ACTOR")


def agent_name() -> str:
    return _first_set("AGENT_NAME", "RUNNER_NAME")


def agent_os() -> str:
    return _first_set("AGENT_OS", "RUNNER_OS")


def staging_directory() -> str:
    return _first_set(
        "BUILD_ARTIFACTSTAGINGDIRECTORY",
        default=os.environ.get("RUNNER_TEMP", "/tmp") + "/a"
        if os.environ.get("RUNNER_TEMP")
        else "/tmp",
    )


def run_url(build_id: str) -> str:
    collection_uri = os.environ.get("SYSTEM_TEAMFOUNDATIONCOLLECTIONURI")
    if collection_uri:
        return (
            collection_uri
            + os.environ.get("SYSTEM_TEAMPROJECT", "")
            + "/_build/results?buildId="
            + build_id
        )

    server_url = os.environ.get("GITHUB_SERVER_URL")
    repository = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if server_url and repository and run_id:
        return f"{server_url}/{repository}/actions/runs/{run_id}"

    return ""
