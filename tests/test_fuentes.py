import json
import tempfile
import unittest
from pathlib import Path

from src.errores import FuenteInvalida
from src.fuentes import FuenteCSV, FuenteDatos, FuenteJSON, fuente_para
from src.modelo import ConsultaPrecio
from src.pipeline import ejecutar_consulta, normalizar_campos

FIXTURES = Path(__file__).parent / "fixtures"
CSV = FIXTURES / "precios_prueba.csv"
JSON = FIXTURES / "precios_prueba.json"
MUESTRAS_DE_DATA = sorted((Path(__file__).parent.parent / "data").glob("muestra*.csv"))


class TestFuentes(unittest.TestCase):
    def test_ambas_fuentes_cumplen_el_contrato_comun(self):
        for fuente in (FuenteCSV(), FuenteJSON()):
            self.assertIsInstance(fuente, FuenteDatos)

    def test_caso_normal_carga_todas_las_filas(self):
        self.assertEqual(len(FuenteCSV().cargar(CSV)), 16)
        self.assertEqual(len(FuenteJSON().cargar(JSON)), 16)

    def test_fuente_para_elige_por_extension(self):
        self.assertIsInstance(fuente_para("x.csv"), FuenteCSV)
        self.assertIsInstance(fuente_para("x.JSON"), FuenteJSON)

    def test_extension_desconocida_da_error_claro(self):
        with self.assertRaisesRegex(FuenteInvalida, "no soportado"):
            fuente_para("datos.xlsx")

    def test_archivo_inexistente_no_se_oculta(self):
        with self.assertRaisesRegex(FuenteInvalida, "No existe"):
            FuenteCSV().cargar("no_existe.csv")

    def test_json_mal_formado(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "roto.json"
            ruta.write_text("[{", encoding="utf-8")
            with self.assertRaisesRegex(FuenteInvalida, "mal formado"):
                FuenteJSON().cargar(ruta)

    def test_json_que_no_es_lista_de_objetos(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "dict.json"
            ruta.write_text(json.dumps({"a": 1}), encoding="utf-8")
            with self.assertRaisesRegex(FuenteInvalida, "lista de objetos"):
                FuenteJSON().cargar(ruta)

    def test_csv_vacio(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "vacio.csv"
            ruta.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(FuenteInvalida, "vacío"):
                FuenteCSV().cargar(ruta)

    def test_propiedad_csv_y_json_equivalentes(self):
        """Ambas lecturas deben producir las mismas filas normalizadas y el mismo resultado."""
        self.assertEqual(
            normalizar_campos(FuenteCSV().cargar(CSV)),
            normalizar_campos(FuenteJSON().cargar(JSON)),
        )
        consulta = ConsultaPrecio("Rosario", "Nafta Super", "2026-06-15")
        res_csv = ejecutar_consulta(FuenteCSV().cargar(CSV), consulta)
        res_json = ejecutar_consulta(FuenteJSON().cargar(JSON), consulta)
        self.assertEqual(res_csv, res_json)

    def test_muestras_de_data_csv_y_json_equivalentes(self):
        """Se verifica con cada muestra del repositorio (sintética o real)."""
        for ruta_csv in MUESTRAS_DE_DATA:
            ruta_json = ruta_csv.with_suffix(".json")
            with self.subTest(muestra=ruta_csv.name):
                self.assertTrue(ruta_json.exists(), f"Falta el JSON equivalente de {ruta_csv.name}")
                self.assertEqual(
                    normalizar_campos(FuenteCSV().cargar(ruta_csv)),
                    normalizar_campos(FuenteJSON().cargar(ruta_json)),
                )


if __name__ == "__main__":
    unittest.main()
