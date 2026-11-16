"""Pruebas de persistencia.py: zonas (HU-02, RF-03), ejecuciones y conteos (HU-08, RF-11, RNF-09)."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from semaforo.modelos import (
    Clase,
    ErrorConfiguracion,
    EstadoEjecucion,
    MetadatosVideo,
    Parametros,
    RegistroConteo,
    Zona,
)
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


PARAMETROS = Parametros(umbral_demanda=5, umbral_confianza=0.5, intervalo_seg=10,
                        verde_min=10, verde_max=28, amarillo=3)
VERSION_MODELO = "best.pt"


def preparar_carriles(repo: RepositorioSQLite) -> tuple[dict[int, int], dict[int, int]]:
    """Tres videos con su zona: devuelve {posición: id_video} y {posición: id_zona}."""
    videos, zonas = {}, {}
    for posicion, nombre in zip((1, 2, 3), ("Ruta 14", "Sagrado Corazón", "Carril 3")):
        videos[posicion] = repo.registrar_video(metadatos(f"carril{posicion}.mp4"))
        zonas[posicion] = repo.guardar_zona(videos[posicion], Zona(nombre, TRIANGULO))
    return videos, zonas


class TestRegistroConteos(unittest.TestCase):
    """HU-08 con conteos simulados (todavía no hay detector)."""

    def setUp(self):
        self.repo = RepositorioSQLite()
        self.videos, self.zonas = preparar_carriles(self.repo)

    def tearDown(self):
        self.repo.cerrar()

    def nueva_ejecucion(self) -> int:
        return self.repo.insertar_ejecucion(PARAMETROS, self.videos, VERSION_MODELO)

    def test_cp11_ca01_un_registro_por_zona_y_clase_con_marca_de_tiempo(self):
        """HU-08 CA-01 / RF-11: al cierre de un intervalo se guarda una fila por clase."""
        id_ejecucion = self.nueva_ejecucion()
        self.repo.insertar_conteo(id_ejecucion, self.zonas[1], {Clase.AUTO: 4, Clase.MOTO: 2},
                                  0.0, 10.0)
        registros = self.repo.consultar_conteos(id_ejecucion)
        self.assertEqual(registros, [
            RegistroConteo(self.zonas[1], Clase.AUTO, 4, 0.0, 10.0),
            RegistroConteo(self.zonas[1], Clase.MOTO, 2, 0.0, 10.0),
            RegistroConteo(self.zonas[1], Clase.CAMION, 0, 0.0, 10.0),
        ])

    def test_cp11_ca02_registros_asociados_a_la_ejecucion_y_a_la_zona(self):
        """HU-08 CA-02 / RN-09: cada registro lleva el id de su ejecución y de su zona."""
        primera, segunda = self.nueva_ejecucion(), self.nueva_ejecucion()
        self.repo.insertar_conteo(primera, self.zonas[1], {Clase.AUTO: 1}, 0.0, 10.0)
        self.repo.insertar_conteo(segunda, self.zonas[3], {Clase.CAMION: 2}, 0.0, 10.0)
        self.assertEqual({r.id_zona for r in self.repo.consultar_conteos(primera)},
                         {self.zonas[1]})
        self.assertEqual({r.id_zona for r in self.repo.consultar_conteos(segunda)},
                         {self.zonas[3]})

    def test_cp25_ca03_nueva_ejecucion_crea_registros_independientes(self):
        """HU-08 CA-03 / RNF-09: repetir los mismos videos no sobrescribe lo anterior."""
        primera = self.nueva_ejecucion()
        self.repo.insertar_conteo(primera, self.zonas[1], {Clase.AUTO: 3}, 0.0, 10.0)
        segunda = self.nueva_ejecucion()
        self.repo.insertar_conteo(segunda, self.zonas[1], {Clase.AUTO: 7}, 0.0, 10.0)
        self.assertNotEqual(primera, segunda)
        self.assertEqual(self.repo.consultar_conteos(primera)[0].cantidad, 3)
        self.assertEqual(self.repo.consultar_conteos(segunda)[0].cantidad, 7)

    def test_cp11_ca04_interrupcion_conserva_lo_ya_guardado(self):
        """HU-08 CA-04: si el proceso se corta, los intervalos confirmados siguen en la base."""
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "semaforo.db"
            repo = RepositorioSQLite(ruta)
            videos, zonas = preparar_carriles(repo)
            id_ejecucion = repo.insertar_ejecucion(PARAMETROS, videos, VERSION_MODELO)
            for inicio in (0.0, 10.0):
                repo.insertar_conteo(id_ejecucion, zonas[1], {Clase.AUTO: 1}, inicio, inicio + 10)
            with self.assertRaises(sqlite3.IntegrityError):  # falla a mitad del 3.er intervalo
                repo.insertar_conteo(id_ejecucion, zonas[1], {Clase.AUTO: 1, Clase.MOTO: -1},
                                     20.0, 30.0)
            repo.actualizar_estado_ejecucion(id_ejecucion, EstadoEjecucion.ABORTADA)
            repo._conexion.close()  # cierre abrupto, sin pasar por cerrar()
            repo = RepositorioSQLite(ruta)
            registros = repo.consultar_conteos(id_ejecucion)
            estado = repo.estado_ejecucion(id_ejecucion)
            repo.cerrar()
        self.assertEqual(len(registros), 6)  # 2 intervalos × 3 clases; el 3.º no quedó a medias
        self.assertEqual({r.intervalo_fin for r in registros}, {10.0, 20.0})
        self.assertIs(estado, EstadoEjecucion.ABORTADA)

    def test_cp13_ejecucion_guarda_parametros_y_los_tres_videos(self):
        """RF-13 / RN-09: la ejecución nace Creada con sus parámetros y un video por posición."""
        id_ejecucion = self.nueva_ejecucion()
        self.assertIs(self.repo.estado_ejecucion(id_ejecucion), EstadoEjecucion.CREADA)
        fila = self.repo._conexion.execute(
            "SELECT version_modelo, umbral_demanda, umbral_confianza, intervalo_seg, verde_min,"
            " verde_max, amarillo FROM ejecucion WHERE id_ejecucion = ?", (id_ejecucion,)).fetchone()
        self.assertEqual(fila, (VERSION_MODELO, 5, 0.5, 10, 10, 28, 3))
        posiciones = self.repo._conexion.execute(
            "SELECT posicion, id_video FROM ejecucion_video WHERE id_ejecucion = ?"
            " ORDER BY posicion", (id_ejecucion,)).fetchall()
        self.assertEqual(dict(posiciones), self.videos)

    def test_ejecucion_requiere_los_tres_videos(self):
        """RN-01: una ejecución procesa siempre los tres carriles."""
        with self.assertRaises(ErrorConfiguracion):
            self.repo.insertar_ejecucion(PARAMETROS, {1: self.videos[1]}, VERSION_MODELO)

    def test_estados_de_la_ejecucion_sin_pausada(self):
        """Figura 10: la ejecución pasa a EnEjecucion y Finalizada; la base rechaza 'Pausada'."""
        id_ejecucion = self.nueva_ejecucion()
        for estado in (EstadoEjecucion.EN_EJECUCION, EstadoEjecucion.FINALIZADA):
            self.repo.actualizar_estado_ejecucion(id_ejecucion, estado)
            self.assertIs(self.repo.estado_ejecucion(id_ejecucion), estado)
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo._conexion.execute(
                "UPDATE ejecucion SET estado = 'Pausada' WHERE id_ejecucion = ?", (id_ejecucion,))

    def test_zona_con_conteos_no_se_puede_eliminar(self):
        """HU-02 CA-04 + RN-09: una zona con conteos registrados se conserva."""
        id_ejecucion = self.nueva_ejecucion()
        self.repo.insertar_conteo(id_ejecucion, self.zonas[2], {Clase.AUTO: 1}, 0.0, 10.0)
        with self.assertRaises(ErrorConfiguracion):
            self.repo.eliminar_zona(self.videos[2])


if __name__ == "__main__":
    unittest.main()
