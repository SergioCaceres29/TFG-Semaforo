"""Captura (HU-01, RF-01): apertura, validación y lectura cuadro a cuadro de un mp4."""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from semaforo.modelos import ErrorVideo, MetadatosVideo

registro = logging.getLogger(__name__)

EXTENSION_ADMITIDA = ".mp4"


class LectorVideo:
    """Lee el video de un carril y entrega cada cuadro con su marca de tiempo n / fps."""

    def __init__(self) -> None:
        self._captura: cv2.VideoCapture | None = None
        self._metadatos: MetadatosVideo | None = None
        self._primer_cuadro: np.ndarray | None = None
        self._n_cuadro = 0

    def abrir(self, ruta: Path) -> bool:
        """RF-01, RN-01, RNF-05: abre el mp4; si no sirve lanza ErrorVideo con el motivo."""
        self.cerrar()
        _validar_ruta(ruta)
        captura = cv2.VideoCapture(str(ruta))
        leido, cuadro = captura.read() if captura.isOpened() else (False, None)
        fps = captura.get(cv2.CAP_PROP_FPS)
        if not leido or fps <= 0:
            captura.release()
            raise ErrorVideo(f"No se pudo abrir «{ruta.name}»: el archivo está dañado "
                             "o no contiene un video válido.")
        captura.set(cv2.CAP_PROP_POS_FRAMES, 0)
        alto, ancho = cuadro.shape[:2]
        total_cuadros = int(captura.get(cv2.CAP_PROP_FRAME_COUNT))
        self._captura = captura
        self._primer_cuadro = cuadro
        self._metadatos = MetadatosVideo(ruta, fps, total_cuadros, ancho, alto)
        self._n_cuadro = 0
        return True

    @property
    def primer_cuadro(self) -> np.ndarray:
        """HU-01 CA-03: cuadro sobre el que se muestra la vista previa y se traza la zona."""
        self._verificar_abierto()
        return self._primer_cuadro

    def obtener_metadatos(self) -> MetadatosVideo:
        """HU-01 CA-03: duración, fps y resolución del video abierto."""
        self._verificar_abierto()
        return self._metadatos

    def leer_cuadro(self) -> tuple[np.ndarray, float] | None:
        """Siguiente cuadro y su marca de tiempo en segundos del video; None al terminar."""
        self._verificar_abierto()
        leido, cuadro = self._captura.read()
        if not leido:
            return None
        marca_tiempo = self._n_cuadro / self._metadatos.fps
        self._n_cuadro += 1
        return cuadro, marca_tiempo

    def cerrar(self) -> None:
        """Libera el archivo de video (se puede llamar aunque no haya uno abierto)."""
        if self._captura is not None:
            self._captura.release()
        self._captura = None
        self._metadatos = None
        self._primer_cuadro = None

    def _verificar_abierto(self) -> None:
        if self._captura is None:
            raise ErrorVideo("No hay un video abierto.")


def _validar_ruta(ruta: Path) -> None:
    """RN-01, RNF-05: solo archivos mp4 existentes."""
    if ruta.suffix.lower() != EXTENSION_ADMITIDA:
        raise ErrorVideo(f"«{ruta.name}» no es un archivo mp4; solo se admiten videos mp4 (RN-01).")
    if not ruta.is_file():
        raise ErrorVideo(f"El archivo «{ruta}» no existe.")
