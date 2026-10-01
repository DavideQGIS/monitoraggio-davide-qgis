import unittest

from Monitoraggio_Davide.core.parsers.radar_lombardia import latest_radar_product, radar_products


INDEX = b"""<html><a href=\"CMP2610012045.MAX.tif.gz\">old</a>
<a href=\"CMP2610012100.MAX.tif.gz\">latest</a>
<a href=\"not-a-radar.txt\">ignore</a></html>"""


class RadarLombardiaParserTests(unittest.TestCase):
    def test_extracts_and_sorts_products(self):
        products = radar_products(INDEX)
        self.assertEqual(len(products), 2)
        self.assertEqual(products[-1]["filename"], "CMP2610012100.MAX.tif.gz")
        self.assertEqual(products[-1]["observed_at"], "2026-10-01T21:00:00Z")

    def test_latest_requires_a_product(self):
        with self.assertRaises(ValueError):
            latest_radar_product(b"<html></html>")


if __name__ == "__main__":
    unittest.main()
