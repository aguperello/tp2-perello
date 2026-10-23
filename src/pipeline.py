"""Flujo de procesamiento: normalizar -> validar -> limpiar -> seleccionar -> comunicar.

Todas las funciones reciben datos ya cargados (lista de diccionarios) y no
dependen del formato del archivo de origen.
"""
import csv
import math
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from src.errores import (
    EsquemaInvalido,
    FechaConFormatoInvalido,
    FechaInexistente,
    ResultadoInconsistente,
)
from src.modelo import normalizar_texto

# Nombre interno -> nombres aceptados en el archivo de origen (en minúsculas).
# SUPUESTO A VERIFICAR contra el CSV real: si una columna se llama distinto,
# basta con agregar el nombre real a la lista correspondiente.
CAMPOS_ORIGEN = {
    "estacion_id": ["idempresa", "estacion_id"],
    "empresa": ["empresa"],
    "direccion": ["direccion"],
    "localidad": ["localidad"],
    "provincia": ["provincia"],
    "producto": ["producto"],
    "tipo_horario": ["tipohorario", "tipo_horario"],
    "precio": ["precio"],
    "fecha_vigencia": ["fecha_vigencia"],
}
CAMPOS_OBLIGATORIOS = ("estacion_id", "localidad", "producto", "precio", "fecha_vigencia")

# Expresión regular de la fecha de cada registro: AAAA-MM-DD con hora opcional.
# Comprueba solo la forma; que la fecha exista lo comprueba ``convertir_fecha``.
FECHA_REGISTRO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?$", re.ASCII)

CAMPOS_RESULTADO = [
    "estacion_id", "empresa", "direccion", "localidad",
    "producto", "tipo_horario", "precio", "fecha_vigencia",
]
CAMPOS_EXPORTACION = CAMPOS_RESULTADO + ["fecha_consulta"]
CAMPOS_RECHAZOS = [
    "fila", "motivo", "detalle", "estacion_id", "direccion",
    "localidad", "producto", "tipo_horario", "precio", "fecha_vigencia",
]


# --------------------------------------------------------------------------
# Normalización y validación de esquema
# --------------------------------------------------------------------------
def normalizar_campos(filas):
    """Unifica nombres de columnas y convierte todo valor a texto sin espacios.

    Una columna ausente queda en ``None``; una presente pero vacía, en ``""``.
    ``_fila`` conserva el número de fila (desde 1) para informar rechazos.
    """
    normalizadas = []
    for numero, fila in enumerate(filas, start=1):
        claves = {str(k).strip().lower(): v for k, v in fila.items() if k is not None}
        nueva = {"_fila": numero}
        for interno, alias in CAMPOS_ORIGEN.items():
            presentes = [nombre for nombre in alias if nombre in claves]
            if not presentes:
                nueva[interno] = None
            else:
                valor = claves[presentes[0]]
                nueva[interno] = "" if valor is None else str(valor).strip()
        normalizadas.append(nueva)
    return normalizadas


def validar_esquema(filas):
    """Verifica que haya filas y que existan las columnas obligatorias."""
    if not filas:
        raise EsquemaInvalido("El archivo no contiene filas de datos.")
    faltantes = [c for c in CAMPOS_OBLIGATORIOS if all(f[c] is None for f in filas)]
    if faltantes:
        detalle = "; ".join(
            f"'{c}' (nombres aceptados: {', '.join(CAMPOS_ORIGEN[c])})" for c in faltantes
        )
        raise EsquemaInvalido(f"Faltan columnas obligatorias: {detalle}.")


# --------------------------------------------------------------------------
# Conversión y limpieza
# --------------------------------------------------------------------------
def convertir_fecha(texto):
    """Convierte 'AAAA-MM-DD[ HH:MM[:SS]]' en datetime.

    La expresión regular valida la forma; ``strptime`` valida que la fecha y la
    hora existan (por ejemplo, rechaza 2026-02-30).
    """
    texto = texto.strip()
    if not FECHA_REGISTRO_RE.match(texto):
        raise FechaConFormatoInvalido(f"'{texto}' no tiene el formato AAAA-MM-DD [HH:MM[:SS]]")
    normalizado = texto.replace("T", " ")
    for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(normalizado, formato)
        except ValueError:
            continue
    raise FechaInexistente(f"'{texto}' no es una fecha u hora válida del calendario")


def _validar_fila(fila):
    """Devuelve (fila_limpia, None) o (None, (motivo, detalle))."""
    for campo in CAMPOS_OBLIGATORIOS:
        if not fila[campo]:
            return None, (f"campo_faltante:{campo}", f"La fila {fila['_fila']} no tiene valor en '{campo}'.")

    texto_precio = fila["precio"]
    if "," in texto_precio and "." not in texto_precio:
        texto_precio = texto_precio.replace(",", ".")
    try:
        precio = float(texto_precio)
    except ValueError:
        precio = math.nan
    if not math.isfinite(precio):
        return None, ("precio_no_numerico", f"El precio '{fila['precio']}' no es un número.")
    if precio <= 0:
        return None, ("precio_fuera_de_rango", f"El precio {precio} debe ser mayor que cero.")

    try:
        fecha = convertir_fecha(fila["fecha_vigencia"])
    except FechaConFormatoInvalido as error:
        return None, ("fecha_formato_invalido", str(error))
    except FechaInexistente as error:
        return None, ("fecha_inexistente", str(error))

    direccion = fila["direccion"] or ""
    limpia = {
        "_fila": fila["_fila"],
        "_crudo": fila,
        "estacion_id": fila["estacion_id"],
        "empresa": fila["empresa"] or "",
        "direccion": direccion,
        "localidad": fila["localidad"],
        "provincia": fila["provincia"] or "",
        "producto": fila["producto"],
        "tipo_horario": fila["tipo_horario"] or "",
        "precio": precio,
        "fecha": fecha,
        # Una empresa puede tener varias bocas de expendio: la estación se
        # identifica por empresa + dirección. SUPUESTO A VERIFICAR.
        "estacion_clave": f"{fila['estacion_id']}|{normalizar_texto(direccion)}",
    }
    return limpia, None


def _rechazo(fila_cruda, motivo, detalle):
    def texto(campo):
        return fila_cruda.get(campo) or ""

    return {
        "fila": fila_cruda["_fila"],
        "motivo": motivo,
        "detalle": detalle,
        "estacion_id": texto("estacion_id"),
        "direccion": texto("direccion"),
        "localidad": texto("localidad"),
        "producto": texto("producto"),
        "tipo_horario": texto("tipo_horario"),
        "precio": texto("precio"),
        "fecha_vigencia": texto("fecha_vigencia"),
    }


def _clave_registro(fila):
    return (
        fila["estacion_clave"],
        normalizar_texto(fila["producto"]),
        normalizar_texto(fila["tipo_horario"]),
        fila["fecha"],
    )


def limpiar_datos(filas):
    """Separa filas válidas de rechazadas y registra el motivo de cada rechazo.

    Reglas: campos obligatorios presentes, precio numérico y mayor que cero,
    fecha con formato y calendario válidos. Luego, sobre las filas válidas:
    un registro idéntico repetido es *duplicado* (se conserva el primero); dos
    registros con misma estación, combustible, horario y fecha pero distinto
    precio son *contradictorios* y se rechazan todos.
    """
    rechazos = []
    limpias = []
    for fila in filas:
        limpia, problema = _validar_fila(fila)
        if problema:
            rechazos.append(_rechazo(fila, *problema))
        else:
            limpias.append(limpia)

    grupos = defaultdict(list)
    for fila in limpias:
        grupos[_clave_registro(fila)].append(fila)

    validos = []
    for fila in limpias:
        grupo = grupos[_clave_registro(fila)]
        precios = sorted({g["precio"] for g in grupo})
        if len(precios) > 1:
            detalle = (
                f"La fila {fila['_fila']} informa {fila['precio']}, pero otra fila de la misma "
                f"estación, combustible, horario y fecha informa un precio distinto {precios}."
            )
            rechazos.append(_rechazo(fila["_crudo"], "contradictorio", detalle))
        elif fila is not grupo[0]:
            detalle = f"La fila {fila['_fila']} repite la fila {grupo[0]['_fila']}."
            rechazos.append(_rechazo(fila["_crudo"], "duplicado", detalle))
        else:
            validos.append(fila)

    rechazos.sort(key=lambda r: r["fila"])
    return validos, rechazos


# --------------------------------------------------------------------------
# Selección de precios vigentes y búsqueda
# --------------------------------------------------------------------------
def seleccionar_vigentes(validos, consulta):
    """Para cada estación (y horario) elige el registro más reciente que no
    supere la fecha de referencia."""
    limite = consulta.fecha_limite()
    vigentes = {}
    for fila in validos:
        if fila["fecha"] > limite or not consulta.coincide(fila):
            continue
        clave = (fila["estacion_clave"], normalizar_texto(fila["tipo_horario"]))
        if clave not in vigentes or fila["fecha"] > vigentes[clave]["fecha"]:
            vigentes[clave] = fila
    return list(vigentes.values())


def buscar_estaciones(vigentes):
    """Ordena de menor a mayor precio (desempate: estación y horario)."""
    ordenadas = sorted(
        vigentes, key=lambda f: (f["precio"], f["estacion_clave"], normalizar_texto(f["tipo_horario"]))
    )
    return [
        {
            "estacion_id": f["estacion_id"],
            "empresa": f["empresa"],
            "direccion": f["direccion"],
            "localidad": f["localidad"],
            "producto": f["producto"],
            "tipo_horario": f["tipo_horario"],
            "precio": f["precio"],
            "fecha_vigencia": f["fecha"],
            "_estacion_clave": f["estacion_clave"],
        }
        for f in ordenadas
    ]


def verificar_resultado(resultado, consulta):
    """Comprueba propiedades que el resultado debe cumplir siempre."""
    limite = consulta.fecha_limite()
    vistos = set()
    anterior = None
    for fila in resultado:
        if fila["precio"] <= 0:
            raise ResultadoInconsistente(f"Precio no positivo en el resultado: {fila}")
        if fila["fecha_vigencia"] > limite:
            raise ResultadoInconsistente(
                f"Hay un precio posterior a la fecha de consulta: {fila['fecha_vigencia']}"
            )
        if not consulta.coincide(fila):
            raise ResultadoInconsistente(f"Hay una fila que no corresponde a la consulta: {fila}")
        clave = (fila["_estacion_clave"], normalizar_texto(fila["tipo_horario"]))
        if clave in vistos:
            raise ResultadoInconsistente(f"Estación repetida en el resultado: {clave}")
        vistos.add(clave)
        if anterior is not None and fila["precio"] < anterior:
            raise ResultadoInconsistente("El resultado no está ordenado por precio ascendente.")
        anterior = fila["precio"]


def contar_estaciones_sin_vigente(validos, consulta, vigentes):
    """Estaciones de la localidad y combustible pedidos que no tienen ningún
    registro anterior o igual a la fecha de referencia."""
    todas = {f["estacion_clave"] for f in validos if consulta.coincide(f)}
    con_precio = {f["estacion_clave"] for f in vigentes}
    return len(todas - con_precio)


def ejecutar_consulta(filas_crudas, consulta):
    """Recorre todo el flujo y devuelve (resultado, rechazos, resumen)."""
    datos = normalizar_campos(filas_crudas)
    validar_esquema(datos)
    validos, rechazos = limpiar_datos(datos)
    vigentes = seleccionar_vigentes(validos, consulta)
    resultado = buscar_estaciones(vigentes)
    verificar_resultado(resultado, consulta)
    resumen = {
        "filas_leidas": len(datos),
        "filas_validas": len(validos),
        "filas_rechazadas": len(rechazos),
        "estaciones_con_precio": len(resultado),
        "estaciones_sin_precio_vigente": contar_estaciones_sin_vigente(validos, consulta, vigentes),
    }
    return resultado, rechazos, resumen


# --------------------------------------------------------------------------
# Salidas
# --------------------------------------------------------------------------
def _escribir_csv(ruta, campos, filas):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(filas)
    return ruta


def exportar_consulta(resultado, ruta, consulta):
    """Guarda el resultado con la fecha de vigencia de cada precio."""
    filas = []
    for fila in resultado:
        salida = {c: fila[c] for c in CAMPOS_RESULTADO}
        salida["fecha_vigencia"] = fila["fecha_vigencia"].strftime("%Y-%m-%d %H:%M:%S")
        salida["fecha_consulta"] = consulta.fecha_referencia.isoformat()
        filas.append(salida)
    return _escribir_csv(ruta, CAMPOS_EXPORTACION, filas)


def guardar_rechazos(rechazos, ruta):
    """Guarda los registros rechazados con su motivo."""
    return _escribir_csv(ruta, CAMPOS_RECHAZOS, rechazos)
