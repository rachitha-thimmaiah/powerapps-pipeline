"""Decide whether TEST or PROD already has this managed solution."""

from __future__ import annotations

import os
import subprocess
import sys

from pac_json import is_managed, parse_pac_json, walk_solution


def main() -> int:
    unique_name = os.environ["SOLUTION_NAME"]
    completed = subprocess.run(
        ["pac", "solution", "list", "--json"],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        print(completed.stdout)
        print(completed.stderr, file=sys.stderr)
        print("pac solution list failed.", file=sys.stderr)
        return completed.returncode or 1

    try:
        payload = parse_pac_json(completed.stdout + "\n" + completed.stderr)
    except ValueError as error:
        print(completed.stdout)
        print(f"::error::{error}", file=sys.stderr)
        return 1

    record = walk_solution(payload, unique_name)
    if record is None:
        stage_and_upgrade = "false"
        print(f"{unique_name} is not in the target environment. Using a first-time managed import.")
    elif not is_managed(record):
        print(
            f"::error::{unique_name} is already in the target as an unmanaged solution. "
            "Remove that unmanaged copy before this pipeline imports the managed artifact.",
            file=sys.stderr,
        )
        return 1
    else:
        stage_and_upgrade = "true"
        print(f"{unique_name} is already managed in the target. Import will stage and upgrade.")

    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as handle:
            handle.write(f"stage_and_upgrade={stage_and_upgrade}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
