"""Máquina de estados de los tres carriles en segundos de simulación (HU-06, RF-08, RN-05, RN-06, RN-11).

Python puro: sin cv2, sin base y sin reloj. Un solo carril fuera de rojo a la vez (RN-06): el que está
en verde o en amarillo. Cada carril lleva su tiempo de video, que avanza solo en verde o amarillo (RN-11).
Ver docs/specs/diseno.md §3 y §4.1.
"""

from __future__ import annotations

from dataclasses import dataclass

from semaforo.modelos import POSICIONES_CARRIL, EstadoSemaforo, Parametros, siguiente_carril

PASO_SEG = 1
"""diseno.md §4.1, regla 2: la simulación avanza de a 1 s de t_sim."""


@dataclass(frozen=True)
class CambioEstado:
    """RF-08: un carril cambió de estado en t_sim; t_video es su tiempo de video en ese instante."""

    marca_tiempo: int
    posicion: int
    estado: EstadoSemaforo
    t_video: int


class ControladorSemaforo:
    """RF-08: aplica verde mínimo, verde máximo y amarillo, y registra cada cambio de estado."""

    def __init__(self, parametros: Parametros, carril_inicial: int = POSICIONES_CARRIL[0]) -> None:
        """Regla 3 (§4.1): en t_sim = 0 el carril inicial arranca en verde por ciclo fijo; el resto en rojo."""
        self._verde_min = parametros.verde_min
        self._verde_max = parametros.verde_max
        self._amarillo = parametros.amarillo
        self.t_sim = 0
        self.t_video = {posicion: 0 for posicion in POSICIONES_CARRIL}
        self.cambios: list[CambioEstado] = []
        self._estados: dict[int, EstadoSemaforo] = {}
        self._inicio_estado: dict[int, int] = {}
        self._activo = carril_inicial
        self._entrante = carril_inicial
        for posicion in POSICIONES_CARRIL:
            self._cambiar(posicion, EstadoSemaforo.VERDE if posicion == carril_inicial else EstadoSemaforo.ROJO)

    @property
    def carril_activo(self) -> int:
        """Carril en verde o en amarillo (el único fuera de rojo, RN-06)."""
        return self._activo

    @property
    def verde_min_cumplido(self) -> bool:
        """HU-06 CA-02: el carril activo está en verde y ya cumplió el verde mínimo."""
        return (self._estados[self._activo] is EstadoSemaforo.VERDE
                and self.tiempo_en_estado(self._activo) >= self._verde_min)

    def tiempo_en_estado(self, posicion: int) -> int:
        """Segundos de t_sim que lleva el carril en su estado actual."""
        return self.t_sim - self._inicio_estado[posicion]

    def obtener_estados(self) -> dict[int, EstadoSemaforo]:
        """RF-08: estado de cada carril en el t_sim actual."""
        return dict(self._estados)

    def tiempos_rojo(self) -> dict[int, int]:
        """RN-07 (regla 8): segundos en rojo desde que pasó a rojo; 0 si no está en rojo."""
        return {posicion: self.tiempo_en_estado(posicion) if estado is EstadoSemaforo.ROJO else 0
                for posicion, estado in self._estados.items()}

    def verificar_tiempos(self) -> None:
        """RN-05, RN-06 (regla 2): procesa en su segundo exacto el fin del amarillo y el verde máximo."""
        tiempo = self.tiempo_en_estado(self._activo)
        estado = self._estados[self._activo]
        if estado is EstadoSemaforo.AMARILLO and tiempo >= self._amarillo:
            self._cambiar(self._activo, EstadoSemaforo.ROJO)
            self._activo = self._entrante
            self._cambiar(self._activo, EstadoSemaforo.VERDE)
        elif estado is EstadoSemaforo.VERDE and tiempo >= self._verde_max:
            self._iniciar_amarillo(siguiente_carril(self._activo))

    def solicitar_transicion(self, carril: int) -> bool:
        """HU-06 CA-02, CA-03: pasa el verde a `carril` (vía amarillo) solo si se cumplió el verde mínimo.

        Se rechaza durante el amarillo (regla 10) y si `carril` ya tiene el verde.
        """
        if carril == self._activo or not self.verde_min_cumplido:
            return False
        self._iniciar_amarillo(carril)
        return True

    def avanzar(self) -> None:
        """RN-11: avanza t_sim un paso; t_video solo avanza en los carriles en verde o amarillo."""
        for posicion, estado in self._estados.items():
            if estado is not EstadoSemaforo.ROJO:
                self.t_video[posicion] += PASO_SEG
        self.t_sim += PASO_SEG

    def _iniciar_amarillo(self, entrante: int) -> None:
        """RN-06: el saliente pasa a amarillo; el entrante recibe el verde al terminar."""
        self._entrante = entrante
        self._cambiar(self._activo, EstadoSemaforo.AMARILLO)

    def _cambiar(self, posicion: int, estado: EstadoSemaforo) -> None:
        self._estados[posicion] = estado
        self._inicio_estado[posicion] = self.t_sim
        self.cambios.append(CambioEstado(self.t_sim, posicion, estado, self.t_video[posicion]))
