"""Fuentes de datos: una interfaz común y dos implementaciones (CSV y JSON).

El resto de la aplicación solo conoce ``FuenteDatos.cargar(ruta)``, que devuelve
siempre una lista de diccionarios. Así la lógica no depende del formato.
"""
import csv
import json
from abc import ABC, abstractmethod
from pathlib import Path

from src.errores import FuenteInvalida


class FuenteDatos(ABC):
    """Contrato común: ``cargar(ruta)`` devuelve una lista de diccionarios."""

    @abstractmethod
    def cargar(self, ruta):
        """Lee el archivo y devuelve ``list[dict]`` con un dict por fila."""

    @staticmethod
    def _verificar_ruta(ruta):
        camino = Path(ruta)
        if not camino.is_file():
            raise FuenteInvalida(f"No existe el archivo de entrada: {camino}")
        return camino


class FuenteCSV(FuenteDatos):
    """Lee un CSV con encabezado. Los valores quedan como texto."""

    def __init__(self, delimitador=","):
        self.delimitador = delimitador

    def cargar(self, ruta):
        camino = self._verificar_ruta(ruta)
        filas = []
        try:
            with camino.open(newline="", encoding="utf-8-sig") as archivo:
                lector = csv.DictReader(archivo, delimiter=self.delimitador)
                if lector.fieldnames is None:
                    raise FuenteInvalida(f"El CSV {camino} está vacío o no tiene encabezado.")
                for numero, fila in enumerate(lector, start=2):
                    if None in fila:
                        raise FuenteInvalida(
                            f"{camino}: la línea {numero} tiene más columnas que el encabezado."
                        )
                    filas.append(dict(fila))
        except UnicodeDecodeError as error:
            raise FuenteInvalida(f"{camino} no está codificado en UTF-8: {error}") from error
        return filas


class FuenteJSON(FuenteDatos):
    """Lee un JSON cuya raíz es una lista de objetos (uno por fila)."""

    def cargar(self, ruta):
        camino = self._verificar_ruta(ruta)
        try:
            with camino.open(encoding="utf-8-sig") as archivo:
                datos = json.load(archivo)
        except json.JSONDecodeError as error:
            raise FuenteInvalida(
                f"{camino}: JSON mal formado (línea {error.lineno}, columna {error.colno}): {error.msg}"
            ) from error
        except UnicodeDecodeError as error:
            raise FuenteInvalida(f"{camino} no está codificado en UTF-8: {error}") from error
        if not isinstance(datos, list) or not all(isinstance(x, dict) for x in datos):
            raise FuenteInvalida(f"{camino}: se esperaba una lista de objetos JSON (una por fila).")
        return datos


def fuente_para(ruta):
    """Elige la implementación según la extensión del archivo."""
    extension = Path(ruta).suffix.lower()
    if extension == ".csv":
        return FuenteCSV()
    if extension == ".json":
        return FuenteJSON()
    raise FuenteInvalida(f"Formato no soportado '{extension}' en {ruta}. Use .csv o .json.")
