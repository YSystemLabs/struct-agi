from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
RUNNER = REPO_ROOT / "experiments" / "multi_preorder_minimal_validation" / "run_validation.py"


class MultiPreorderValidationSmokeTests(unittest.TestCase):
    def test_runner_writes_report_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "validation_report.v0_9.json"
            manifest_path = Path(temp_dir) / "validation_manifest.v0_9.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--limit",
                    "1",
                    "--max-folds",
                    "1",
                    "--output",
                    str(report_path),
                    "--manifest-output",
                    str(manifest_path),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
            )

            self.assertIn("Wrote report to", completed.stdout)
            self.assertIn("Wrote manifest to", completed.stdout)
            self.assertTrue(report_path.exists())
            self.assertTrue(manifest_path.exists())

            report = json.loads(report_path.read_text(encoding="utf-8"))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertEqual("multi_preorder_minimal_validation_v0_9", report["experiment_id"])
            self.assertEqual("exploratory", report["package_status"])
            self.assertIn("formal_verdict", report)
            self.assertIn("status", report["formal_verdict"])
            self.assertIn("provenance", report)
            self.assertIn("git_commit", report["provenance"])

            self.assertEqual(str(report_path.resolve()), manifest["canonical_artifacts"]["report"]["path"])
            self.assertEqual(str(manifest_path.resolve()), manifest["canonical_artifacts"]["manifest"]["path"])
            self.assertEqual(_sha256(report_path), manifest["canonical_artifacts"]["report"]["sha256"])
            self.assertEqual(report["formal_verdict"]["status"], manifest["formal_verdict"]["status"])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


if __name__ == "__main__":
    unittest.main()