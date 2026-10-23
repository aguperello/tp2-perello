"""Genera una muestra SINTÉTICA (inventada) para probar la aplicación sin el CSV real.

Con semilla fija, la salida es siempre idéntica. Incluye a propósito filas
inválidas, duplicadas y contradictorias. NO son precios reales.

Uso:  python -m src.datos_sinteticos
"""
import random
from datetime import datetime, timedelta

from src.preparar_muestra import escribir_muestra

ENCABEZADO = [
    "idempresa", "empresa", "direccion", "localidad",
    "provincia", "producto", "tipohorario", "precio", "fecha_vigencia",
]
ESTACIONES = [
    ("1001", "PETROLERA ALFA S.A.", "Calle Ficticia 100", "ROSARIO", "SANTA FE"),
    ("1002", "ESTACION BETA S.R.L.", "Calle Ficticia 200", "ROSARIO", "SANTA FE"),
    ("1003", "COMBUSTIBLES GAMMA", "Calle Ficticia 300", "ROSARIO", "SANTA FE"),
    ("1004", "SERVICENTRO DELTA", "Calle Ficticia 400", "Rosario", "SANTA FE"),
    ("1005", "ESTACION EPSILON", "Calle Ficticia 500", "ROSARIO", "SANTA FE"),
    ("1006", "PETROLERA ALFA S.A.", "Calle Ficticia 600", "SANTA FE", "SANTA FE"),
    ("1007", "ESTACION ZETA", "Calle Ficticia 700", "SANTA FE", "SANTA FE"),
    ("1008", "ESTACION ETA", "Calle Ficticia 800", "CORDOBA", "CORDOBA"),
]
PRODUCTOS = [("Nafta (súper) entre 92 y 95 Ron", 1300.0), ("Gas Oil Grado 2", 1250.0)]


def generar(semilla=42):
    azar = random.Random(semilla)
    inicio = datetime(2026, 5, 1)
    filas = []
    for id_, empresa, direccion, localidad, provincia in ESTACIONES:
        for producto, base in PRODUCTOS:
            precio = base * (0.95 + azar.random() * 0.1)
            for dia in sorted(azar.sample(range(0, 172), azar.randint(3, 6))):
                precio *= 1 + azar.random() * 0.05
                momento = inicio + timedelta(days=dia, hours=azar.randint(6, 22), minutes=azar.randint(0, 59))
                filas.append(dict(zip(ENCABEZADO, [
                    id_, empresa, direccion, localidad, provincia, producto, "Diurno",
                    str(round(precio, 2)), momento.strftime("%Y-%m-%d %H:%M:%S"),
                ])))
    base_fila = ["1001", "PETROLERA ALFA S.A.", "Calle Ficticia 100", "ROSARIO", "SANTA FE",
                 PRODUCTOS[0][0], "Diurno"]
    malas = [
        base_fila + ["-5", "2026-06-01 08:00:00"],        # precio fuera de rango
        base_fila + ["abc", "2026-06-02 08:00:00"],       # precio no numérico
        base_fila + ["1400.0", "14/06/2026"],             # formato de fecha inválido
        base_fila + ["1400.0", "2026-02-30 08:00:00"],    # fecha inexistente
        base_fila + ["1410.0", "2026-07-05 08:00:00"],    # contradictorio (par)
        base_fila + ["1420.0", "2026-07-05 08:00:00"],
        ["1002", "ESTACION BETA S.R.L.", "Calle Ficticia 200", "", "SANTA FE",
         PRODUCTOS[0][0], "Diurno", "1400.0", "2026-07-06 08:00:00"],  # localidad faltante
    ]
    filas.extend(dict(zip(ENCABEZADO, m)) for m in malas)
    filas.append(dict(filas[0]))  # duplicado exacto de la primera fila
    return filas


if __name__ == "__main__":
    filas = generar()
    escribir_muestra(ENCABEZADO, filas, "data/muestra_sintetica.csv", "data/muestra_sintetica.json")
    print(f"{len(filas)} filas sintéticas -> data/muestra_sintetica.csv y data/muestra_sintetica.json")
