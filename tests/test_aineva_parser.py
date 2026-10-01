import unittest

from Monitoraggio_Davide.core.parsers.aineva import parse_caaml_bulletin


SAMPLE = b"""<?xml version="1.0"?>
<caaml:Bulletin xmlns:caaml="http://caaml.org/Schemas/V5.0/Profiles/BulletinEAWS" xmlns:gml="http://www.opengis.net/gml" xmlns:xlink="http://www.w3.org/1999/xlink" gml:id="IT-TEST">
  <caaml:dateTimeReport>2026-12-01T16:00:00+01:00</caaml:dateTimeReport>
  <caaml:validTime><gml:TimePeriod><gml:beginPosition>2026-12-02T00:00:00+01:00</gml:beginPosition><gml:endPosition>2026-12-02T23:59:00+01:00</gml:endPosition></gml:TimePeriod></caaml:validTime>
  <caaml:BulletinResult>
    <caaml:locRef xlink:href="#LOMBARDIA-01" />
    <caaml:dangerRating><caaml:mainValue>3</caaml:mainValue></caaml:dangerRating>
    <caaml:avalancheProblem><caaml:problemType>new_snow</caaml:problemType></caaml:avalancheProblem>
  </caaml:BulletinResult>
  <caaml:BulletinResult><caaml:dangerRating><caaml:mainValue>2</caaml:mainValue></caaml:dangerRating></caaml:BulletinResult>
</caaml:Bulletin>"""


class AinevaParserTests(unittest.TestCase):
    def test_caaml_summary(self):
        bulletin = parse_caaml_bulletin(SAMPLE)
        self.assertEqual(bulletin["bulletin_id"], "IT-TEST")
        self.assertEqual(bulletin["max_danger"], 3)
        self.assertEqual(bulletin["danger_levels"], [2, 3])
        self.assertEqual(bulletin["problems"], ["new_snow"])
        self.assertEqual(bulletin["regions"], ["LOMBARDIA-01"])
        self.assertEqual(bulletin["valid_to"], "2026-12-02T23:59:00+01:00")


if __name__ == "__main__":
    unittest.main()
