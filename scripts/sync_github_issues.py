#!/usr/bin/env python3
"""Validate the roadmap issue manifest and optionally create missing GitHub work.

Dry-run is the default. Applying changes requires both ``--apply`` and a
repo-scoped ``GITHUB_TOKEN``. Existing issues are recognized by the stable
``roadmap-id`` marker, so rerunning the command does not duplicate them.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "planning" / "issues.json"
API = "https://api.github.com"


def load_manifest(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    issues = document.get("issues")
    labels = document.get("labels")
    milestones = document.get("milestones")
    if not isinstance(issues, list) or not issues:
        raise ValueError("manifest must contain a non-empty issues list")
    if not isinstance(labels, list) or not isinstance(milestones, list):
        raise ValueError("manifest labels and milestones must be lists")

    issue_ids = [item.get("id") for item in issues]
    if any(not value for value in issue_ids) or len(issue_ids) != len(set(issue_ids)):
        raise ValueError("issue ids must be present and unique")
    titles = [item.get("title") for item in issues]
    if any(not value for value in titles) or len(titles) != len(set(titles)):
        raise ValueError("issue titles must be present and unique")

    label_names = {item.get("name") for item in labels}
    milestone_titles = {item.get("title") for item in milestones}
    known_ids = set(issue_ids)
    order = {issue_id: index for index, issue_id in enumerate(issue_ids)}
    for item in issues:
        required = ("milestone", "labels", "objective", "acceptance", "validation")
        missing = [field for field in required if not item.get(field)]
        if missing:
            raise ValueError(f"{item['id']}: missing {', '.join(missing)}")
        unknown_labels = set(item["labels"]) - label_names
        if unknown_labels:
            raise ValueError(f"{item['id']}: unknown labels {sorted(unknown_labels)}")
        if item["milestone"] not in milestone_titles:
            raise ValueError(f"{item['id']}: unknown milestone {item['milestone']!r}")
        for dependency in item.get("dependencies", []):
            if dependency not in known_ids:
                raise ValueError(f"{item['id']}: unknown dependency {dependency!r}")
            if order[dependency] >= order[item["id"]]:
                raise ValueError(f"{item['id']}: dependency {dependency!r} must appear earlier")
    return document


def marker(issue_id: str) -> str:
    return f"<!-- roadmap-id: {issue_id} -->"


def render_body(item: dict[str, Any]) -> str:
    dependencies = item.get("dependencies") or []
    dependency_text = ", ".join(f"`{value}`" for value in dependencies) or "None"
    acceptance = "\n".join(f"- [ ] {value}" for value in item["acceptance"])
    validation = "\n".join(f"- [ ] {value}" for value in item["validation"])
    return (
        f"{marker(item['id'])}\n\n"
        f"## Objective\n\n{item['objective']}\n\n"
        f"## Dependencies\n\n{dependency_text}\n\n"
        f"## Acceptance criteria\n\n{acceptance}\n\n"
        f"## Validation evidence\n\n{validation}\n\n"
        "## Completion record\n\n"
        "- PR/commit:\n"
        "- Domain reviewer:\n"
        "- Residual risk:\n"
    )


class GitHub:
    def __init__(self, token: str) -> None:
        self.token = token

    def request(self, method: str, path: str, payload: Any | None = None) -> tuple[int, Any]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            API + path,
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "iran-auto-claim-roadmap-sync",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
                return response.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            raw = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub {method} {path} failed ({error.code}): {raw}") from error


def repo_path(repo: str, suffix: str) -> str:
    owner, separator, name = repo.partition("/")
    if not separator or not owner or not name or "/" in name:
        raise ValueError("--repo must be in owner/name form")
    return f"/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(name)}{suffix}"


def apply_manifest(document: dict[str, Any], repo: str, client: GitHub) -> tuple[int, int]:
    _, remote_milestones = client.request(
        "GET", repo_path(repo, "/milestones?state=all&per_page=100")
    )
    milestone_numbers = {item["title"]: item["number"] for item in remote_milestones}
    for milestone in document["milestones"]:
        if milestone["title"] in milestone_numbers:
            continue
        _, created = client.request(
            "POST",
            repo_path(repo, "/milestones"),
            {"title": milestone["title"], "description": milestone.get("description", "")},
        )
        milestone_numbers[milestone["title"]] = created["number"]
        print(f"created milestone: {milestone['title']}")

    _, remote_labels = client.request("GET", repo_path(repo, "/labels?per_page=100"))
    existing_labels = {item["name"] for item in remote_labels}
    for label in document["labels"]:
        if label["name"] in existing_labels:
            continue
        client.request("POST", repo_path(repo, "/labels"), label)
        existing_labels.add(label["name"])
        print(f"created label: {label['name']}")

    _, remote_issues = client.request(
        "GET", repo_path(repo, "/issues?state=all&per_page=100&sort=created&direction=asc")
    )
    existing_markers = {
        roadmap_marker
        for issue in remote_issues
        for roadmap_marker in [next(
            (marker(item["id"]) for item in document["issues"] if marker(item["id"]) in (issue.get("body") or "")),
            None,
        )]
        if roadmap_marker
    }

    created_count = 0
    skipped_count = 0
    for item in document["issues"]:
        issue_marker = marker(item["id"])
        if issue_marker in existing_markers:
            skipped_count += 1
            print(f"exists: {item['id']} {item['title']}")
            continue
        payload = {
            "title": f"[{item['id']}] {item['title']}",
            "body": render_body(item),
            "labels": item["labels"],
            "milestone": milestone_numbers[item["milestone"]],
        }
        _, created = client.request("POST", repo_path(repo, "/issues"), payload)
        created_count += 1
        print(f"created #{created['number']}: {item['id']} {item['title']}")
    return created_count, skipped_count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--repo", default=None, help="GitHub repository in owner/name form")
    parser.add_argument("--apply", action="store_true", help="create missing labels, milestones, and issues")
    args = parser.parse_args(argv)

    try:
        document = load_manifest(args.manifest)
        repo = args.repo or document.get("repository")
        if not repo:
            raise ValueError("repository is required in the manifest or --repo")
        repo_path(repo, "")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"manifest error: {error}", file=sys.stderr)
        return 2

    print(
        f"valid manifest: {len(document['milestones'])} milestones, "
        f"{len(document['labels'])} labels, {len(document['issues'])} issues"
    )
    if not args.apply:
        for item in document["issues"]:
            print(f"DRY-RUN {item['id']}: {item['title']}")
        return 0

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("--apply requires GITHUB_TOKEN", file=sys.stderr)
        return 2
    try:
        created, skipped = apply_manifest(document, repo, GitHub(token))
    except (RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(f"issue sync complete: {created} created, {skipped} already present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
