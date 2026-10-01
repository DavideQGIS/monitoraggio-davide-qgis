import unittest

from Monitoraggio_Davide.config import AREAS, CAPITALS


class AreaConfigurationTests(unittest.TestCase):
    def test_every_province_has_one_capital(self):
        expected = {(area, province) for area, provinces in AREAS.items() for province in provinces}
        actual = {(item["area"], item["province"]) for item in CAPITALS}
        self.assertEqual(actual, expected)

    def test_capital_coordinates_are_in_northern_italy(self):
        for item in CAPITALS:
            self.assertGreater(item["latitude"], 43.0)
            self.assertLess(item["latitude"], 47.5)
            self.assertGreater(item["longitude"], 8.0)
            self.assertLess(item["longitude"], 13.5)


if __name__ == "__main__":
    unittest.main()
