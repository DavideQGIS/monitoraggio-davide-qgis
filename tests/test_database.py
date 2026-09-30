import tempfile
import unittest
from pathlib import Path

from Monitoraggio_Davide.database import database_status, save_diagnostic, upsert_sources


class DatabaseTests(unittest.TestCase):
    def test_cache_schema_sources_and_diagnostics(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "cache.sqlite")
            upsert_sources(path, [{"name": "Fonte prova", "url": "https://example.test", "area": "Test"}])
            save_diagnostic(path, {"source": "Fonte prova", "status": "OK", "http": "200", "ms": 12, "detail": "Raggiungibile"})
            status = database_status(path)
            self.assertTrue(status["available"])
            self.assertEqual(status["schema_version"], 1)
            self.assertEqual(status["diagnostics"], 1)

    def test_missing_cache(self):
        self.assertFalse(database_status("")["available"])


if __name__ == "__main__":
    unittest.main()

