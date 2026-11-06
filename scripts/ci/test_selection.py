"""Local checks for solution selection and quality validation."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import detect_solutions
import validate_solution


SOLUTION_XML = """<?xml version="1.0" encoding="utf-8"?>
<ImportExportXml>
  <SolutionManifest>
    <UniqueName>{name}</UniqueName>
    <Version>{version}</Version>
    <Managed>{managed}</Managed>
    <Publisher>
      <UniqueName>l48</UniqueName>
      <CustomizationPrefix>l48</CustomizationPrefix>
    </Publisher>
  </SolutionManifest>
</ImportExportXml>
"""


def write_solution(root: Path, name: str, version: str = "1.0.0.1", managed: str = "0") -> None:
    folder = root / "solutions" / name / "Other"
    folder.mkdir(parents=True)
    (folder / "Solution.xml").write_text(
        SOLUTION_XML.format(name=name, version=version, managed=managed),
        encoding="utf-8",
    )


class SelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        write_solution(self.root, "SamplePipelineApp")
        self.catalog = {
            "SamplePipelineApp": {
                "uniqueName": "SamplePipelineApp",
                "displayName": "Sample Pipeline App",
                "enabled": True,
                "processCanvasApps": False,
            }
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_readme_only_is_ignored(self) -> None:
        selected = detect_solutions.select_solutions(
            self.root,
            self.catalog,
            ["solutions/SamplePipelineApp/README.md"],
            "",
            None,
        )
        self.assertEqual(selected, [])

    def test_solution_change_is_selected(self) -> None:
        selected = detect_solutions.select_solutions(
            self.root,
            self.catalog,
            ["solutions/SamplePipelineApp/Other/Solution.xml"],
            "",
            None,
        )
        self.assertEqual(selected[0]["uniqueName"], "SamplePipelineApp")
        self.assertEqual(selected[0]["version"], "1.0.0.1")
        self.assertFalse(selected[0]["hasTestSettings"])

    def test_settings_file_marks_the_matrix(self) -> None:
        settings = self.root / "config" / "SamplePipelineApp"
        settings.mkdir(parents=True)
        (settings / "test.settings.json").write_text("{}", encoding="utf-8")
        selected = detect_solutions.select_solutions(
            self.root,
            self.catalog,
            ["config/SamplePipelineApp/test.settings.json"],
            "",
            None,
        )
        self.assertTrue(selected[0]["hasTestSettings"])
        self.assertFalse(selected[0]["hasProdSettings"])

    def test_dispatch_all_skips_disabled_entries(self) -> None:
        self.catalog["SamplePipelineApp"]["enabled"] = False
        selected = detect_solutions.select_solutions(self.root, self.catalog, [], "", "all")
        self.assertEqual(selected, [])

    def test_invalid_version_fails(self) -> None:
        write_target = self.root / "solutions" / "SamplePipelineApp" / "Other" / "Solution.xml"
        write_target.write_text(
            SOLUTION_XML.format(name="SamplePipelineApp", version="1.0", managed="0"),
            encoding="utf-8",
        )
        with self.assertRaises(SystemExit):
            detect_solutions.select_solutions(
                self.root,
                self.catalog,
                ["solutions/SamplePipelineApp/Other/Solution.xml"],
                "",
                None,
            )

    def test_quality_validation_accepts_an_enabled_unpack(self) -> None:
        catalog_dir = self.root / "catalog"
        catalog_dir.mkdir()
        (catalog_dir / "solutions.json").write_text(
            json.dumps({"solutions": [self.catalog["SamplePipelineApp"]]}),
            encoding="utf-8",
        )
        self.assertEqual(validate_solution.validate_solution(self.root, "SamplePipelineApp"), [])

    def test_quality_validation_rejects_managed_source(self) -> None:
        managed_root = self.root / "solutions" / "SamplePipelineApp" / "Other" / "Solution.xml"
        managed_root.write_text(
            SOLUTION_XML.format(name="SamplePipelineApp", version="1.0.0.1", managed="1"),
            encoding="utf-8",
        )
        catalog_dir = self.root / "catalog"
        catalog_dir.mkdir()
        (catalog_dir / "solutions.json").write_text(
            json.dumps({"solutions": [self.catalog["SamplePipelineApp"]]}),
            encoding="utf-8",
        )
        errors = validate_solution.validate_solution(self.root, "SamplePipelineApp")
        self.assertTrue(any("unmanaged" in error.lower() or "managed" in error.lower() for error in errors))


if __name__ == "__main__":
    unittest.main()
