import unittest

from src.preparar_muestra import fecha_a_iso


class TestFechaAIso(unittest.TestCase):
    def test_convierte_formato_del_csv_oficial(self):
        self.assertEqual(fecha_a_iso("01/04/2024 10:11"), "2024-04-01 10:11")

    def test_convierte_sin_hora(self):
        self.assertEqual(fecha_a_iso("14/06/2026"), "2026-06-14")

    def test_fecha_inexistente_se_deja_igual(self):
        self.assertEqual(fecha_a_iso("31/02/2024 10:00"), "31/02/2024 10:00")

    def test_otro_formato_se_deja_igual(self):
        self.assertEqual(fecha_a_iso("abc"), "abc")
        self.assertEqual(fecha_a_iso("2024-04-01 10:11"), "2024-04-01 10:11")


if __name__ == "__main__":
    unittest.main()
