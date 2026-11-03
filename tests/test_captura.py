"""Pruebas de captura.py (HU-01, RF-01, RNF-05)."""

import tempfile
import unittest
from pathlib import Path

from semaforo.captura import LectorVideo
from semaforo.modelos import ErrorVideo
from tests.fabrica_videos import (
    ALTO_PRUEBA,
    ANCHO_PRUEBA,
    CUADROS_PRUEBA,
    FPS_PRUEBA,
    crear_corrupto,
    crear_mp4,
)


class TestLectorVideo(unittest.TestCase):
    def setUp(self):
        self._temporal = tempfile.TemporaryDirectory()
        self.carpeta = Path(self._temporal.name)
        self.lector = LectorVideo()

    def tearDown(self):
        self.lector.cerrar()
        self._temporal.cleanup()

    def test_cp01_ca03_video_valido_entrega_primer_cuadro_y_metadatos(self):
        """HU-01 CA-03 / RF-01: duración, fps y resolución del video, y su primer cuadro."""
        ruta = crear_mp4(self.carpeta / "carril1.mp4")
        self.assertTrue(self.lector.abrir(ruta))
        metadatos = self.lector.obtener_metadatos()
        self.assertEqual(metadatos.ruta, ruta)
        self.assertAlmostEqual(metadatos.fps, FPS_PRUEBA, places=2)
        self.assertEqual(metadatos.resolucion, f"{ANCHO_PRUEBA}x{ALTO_PRUEBA}")
        self.assertAlmostEqual(metadatos.duracion, CUADROS_PRUEBA / FPS_PRUEBA, places=2)
        self.assertEqual(self.lector.primer_cuadro.shape, (ALTO_PRUEBA, ANCHO_PRUEBA, 3))

    def test_cp01_leer_cuadro_marca_tiempo_en_segundos_del_video(self):
        """RF-01 / CLAUDE.md §1: el cuadro n tiene marca n / fps; None al terminar."""
        self.lector.abrir(crear_mp4(self.carpeta / "carril1.mp4"))
        marcas = []
        while (lectura := self.lector.leer_cuadro()) is not None:
            marcas.append(lectura[1])
        self.assertEqual(len(marcas), CUADROS_PRUEBA)
        self.assertEqual(marcas[0], 0.0)
        self.assertAlmostEqual(marcas[-1], (CUADROS_PRUEBA - 1) / FPS_PRUEBA)

    def test_cp21_ca02_rechaza_extension_no_mp4(self):
        """HU-01 CA-02 / RN-01, RNF-05: otra extensión → ErrorVideo con mensaje."""
        ruta = crear_mp4(self.carpeta / "carril1.avi")
        with self.assertRaisesRegex(ErrorVideo, "mp4"):
            self.lector.abrir(ruta)

    def test_cp21_rechaza_archivo_inexistente(self):
        """RNF-05: archivo inexistente → ErrorVideo con mensaje."""
        with self.assertRaisesRegex(ErrorVideo, "no existe"):
            self.lector.abrir(self.carpeta / "no_esta.mp4")

    def test_cp21_ca04_mp4_corrupto_informa_error_controlado(self):
        """HU-01 CA-04 / RNF-05: mp4 que no abre → ErrorVideo; el lector sigue usable."""
        with self.assertRaisesRegex(ErrorVideo, "dañado"):
            self.lector.abrir(crear_corrupto(self.carpeta / "roto.mp4"))
        self.assertTrue(self.lector.abrir(crear_mp4(self.carpeta / "carril1.mp4")))


if __name__ == "__main__":
    unittest.main()
