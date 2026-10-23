"""Interfaz de consola del buscador de precios vigentes de combustibles.

Uso (desde la raíz del repositorio):
    python -m src.main --entrada data/muestra.csv --localidad Rosario \
        --combustible "Gas Oil Grado 2" --fecha 2026-10-14
"""
import argparse
import sys

from src.errores import ErrorDeDatos, ParametroInvalido
from src.fuentes import fuente_para
from src.modelo import ConsultaPrecio
from src.pipeline import (
    ejecutar_consulta,
    exportar_consulta,
    guardar_rechazos,
    normalizar_campos,
    validar_esquema,
)


def construir_parser():
    parser = argparse.ArgumentParser(
        prog="python -m src.main",
        description="Busca los precios vigentes de un combustible en una localidad a una fecha dada.",
    )
    parser.add_argument("--entrada", required=True, help="Archivo de datos (.csv o .json).")
    parser.add_argument("--localidad", help="Localidad a consultar (ej.: Rosario).")
    parser.add_argument("--combustible", help="Nombre del combustible tal como figura en los datos.")
    parser.add_argument("--fecha", help="Fecha de referencia AAAA-MM-DD.")
    parser.add_argument("--horario", help="Filtro opcional por tipo de horario.")
    parser.add_argument("--salida", default="outputs/consulta.csv", help="CSV con el resultado.")
    parser.add_argument("--rechazos", default="outputs/rechazos.csv", help="CSV con los registros rechazados.")
    parser.add_argument("--top", type=int, default=10, help="Cuántas filas mostrar en pantalla (se guardan todas).")
    parser.add_argument(
        "--listar", choices=["localidades", "combustibles"],
        help="Muestra los valores distintos disponibles en el archivo y termina.",
    )
    return parser


def _listar(filas_crudas, campo):
    datos = normalizar_campos(filas_crudas)
    validar_esquema(datos)
    clave = "localidad" if campo == "localidades" else "producto"
    valores = sorted({f[clave] for f in datos if f[clave]})
    print(f"{len(valores)} valores distintos de '{clave}':")
    for valor in valores:
        print(f"  {valor}")


def _imprimir_tabla(resultado, top):
    columnas = [("precio", "Precio"), ("empresa", "Empresa"), ("direccion", "Dirección"),
                ("tipo_horario", "Horario"), ("fecha_vigencia", "Vigente desde")]
    filas = []
    for fila in resultado[:top]:
        filas.append([
            f"{fila['precio']:.2f}", fila["empresa"], fila["direccion"],
            fila["tipo_horario"], fila["fecha_vigencia"].strftime("%Y-%m-%d %H:%M"),
        ])
    anchos = [max(len(titulo), *(len(f[i]) for f in filas)) for i, (_, titulo) in enumerate(columnas)]
    print("  ".join(titulo.ljust(anchos[i]) for i, (_, titulo) in enumerate(columnas)))
    print("  ".join("-" * a for a in anchos))
    for fila in filas:
        print("  ".join(valor.ljust(anchos[i]) for i, valor in enumerate(fila)))


def main(argv=None):
    parser = construir_parser()
    args = parser.parse_args(argv)
    if not args.listar and not (args.localidad and args.combustible and args.fecha):
        parser.error("Indique --localidad, --combustible y --fecha (o use --listar).")

    try:
        crudos = fuente_para(args.entrada).cargar(args.entrada)
        if args.listar:
            _listar(crudos, args.listar)
            return 0
        consulta = ConsultaPrecio(args.localidad, args.combustible, args.fecha, args.horario)
        resultado, rechazos, resumen = ejecutar_consulta(crudos, consulta)
    except (ErrorDeDatos, ParametroInvalido) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    guardar_rechazos(rechazos, args.rechazos)
    print(f"Consulta: {consulta.combustible} en {consulta.localidad}, precios vigentes al {consulta.fecha_referencia.isoformat()}")
    print(
        f"Filas leídas: {resumen['filas_leidas']} | válidas: {resumen['filas_validas']} | "
        f"rechazadas: {resumen['filas_rechazadas']} (ver {args.rechazos})"
    )
    if not resultado:
        print(
            "Sin resultados: ninguna estación tiene un precio informado para esa localidad, "
            "combustible y fecha (o todos sus registros son posteriores a la fecha)."
        )
        print(f"Estaciones de la localidad sin precio vigente a esa fecha: {resumen['estaciones_sin_precio_vigente']}")
        return 0

    print()
    _imprimir_tabla(resultado, args.top)
    exportar_consulta(resultado, args.salida, consulta)
    print()
    print(f"{resumen['estaciones_con_precio']} estaciones con precio vigente; "
          f"{resumen['estaciones_sin_precio_vigente']} sin precio vigente a esa fecha.")
    print(f"Resultado guardado en {args.salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
