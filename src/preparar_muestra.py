"""Recorta el CSV histórico completo a una muestra chica (CSV + JSON equivalentes).

Lee el archivo de a una fila (no lo carga entero en memoria) y conserva las
filas de una localidad dentro de un rango de fechas. Convierte las fechas de
DD/MM/AAAA HH:MM a AAAA-MM-DD HH:MM. Las filas con fecha mal
formada se conservan a propósito, para que la muestra incluya casos a limpiar.

Uso:
    python -m src.preparar_muestra --entrada precios-historicos.csv \
        --localidad Rosario --desde 2026-05-01 --hasta 2026-10-20
"""
import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from src.modelo import normalizar_texto
from src.pipeline import CAMPOS_ORIGEN

ENTERO_RE = re.compile(r"-?[1-9]\d*|0")
# El CSV oficial trae las fechas como DD/MM/AAAA HH:MM; la aplicación espera AAAA-MM-DD HH:MM.
FECHA_ORIGEN_RE = re.compile(r"(\d{2})/(\d{2})/(\d{4})(?: (\d{2}:\d{2}(?::\d{2})?))?")


def fecha_a_iso(texto):
    """Convierte 'DD/MM/AAAA[ HH:MM[:SS]]' a 'AAAA-MM-DD[ HH:MM[:SS]]'.

    Si el texto no tiene ese formato, o la fecha no existe en el calendario,
    se devuelve igual para que la limpieza posterior lo rechace y lo registre.
    """
    coincidencia = FECHA_ORIGEN_RE.fullmatch(texto.strip())
    if not coincidencia:
        return texto
    dia, mes, anio, hora = coincidencia.groups()
    try:
        datetime(int(anio), int(mes), int(dia))
    except ValueError:
        return texto
    return f"{anio}-{mes}-{dia}" + (f" {hora}" if hora else "")


def valor_para_json(campo, texto):
    """El precio va como número cuando el texto lo representa exactamente."""
    if campo != "precio":
        return texto
    if ENTERO_RE.fullmatch(texto):
        return int(texto)
    try:
        numero = float(texto)
    except ValueError:
        return texto
    return numero if str(numero) == texto else texto


def escribir_muestra(encabezado, filas, ruta_csv, ruta_json):
    """Escribe las mismas filas en CSV y en JSON (lista de objetos)."""
    for ruta in (ruta_csv, ruta_json):
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    with open(ruta_csv, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=encabezado)
        escritor.writeheader()
        escritor.writerows(filas)
    como_json = [{k: valor_para_json(k.strip().lower(), v) for k, v in fila.items()} for fila in filas]
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(como_json, f, ensure_ascii=False, indent=1)


def _columna(encabezado, interno):
    for nombre in encabezado:
        if nombre.strip().lower() in CAMPOS_ORIGEN[interno]:
            return nombre
    raise SystemExit(f"Error: el CSV no tiene una columna para '{interno}' (acepta: {CAMPOS_ORIGEN[interno]}).")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--entrada", required=True)
    parser.add_argument("--localidad", required=True)
    parser.add_argument("--desde", default="0000-01-01", help="AAAA-MM-DD (incluida)")
    parser.add_argument("--hasta", default="9999-12-31", help="AAAA-MM-DD (incluida)")
    parser.add_argument("--max-filas", type=int, default=5000)
    parser.add_argument("--salida-csv", default="data/muestra.csv")
    parser.add_argument("--salida-json", default="data/muestra.json")
    args = parser.parse_args(argv)

    objetivo = normalizar_texto(args.localidad)
    filas, leidas = [], 0
    with open(args.entrada, newline="", encoding="utf-8-sig") as f:
        lector = csv.DictReader(f)
        encabezado = lector.fieldnames
        col_loc = _columna(encabezado, "localidad")
        col_fecha = _columna(encabezado, "fecha_vigencia")
        for fila in lector:
            leidas += 1
            if normalizar_texto(fila[col_loc] or "") != objetivo:
                continue
            fila[col_fecha] = fecha_a_iso(fila[col_fecha] or "")
            dia = fila[col_fecha].strip()[:10]
            es_iso = re.fullmatch(r"\d{4}-\d{2}-\d{2}", dia) is not None
            if es_iso and not (args.desde <= dia <= args.hasta):
                continue
            filas.append(fila)
    if len(filas) > args.max_filas:
        print(f"Aviso: {len(filas)} filas coinciden; se conservan las últimas {args.max_filas}.", file=sys.stderr)
        filas = filas[-args.max_filas:]
    if not filas:
        raise SystemExit("Error: ninguna fila coincide con la localidad y el rango indicados.")
    escribir_muestra(encabezado, filas, args.salida_csv, args.salida_json)
    print(f"{leidas} filas leídas, {len(filas)} conservadas -> {args.salida_csv} y {args.salida_json}")


if __name__ == "__main__":
    main()
