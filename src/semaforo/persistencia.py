"""Persistencia (HU-08, RF-03, RF-11..14): único módulo con acceso a SQLite.

Por ahora cubre videos y zonas virtuales (HU-02). `conteo` y `evento_fase` son de
solo inserción (RNF-09); los triggers del esquema lo garantizan.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

from semaforo.modelos import ErrorConfiguracion, MetadatosVideo, Zona

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

    def cerrar(self) -> None:
        """Cierra la conexión con la base."""
        self._conexion.close()

    def _id_zona(self, id_video: int) -> int | None:
        fila = self._conexion.execute("SELECT id_zona FROM zona_virtual WHERE id_video = ?",
                                      (id_video,)).fetchone()
        return None if fila is None else fila[0]
