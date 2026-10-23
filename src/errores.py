"""Excepciones propias de la aplicación.

Cada una lleva un mensaje pensado para quien usa el programa, de modo que
main.py pueda mostrarlo tal cual en lugar de un traceback.
"""


class ErrorDeDatos(Exception):
    """Problema con los datos de entrada (archivo, esquema o resultado)."""


class FuenteInvalida(ErrorDeDatos):
    """El archivo no existe, está vacío o no tiene la estructura esperada."""


class EsquemaInvalido(ErrorDeDatos):
    """Faltan columnas obligatorias o no hay filas para analizar."""


class ResultadoInconsistente(ErrorDeDatos):
    """El resultado calculado viola una propiedad que debía cumplirse."""


class ParametroInvalido(ValueError):
    """Un parámetro de la consulta (localidad, combustible, fecha) es inválido."""


class FechaConFormatoInvalido(ValueError):
    """El texto no respeta el patrón AAAA-MM-DD [HH:MM[:SS]]."""


class FechaInexistente(ValueError):
    """El texto respeta el patrón pero no es una fecha/hora real."""
