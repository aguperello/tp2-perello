"""Modelo del dominio: la consulta de precios vigentes."""
import re
import unicodedata
from datetime import date, datetime, time

from src.errores import ParametroInvalido

# Patrón de la fecha de referencia pasada por parámetro: AAAA-MM-DD.
# Solo comprueba la forma; que el día exista lo verifica ``_parsear_fecha``.
FECHA_CONSULTA_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$", re.ASCII)


def normalizar_texto(texto):
    """Minúsculas, sin acentos y sin espacios sobrantes, para comparar textos."""
    descompuesto = unicodedata.normalize("NFKD", str(texto))
    sin_marcas = "".join(c for c in descompuesto if not unicodedata.combining(c))
    return sin_marcas.casefold().strip()


class ConsultaPrecio:
    """Parámetros de una consulta, ya validados, y el criterio de coincidencia.

    Atributos: localidad, combustible, fecha_referencia (date) y horario
    (opcional). La comparación de textos ignora mayúsculas y acentos.
    """

    def __init__(self, localidad, combustible, fecha_referencia, horario=None):
        if not isinstance(localidad, str) or not localidad.strip():
            raise ParametroInvalido("La localidad no puede estar vacía.")
        if not isinstance(combustible, str) or not combustible.strip():
            raise ParametroInvalido("El combustible no puede estar vacío.")
        self.localidad = localidad.strip()
        self.combustible = combustible.strip()
        self.fecha_referencia = self._parsear_fecha(fecha_referencia)
        self.horario = horario.strip() if isinstance(horario, str) and horario.strip() else None
        self._localidad = normalizar_texto(self.localidad)
        self._combustible = normalizar_texto(self.combustible)
        self._horario = normalizar_texto(self.horario) if self.horario else None

    @staticmethod
    def _parsear_fecha(valor):
        if isinstance(valor, datetime):
            return valor.date()
        if isinstance(valor, date):
            return valor
        texto = str(valor).strip()
        coincidencia = FECHA_CONSULTA_RE.match(texto)
        if not coincidencia:
            raise ParametroInvalido(f"La fecha '{texto}' no tiene el formato AAAA-MM-DD (ej.: 2026-10-14).")
        anio, mes, dia = (int(g) for g in coincidencia.groups())
        try:
            return date(anio, mes, dia)
        except ValueError as error:
            raise ParametroInvalido(f"La fecha '{texto}' no existe en el calendario ({error}).") from error

    def fecha_limite(self):
        """Último instante incluido: el final del día de referencia."""
        return datetime.combine(self.fecha_referencia, time.max)

    def coincide(self, fila):
        """True si la fila limpia es de la localidad, combustible y horario pedidos."""
        if normalizar_texto(fila["localidad"]) != self._localidad:
            return False
        if normalizar_texto(fila["producto"]) != self._combustible:
            return False
        if self._horario is not None and normalizar_texto(fila["tipo_horario"]) != self._horario:
            return False
        return True

    def __repr__(self):
        return (
            f"ConsultaPrecio(localidad={self.localidad!r}, combustible={self.combustible!r}, "
            f"fecha_referencia={self.fecha_referencia.isoformat()}, horario={self.horario!r})"
        )
