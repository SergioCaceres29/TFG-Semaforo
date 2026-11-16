"""Pruebas de persistencia.py: esquema y zonas virtuales (HU-02, RF-03, RNF-09)."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from semaforo.modelos import ErrorConfiguracion, MetadatosVideo, Zona
from semaforo.persistencia import RepositorioSQLite

TRIANGULO = ((0, 0), (100, 0), (50, 80))
CUADRADO = ((10, 10), (200, 10), (200, 200), (10, 200))


def metadatos(nombre: str) -> MetadatosVideo:
    return MetadatosVideo(Path("C:/videos") / nombre, 30.0, 300, 1920, 1080)


class TestRepositorioZonas(unittest.TestCase):
    def setUp(self):
        self.repo = RepositorioSQLite()

    def tearDown(self):
        self.repo.cerrar()

    def test_cp03_ca03_zona_se_guarda_asociada_al_video_y_se_reutiliza(self):
        """HU-02 CA-03 / RF-03: la zona persiste y se recupera al reabrir la base."""
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "db" / "semaforo.db"
            repo = RepositorioSQLite(ruta)
            id_video = repo.registrar_video(metadatos("carril1.mp4"))
            repo.guardar_zona(id_video, Zona("Norte", TRIANGULO))
            repo.cerrar()
            repo = RepositorioSQLite(ruta)
            id_otra_vez = repo.registrar_video(metadatos("carril1.mp4"))
            zona = repo.obtener_zona(id_otra_vez)
            repo.cerrar()
        self.assertEqual(id_otra_vez, id_video)
        self.assertEqual((zona.nombre_carril, zona.vertices), ("Norte", TRIANGULO))

    def test_cp03_mismo_archivo_en_otra_carpeta_es_el_mismo_video(self):
        """RF-03: el video se reconoce por nombre y resolución, no por la ruta completa."""
        primero = self.repo.registrar_video(metadatos("carril1.mp4"))
        otra_carpeta = MetadatosVideo(Path("D:/otra/carril1.mp4"), 30.0, 300, 1920, 1080)
        self.assertEqual(self.repo.registrar_video(otra_carpeta), primero)
        self.assertNotEqual(self.repo.registrar_video(metadatos("carril2.mp4")), primero)

    def test_cp03_ca02_una_sola_zona_por_video(self):
        """HU-02 CA-02: guardar otra zona en el mismo video reemplaza la anterior."""
        id_video = self.repo.registrar_video(metadatos("carril1.mp4"))
        id_zona = self.repo.guardar_zona(id_video, Zona("Norte", TRIANGULO))
        self.assertEqual(self.repo.guardar_zona(id_video, Zona("Sur", CUADRADO)), id_zona)
        self.assertEqual(self.repo.obtener_zona(id_video), Zona("Sur", CUADRADO, id_zona))

    def test_cp03_ca04_modificar_o_eliminar_una_zona_no_afecta_las_demas(self):
        """HU-02 CA-04: se edita o elimina una zona sin redefinir las otras."""
        ids = [self.repo.registrar_video(metadatos(f"carril{n}.mp4")) for n in (1, 2, 3)]
        for id_video, nombre in zip(ids, ("Norte", "Sur", "Este")):
            self.repo.guardar_zona(id_video, Zona(nombre, TRIANGULO))
        self.repo.guardar_zona(ids[0], Zona("Norte", CUADRADO))
        self.repo.eliminar_zona(ids[1])
        self.assertEqual(self.repo.obtener_zona(ids[0]).vertices, CUADRADO)
        self.assertIsNone(self.repo.obtener_zona(ids[1]))
        self.assertEqual(self.repo.obtener_zona(ids[2]).nombre_carril, "Este")

    def test_cp03_no_elimina_zona_con_conteos_registrados(self):
        """RN-09: una zona con conteos históricos no se borra; error controlado."""
        id_video = self.repo.registrar_video(metadatos("carril1.mp4"))
        id_zona = self.repo.guardar_zona(id_video, Zona("Norte", TRIANGULO))
        self.repo._conexion.execute(
            "INSERT INTO ejecucion (fecha_hora, version_modelo, umbral_demanda, umbral_confianza,"
            " intervalo_seg, verde_min, verde_max, amarillo, estado)"
            " VALUES ('2026-11-03', 'best.pt', 5, 0.5, 10, 10, 60, 3, 'Finalizada')")
        self.repo._conexion.execute(
            "INSERT INTO conteo (id_ejecucion, id_zona, id_clase, cantidad, intervalo_inicio,"
            " intervalo_fin) VALUES (1, ?, 1, 4, 0, 10)", (id_zona,))
        with self.assertRaisesRegex(ErrorConfiguracion, "conteos"):
            self.repo.eliminar_zona(id_video)
        self.assertIsNotNone(self.repo.obtener_zona(id_video))


class TestEsquema(unittest.TestCase):
    def test_cp25_conteo_es_de_solo_insercion(self):
        """RNF-09: los triggers bloquean UPDATE y DELETE sobre conteo."""
        repo = RepositorioSQLite()
        conexion = repo._conexion
        conexion.execute("INSERT INTO video (nombre_archivo, duracion_seg, fps, resolucion)"
                         " VALUES ('a.mp4', 10, 30, '1920x1080')")
        conexion.execute("INSERT INTO zona_virtual (id_video, nombre_carril, vertices)"
                         " VALUES (1, 'Norte', '[[0,0],[1,0],[0,1]]')")
        conexion.execute(
            "INSERT INTO ejecucion (fecha_hora, version_modelo, umbral_demanda, umbral_confianza,"
            " intervalo_seg, verde_min, verde_max, amarillo, estado)"
            " VALUES ('2026-11-03', 'best.pt', 5, 0.5, 10, 10, 60, 3, 'Finalizada')")
        conexion.execute("INSERT INTO conteo (id_ejecucion, id_zona, id_clase, cantidad,"
                         " intervalo_inicio, intervalo_fin) VALUES (1, 1, 1, 4, 0, 10)")
        for sentencia in ("UPDATE conteo SET cantidad = 9", "DELETE FROM conteo"):
            with self.assertRaisesRegex(sqlite3.IntegrityError, "RNF-09"):
                conexion.execute(sentencia)
        repo.cerrar()


if __name__ == "__main__":
    unittest.main()
