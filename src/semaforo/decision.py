"""Motor de reglas y generación de los planes (HU-05, HU-06, RF-07, RF-08, RN-04, RN-07, RN-08, RN-11).

Python puro: se ejecuta después del análisis sobre los conteos guardados, sin cv2, sin base y sin reloj.
Orden de evaluación: umbral (RN-04) → mayor demanda → tiempo en rojo (RN-07) → menor posición;
si nadie supera el umbral, ciclo fijo (RN-08). Reglas de la simulación en docs/specs/diseno.md §4.1.
"""

from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence

from semaforo.control_fases import CambioEstado, ControladorSemaforo
from semaforo.modelos import POSICIONES_CARRIL, EventoFase, Parametros, RegistroConteo, TipoPlan, siguiente_carril

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
    """RF-07, RF-08: decide la prioridad en cada evaluación y genera los planes RECOMENDADO y FIJO."""

    def __init__(self, parametros: Parametros) -> None:
        """Recibe los parámetros de la ejecución: umbral, intervalo de evaluación y tiempos de fase."""
        self.parametros = parametros
        self.umbral_demanda = parametros.umbral_demanda

    def generar_plan_recomendado(self, demanda: Mapping[int, SerieDemanda], duracion: int) -> list[EventoFase]:
        """HU-06 / RF-08: plan del motor de reglas sobre la demanda registrada, de `duracion` s de simulación."""
        return self._generar(TipoPlan.RECOMENDADO, demanda, duracion)

    def generar_plan_fijo(self, demanda: Mapping[int, SerieDemanda], duracion: int) -> list[EventoFase]:
        """RN-08, RF-17: ciclo fijo 1 → 2 → 3 con verde_max + amarillo, misma duración que el recomendado."""
        return self._generar(TipoPlan.FIJO, demanda, duracion)

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
        return siguiente_carril(carril_actual)

    def _generar(self, tipo_plan: TipoPlan, demanda: Mapping[int, SerieDemanda], duracion: int) -> list[EventoFase]:
        """HU-06 CA-05: simula de a 1 s hasta la duración; el FIJO solo aplica los vencimientos (RN-08)."""
        controlador = ControladorSemaforo(self.parametros)
        while controlador.t_sim < duracion:
            controlador.verificar_tiempos()
            if tipo_plan is TipoPlan.RECOMENDADO and self._toca_evaluar(controlador):
                self._evaluar(controlador, demanda)
            controlador.avanzar()
        return _armar_eventos(tipo_plan, controlador.cambios, demanda, duracion)

    def _toca_evaluar(self, controlador: ControladorSemaforo) -> bool:
        """Regla 2 (§4.1): se decide al cumplirse verde_min y en cada intervalo_seg de t_sim, nunca en amarillo."""
        if not controlador.verde_min_cumplido:
            return False
        recien_cumplido = controlador.tiempo_en_estado(controlador.carril_activo) == self.parametros.verde_min
        return recien_cumplido or controlador.t_sim % self.parametros.intervalo_seg == 0

    def _evaluar(self, controlador: ControladorSemaforo, demanda: Mapping[int, SerieDemanda]) -> None:
        """RN-04, RN-07, RN-11: con la demanda de cada carril en su t_video; sin candidatos sigue el ciclo (regla 9)."""
        demandas = {p: demanda_en_instante(demanda[p], controlador.t_video[p]) for p in POSICIONES_CARRIL}
        elegido = self.seleccionar_carril_prioritario(demandas, controlador.tiempos_rojo())
        if elegido is not None:
            controlador.solicitar_transicion(elegido)


def _armar_eventos(tipo_plan: TipoPlan, cambios: Sequence[CambioEstado], demanda: Mapping[int, SerieDemanda],
                   duracion: int) -> list[EventoFase]:
    """RF-12: cada cambio dura hasta el siguiente de su carril; el último se trunca en la duración (regla 11)."""
    fin_por_carril: dict[int, int] = {}
    eventos: list[EventoFase] = []
    for cambio in reversed(cambios):
        fin = fin_por_carril.get(cambio.posicion, duracion)
        eventos.append(EventoFase(tipo_plan, cambio.posicion, cambio.estado, cambio.marca_tiempo,
                                  fin - cambio.marca_tiempo, demanda_en_instante(demanda[cambio.posicion],
                                                                                 cambio.t_video)))
        fin_por_carril[cambio.posicion] = cambio.marca_tiempo
    return eventos[::-1]
