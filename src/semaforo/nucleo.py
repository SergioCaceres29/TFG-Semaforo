"""Núcleo (CU-02): único módulo que coordina a los demás.

Por ahora cubre la carga y validación de los tres videos (HU-01), la definición y
persistencia de sus zonas (HU-02) y la configuración de parámetros (RF-10). `GestorEjecucion` y el bucle de cuadros se
agregan en la integración (Sprint 4).
"""

from __future__ import annotations

import logging
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from semaforo.captura import LectorVideo
from semaforo import configuracion
from semaforo.configuracion import leer_parametros, validar_zona
from semaforo.modelos import (
    NUM_CARRILES,
    POSICIONES_CARRIL,
    ErrorVideo,
    MetadatosVideo,
    Parametros,
    Zona,
)
from semaforo.persistencia import RepositorioSQLite
from semaforo.visualizacion import Visualizador

registro = logging.getLogger(__name__)

RUTA_BASE_DATOS = Path("datos") / "db" / "semaforo.db"

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


ETIQUETAS_PARAMETROS = configuracion.ETIQUETAS_PARAMETROS
"""RF-10: etiquetas del formulario (la interfaz no importa configuracion.py)."""
PARAMETROS_INICIALES = configuracion.PARAMETROS_INICIALES
"""RF-10: valores con los que arranca el formulario."""


def configurar_parametros(textos: Mapping[str, str]) -> Parametros:
    """RF-10: valida los parámetros del formulario antes de ejecutar (ErrorConfiguracion si no)."""
    parametros = leer_parametros(textos)
    registro.info("Parámetros configurados: %s", parametros)
    return parametros


class GestorZonas:
    """HU-02 (RF-02, RF-03): valida las zonas del operador y las guarda por video."""

    def __init__(self, repositorio: RepositorioSQLite) -> None:
        self._repositorio = repositorio

    def registrar_video(self, metadatos: MetadatosVideo) -> int:
        """RF-03: id del video en la base (lo da de alta la primera vez)."""
        return self._repositorio.registrar_video(metadatos)

    def zona_guardada(self, id_video: int) -> Zona | None:
        """RF-03: zona definida antes para el video, para reutilizarla sin redefinirla."""
        return self._repositorio.obtener_zona(id_video)

    def guardar_zona(self, id_video: int, zona: Zona, nombres_otros_carriles: Iterable[str]) -> Zona:
        """HU-02 CA-02, CA-03: valida la zona y la guarda asociada al video."""
        valida = validar_zona(zona, nombres_otros_carriles)
        id_zona = self._repositorio.guardar_zona(id_video, valida)
        registro.info("Zona «%s» guardada (video %d, %d vértices)", valida.nombre_carril, id_video,
                      len(valida.vertices))
        return replace(valida, id_zona=id_zona)

    def eliminar_zona(self, id_video: int) -> None:
        """HU-02 CA-04: elimina la zona del video sin tocar las demás."""
        self._repositorio.eliminar_zona(id_video)
        registro.info("Zona del video %d eliminada", id_video)

    def cerrar(self) -> None:
        """Cierra la base de datos."""
        self._repositorio.cerrar()


def crear_gestor_zonas(ruta: Path | str = RUTA_BASE_DATOS) -> GestorZonas:
    """Gestor de zonas sobre la base indicada (las pruebas usan ":memory:")."""
    return GestorZonas(RepositorioSQLite(ruta))
