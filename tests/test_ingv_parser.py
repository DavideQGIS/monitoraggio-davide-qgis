import unittest

from Monitoraggio_Davide.core.parsers.ingv import parse_geojson


class IngvParserTests(unittest.TestCase):
    def test_parses_and_sorts_events(self):
        payload = {"features": [
            {"properties": {"eventId": "old", "time": "2026-09-29", "mag": 1.2}, "geometry": {"coordinates": [10, 45, 8]}},
            {"properties": {"eventId": "new", "time": "2026-09-30", "mag": 2.3}, "geometry": {"coordinates": [11, 46, 9]}},
            {"properties": {"eventId": "bad"}, "geometry": {"coordinates": [11]}},
        ]}
        events = parse_geojson(payload)
        self.assertEqual([event["event_id"] for event in events], ["new", "old"])
        self.assertEqual(events[0]["depth"], 9)


if __name__ == "__main__":
    unittest.main()
