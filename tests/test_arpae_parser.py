import unittest

from Monitoraggio_Davide.core.parsers.arpae import parse_hydro_payload


class ArpaeParserTests(unittest.TestCase):
    def test_coordinates_value_and_thresholds(self):
        payload = [{
            "idstazione": "B13215",
            "nomestaz": "Ponte prova",
            "lon": 1123456,
            "lat": 4456789,
            "value": "1,42",
            "soglia1": "1.5",
            "soglia2": "2.0",
            "soglia3": "2.5",
            "precedente": "N",
        }]
        stations = parse_hydro_payload(payload, "2026-09-30T12:00+02:00")
        self.assertEqual(len(stations), 1)
        self.assertAlmostEqual(stations[0]["longitude"], 11.23456)
        self.assertEqual(stations[0]["latest"]["value"], 1.42)
        self.assertEqual(stations[0]["threshold"]["alarm"], 2.5)

    def test_zero_threshold_means_missing(self):
        stations = parse_hydro_payload([{"idstazione": "1", "soglia1": 0}], "ora")
        self.assertIsNone(stations[0]["threshold"]["attention"])


if __name__ == "__main__":
    unittest.main()
