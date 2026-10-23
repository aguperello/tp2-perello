import csv
import tempfile
import unittest
from collections import Counter
from datetime import datetime
from pathlib import Path

from src.errores import EsquemaInvalido, FechaConFormatoInvalido, FechaInexistente, ResultadoInconsistente
from src.fuentes import FuenteCSV
from src.modelo import ConsultaPrecio
from src.pipeline import (
    buscar_estaciones,
    convertir_fecha,
    ejecutar_consulta,
    exportar_consulta,
    guardar_rechazos,
    limpiar_datos,
    normalizar_campos,
    validar_esquema,
    verificar_resultado,
)

CSV = Path(__file__).parent / "fixtures" / "precios_prueba.csv"
COMBUSTIBLE = "Nafta Super"


def cargar():
    return FuenteCSV().cargar(CSV)


def consultar(fecha, localidad="Rosario", combustible=COMBUSTIBLE):
    return ejecutar_consulta(cargar(), ConsultaPrecio(localidad, combustible, fecha))


class TestSeleccionDeVigentes(unittest.TestCase):
    def test_caso_normal_ordenado_por_precio(self):
        resultado, _, _ = consultar("2026-06-15")
        self.assertEqual([f["estacion_id"] for f in resultado], ["200", "100", "300"])
        self.assertEqual([f["precio"] for f in resultado], [1050.0, 1100.0, 1300.0])

    def test_actualizacion_posterior_a_la_consulta_queda_excluida(self):
        resultado, _, _ = consultar("2026-06-15")
        estacion_100 = next(f for f in resultado if f["estacion_id"] == "100")
        self.assertEqual(estacion_100["precio"], 1100.0)  # no 1200 (del 2026-07-01)
        self.assertNotIn("400", [f["estacion_id"] for f in resultado])  # solo tiene registro posterior

    def test_se_elige_el_registro_correcto_con_dos_actualizaciones(self):
        antes, _, _ = consultar("2026-05-31")
        despues, _, _ = consultar("2026-07-20")
        self.assertEqual(next(f for f in antes if f["estacion_id"] == "100")["precio"], 1000.0)
        self.assertEqual(next(f for f in despues if f["estacion_id"] == "100")["precio"], 1200.0)

    def test_el_dia_de_referencia_esta_incluido(self):
        resultado, _, _ = consultar("2026-06-01")  # el registro es de ese día a las 10:00
        self.assertEqual(next(f for f in resultado if f["estacion_id"] == "100")["precio"], 1100.0)

    def test_localidad_sin_resultados_da_lista_vacia(self):
        resultado, _, resumen = consultar("2026-06-15", localidad="Ushuaia")
        self.assertEqual(resultado, [])
        self.assertEqual(resumen["estaciones_sin_precio_vigente"], 0)

    def test_fecha_anterior_a_todos_los_registros(self):
        resultado, _, resumen = consultar("2026-04-01")
        self.assertEqual(resultado, [])
        self.assertEqual(resumen["estaciones_sin_precio_vigente"], 4)  # 100, 200, 300 y 400

    def test_no_se_mezclan_combustibles_ni_localidades(self):
        gas, _, _ = consultar("2026-06-15", combustible="Gas Oil")
        self.assertEqual([f["estacion_id"] for f in gas], ["200"])
        cordoba, _, _ = consultar("2026-06-15", localidad="Cordoba")
        self.assertEqual([f["estacion_id"] for f in cordoba], ["500"])

    def test_localidad_con_distinta_capitalizacion_se_incluye(self):
        resultado, _, _ = consultar("2026-06-15")
        self.assertIn("300", [f["estacion_id"] for f in resultado])  # figura como "Rosario"

    def test_propiedades_del_resultado_para_varias_fechas(self):
        for fecha in ["2026-05-01", "2026-05-31", "2026-06-15", "2026-07-20", "2026-12-31"]:
            with self.subTest(fecha=fecha):
                consulta = ConsultaPrecio("Rosario", COMBUSTIBLE, fecha)
                resultado, _, _ = ejecutar_consulta(cargar(), consulta)
                precios = [f["precio"] for f in resultado]
                self.assertEqual(precios, sorted(precios))
                self.assertTrue(all(f["fecha_vigencia"] <= consulta.fecha_limite() for f in resultado))
                claves = [(f["_estacion_clave"], f["tipo_horario"]) for f in resultado]
                self.assertEqual(len(claves), len(set(claves)))

    def test_repetir_la_consulta_da_el_mismo_resultado(self):
        self.assertEqual(consultar("2026-06-15"), consultar("2026-06-15"))


class TestLimpieza(unittest.TestCase):
    def setUp(self):
        self.validos, self.rechazos = limpiar_datos(normalizar_campos(cargar()))

    def test_motivos_de_rechazo(self):
        esperados = Counter({
            "precio_fuera_de_rango": 1,
            "precio_no_numerico": 1,
            "fecha_formato_invalido": 1,
            "fecha_inexistente": 1,
            "duplicado": 1,
            "contradictorio": 2,
            "campo_faltante:localidad": 1,
        })
        self.assertEqual(Counter(r["motivo"] for r in self.rechazos), esperados)

    def test_conservacion_de_filas(self):
        self.assertEqual(len(self.validos) + len(self.rechazos), 16)
        self.assertEqual(len(self.validos), 8)

    def test_contradictorios_se_rechazan_todos(self):
        self.assertNotIn("700", {f["estacion_id"] for f in self.validos})

    def test_duplicado_conserva_solo_el_primero(self):
        beta = [f for f in self.validos if f["estacion_id"] == "200" and f["producto"] == COMBUSTIBLE]
        self.assertEqual(len(beta), 1)

    def test_cada_rechazo_informa_fila_y_detalle(self):
        for rechazo in self.rechazos:
            self.assertTrue(rechazo["detalle"])
            self.assertGreaterEqual(rechazo["fila"], 1)

    def test_precio_con_coma_decimal_se_acepta(self):
        fila = normalizar_campos([{
            "idempresa": "1", "localidad": "R", "producto": "P", "direccion": "D",
            "precio": "1234,5", "fecha_vigencia": "2026-06-01",
        }])
        validos, rechazos = limpiar_datos(fila)
        self.assertEqual(validos[0]["precio"], 1234.5)
        self.assertEqual(rechazos, [])


class TestFechas(unittest.TestCase):
    def test_formatos_validos(self):
        self.assertEqual(convertir_fecha("2026-06-01"), datetime(2026, 6, 1))
        self.assertEqual(convertir_fecha("2026-06-01 10:30"), datetime(2026, 6, 1, 10, 30))
        self.assertEqual(convertir_fecha("2026-06-01T10:30:15"), datetime(2026, 6, 1, 10, 30, 15))

    def test_la_expresion_regular_rechaza_formatos_ajenos(self):
        for texto in ["01/06/2026", "2026-6-1", "junio", "2026-06-01 10", "٢٠٢٦-٠٦-٠١"]:
            with self.subTest(texto=texto):
                with self.assertRaises(FechaConFormatoInvalido):
                    convertir_fecha(texto)

    def test_el_calendario_rechaza_fechas_que_pasan_la_regex(self):
        for texto in ["2026-02-30", "2026-13-01", "2026-02-29", "2026-06-01 25:00"]:
            with self.subTest(texto=texto):
                with self.assertRaises(FechaInexistente):
                    convertir_fecha(texto)

    def test_anio_bisiesto(self):
        self.assertEqual(convertir_fecha("2028-02-29"), datetime(2028, 2, 29))


class TestEsquemaYVerificacion(unittest.TestCase):
    def test_archivo_sin_filas(self):
        with self.assertRaisesRegex(EsquemaInvalido, "no contiene filas"):
            validar_esquema([])

    def test_columna_obligatoria_ausente_nombra_la_columna(self):
        filas = normalizar_campos([{"idempresa": "1", "localidad": "R", "producto": "P", "fecha_vigencia": "2026-06-01"}])
        with self.assertRaisesRegex(EsquemaInvalido, "precio"):
            validar_esquema(filas)

    def test_alias_de_columnas(self):
        filas = normalizar_campos([{"ESTACION_ID": "1", "Tipo_Horario": "Diurno"}])
        self.assertEqual(filas[0]["estacion_id"], "1")
        self.assertEqual(filas[0]["tipo_horario"], "Diurno")

    def test_verificar_resultado_detecta_orden_incorrecto(self):
        resultado, _, _ = consultar("2026-06-15")
        consulta = ConsultaPrecio("Rosario", COMBUSTIBLE, "2026-06-15")
        with self.assertRaisesRegex(ResultadoInconsistente, "ordenado"):
            verificar_resultado(list(reversed(resultado)), consulta)

    def test_verificar_resultado_detecta_precio_posterior(self):
        resultado, _, _ = consultar("2026-07-20")
        consulta = ConsultaPrecio("Rosario", COMBUSTIBLE, "2026-06-15")
        with self.assertRaisesRegex(ResultadoInconsistente, "posterior"):
            verificar_resultado(resultado, consulta)


class TestSalidas(unittest.TestCase):
    def test_exporta_resultado_y_rechazos(self):
        consulta = ConsultaPrecio("Rosario", COMBUSTIBLE, "2026-06-15")
        resultado, rechazos, _ = ejecutar_consulta(cargar(), consulta)
        with tempfile.TemporaryDirectory() as tmp:
            ruta_res = exportar_consulta(resultado, Path(tmp) / "sub" / "consulta.csv", consulta)
            ruta_rech = guardar_rechazos(rechazos, Path(tmp) / "rechazos.csv")
            with open(ruta_res, newline="", encoding="utf-8") as f:
                filas = list(csv.DictReader(f))
            with open(ruta_rech, newline="", encoding="utf-8") as f:
                filas_rech = list(csv.DictReader(f))
        self.assertEqual(len(filas), 3)
        self.assertEqual(filas[0]["precio"], "1050.0")
        self.assertEqual(filas[0]["fecha_consulta"], "2026-06-15")
        self.assertEqual(len(filas_rech), 8)
        self.assertEqual(buscar_estaciones([]), [])


if __name__ == "__main__":
    unittest.main()
