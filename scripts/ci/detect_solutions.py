"""Choose which catalog solutions this commit or pull request should build."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

from solution_manifest import read_solution_manifest

NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,99}$")
VERSION_PATTERN = re.compile(r"^(0|[1-9]\d{0,4})\.(0|[1-9]\d{0,4})\.(0|[1-9]\d{0,4})\.(0|[1-9]\d{0,4})$")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_catalog(catalog_path: Path) -> dict[str, dict]:
    payload = json.loads(catalog_path.read_text(encoding="utf-8-sig"))
    entries = payload.get("solutions")
    if not isinstance(entries, list):
        raise SystemExit(f"{catalog_path} must contain a solutions array.")

    catalog: dict[str, dict] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise SystemExit(f"Catalog entry is not an object: {entry!r}")
        name = str(entry.get("uniqueName", "")).strip()
        if not NAME_PATTERN.fullmatch(name):
            raise SystemExit(f"Catalog uniqueName is invalid: {name!r}")
        if name in catalog:
            raise SystemExit(f"Duplicate catalog uniqueName: {name}")
        catalog[name] = entry
    return catalog


def run_git(root: Path, args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=check,
    )


def changed_files_from_git(root: Path) -> tuple[list[str], str]:
    override = os.environ.get("CHANGED_FILES")
    if override is not None:
        files = [line.strip().replace("\\", "/") for line in override.splitlines() if line.strip()]
        return files, os.environ.get("CATALOG_DIFF", "")

    head = os.environ.get("HEAD_SHA") or "HEAD"
    base = os.environ.get("BASE_SHA", "")
    if not base or set(base) == {"0"}:
        parents = run_git(root, ["rev-list", "--parents", "-n", "1", head]).stdout.split()
        if len(parents) <= 1:
            listing = run_git(root, ["ls-tree", "-r", "--name-only", head]).stdout
            return [line.strip() for line in listing.splitlines() if line.strip()], ""
        base = parents[1]

    diff_spec = f"{base}...{head}" if os.environ.get("DIFF_MODE") == "pull_request" else None
    diff_args = ["diff", "--name-only", diff_spec] if diff_spec else ["diff", "--name-only", base, head]
    diff = run_git(root, diff_args, check=False)
    if diff.returncode != 0:
        run_git(root, ["fetch", "--no-tags", "origin", base, head], check=False)
        diff = run_git(root, diff_args)
    files = [line.strip().replace("\\", "/") for line in diff.stdout.splitlines() if line.strip()]

    revision_args = [diff_spec] if diff_spec else [base, head]
    catalog_args = ["diff", "--unified=0", *revision_args, "--", "catalog/solutions.json"]
    catalog_diff = run_git(
        root,
        catalog_args,
        check=False,
    )
    catalog_text = catalog_diff.stdout if catalog_diff.returncode == 0 else ""
    return files, catalog_text


def names_from_paths(files: list[str]) -> set[str]:
    names: set[str] = set()
    for path in files:
        parts = path.split("/")
        if len(parts) < 2:
            continue
        if parts[0] == "solutions" and len(parts) >= 3:
            if path == f"solutions/{parts[1]}/README.md":
                continue
            names.add(parts[1])
        elif parts[0] == "config" and len(parts) >= 3:
            names.add(parts[1])
    return names


def matrix_entry(root: Path, name: str, catalog: dict[str, dict]) -> dict:
    if not NAME_PATTERN.fullmatch(name):
        raise SystemExit(f"Solution folder name is invalid: {name}")

    folder = root / "solutions" / name
    manifest = read_solution_manifest(folder)
    if manifest["uniqueName"] != name:
        raise SystemExit(
            f"{folder} contains UniqueName {manifest['uniqueName']!r}, which does not match the folder."
        )
    if not VERSION_PATTERN.fullmatch(manifest["version"]):
        raise SystemExit(
            f"{name} version {manifest['version']!r} must be four numbers, such as 1.0.0.1."
        )

    entry = catalog.get(name, {})
    return {
        "uniqueName": name,
        "version": manifest["version"],
        "displayName": str(entry.get("displayName") or name),
        "processCanvasApps": bool(entry.get("processCanvasApps", False)),
        "hasTestSettings": (root / "config" / name / "test.settings.json").is_file(),
        "hasProdSettings": (root / "config" / name / "prod.settings.json").is_file(),
    }


def select_solutions(
    root: Path,
    catalog: dict[str, dict],
    files: list[str],
    catalog_diff: str,
    solution_filter: str | None,
) -> list[dict]:
    if solution_filter and solution_filter != "all":
        if solution_filter not in catalog:
            raise SystemExit(f"{solution_filter} is not in catalog/solutions.json.")
        if catalog[solution_filter].get("enabled") is not True:
            raise SystemExit(f"{solution_filter} is disabled in the catalog. Export it and set enabled to true.")
        return [matrix_entry(root, solution_filter, catalog)]

    if solution_filter == "all":
        selected = []
        for name, entry in catalog.items():
            manifest_path = root / "solutions" / name / "Other" / "Solution.xml"
            if entry.get("enabled") is True and manifest_path.is_file():
                selected.append(matrix_entry(root, name, catalog))
        return selected

    names = names_from_paths(files)
    if "catalog/solutions.json" in files:
        for name in catalog:
            if name in catalog_diff and (root / "solutions" / name / "Other" / "Solution.xml").is_file():
                names.add(name)

    return [matrix_entry(root, name, catalog) for name in sorted(names)]


def write_github_output(matrix: list[dict]) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    payload = json.dumps({"include": matrix}, separators=(",", ":"))
    print(payload)
    if not output_path:
        return

    delimiter = f"MATRIX_{uuid.uuid4().hex}"
    with open(output_path, "a", encoding="utf-8") as handle:
        handle.write(f"has_solutions={'true' if matrix else 'false'}\n")
        handle.write(f"matrix<<{delimiter}\n")
        handle.write(payload)
        handle.write(f"\n{delimiter}\n")


def write_summary(matrix: list[dict]) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    lines = ["### Solutions selected for this run", ""]
    if not matrix:
        lines.append("No solution changes to build.")
    else:
        lines.extend(
            [
                "| Solution | Version | TEST settings | PROD settings |",
                "| --- | --- | --- | --- |",
            ]
        )
        for entry in matrix:
            lines.append(
                f"| `{entry['uniqueName']}` | {entry['version']} | "
                f"{'yes' if entry['hasTestSettings'] else 'no'} | "
                f"{'yes' if entry['hasProdSettings'] else 'no'} |"
            )
    with open(summary_path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main() -> int:
    root = repo_root()
    catalog = load_catalog(root / "catalog" / "solutions.json")
    solution_filter = os.environ.get("SOLUTION_FILTER", "").strip() or None
    if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch" and not solution_filter:
        solution_filter = "all"

    if solution_filter:
        files, catalog_diff = [], ""
    else:
        files, catalog_diff = changed_files_from_git(root)

    matrix = select_solutions(root, catalog, files, catalog_diff, solution_filter)
    write_github_output(matrix)
    write_summary(matrix)
    if not matrix:
        print("No solution changes selected.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (FileNotFoundError, ValueError) as error:
        print(f"::error::{error}", file=sys.stderr)
        sys.exit(1)
