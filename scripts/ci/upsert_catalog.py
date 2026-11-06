"""Add or enable a solution in catalog/solutions.json."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,99}$")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--owner", default="unassigned")
    args = parser.parse_args()

    if not NAME_PATTERN.fullmatch(args.name):
        print(f"Invalid solution unique name: {args.name}", file=sys.stderr)
        return 1

    catalog_path = repo_root() / "catalog" / "solutions.json"
    payload = json.loads(catalog_path.read_text(encoding="utf-8-sig"))
    solutions = payload.setdefault("solutions", [])
    existing = next((entry for entry in solutions if entry.get("uniqueName") == args.name), None)

    if existing is None:
        solutions.append(
            {
                "uniqueName": args.name,
                "displayName": args.display_name,
                "owner": args.owner,
                "enabled": True,
                "processCanvasApps": False,
            }
        )
        print(f"Added {args.name} to the catalog and enabled it.")
    else:
        existing["enabled"] = True
        existing.setdefault("processCanvasApps", False)
        existing.setdefault("owner", args.owner)
        print(f"Enabled existing catalog entry {args.name}.")

    catalog_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
