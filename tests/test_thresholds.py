import unittest

from Monitoraggio_Davide.thresholds import apply_thresholds, evaluate


class ThresholdTests(unittest.TestCase):
    def test_evaluate_above_thresholds(self):
        threshold = {"direction": "above", "attention": 1.0, "prealarm": 2.0, "alarm": 3.0}
        self.assertEqual(evaluate(0.5, threshold), "Regolare")
        self.assertEqual(evaluate(1.0, threshold), "Attenzione")
        self.assertEqual(evaluate(2.0, threshold), "Preallarme")
        self.assertEqual(evaluate(3.0, threshold), "Allarme")

    def test_evaluate_below_thresholds(self):
        threshold = {"direction": "below", "attention": 3.0, "prealarm": 2.0, "alarm": 1.0}
        self.assertEqual(evaluate(4.0, threshold), "Regolare")
        self.assertEqual(evaluate(3.0, threshold), "Attenzione")
        self.assertEqual(evaluate(2.0, threshold), "Preallarme")
        self.assertEqual(evaluate(1.0, threshold), "Allarme")

    def test_missing_value_and_threshold(self):
        self.assertEqual(evaluate(None, {}), "Dato assente")
        self.assertEqual(evaluate(1.0, {}), "Soglia assente")

    def test_apply_thresholds_matches_sensor_id(self):
        stations = [{
            "sensor_id": "A-1",
            "name": "Idrometro prova",
            "sensor_type": "Livello idrometrico",
            "latest": {"value": 2.5},
        }]
        thresholds = [{
            "source": "ARPA Test",
            "sensor_id": "A-1",
            "station_name": "",
            "sensor_type": "Livello idrometrico",
            "direction": "above",
            "attention": 1.0,
            "prealarm": 2.0,
            "alarm": 3.0,
        }]
        counts = apply_thresholds(stations, thresholds, "ARPA Test")
        self.assertEqual(stations[0]["criticality"], "Preallarme")
        self.assertEqual(counts["Preallarme"], 1)


if __name__ == "__main__":
    unittest.main()

