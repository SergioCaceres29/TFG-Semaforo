"""Visualización (HU-07, RF-09): prepara los cuadros que muestra la interfaz.

La interfaz es tkinter sin Pillow: los cuadros se entregan como bytes PPM para
`tk.PhotoImage`. Las cajas, zonas y conteos dibujados se agregan con HU-07.
"""

from __future__ import annotations

import cv2
import numpy as np

from semaforo.modelos import ErrorVideo


class Visualizador:
    """RF-09: composición de los cuadros de cada carril."""

    @staticmethod
    def codificar_ppm(cuadro: np.ndarray, ancho_max: int, alto_max: int) -> bytes:
        """Escala el cuadro sin deformarlo para que entre en ancho_max × alto_max y lo pasa a PPM."""
        alto, ancho = cuadro.shape[:2]
        escala = min(ancho_max / ancho, alto_max / alto)
        tamano = (max(1, round(ancho * escala)), max(1, round(alto * escala)))
        reducido = cv2.resize(cuadro, tamano, interpolation=cv2.INTER_AREA)
        codificado, datos = cv2.imencode(".ppm", reducido)
        if not codificado:
            raise ErrorVideo("No se pudo preparar la imagen del cuadro.")
        return datos.tobytes()
