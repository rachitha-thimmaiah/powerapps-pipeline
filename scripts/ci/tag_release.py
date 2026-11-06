"""Create the annotated release tag for a solution that reached PROD."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(args), flush=True)
    return subprocess.run(args, text=True, capture_output=True, check=False)


def main() -> int:
    manifest = json.loads(Path(os.environ.get("MANIFEST_PATH", "out/manifest.json")).read_text(encoding="utf-8-sig"))
    unique_name = manifest["uniqueName"]
    version = manifest["version"]
    commit = manifest.get("commit") or os.environ["GITHUB_SHA"]
    tag = f"release/{unique_name}/{version}"
    message = (
        f"PROD {unique_name} {version}\n\n"
        f"The managed solution packed in workflow run {manifest.get('runId', '')} "
        f"was imported to PROD without a rebuild.\n"
        f"{manifest.get('runUrl', '')}\n"
    )

    existing = run(["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}^{{}}"])
    if existing.returncode == 0:
        current = existing.stdout.strip()
        head = run(["git", "rev-parse", "-q", "--verify", f"{commit}^{{}}"])
        if existing.stdout.strip() and head.stdout.strip() == current:
            print(f"{tag} already points at {commit}.")
            return 0
        print(f"::error::{tag} already exists and points at a different commit.", file=sys.stderr)
        return 1

    config_name = run(["git", "config", "user.name", "github-actions[bot]"])
    config_email = run(
        ["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"]
    )
    if config_name.returncode != 0 or config_email.returncode != 0:
        print(config_name.stderr or config_email.stderr, file=sys.stderr)
        return 1

    created = run(["git", "tag", "-a", tag, commit, "-m", message])
    if created.returncode != 0:
        print(created.stderr, file=sys.stderr)
        return created.returncode

    pushed = run(["git", "push", "origin", f"refs/tags/{tag}"])
    if pushed.returncode != 0:
        print(pushed.stderr, file=sys.stderr)
        return pushed.returncode

    print(f"Created {tag} at {commit}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
