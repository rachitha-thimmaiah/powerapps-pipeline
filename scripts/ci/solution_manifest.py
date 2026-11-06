"""Read the unpacked Dataverse solution manifest."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child_text(parent: ET.Element, name: str) -> str:
    for child in list(parent):
        if local_name(child.tag) == name:
            return (child.text or "").strip()
    return ""


def read_solution_manifest(solution_folder: Path) -> dict[str, str]:
    manifest_path = solution_folder / "Other" / "Solution.xml"
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"{manifest_path} is missing. Unpack an unmanaged export with "
            "scripts/Export-Solution.ps1 so the folder contains Other/Solution.xml."
        )

    root = ET.parse(manifest_path).getroot()
    solution_manifest = next(
        (element for element in root.iter() if local_name(element.tag) == "SolutionManifest"),
        None,
    )
    if solution_manifest is None:
        raise ValueError(f"{manifest_path} has no SolutionManifest element.")

    unique_name = child_text(solution_manifest, "UniqueName")
    version = child_text(solution_manifest, "Version")
    managed = child_text(solution_manifest, "Managed")
    publisher = next(
        (element for element in list(solution_manifest) if local_name(element.tag) == "Publisher"),
        None,
    )
    prefix = child_text(publisher, "CustomizationPrefix") if publisher is not None else ""

    return {
        "uniqueName": unique_name,
        "version": version,
        "managed": managed,
        "publisherPrefix": prefix,
        "path": str(manifest_path),
    }
