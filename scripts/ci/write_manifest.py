"""Write the release manifest that travels with the managed zip."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> int:
    unique_name = os.environ["SOLUTION_NAME"]
    version = os.environ["SOLUTION_VERSION"]
    out_dir = Path(os.environ.get("OUT_DIR", "out"))
    out_dir.mkdir(parents=True, exist_ok=True)
    solution_file = f"{unique_name}_managed.zip"
    if not (out_dir / solution_file).is_file():
        print(f"Missing packed solution {out_dir / solution_file}", file=sys.stderr)
        return 1

    manifest = {
        "uniqueName": unique_name,
        "version": version,
        "displayName": os.environ.get("SOLUTION_DISPLAY_NAME", unique_name),
        "commit": os.environ.get("GITHUB_SHA", ""),
        "runId": os.environ.get("GITHUB_RUN_ID", ""),
        "runUrl": f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
        f"{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}",
        "packageType": "Managed",
        "solutionFile": solution_file,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
