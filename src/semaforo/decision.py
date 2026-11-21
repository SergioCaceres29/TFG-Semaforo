"""Motor de reglas de prioridad sobre la demanda registrada (HU-05, RF-07, RN-04, RN-07, RN-08, RN-11).

Python puro: se ejecuta después del análisis sobre los conteos guardados, sin cv2, sin base y sin reloj.
Orden de evaluación: umbral (RN-04) → mayor demanda → tiempo en rojo (RN-07) → menor posición;
si nadie supera el umbral, ciclo fijo (RN-08).
"""

from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence

from semaforo.modelos import POSICIONES_CARRIL, RegistroConteo

SerieDemanda = tuple[tuple[float, int], ...]
"""Demanda de un carril por intervalo cerrado: (intervalo_fin en s del video, demanda), ordenada por fin."""


def agrupar_demanda(conteos: Iterable[RegistroConteo], posicion_por_zona: Mapping[int, int]) -> dict[int, SerieDemanda]:
    """CLAUDE.md §6: demanda de cada carril por intervalo = suma de las tres clases del cuadro de cierre."""
    sumas: dict[int, dict[float, int]] = {posicion: defaultdict(int) for posicion in POSICIONES_CARRIL}
    for conteo in conteos:
        sumas[posicion_por_zona[conteo.id_zona]][conteo.intervalo_fin] += conteo.cantidad
    return {posicion: tuple(sorted(por_fin.items())) for posicion, por_fin in sumas.items()}


def demanda_en_instante(serie: SerieDemanda, t_video: float) -> int:
    """RN-11 (regla 1a, 20/11/2026): demanda del último intervalo con fin ≤ t_video; 0 antes del primer cierre."""
    cerrados = bisect_right(serie, t_video, key=lambda intervalo: intervalo[0])
    return serie[cerrados - 1][1] if cerrados else 0


class MotorDecision:
    """RF-07: decide qué carril recibe la prioridad en cada evaluación."""

    def __init__(self, umbral_demanda: int) -> None:
        """Recibe el umbral de demanda de la ejecución (Parametros.umbral_demanda)."""
        self.umbral_demanda = umbral_demanda

    def seleccionar_carril_prioritario(self, demandas: Mapping[int, int],
                                       tiempos_rojo: Mapping[int, float]) -> int | None:
        """RN-04: el candidato (demanda > umbral) de mayor demanda; None si nadie supera el umbral (RN-08)."""
        candidatos = [posicion for posicion, demanda in demandas.items() if demanda > self.umbral_demanda]
        if not candidatos:
            return None
        mayor = max(demandas[posicion] for posicion in candidatos)
        return self.resolver_empate([p for p in candidatos if demandas[p] == mayor], tiempos_rojo)

    def resolver_empate(self, empatados: Sequence[int], tiempos_rojo: Mapping[int, float]) -> int:
        """RN-07: gana el de más tiempo acumulado en rojo; si también empatan, la menor posición (regla 7)."""
        return min(empatados, key=lambda posicion: (-tiempos_rojo[posicion], posicion))

    def aplicar_ciclo_por_defecto(self, carril_actual: int) -> int:
        """RN-08: siguiente carril del ciclo fijo por posición, 1 → 2 → 3 → 1."""
        return POSICIONES_CARRIL[carril_actual % len(POSICIONES_CARRIL)]
