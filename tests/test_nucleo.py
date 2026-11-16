"""Pruebas de nucleo.py: carga y validación de los tres videos (HU-01, RF-01)."""

import tempfile
import unittest
from pathlib import Path

from semaforo.modelos import ErrorConfiguracion, ErrorVideo, MetadatosVideo, Zona
from semaforo.nucleo import cargar_video, crear_gestor_zonas, validar_videos_carriles
from tests.fabrica_videos import CUADROS_PRUEBA, FPS_PRUEBA, crear_mp4


def metadatos(fps: float = 30.0, cuadros: int = 300) -> MetadatosVideo:
    return MetadatosVideo(Path("carril.mp4"), fps, cuadros, 1920, 1080)


class TestValidarVideosCarriles(unittest.TestCase):
    def test_cp01_ca05_exige_video_en_los_tres_carriles(self):
        """HU-01 CA-05 / RN-01: la ejecución no se habilita hasta tener los tres videos."""
        with self.assertRaisesRegex(ErrorVideo, "3"):
            validar_videos_carriles({1: metadatos(), 2: metadatos()})

    def test_cp01_ca06_rechaza_fps_distintos(self):
        """HU-01 CA-06: fps distintos entre carriles → ErrorVideo con mensaje."""
        with self.assertRaisesRegex(ErrorVideo, "fps"):
            validar_videos_carriles({1: metadatos(30.0), 2: metadatos(30.0), 3: metadatos(25.0)})

    def test_cp01_ca06_duracion_comun_es_la_del_mas_corto(self):
        """HU-01 CA-06: si la duración difiere, se procesa hasta el final del más corto."""
        duracion = validar_videos_carriles(
            {1: metadatos(cuadros=300), 2: metadatos(cuadros=240), 3: metadatos(cuadros=270)})
        self.assertAlmostEqual(duracion, 8.0)

    def test_cp01_ca06_tolera_redondeo_de_fps(self):
        """HU-01 CA-06: 29.97 informado con distinto redondeo cuenta como el mismo fps."""
        duracion = validar_videos_carriles(
            {1: metadatos(29.97), 2: metadatos(29.97003), 3: metadatos(29.9700299)})
        self.assertGreater(duracion, 0)


class TestCargarVideo(unittest.TestCase):
    def test_cp01_ca03_cargar_video_devuelve_metadatos_y_primer_cuadro(self):
        """HU-01 CA-03: al cargar se obtienen los metadatos y el primer cuadro a mostrar."""
        with tempfile.TemporaryDirectory() as carpeta:
            cargado = cargar_video(crear_mp4(Path(carpeta) / "carril1.mp4"))
        self.assertAlmostEqual(cargado.metadatos.duracion, CUADROS_PRUEBA / FPS_PRUEBA, places=2)
        self.assertEqual(cargado.primer_cuadro.ndim, 3)


class TestGestorZonas(unittest.TestCase):
    TRIANGULO = ((0, 0), (100, 0), (50, 80))

    def setUp(self):
        self.gestor = crear_gestor_zonas(":memory:")
        self.id_video = self.gestor.registrar_video(metadatos())

    def tearDown(self):
        self.gestor.cerrar()

    def test_cp02_ca02_rechaza_zona_invalida_sin_guardarla(self):
        """HU-02 CA-02: con nombre repetido entre carriles no se guarda nada."""
        with self.assertRaises(ErrorConfiguracion):
            self.gestor.guardar_zona(self.id_video, Zona("Norte", self.TRIANGULO), ["Norte"])
        self.assertIsNone(self.gestor.zona_guardada(self.id_video))

    def test_cp03_ca03_zona_guardada_se_recupera_al_registrar_de_nuevo_el_video(self):
        """HU-02 CA-03 / RF-03: la zona queda asociada al video y se reutiliza."""
        guardada = self.gestor.guardar_zona(self.id_video, Zona(" Norte ", self.TRIANGULO), [])
        self.assertEqual(guardada.nombre_carril, "Norte")
        id_video = self.gestor.registrar_video(metadatos())
        self.assertEqual(self.gestor.zona_guardada(id_video), guardada)


if __name__ == "__main__":
    unittest.main()
