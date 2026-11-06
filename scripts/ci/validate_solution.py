"""Quality checks for one unpacked solution before checker or packaging."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from solution_manifest import read_solution_manifest

VERSION_PATTERN = re.compile(r"^(0|[1-9]\d{0,4})\.(0|[1-9]\d{0,4})\.(0|[1-9]\d{0,4})\.(0|[1-9]\d{0,4})$")
PREFIX_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9]{1,7}$")
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r'"clientSecret"\s*:', re.IGNORECASE),
    re.compile(r'"client_secret"\s*:', re.IGNORECASE),
)
TEXT_SUFFIXES = {".xml", ".json", ".yml", ".yaml", ".txt", ".md", ".cs", ".js", ".ts"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def catalog_entry(root: Path, unique_name: str) -> dict | None:
    payload = json.loads((root / "catalog" / "solutions.json").read_text(encoding="utf-8-sig"))
    for entry in payload.get("solutions", []):
        if entry.get("uniqueName") == unique_name:
            return entry
    return None


def validate_solution(root: Path, unique_name: str) -> list[str]:
    errors: list[str] = []
    folder = root / "solutions" / unique_name
    if not folder.is_dir():
        return [f"Missing solution folder {folder}."]

    entry = catalog_entry(root, unique_name)
    if entry is None:
        errors.append(f"Add {unique_name} to catalog/solutions.json. Export-Solution.ps1 does this.")
    elif entry.get("enabled") is not True:
        errors.append(f"{unique_name} is in the catalog with enabled=false. Set it to true when the unpack is ready.")

    try:
        manifest = read_solution_manifest(folder)
    except (FileNotFoundError, ValueError) as error:
        return errors + [str(error)]

    if manifest["uniqueName"] != unique_name:
        errors.append(
            f"Folder name is {unique_name}, but Solution.xml UniqueName is {manifest['uniqueName']!r}."
        )
    if not VERSION_PATTERN.fullmatch(manifest["version"]):
        errors.append(f"Version {manifest['version']!r} must look like 1.0.0.1.")
    if manifest["managed"].lower() not in {"0", "false"}:
        errors.append(
            "Solution.xml is managed. Export the unmanaged solution from L48 DEV and unpack it with package type Both."
        )
    if not PREFIX_PATTERN.fullmatch(manifest["publisherPrefix"]):
        errors.append(
            f"Publisher prefix {manifest['publisherPrefix']!r} must be 2 to 8 letters or digits and start with a letter."
        )

    for path in folder.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() == ".zip":
            errors.append(f"Do not commit solution zip files: {path.relative_to(root)}")
        if path.name.lower().startswith(".env") or "clientsecret" in path.name.lower():
            errors.append(f"Remove secret-like file {path.relative_to(root)}")
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"Possible secret in {path.relative_to(root)} matched {pattern.pattern}")
                break

    return errors


def main() -> int:
    root = repo_root()
    unique_name = os.environ.get("SOLUTION_NAME", "").strip()
    if not unique_name:
        print("SOLUTION_NAME is required.", file=sys.stderr)
        return 1

    errors = validate_solution(root, unique_name)
    if errors:
        for error in errors:
            print(f"::error::{error}", file=sys.stderr)
        return 1

    print(f"{unique_name} passed quality validation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
