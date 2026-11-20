"""Conteo de demanda por zona virtual sin tracking (HU-04, RF-06, RN-03).

El conteo de un intervalo es la ocupación de cada zona en su cuadro de cierre: el primer cuadro con
t ≥ fin del intervalo (t = n / fps, segundos del video). Así un vehículo cuenta una sola vez por intervalo.
El último intervalo, si queda incompleto, no se registra. No accede a la base: el núcleo guarda lo que devuelve.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import cv2
import numpy as np

from semaforo.modelos import Clase, Deteccion, ErrorConfiguracion, RegistroConteo, Zona

Ocupacion = dict[Clase, int]


def ocupacion_vacia() -> Ocupacion:
    """Ocupación con las tres clases en 0 (RN-02)."""
    return {clase: 0 for clase in Clase}


class ContadorZonas:
    """RF-06: ocupación de la zona de cada carril, consolidada al cierre de cada intervalo."""

    def __init__(self, zonas: Mapping[int, Zona], intervalo_seg: int) -> None:
        """Recibe la zona guardada de cada carril (posición → Zona con id_zona) y el intervalo en segundos."""
        sin_guardar = [zona.nombre_carril for zona in zonas.values() if zona.id_zona is None]
        if sin_guardar:
            raise ErrorConfiguracion(f"Hay que guardar la zona antes de contar: {', '.join(sin_guardar)}.")
        self._zonas = dict(sorted(zonas.items()))
        self._intervalo_seg = intervalo_seg
        self._indice_intervalo = 0
        self._ocupacion = {posicion: ocupacion_vacia() for posicion in self._zonas}

    @staticmethod
    def evaluar_pertenencia(deteccion: Deteccion, zona: Zona) -> bool:
        """RF-06: el centro inferior de la caja está dentro de la zona o sobre su borde."""
        contorno = np.array(zona.vertices, dtype=np.int32).reshape(-1, 1, 2)
        punto = ((deteccion.x1 + deteccion.x2) / 2, deteccion.y2)
        return cv2.pointPolygonTest(contorno, punto, False) >= 0

    def acumular_por_intervalo(self, t: float,
                               detecciones_por_carril: Mapping[int, Sequence[Deteccion]]) -> list[RegistroConteo]:
        """HU-04 CA-01..CA-03: actualiza la ocupación del cuadro y, si t cierra el intervalo, la consolida.

        Las detecciones de cada carril se evalúan solo contra su zona. Devuelve un registro por zona y clase
        al cierre, o una lista vacía si el intervalo sigue abierto.
        """
        self._ocupacion = {posicion: self._ocupacion_de(detecciones_por_carril.get(posicion, ()), zona)
                           for posicion, zona in self._zonas.items()}
        inicio = float(self._indice_intervalo * self._intervalo_seg)
        fin = inicio + self._intervalo_seg
        if t < fin:
            return []
        self._indice_intervalo += 1
        return [RegistroConteo(zona.id_zona, clase, self._ocupacion[posicion][clase], inicio, fin)
                for posicion, zona in self._zonas.items() for clase in Clase]

    def obtener_demanda_por_carril(self) -> dict[int, Ocupacion]:
        """RF-06, RF-09: ocupación del último cuadro procesado, por carril y clase."""
        return {posicion: dict(ocupacion) for posicion, ocupacion in self._ocupacion.items()}

    def _ocupacion_de(self, detecciones: Sequence[Deteccion], zona: Zona) -> Ocupacion:
        """Vehículos de cada clase dentro de la zona en un cuadro."""
        ocupacion = ocupacion_vacia()
        for deteccion in detecciones:
            if self.evaluar_pertenencia(deteccion, zona):
                ocupacion[deteccion.clase] += 1
        return ocupacion
