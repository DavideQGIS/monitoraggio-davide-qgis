import unittest

from Monitoraggio_Davide.core.source_registry import SOURCES, source_by_key, source_catalog


class SourceRegistryTests(unittest.TestCase):
    def test_keys_are_unique(self):
        keys = [source.key for source in SOURCES]
        self.assertEqual(len(keys), len(set(keys)))

    def test_catalog_keeps_legacy_fields(self):
        required = {"name", "group", "area", "url"}
        for row in source_catalog():
            self.assertTrue(required.issubset(row))

    def test_lookup(self):
        self.assertEqual(source_by_key("arpav_idrometeo").area, "Veneto")
        with self.assertRaises(KeyError):
            source_by_key("fonte_inesistente")


if __name__ == "__main__":
    unittest.main()

