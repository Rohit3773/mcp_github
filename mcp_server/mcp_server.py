import json
import os
from typing import List, Optional

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("GitHubTools")

# ---------------- GitHub Helpers ----------------
GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


def _gh_headers() -> dict:
    if not GITHUB_TOKEN:
        raise RuntimeError("GITHUB_TOKEN not set. Put it in your .env")
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _gh_request(
    method: str,
    path: str,
    *,
    json_body: Optional[dict] = None,
    params: Optional[dict] = None,
) -> dict:
    url = f"{GITHUB_API}{path}"
    resp = requests.request(
        method,
        url,
        headers=_gh_headers(),
        json=json_body,
        params=params,
        timeout=30,
    )
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = {"message": resp.text}
        raise RuntimeError(f"GitHub API {method} {path} failed [{resp.status_code}]: {detail}")
    try:
        return resp.json()
    except Exception:
        return {"ok": True, "status": resp.status_code}

# ---------------- Tools ----------------
@mcp.tool()
def greet(name: str) -> str:
    """
    Return a friendly greeting for the given name.
    """
    return f"Hello, {name}! 👋"


@mcp.tool()
def gh_create_issue(
    owner: str,
    repo: str,
    title: str,
    body: str = "",
    labels: Optional[List[str]] = None,
    assignees: Optional[List[str]] = None,
) -> str:
    """
    Create a GitHub issue.
    Args:
      owner: org or username (e.g., 'octocat')
      repo: repository name (e.g., 'hello-world')
      title: issue title
      body: issue body (markdown)
      labels: list of label names
      assignees: list of usernames to assign
    Returns: JSON string with created issue (number, html_url, id, state)
    """
    payload = {"title": title}
    if body:
        payload["body"] = body
    if labels:
        payload["labels"] = labels
    if assignees:
        payload["assignees"] = assignees

    data = _gh_request("POST", f"/repos/{owner}/{repo}/issues", json_body=payload)
    return json.dumps(
        {
            "number": data.get("number"),
            "url": data.get("html_url"),
            "id": data.get("id"),
            "state": data.get("state"),
        },
        indent=2,
    )


@mcp.tool()
def gh_open_pull_request(
    owner: str,
    repo: str,
    head: str,
    base: str,
    title: str,
    body: str = "",
    draft: bool = False,
    maintainer_can_modify: bool = True,
) -> str:
    """
    Open a pull request.
    Args:
      owner: org or username (e.g., 'octocat')
      repo: repository name
      head: branch or 'user:branch' if from a fork (e.g., 'feature-branch' or 'octocat:feature-branch')
      base: base branch (e.g., 'main' or 'develop')
      title: PR title
      body: PR body (markdown)
      draft: create PR as draft
      maintainer_can_modify: allow maintainers to push to the source branch
    Returns: JSON string with PR info (number, html_url, id, state)
    """
    payload = {
        "title": title,
        "head": head,
        "base": base,
        "body": body,
        "draft": draft,
        "maintainer_can_modify": maintainer_can_modify,
    }
    data = _gh_request("POST", f"/repos/{owner}/{repo}/pulls", json_body=payload)
    return json.dumps(
        {
            "number": data.get("number"),
            "url": data.get("html_url"),
            "id": data.get("id"),
            "state": data.get("state"),
        },
        indent=2,
    )


@mcp.tool()
def gh_list_open_issues(
    owner: str,
    repo: str,
    labels: Optional[List[str]] = None,
    assignee: Optional[str] = None,
    limit: int = 50,
) -> str:
    """
    List open GitHub issues for a repo (excludes PRs).
    Args:
      owner: org or username (e.g., 'octocat')
      repo: repository name (e.g., 'hello-world')
      labels: filter by these label names
      assignee: filter by username assigned to the issue ('*' for any assigned)
      limit: max number of issues to return (<= 100)
    Returns: JSON string list of issues with (number, title, url, state, labels, assignees)
    """
    per_page = max(1, min(limit, 100))
    params = {
        "state": "open",
        "per_page": per_page,
    }
    if labels:
        params["labels"] = ",".join(labels)
    if assignee:
        params["assignee"] = assignee

    # NOTE: /issues returns both issues and PRs; filter out PRs by presence of "pull_request"
    items = _gh_request("GET", f"/repos/{owner}/{repo}/issues", params=params)
    issues = []
    for it in items:
        if "pull_request" in it:
            continue
        issues.append(
            {
                "number": it.get("number"),
                "title": it.get("title"),
                "url": it.get("html_url"),
                "state": it.get("state"),
                "labels": [lbl.get("name") for lbl in (it.get("labels") or [])],
                "assignees": [a.get("login") for a in (it.get("assignees") or [])],
            }
        )
        if len(issues) >= limit:
            break

    return json.dumps(issues, indent=2)

# ---------------- Main ----------------
if __name__ == "__main__":
    # Run server via stdio
    mcp.run()
