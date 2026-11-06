"""Confirm the target environment has the managed solution version from the artifact."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from pac_json import field, parse_pac_json, walk_solution


def version_tuple(value: str) -> tuple[int, int, int, int]:
    parts = value.strip().split(".")
    if len(parts) != 4 or not all(part.isdigit() for part in parts):
        raise ValueError(f"Version {value!r} is not a four-part Dataverse version.")
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def main() -> int:
    manifest_path = Path(os.environ.get("MANIFEST_PATH", "out/manifest.json"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    unique_name = manifest["uniqueName"]
    expected = version_tuple(manifest["version"])

    completed = subprocess.run(
        ["pac", "solution", "list", "--json"],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        print(completed.stdout)
        print(completed.stderr, file=sys.stderr)
        return completed.returncode or 1

    record = walk_solution(parse_pac_json(completed.stdout + "\n" + completed.stderr), unique_name)
    if record is None:
        print(f"::error::Smoke test failed. {unique_name} is not in the target environment.", file=sys.stderr)
        return 1

    actual_raw = field(record, "VersionNumber", "Version", "version")
    actual = version_tuple(actual_raw)
    if actual != expected:
        print(
            f"::error::Smoke test failed. {unique_name} is {actual_raw} in the target. "
            f"The artifact version is {manifest['version']}.",
            file=sys.stderr,
        )
        return 1

    print(f"Smoke test passed. {unique_name} {manifest['version']} is present in the target.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
