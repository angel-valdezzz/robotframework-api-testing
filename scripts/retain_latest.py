"""Delete older report artifacts only for this workflow's main executions."""

import json
import os
import urllib.request


def request(path, method="GET"):
    base = f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}"
    req = urllib.request.Request(
        base + path,
        method=method,
        headers={
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read()
        return json.loads(data) if data else None


def main():
    if os.environ["GITHUB_REF"] != "refs/heads/main":
        raise SystemExit("Cleanup is limited to main")
    current = request(f"/actions/runs/{os.environ['GITHUB_RUN_ID']}")
    artifact_id = int(os.environ["CURRENT_ARTIFACT_ID"])
    kept = request(f"/actions/artifacts/{artifact_id}")
    allowed = set(os.environ["REPORT_ARTIFACT_NAMES"].split(","))
    if (
        kept["expired"]
        or kept["name"] not in allowed
        or kept["workflow_run"]["id"] != current["id"]
    ):
        raise SystemExit("Current report artifact was not verified")
    # Collect first so pagination is not shifted while deleting.
    candidates = []
    page = 1
    while True:
        data = request(f"/actions/artifacts?per_page=100&page={page}")["artifacts"]
        if not data:
            break
        for artifact in data:
            run = artifact.get("workflow_run") or {}
            if (
                artifact["name"] in allowed
                and artifact["id"] != artifact_id
                and run.get("head_branch") == "main"
                and artifact["created_at"] < kept["created_at"]
            ):
                candidates.append(artifact)
        page += 1
    for artifact in candidates:
        run = request(f"/actions/runs/{artifact['workflow_run']['id']}")
        if run["workflow_id"] == current["workflow_id"] and run["event"] in [
            "push",
            "workflow_dispatch",
        ]:
            request(f"/actions/artifacts/{artifact['id']}", "DELETE")
            print(f"Removed previous report artifact {artifact['id']}")


if __name__ == "__main__":
    main()
