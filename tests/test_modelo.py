import unittest
from datetime import date, datetime

from src.errores import ParametroInvalido
from src.modelo import ConsultaPrecio, normalizar_texto


class TestConsultaPrecio(unittest.TestCase):
    def test_caso_normal(self):
        c = ConsultaPrecio(" Rosario ", "Gas Oil", "2026-10-14")
        self.assertEqual(c.localidad, "Rosario")
        self.assertEqual(c.fecha_referencia, date(2026, 10, 14))

    def test_fecha_limite_incluye_todo_el_dia(self):
        c = ConsultaPrecio("Rosario", "Gas Oil", "2026-10-14")
        self.assertGreater(c.fecha_limite(), datetime(2026, 10, 14, 23, 59, 59))
        self.assertLess(c.fecha_limite(), datetime(2026, 10, 15))

    def test_fechas_invalidas_dan_mensaje_claro(self):
        casos = {
            "15/06/2026": "formato",   # no respeta el patrón (expresión regular)
            "2026-13-01": "calendario",  # respeta el patrón pero el mes no existe
            "2026-02-30": "calendario",
            "2026-02-29": "calendario",  # 2026 no es bisiesto
        }
        for texto, palabra in casos.items():
            with self.subTest(fecha=texto):
                with self.assertRaisesRegex(ParametroInvalido, palabra):
                    ConsultaPrecio("Rosario", "Gas Oil", texto)

    def test_fecha_bisiesta_valida(self):
        self.assertEqual(ConsultaPrecio("R", "G", "2028-02-29").fecha_referencia, date(2028, 2, 29))

    def test_parametros_vacios(self):
        with self.assertRaisesRegex(ParametroInvalido, "localidad"):
            ConsultaPrecio("  ", "Gas Oil", "2026-10-14")
        with self.assertRaisesRegex(ParametroInvalido, "combustible"):
            ConsultaPrecio("Rosario", "", "2026-10-14")

    def test_coincidencia_ignora_mayusculas_y_acentos(self):
        c = ConsultaPrecio("córdoba", "nafta súper", "2026-10-14")
        fila = {"localidad": "CORDOBA", "producto": "Nafta Super", "tipo_horario": ""}
        self.assertTrue(c.coincide(fila))

    def test_filtro_de_horario(self):
        c = ConsultaPrecio("Rosario", "Gas Oil", "2026-10-14", horario="Nocturno")
        base = {"localidad": "Rosario", "producto": "Gas Oil"}
        self.assertFalse(c.coincide({**base, "tipo_horario": "Diurno"}))
        self.assertTrue(c.coincide({**base, "tipo_horario": "nocturno"}))

    def test_normalizar_texto(self):
        self.assertEqual(normalizar_texto("  ÁÉÍ Ñu "), "aei nu")


if __name__ == "__main__":
    unittest.main()
