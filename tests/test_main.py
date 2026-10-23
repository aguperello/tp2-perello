import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from src.main import main

FIXTURES = Path(__file__).parent / "fixtures"


def ejecutar(*argumentos):
    salida, error = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(salida), contextlib.redirect_stderr(error):
        try:
            codigo = main(list(argumentos))
        except SystemExit as e:  # argparse sale con SystemExit
            codigo = e.code
    return codigo, salida.getvalue(), error.getvalue()


class TestMain(unittest.TestCase):
    def test_consulta_normal_con_csv_y_con_json_da_la_misma_salida(self):
        with tempfile.TemporaryDirectory() as tmp:
            textos = []
            for nombre in ("precios_prueba.csv", "precios_prueba.json"):
                salida_csv = Path(tmp) / f"{nombre}.out.csv"
                codigo, salida, _ = ejecutar(
                    "--entrada", str(FIXTURES / nombre), "--localidad", "Rosario",
                    "--combustible", "Nafta Super", "--fecha", "2026-06-15",
                    "--salida", str(salida_csv), "--rechazos", str(Path(tmp) / "r.csv"),
                )
                self.assertEqual(codigo, 0)
                textos.append(salida_csv.read_text(encoding="utf-8"))
        self.assertEqual(textos[0], textos[1])

    def test_fecha_invalida_da_error_comprensible(self):
        codigo, _, error = ejecutar(
            "--entrada", str(FIXTURES / "precios_prueba.csv"), "--localidad", "Rosario",
            "--combustible", "Nafta Super", "--fecha", "2026-02-30",
        )
        self.assertEqual(codigo, 2)
        self.assertIn("no existe en el calendario", error)

    def test_archivo_inexistente(self):
        codigo, _, error = ejecutar(
            "--entrada", "nada.csv", "--localidad", "R", "--combustible", "C", "--fecha", "2026-01-01",
        )
        self.assertEqual(codigo, 2)
        self.assertIn("No existe", error)

    def test_sin_resultados_informa_explicitamente(self):
        with tempfile.TemporaryDirectory() as tmp:
            codigo, salida, _ = ejecutar(
                "--entrada", str(FIXTURES / "precios_prueba.csv"), "--localidad", "Ushuaia",
                "--combustible", "Nafta Super", "--fecha", "2026-06-15",
                "--salida", str(Path(tmp) / "s.csv"), "--rechazos", str(Path(tmp) / "r.csv"),
            )
        self.assertEqual(codigo, 0)
        self.assertIn("Sin resultados", salida)

    def test_faltan_parametros(self):
        codigo, _, _ = ejecutar("--entrada", str(FIXTURES / "precios_prueba.csv"))
        self.assertEqual(codigo, 2)

    def test_listar_combustibles(self):
        codigo, salida, _ = ejecutar("--entrada", str(FIXTURES / "precios_prueba.csv"), "--listar", "combustibles")
        self.assertEqual(codigo, 0)
        self.assertIn("Nafta Super", salida)
        self.assertIn("Gas Oil", salida)


if __name__ == "__main__":
    unittest.main()
