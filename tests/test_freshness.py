import unittest
from datetime import datetime, timezone

from Monitoraggio_Davide.core.freshness import annotate_freshness, freshness_state


class FreshnessTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)

    def test_states(self):
        self.assertEqual(freshness_state("2026-09-30T11:45:00Z", self.now)["state"], "Recente")
        self.assertEqual(freshness_state("2026-09-30T10:30:00Z", self.now)["state"], "Ritardato")
        self.assertEqual(freshness_state("2026-09-30T06:00:00Z", self.now)["state"], "Scaduto")
        self.assertEqual(freshness_state("", self.now)["state"], "Data assente")

    def test_arpav_solar_time_offset(self):
        result = freshness_state("2026-09-30 12:50", self.now, utc_offset_minutes=60)
        self.assertEqual(result["state"], "Recente")
        self.assertEqual(result["age_minutes"], 10)

    def test_annotation(self):
        stations = [{"latest": {"observed_at": "2026-09-30T11:55:00Z", "value": 1.2}}]
        counts = annotate_freshness(stations, self.now)
        self.assertEqual(counts["Recente"], 1)
        self.assertEqual(stations[0]["latest"]["age_minutes"], 5)


if __name__ == "__main__":
    unittest.main()

