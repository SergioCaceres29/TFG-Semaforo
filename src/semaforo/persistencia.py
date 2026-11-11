"""Persistencia (HU-08, RF-03, RF-11..14): único módulo con acceso a SQLite.

Cubre videos y zonas virtuales (HU-02), ejecuciones y conteos (HU-08). `conteo` y
`evento_fase` son de solo inserción (RNF-09); los triggers del esquema lo garantizan.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Mapping
from dataclasses import astuple
from datetime import datetime
from pathlib import Path

from semaforo.modelos import (
    POSICIONES_CARRIL,
    Clase,
    ErrorConfiguracion,
    EstadoEjecucion,
    MetadatosVideo,
    Parametros,
    RegistroConteo,
    Zona,
)

registro = logging.getLogger(__name__)

RUTA_ESQUEMA = Path(__file__).with_name("esquema.sql")
BASE_EN_MEMORIA = ":memory:"


class RepositorioSQLite:
    """Abre la base, aplica el esquema y resuelve las consultas de los demás módulos."""

    def __init__(self, ruta: Path | str = BASE_EN_MEMORIA) -> None:
        if str(ruta) != BASE_EN_MEMORIA:
            Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        self._conexion = sqlite3.connect(str(ruta))
        self._conexion.execute("PRAGMA foreign_keys = ON")
        self._conexion.executescript(RUTA_ESQUEMA.read_text(encoding="utf-8"))

    def registrar_video(self, metadatos: MetadatosVideo) -> int:
        """RF-03: id del video; se reconoce por nombre de archivo y resolución, no por la ruta."""
        fila = self._conexion.execute(
            "SELECT id_video FROM video WHERE nombre_archivo = ? AND resolucion = ?",
            (metadatos.ruta.name, metadatos.resolucion)).fetchone()
        if fila is not None:
            return fila[0]
        with self._conexion:
            cursor = self._conexion.execute(
                "INSERT INTO video (nombre_archivo, duracion_seg, fps, resolucion) VALUES (?, ?, ?, ?)",
                (metadatos.ruta.name, metadatos.duracion, metadatos.fps, metadatos.resolucion))
        return cursor.lastrowid

    def guardar_zona(self, id_video: int, zona: Zona) -> int:
        """HU-02 CA-02, CA-03: una sola zona por video; si ya existe se actualiza."""
        vertices = json.dumps([list(v) for v in zona.vertices])
        existente = self._id_zona(id_video)
        with self._conexion:
            if existente is None:
                cursor = self._conexion.execute(
                    "INSERT INTO zona_virtual (id_video, nombre_carril, vertices) VALUES (?, ?, ?)",
                    (id_video, zona.nombre_carril, vertices))
                return cursor.lastrowid
            self._conexion.execute(
                "UPDATE zona_virtual SET nombre_carril = ?, vertices = ? WHERE id_zona = ?",
                (zona.nombre_carril, vertices, existente))
        return existente

    def obtener_zona(self, id_video: int) -> Zona | None:
        """RF-03: zona guardada del video, o None si todavía no tiene."""
        fila = self._conexion.execute(
            "SELECT id_zona, nombre_carril, vertices FROM zona_virtual WHERE id_video = ?",
            (id_video,)).fetchone()
        if fila is None:
            return None
        id_zona, nombre, vertices = fila
        return Zona(nombre, tuple((x, y) for x, y in json.loads(vertices)), id_zona)

    def eliminar_zona(self, id_video: int) -> None:
        """HU-02 CA-04: borra la zona del video; si tiene conteos registrados no se borra (RN-09)."""
        try:
            with self._conexion:
                self._conexion.execute("DELETE FROM zona_virtual WHERE id_video = ?", (id_video,))
        except sqlite3.IntegrityError as error:
            raise ErrorConfiguracion("La zona tiene conteos registrados y no se puede eliminar; "
                                     "podés modificar sus vértices.") from error

    def insertar_ejecucion(self, parametros: Parametros, videos: Mapping[int, int],
                           version_modelo: str) -> int:
        """RF-13, RN-09: crea la ejecución (estado Creada) con sus parámetros y sus 3 videos.

        `videos` asocia cada posición de carril (1, 2, 3) con el id del video.
        """
        if set(videos) != set(POSICIONES_CARRIL):
            raise ErrorConfiguracion("Una ejecución necesita un video en cada uno de los tres "
                                     "carriles.")
        fecha_hora = datetime.now().isoformat(timespec="seconds")  # solo registro, no lógica
        with self._conexion:
            cursor = self._conexion.execute(
                "INSERT INTO ejecucion (fecha_hora, version_modelo, umbral_demanda,"
                " umbral_confianza, intervalo_seg, verde_min, verde_max, amarillo, estado)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (fecha_hora, version_modelo, *astuple(parametros), EstadoEjecucion.CREADA.value))
            id_ejecucion = cursor.lastrowid
            self._conexion.executemany(
                "INSERT INTO ejecucion_video (id_ejecucion, id_video, posicion) VALUES (?, ?, ?)",
                [(id_ejecucion, videos[p], p) for p in POSICIONES_CARRIL])
        registro.info("Ejecución %d creada", id_ejecucion)
        return id_ejecucion

    def actualizar_estado_ejecucion(self, id_ejecucion: int, estado: EstadoEjecucion) -> None:
        """Figura 10: cambia el estado de la ejecución (la única tabla de resultados que se actualiza)."""
        with self._conexion:
            self._conexion.execute("UPDATE ejecucion SET estado = ? WHERE id_ejecucion = ?",
                                   (estado.value, id_ejecucion))

    def estado_ejecucion(self, id_ejecucion: int) -> EstadoEjecucion:
        """Figura 10: estado guardado de la ejecución."""
        fila = self._conexion.execute("SELECT estado FROM ejecucion WHERE id_ejecucion = ?",
                                      (id_ejecucion,)).fetchone()
        return EstadoEjecucion(fila[0])

    def insertar_conteo(self, id_ejecucion: int, id_zona: int, conteo: Mapping[Clase, int],
                        intervalo_inicio: float, intervalo_fin: float) -> None:
        """HU-08 CA-01, CA-04 / RF-11: una fila por clase al cierre del intervalo.

        Las clases ausentes se guardan con 0. Las tres filas se confirman juntas: ante
        un corte, el intervalo queda completo o no queda.
        """
        filas = [(id_ejecucion, id_zona, clase.descripcion, conteo.get(clase, 0),
                  intervalo_inicio, intervalo_fin) for clase in Clase]
        with self._conexion:
            self._conexion.executemany(
                "INSERT INTO conteo (id_ejecucion, id_zona, id_clase, cantidad, intervalo_inicio,"
                " intervalo_fin) VALUES (?, ?,"
                " (SELECT id_clase FROM clase_vehiculo WHERE descripcion = ?), ?, ?, ?)",
                filas)

    def consultar_conteos(self, id_ejecucion: int) -> list[RegistroConteo]:
        """RF-11, CU-03: conteos de una ejecución, ordenados por intervalo, zona y clase."""
        filas = self._conexion.execute(
            "SELECT c.id_zona, cv.descripcion, c.cantidad, c.intervalo_inicio, c.intervalo_fin"
            " FROM conteo c JOIN clase_vehiculo cv ON cv.id_clase = c.id_clase"
            " WHERE c.id_ejecucion = ?"
            " ORDER BY c.intervalo_inicio, c.id_zona, c.id_clase", (id_ejecucion,)).fetchall()
        return [RegistroConteo(id_zona, Clase[descripcion.upper()], cantidad, inicio, fin)
                for id_zona, descripcion, cantidad, inicio, fin in filas]

    def cerrar(self) -> None:
        """Cierra la conexión con la base."""
        self._conexion.close()

    def _id_zona(self, id_video: int) -> int | None:
        fila = self._conexion.execute("SELECT id_zona FROM zona_virtual WHERE id_video = ?",
                                      (id_video,)).fetchone()
        return None if fila is None else fila[0]
