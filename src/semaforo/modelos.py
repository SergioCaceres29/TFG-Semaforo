"""Tipos compartidos por todos los módulos: enums, mensajes y excepciones propias."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum

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
    """RF-16: ciclo de vida de una ejecución."""

    CREADA = "Creada"
    EN_EJECUCION = "EnEjecucion"
    PAUSADA = "Pausada"
    FINALIZADA = "Finalizada"
    ABORTADA = "Abortada"


class ErrorVideo(Exception):
    """RNF-05: video inexistente, corrupto, no mp4 o incompatible con los otros carriles."""


class ErrorConfiguracion(Exception):
    """RF-02, RF-10: zona o parámetro inválido."""


@dataclass(frozen=True)
class CambioFase:
    """RF-08, RF-09: estados de los tres carriles después de una transición."""

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
    """RF-16: avance de la ejecución en segundos del video."""

    marca_tiempo: float
    duracion: float
    estado: EstadoEjecucion


MensajeInterfaz = CambioFase | ActualizacionCarril | ProgresoEjecucion
