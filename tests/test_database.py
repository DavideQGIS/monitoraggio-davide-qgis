import tempfile
import unittest
from pathlib import Path

from Monitoraggio_Davide.database import database_status, save_diagnostic, save_radar_product, upsert_sources


class DatabaseTests(unittest.TestCase):
    def test_cache_schema_sources_and_diagnostics(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "cache.sqlite")
            upsert_sources(path, [{"name": "Fonte prova", "url": "https://example.test", "area": "Test"}])
            save_diagnostic(path, {"source": "Fonte prova", "status": "OK", "http": "200", "ms": 12, "detail": "Raggiungibile"})
            save_radar_product(path, {"observed_at": "2026-10-01T21:00:00Z", "filename": "CMP2610012100.MAX.tif.gz", "path": "/tmp/radar.tif", "compressed_bytes": 123})
            status = database_status(path)
            self.assertTrue(status["available"])
            self.assertEqual(status["schema_version"], 2)
            self.assertEqual(status["diagnostics"], 1)

    def test_missing_cache(self):
        self.assertFalse(database_status("")["available"])


if __name__ == "__main__":
    unittest.main()
