"""Pruebas de deteccion.py (HU-03, RF-04, RF-05, RN-02).

Las que necesitan `modelos/best.pt` se saltan si el archivo no existe. Como imagen con contenido se usa
`bus.jpg`, que viene con Ultralytics (nunca videos de validación ni el dataset, RN-10).
"""

import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from semaforo.deteccion import Detector
from semaforo.modelos import Clase, Deteccion, ErrorConfiguracion

RUTA_PESOS = Path(__file__).resolve().parent.parent / "modelos" / "best.pt"
UMBRAL = 0.5
CAJA = (10.0, 20.0, 110.0, 220.0)


def imagen_de_ultralytics() -> np.ndarray | None:
    """bus.jpg de los recursos de Ultralytics, o None si no está."""
    import ultralytics

    ruta = Path(ultralytics.__file__).parent / "assets" / "bus.jpg"
    return cv2.imread(str(ruta)) if ruta.is_file() else None


class TestFiltroDetecciones(unittest.TestCase):
    """Filtro de clase y confianza con salidas simuladas del modelo (sin best.pt)."""

    def setUp(self):
        self.detector = Detector(UMBRAL)

    def test_cp04_ca01_cada_caja_conserva_su_confianza(self):
        """HU-03 CA-01 / RF-04: cada detección lleva su caja y su nivel de confianza."""
        detecciones = self.detector.filtrar_por_clase([CAJA], [Clase.AUTO.value], [0.87])
        self.assertEqual(detecciones, [Deteccion(Clase.AUTO, 0.87, *CAJA)])

    def test_cp04_ca03_descarta_confianza_menor_al_umbral(self):
        """HU-03 CA-03 / RF-04: lo que tiene confianza menor al umbral no suma demanda."""
        detecciones = self.detector.filtrar_por_clase([CAJA, CAJA], [Clase.AUTO.value, Clase.MOTO.value],
                                                      [UMBRAL - 0.01, 0.9])
        self.assertEqual([d.clase for d in detecciones], [Clase.MOTO])

    def test_cp04_ca03_conserva_confianza_igual_al_umbral(self):
        """HU-03 CA-03: solo se descarta lo que es menor al umbral; igual al umbral se conserva."""
        detecciones = self.detector.filtrar_por_clase([CAJA], [Clase.CAMION.value], [UMBRAL])
        self.assertEqual(len(detecciones), 1)

    def test_cp05_ca02_descarta_clase_fuera_de_rn02(self):
        """HU-03 CA-02 / RF-05, RN-02: un índice que no es auto, moto ni camión se descarta."""
        indice_desconocido = max(c.value for c in Clase) + 1
        detecciones = self.detector.filtrar_por_clase([CAJA, CAJA], [indice_desconocido, Clase.CAMION.value],
                                                      [0.95, 0.95])
        self.assertEqual([d.clase for d in detecciones], [Clase.CAMION])

    def test_cp05_ca02_indice_del_modelo_se_traduce_a_clase(self):
        """RF-05, CLAUDE.md §6: índice 0 = auto, 1 = camión, 2 = moto."""
        detecciones = self.detector.filtrar_por_clase([CAJA] * 3, [0, 1, 2], [0.9] * 3)
        self.assertEqual([d.clase for d in detecciones], [Clase.AUTO, Clase.CAMION, Clase.MOTO])


class TestCargaModelo(unittest.TestCase):
    def test_cp04_modelo_inexistente_da_error_controlado(self):
        """RNF-05: pesos inexistentes → ErrorConfiguracion con mensaje, sin cerrar el programa."""
        with tempfile.TemporaryDirectory() as carpeta:
            with self.assertRaises(ErrorConfiguracion):
                Detector(UMBRAL).cargar_modelo(Path(carpeta) / "no_existe.pt")

    def test_cp04_detectar_sin_modelo_cargado_da_error_controlado(self):
        """RNF-05: detectar antes de cargar el modelo → ErrorConfiguracion."""
        with self.assertRaises(ErrorConfiguracion):
            Detector(UMBRAL).detectar([np.zeros((36, 64, 3), dtype=np.uint8)])


@unittest.skipUnless(RUTA_PESOS.is_file(), "Falta modelos/best.pt")
class TestDetectorConModelo(unittest.TestCase):
    """HU-03 con el modelo real (modelos/best.pt)."""

    @classmethod
    def setUpClass(cls):
        cls.detector = Detector(UMBRAL)
        cls.detector.cargar_modelo(RUTA_PESOS)

    def test_cp05_ca02_mapeo_del_modelo_coincide_con_clase(self):
        """HU-03 CA-02 / RN-02: el modelo cargado tiene exactamente las tres clases del enum Clase."""
        self.assertEqual(self.detector.nombres_modelo, {c.value: c.descripcion for c in Clase})

    def test_cp04_ca01_detectar_en_lote_devuelve_una_lista_por_cuadro(self):
        """HU-03 CA-01 / RF-04: lote de 3 cuadros (uno por carril) → 3 listas de detecciones ya filtradas."""
        imagen = imagen_de_ultralytics()
        if imagen is None:
            self.skipTest("Ultralytics sin bus.jpg")
        vacio = np.zeros((1080, 1920, 3), dtype=np.uint8)
        resultado = self.detector.detectar([imagen, vacio, imagen])
        self.assertEqual(len(resultado), 3)
        self.assertEqual(resultado[1], [], "un cuadro negro no debe tener vehículos")
        alto, ancho = imagen.shape[:2]
        for deteccion in resultado[0] + resultado[2]:
            self.assertIsInstance(deteccion.clase, Clase)
            self.assertGreaterEqual(deteccion.confianza, UMBRAL)
            self.assertLessEqual(deteccion.confianza, 1.0)
            self.assertTrue(0 <= deteccion.x1 < deteccion.x2 <= ancho)
            self.assertTrue(0 <= deteccion.y1 < deteccion.y2 <= alto)
        self.assertEqual(resultado[0], resultado[2], "el mismo cuadro da las mismas detecciones")


class TestMetasDelModelo(unittest.TestCase):
    """Criterios que se miden fuera de las pruebas automáticas."""

    @unittest.skip("Manual: se mide en Colab sobre el conjunto de prueba independiente")
    def test_cp17_ca04_map50_en_conjunto_de_prueba(self):
        """HU-03 CA-04 / RNF-01: mAP50 ≥ 80 % en el conjunto de prueba (3 clases).

        Procedimiento: en Colab, `YOLO("best.pt").val(data="data.yaml", split="test")` y anotar
        `metrics.box.map50` en el informe de pruebas (Etapa 4). Resultado obtenido: completar a mano.
        """

    @unittest.skip("Manual: se mide en la integración (Sprint 4) analizando los tres videos 1920×1080")
    def test_cp20_ram_analizando_tres_videos(self):
        """RNF-04: ≤ 8 GB de RAM durante el análisis de los tres videos.

        Procedimiento: ejecutar un análisis completo y registrar el pico de memoria del proceso
        (Administrador de tareas → Detalles → «Espacio de trabajo máximo»).
        """


if __name__ == "__main__":
    unittest.main()
