import unittest

from Monitoraggio_Davide.core.parsers.arpav import parse_arpav_xml


SAMPLE = b"""<?xml version="1.0"?>
<CONTENITORE>
  <ISTANTERUN>202609301315</ISTANTERUN>
  <PROJECTION>EPSG:4258</PROJECTION>
  <STAZIONE>
    <IDSTAZ>10</IDSTAZ><NOME>Padova prova</NOME><X>11.88</X><Y>45.41</Y>
    <QUOTA>12</QUOTA><PROVINCIA>PD</PROVINCIA><COMUNE>PADOVA</COMUNE>
    <SENSORE><ID>22</ID><PARAMNM>Livello idrometrico</PARAMNM><UNITNM>m</UNITNM>
      <DATI ISTANTE="202609301300"><VM>1,20</VM></DATI>
      <DATI ISTANTE="202609301310"><VM>1.25</VM></DATI>
      <DATI ISTANTE="202609301320"><VM></VM></DATI>
    </SENSORE>
  </STAZIONE>
  <STAZIONE>
    <IDSTAZ>11</IDSTAZ><NOME>Belluno prova</NOME><X>12.1</X><Y>46.1</Y>
    <QUOTA>400</QUOTA><PROVINCIA>BL</PROVINCIA><COMUNE>BELLUNO</COMUNE>
  </STAZIONE>
</CONTENITORE>"""


class ArpavParserTests(unittest.TestCase):
    def test_filters_padova_and_selects_latest_value(self):
        stations, summary = parse_arpav_xml(SAMPLE, "Padova")
        self.assertEqual(len(stations), 1)
        self.assertEqual(stations[0]["latest"]["value"], 1.25)
        self.assertEqual(stations[0]["latest"]["observed_at"], "2026-09-30 13:10")
        self.assertEqual(summary["stations"], 1)
        self.assertEqual(summary["sensors"], 1)
        self.assertEqual(summary["projection"], "EPSG:4258")

    def test_rejects_unexpected_projection(self):
        payload = SAMPLE.replace(b"EPSG:4258", b"EPSG:3003")
        with self.assertRaises(ValueError):
            parse_arpav_xml(payload, "Padova")


if __name__ == "__main__":
    unittest.main()
