import hashlib
import tempfile
import unittest
from pathlib import Path

from tools.download_corpus import build_pdf_path, existing_pdf_path, render_not_downloaded, validate_pdf


class DownloadCorpusTests(unittest.TestCase):
    def test_path_is_sharded_and_stable(self):
        work = {"title": "World Models / for Robots", "stable_id": "doi:10.1/abc"}
        path = build_pdf_path(Path("papers"), "AI", "CoRL", 2025, 7, work)
        digest = hashlib.sha256(work["stable_id"].encode()).hexdigest()[:2]
        self.assertEqual(path.parent.name, digest)
        self.assertTrue(path.name.startswith("0007_World_Models_for_Robots_"))

    def test_invalid_pdf_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.pdf"
            path.write_bytes(b"<html>blocked</html>")
            ok, reason = validate_pdf(path)
            self.assertFalse(ok)
            self.assertEqual(reason, "invalid_pdf")

    def test_existing_relative_path_survives_manifest_reordering(self):
        row = {"relative_path": "papers/AI/CoRL/2025/aa/original.pdf"}
        self.assertEqual(
            existing_pdf_path(Path("D:/repo"), row),
            Path("D:/repo/papers/AI/CoRL/2025/aa/original.pdf"),
        )

    def test_failure_markdown_groups_by_venue(self):
        rows = [{
            "domain": "AI", "venue": "CoRL", "year": 2025, "title": "Missing Paper",
            "authors": "A. Author", "track": "main", "stable_id": "W1",
            "landing_url": "https://example.test/paper", "pdf_url": "",
            "status": "pdf_url_missing", "failure_reason": "no legal PDF found",
            "attempts": 2, "last_attempt": "2026-09-19T00:00:00+08:00",
        }]
        rendered = render_not_downloaded(rows, {"CoRL": 1})
        self.assertIn("## AI", rendered)
        self.assertIn("### CoRL (2025)", rendered)
        self.assertIn("Missing Paper", rendered)
        self.assertIn("pdf_url_missing", rendered)


if __name__ == "__main__":
    unittest.main()
