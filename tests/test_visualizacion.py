"""Pruebas de visualizacion.py (RF-09)."""

import unittest

import numpy as np

from semaforo.visualizacion import Visualizador


class TestCodificarPpm(unittest.TestCase):
    def test_cuadro_se_escala_sin_deformar_y_se_codifica_en_ppm(self):
        """HU-01 CA-03: el primer cuadro 16:9 entra en el área disponible en formato PPM."""
        cuadro = np.zeros((1080, 1920, 3), dtype=np.uint8)
        ppm = Visualizador.codificar_ppm(cuadro, 400, 400)
        self.assertTrue(ppm.startswith(b"P6"))
        ancho, alto = (int(v) for v in ppm.split()[1:3])
        self.assertEqual((ancho, alto), (400, 225))


if __name__ == "__main__":
    unittest.main()
