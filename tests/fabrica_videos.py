"""Videos sintéticos pequeños para las pruebas (nunca videos de validación ni del dataset).

Se generan en una carpeta temporal en cada prueba para no versionar archivos binarios.
"""

from pathlib import Path

import cv2
import numpy as np

FPS_PRUEBA = 10.0
CUADROS_PRUEBA = 20
ANCHO_PRUEBA = 64
ALTO_PRUEBA = 36


def crear_mp4(ruta: Path, fps: float = FPS_PRUEBA, cuadros: int = CUADROS_PRUEBA,
              ancho: int = ANCHO_PRUEBA, alto: int = ALTO_PRUEBA) -> Path:
    """Escribe un mp4 válido de `cuadros` cuadros de color liso."""
    escritor = cv2.VideoWriter(str(ruta), cv2.VideoWriter_fourcc(*"mp4v"), fps, (ancho, alto))
    for n in range(cuadros):
        escritor.write(np.full((alto, ancho, 3), n * 10 % 256, dtype=np.uint8))
    escritor.release()
    return ruta


def crear_corrupto(ruta: Path) -> Path:
    """Escribe un archivo con la extensión pedida pero sin contenido de video."""
    ruta.write_bytes(b"esto no es un video" * 50)
    return ruta
