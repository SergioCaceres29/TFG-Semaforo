"""Tipos compartidos por todos los módulos: enums, mensajes y excepciones propias."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum
from pathlib import Path

NUM_CARRILES = 3
POSICIONES_CARRIL: tuple[int, ...] = tuple(range(1, NUM_CARRILES + 1))


class Clase(IntEnum):
    """RN-02: únicas clases admitidas. El valor es el índice del modelo (dataset/data.yaml)."""

    AUTO = 0
    MOTO = 1
    CAMION = 2

    @property
    def descripcion(self) -> str:
        """Nombre tal como figura en la tabla clase_vehiculo."""
        return self.name.lower()


class EstadoSemaforo(Enum):
    """RF-08: estado visible de un carril (el que se guarda en evento_fase)."""

    VERDE = "VERDE"
    AMARILLO = "AMARILLO"
    ROJO = "ROJO"


class EstadoEjecucion(Enum):
    """Figura 10: ciclo de vida de una ejecución. La demostración no lo modifica (sin Pausada)."""

    CREADA = "Creada"
    EN_EJECUCION = "EnEjecucion"
    FINALIZADA = "Finalizada"
    ABORTADA = "Abortada"


class ErrorVideo(Exception):
    """RNF-05: video inexistente, corrupto, no mp4 o incompatible con los otros carriles."""


class ErrorConfiguracion(Exception):
    """RF-02, RF-10: zona o parámetro inválido."""


@dataclass(frozen=True)
class MetadatosVideo:
    """RF-01 (HU-01 CA-03): datos de un video cargado, los mismos de la tabla video."""

    ruta: Path
    fps: float
    total_cuadros: int
    ancho: int
    alto: int

    @property
    def duracion(self) -> float:
        """Segundos del video (total_cuadros / fps)."""
        return self.total_cuadros / self.fps

    @property
    def resolucion(self) -> str:
        """Resolución con el formato de video.resolucion, ej. '1920x1080'."""
        return f"{self.ancho}x{self.alto}"


@dataclass(frozen=True)
class Parametros:
    """RF-10: parámetros de una ejecución (mismas columnas que la tabla ejecucion).

    Los tiempos son segundos enteros; las reglas de validación están en configuracion.py.
    """

    umbral_demanda: int
    umbral_confianza: float
    intervalo_seg: int
    verde_min: int
    verde_max: int
    amarillo: int


@dataclass(frozen=True)
class RegistroConteo:
    """RF-11, RN-03: ocupación de una zona y clase en el cuadro de cierre de un intervalo.

    Los límites del intervalo están en segundos del video.
    """

    id_zona: int
    clase: Clase
    cantidad: int
    intervalo_inicio: float
    intervalo_fin: float


Vertice = tuple[int, int]


@dataclass(frozen=True)
class Zona:
    """RF-02: zona virtual del video de un carril, con vértices en píxeles del video."""

    nombre_carril: str
    vertices: tuple[Vertice, ...]
    id_zona: int | None = None


@dataclass(frozen=True)
class CambioFase:
    """RF-08, RF-16: estados de los tres carriles después de una transición (segundos de simulación)."""

    marca_tiempo: float
    estados: dict[int, EstadoSemaforo]


@dataclass(frozen=True)
class ActualizacionCarril:
    """RF-06, RF-09: conteo vigente de un carril por clase."""

    posicion: int
    conteo: dict[Clase, int]

    @property
    def demanda(self) -> int:
        """Demanda del carril = suma de las tres clases."""
        return sum(self.conteo.values())


@dataclass(frozen=True)
class ProgresoEjecucion:
    """CU-02, RF-16: avance en segundos (del video en el análisis, de simulación en la demostración)."""

    marca_tiempo: float
    duracion: float
    estado: EstadoEjecucion


MensajeInterfaz = CambioFase | ActualizacionCarril | ProgresoEjecucion
