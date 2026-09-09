#!/usr/bin/env python3
"""
Compare a live Azure DevOps pipeline run against the live GitHub Actions run
of its migrated workflow, for the same repository commit.

Unlike the baseline checks in validate_migration.py, nothing here is measured
by hand: the "expected" column is read from the Azure DevOps REST API and the
"actual" column from the GitHub Actions REST API.

Outcomes per service:
  PASS       both systems ran the commit and their results agree
  MISMATCH   both systems ran the commit and their results differ
  EXCEPTION  one side has no run for the commit (reported, not silently passed)
"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from io import BytesIO

TIMEOUT = 30


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def _get(url: str, headers: dict, binary: bool = False):
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            payload = response.read()
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"HTTP {error.code} for {url}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"{error.reason} for {url}") from error
    return payload if binary else json.loads(payload or b"{}")


ADO_RESOURCE = "499b84ac-1321-427f-aa17-267ca6975798/.default"


def _entra_token() -> str | None:
    """Exchange an Entra service-principal client secret for an ADO token."""
    tenant = os.environ.get("AZURE_TENANT_ID")
    client_id = os.environ.get("AZURE_CLIENT_ID")
    secret = os.environ.get("AZURE_CLIENT_SECRET")
    if not (tenant and client_id and secret):
        return None
    body = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": secret,
        "scope": ADO_RESOURCE,
        "grant_type": "client_credentials",
    }).encode()
    request = urllib.request.Request(
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token", data=body
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read())["access_token"]


def ado_credentials() -> dict | None:
    """Authorization headers for the ADO REST API, or None when unavailable."""
    pat = os.environ.get("AZURE_DEVOPS_EXT_PAT")
    if pat:
        token = base64.b64encode(f":{pat}".encode()).decode()
        return {"Authorization": f"Basic {token}", "Accept": "application/json"}
    try:
        bearer = _entra_token()
    except (urllib.error.URLError, KeyError, ValueError):
        return None
    if not bearer:
        return None
    return {"Authorization": f"Bearer {bearer}", "Accept": "application/json"}


def _gh_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


# ---------------------------------------------------------------------------
# Azure DevOps side
# ---------------------------------------------------------------------------

def ado_facts(org: str, project: str, pipeline: str, sha: str, headers: dict) -> dict:
    """Collect result, test count and artifacts for an ADO run of `sha`."""
    base = f"https://dev.azure.com/{urllib.parse.quote(org)}/{urllib.parse.quote(project)}/_apis"

    definitions = _get(
        f"{base}/build/definitions?name={urllib.parse.quote(pipeline)}&api-version=7.1",
        headers,
    ).get("value") or []
    if not definitions:
        return {"status": "exception", "reason": f"no ADO pipeline named {pipeline}"}
    definition_id = definitions[0]["id"]

    builds = _get(
        f"{base}/build/builds?definitions={definition_id}"
        f"&statusFilter=completed&$top=50&api-version=7.1",
        headers,
    ).get("value") or []
    build = next((b for b in builds if (b.get("sourceVersion") or "").startswith(sha[:12])), None)
    if build is None:
        return {
            "status": "exception",
            "reason": f"no completed ADO run of {pipeline} for commit {sha[:8]}",
            "definition_id": definition_id,
        }

    build_id = build["id"]
    artifacts = _get(
        f"{base}/build/builds/{build_id}/artifacts?api-version=7.1", headers
    ).get("value") or []

    runs = _get(
        f"{base}/test/runs?buildUri={urllib.parse.quote(build['uri'])}&api-version=7.1",
        headers,
    ).get("value") or []
    total = sum(int(r.get("totalTests") or 0) for r in runs)
    passed = sum(int(r.get("passedTests") or 0) for r in runs)

    return {
        "status": "ok",
        "build_id": build_id,
        "url": build.get("_links", {}).get("web", {}).get("href", ""),
        "result": build.get("result", "unknown"),
        "commit": build.get("sourceVersion", ""),
        "tests_total": total,
        "tests_passed": passed,
        "artifacts": sorted(a["name"] for a in artifacts),
    }


# ---------------------------------------------------------------------------
# GitHub Actions side
# ---------------------------------------------------------------------------

def _count_junit_tests(blob: bytes) -> int:
    """Sum testcase elements across every JUnit XML file in a zip artifact."""
    count = 0
    with zipfile.ZipFile(BytesIO(blob)) as archive:
        for name in archive.namelist():
            if not name.endswith(".xml"):
                continue
            try:
                root = ET.fromstring(archive.read(name))
            except ET.ParseError:
                continue
            suites = [root] if root.tag == "testsuite" else root.iter("testsuite")
            for suite in suites:
                count += len(suite.findall("testcase"))
    return count


def gha_facts(repo: str, workflow: str, sha: str, token: str) -> dict:
    """Collect conclusion, test count and artifacts for a GHA run of `sha`."""
    base = f"https://api.github.com/repos/{repo}"
    headers = _gh_headers(token)

    runs = _get(
        f"{base}/actions/workflows/{urllib.parse.quote(workflow)}/runs"
        f"?head_sha={sha}&per_page=1",
        headers,
    ).get("workflow_runs") or []
    if not runs:
        return {"status": "exception", "reason": f"no GHA run of {workflow} for commit {sha[:8]}"}
    run = runs[0]

    artifacts = _get(
        f"{base}/actions/runs/{run['id']}/artifacts?per_page=100", headers
    ).get("artifacts") or []

    tests = 0
    for artifact in artifacts:
        if "test" not in artifact["name"].lower():
            continue
        try:
            tests += _count_junit_tests(
                _get(artifact["archive_download_url"], headers, binary=True)
            )
        except (RuntimeError, zipfile.BadZipFile):
            continue

    return {
        "status": "ok",
        "run_id": run["id"],
        "url": run.get("html_url", ""),
        "result": run.get("conclusion") or run.get("status") or "unknown",
        "commit": run.get("head_sha", ""),
        "tests_total": tests,
        "artifacts": sorted(a["name"] for a in artifacts),
    }


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

_RESULT_EQUIVALENTS = {
    "succeeded": "success",
    "partiallysucceeded": "success",
    "success": "success",
    "failed": "failure",
    "failure": "failure",
    "canceled": "cancelled",
    "cancelled": "cancelled",
}


def _normalise(result: str) -> str:
    return _RESULT_EQUIVALENTS.get((result or "").lower(), (result or "").lower())


def compare(service: str, sha: str, ado: dict, gha: dict) -> tuple[str, str]:
    """Return (outcome, markdown) for one service."""
    lines = [
        f"### Runtime Parity — `{service}`",
        "",
        f"**Commit:** `{sha[:8]}`",
        "",
    ]

    if ado["status"] != "ok" or gha["status"] != "ok":
        reason = ado.get("reason") or gha.get("reason")
        lines += [
            f"**Outcome: EXCEPTION** — {reason}.",
            "",
            "No parity claim is made for this commit.",
        ]
        return "EXCEPTION", "\n".join(lines)

    rows = [
        ("Result", ado["result"], gha["result"], _normalise(ado["result"]) == _normalise(gha["result"])),
        ("Tests run", str(ado["tests_total"]), str(gha["tests_total"]), ado["tests_total"] == gha["tests_total"]),
        ("Artifacts", str(len(ado["artifacts"])), str(len(gha["artifacts"])), len(ado["artifacts"]) == len(gha["artifacts"])),
    ]

    lines += [
        "| Signal | Azure DevOps | GitHub Actions | Match |",
        "|--------|--------------|----------------|-------|",
    ]
    lines += [f"| {n} | {a} | {g} | {'yes' if m else 'NO'} |" for n, a, g, m in rows]
    lines += [
        "",
        f"ADO run [{ado['build_id']}]({ado['url']}) · "
        f"GHA run [{gha['run_id']}]({gha['url']})",
        "",
        f"- ADO artifacts: {', '.join(ado['artifacts']) or 'none'}",
        f"- GHA artifacts: {', '.join(gha['artifacts']) or 'none'}",
        "",
    ]

    mismatched = [n for n, _, _, m in rows if not m]
    if mismatched:
        lines.append(f"**Outcome: MISMATCH** — {', '.join(mismatched)} differ; remediation required.")
        return "MISMATCH", "\n".join(lines)
    lines.append("**Outcome: PASS** — measured from both live runs, not from a stored baseline.")
    return "PASS", "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="ADO ↔ GHA runtime parity report")
    parser.add_argument("--service", required=True)
    parser.add_argument("--ado-org", required=True)
    parser.add_argument("--ado-project", required=True)
    parser.add_argument("--ado-pipeline", required=True, help="ADO pipeline definition name")
    parser.add_argument("--gh-repo", required=True, help="owner/name")
    parser.add_argument("--gh-workflow", required=True, help="Workflow file name")
    parser.add_argument("--sha", required=True, help="Commit both systems must have run")
    parser.add_argument("--output", help="Write the markdown report here as well")
    args = parser.parse_args()

    ado_headers = ado_credentials()
    token = os.environ.get("GITHUB_TOKEN", "")
    if not ado_headers or not token:
        print(
            f"### Runtime Parity — `{args.service}`\n\n"
            "**Outcome: EXCEPTION** — no Azure DevOps or GitHub credentials are available, "
            "so no live comparison was attempted."
        )
        return 0

    try:
        ado = ado_facts(args.ado_org, args.ado_project, args.ado_pipeline, args.sha, ado_headers)
        gha = gha_facts(args.gh_repo, args.gh_workflow, args.sha, token)
    except RuntimeError as error:
        print(
            f"### Runtime Parity — `{args.service}`\n\n"
            f"**Outcome: EXCEPTION** — could not read run data: {error}"
        )
        return 0

    outcome, report = compare(args.service, args.sha, ado, gha)
    print(report)
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w") as handle:
            handle.write(report)
    return 1 if outcome == "MISMATCH" else 0


if __name__ == "__main__":
    sys.exit(main())
