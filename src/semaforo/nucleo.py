"""Núcleo (CU-02): único módulo que coordina a los demás.

Por ahora cubre la carga y validación de los tres videos (HU-01). `GestorEjecucion`
y el bucle de cuadros se agregan en la integración (Sprint 4).
"""

from __future__ import annotations

import logging
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from semaforo.captura import LectorVideo
from semaforo.modelos import NUM_CARRILES, POSICIONES_CARRIL, ErrorVideo, MetadatosVideo
from semaforo.visualizacion import Visualizador

registro = logging.getLogger(__name__)

TOLERANCIA_FPS = 1e-3
"""Diferencia relativa de fps que se considera redondeo del contenedor (29.97 ≈ 29.97003)."""


@dataclass(frozen=True)
class VideoCargado:
    """HU-01 CA-03: video validado de un carril, listo para mostrar y trazar su zona."""

    metadatos: MetadatosVideo
    primer_cuadro: np.ndarray


def cargar_video(ruta: Path) -> VideoCargado:
    """HU-01 CA-02..CA-04: valida el mp4 y devuelve sus metadatos y su primer cuadro."""
    lector = LectorVideo()
    try:
        lector.abrir(ruta)
        cargado = VideoCargado(lector.obtener_metadatos(), lector.primer_cuadro)
    finally:
        lector.cerrar()
    metadatos = cargado.metadatos
    registro.info("Video cargado %s: %s, %.2f fps, %.1f s", ruta.name, metadatos.resolucion,
                  metadatos.fps, metadatos.duracion)
    return cargado


def vista_previa(cuadro: np.ndarray, ancho: int, alto: int) -> bytes:
    """HU-01 CA-03: cuadro en PPM ajustado al área de la tarjeta del carril."""
    return Visualizador.codificar_ppm(cuadro, ancho, alto)


def validar_videos_carriles(metadatos: Mapping[int, MetadatosVideo]) -> float:
    """HU-01 CA-05, CA-06: un video por carril con iguales fps.

    Devuelve la duración a procesar: la del video más corto.
    """
    faltantes = [str(p) for p in POSICIONES_CARRIL if p not in metadatos]
    if faltantes:
        raise ErrorVideo(f"Se necesitan los {NUM_CARRILES} videos; falta el de los carriles "
                         f"{', '.join(faltantes)}.")
    videos = [metadatos[p] for p in POSICIONES_CARRIL]
    referencia = videos[0].fps
    if not all(math.isclose(v.fps, referencia, rel_tol=TOLERANCIA_FPS) for v in videos):
        detalle = ", ".join(f"carril {p}: {v.fps:.2f}" for p, v in zip(POSICIONES_CARRIL, videos))
        raise ErrorVideo(f"Los videos de los tres carriles deben tener los mismos fps ({detalle}).")
    duracion = min(v.duracion for v in videos)
    if any(not math.isclose(v.duracion, duracion) for v in videos):
        registro.info("Duraciones distintas: se procesará hasta %.1f s (el video más corto).",
                      duracion)
    return duracion
