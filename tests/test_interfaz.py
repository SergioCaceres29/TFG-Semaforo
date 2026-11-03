"""Pruebas de la interfaz del operador.

Las de presentación y demostración no abren ventana. Las de HU-01 crean la ventana
oculta (se saltan si no hay entorno gráfico) y cargan mp4 sintéticos.
"""

import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest import mock

from semaforo.interfaz import (
    LUZ_APAGADA,
    LUZ_ENCENDIDA,
    InterfazPrincipal,
    SimuladorDemostracion,
    color_luz,
    formatear_tiempo,
    rectangulo_video,
)
from semaforo.modelos import (
    POSICIONES_CARRIL,
    CambioFase,
    EstadoEjecucion,
    EstadoSemaforo,
    ProgresoEjecucion,
)
from tests.fabrica_videos import CUADROS_PRUEBA, FPS_PRUEBA, crear_corrupto, crear_mp4


def recorrer_demostracion(duracion: float) -> list:
    simulador = SimuladorDemostracion(duracion=duracion)
    mensajes = []
    while not simulador.terminado:
        mensajes.extend(simulador.avanzar())
    return mensajes


class TestPresentacion(unittest.TestCase):
    def test_solo_la_luz_del_estado_vigente_esta_encendida(self):
        """RF-09: el semáforo muestra un único estado."""
        for luz in EstadoSemaforo:
            esperado = LUZ_ENCENDIDA[luz] if luz is EstadoSemaforo.AMARILLO else LUZ_APAGADA[luz]
            self.assertEqual(color_luz(luz, EstadoSemaforo.AMARILLO), esperado)

    def test_formatea_segundos_del_video(self):
        self.assertEqual(formatear_tiempo(0), "00:00")
        self.assertEqual(formatear_tiempo(151.7), "02:31")

    def test_video_conserva_relacion_16_9_centrado(self):
        self.assertEqual(rectangulo_video(400, 400), (0, 87, 400, 312))
        self.assertEqual(rectangulo_video(1000, 180), (340, 0, 660, 180))


class TestSimuladorDemostracion(unittest.TestCase):
    def test_nunca_hay_dos_carriles_en_verde(self):
        """La demostración no debe contradecir RN-06 aunque no sea el motor real."""
        for mensaje in recorrer_demostracion(120):
            if isinstance(mensaje, CambioFase):
                verdes = [p for p, e in mensaje.estados.items() if e is EstadoSemaforo.VERDE]
                self.assertLessEqual(len(verdes), 1)

    def test_verde_pasa_por_amarillo_antes_de_rojo(self):
        """La demostración no debe contradecir RN-06: verde → amarillo → rojo."""
        anteriores = None
        for mensaje in recorrer_demostracion(120):
            if not isinstance(mensaje, CambioFase):
                continue
            if anteriores is not None:
                for posicion, estado in mensaje.estados.items():
                    if anteriores[posicion] is EstadoSemaforo.VERDE:
                        self.assertNotEqual(estado, EstadoSemaforo.ROJO)
            anteriores = mensaje.estados

    def test_termina_finalizada_en_la_duracion_indicada(self):
        progresos = [m for m in recorrer_demostracion(30) if isinstance(m, ProgresoEjecucion)]
        self.assertEqual(progresos[-1].marca_tiempo, 30)
        self.assertIs(progresos[-1].estado, EstadoEjecucion.FINALIZADA)


class TestCargaVideos(unittest.TestCase):
    """HU-01 desde la ventana del operador (los mensajes de error se interceptan)."""

    def setUp(self):
        try:
            self.ventana = InterfazPrincipal()
        except tk.TclError as error:
            self.skipTest(f"Sin entorno gráfico: {error}")
        self.ventana.withdraw()
        self._temporal = tempfile.TemporaryDirectory()
        self.carpeta = Path(self._temporal.name)
        parche = mock.patch("semaforo.interfaz.messagebox.showerror")
        self.mostrar_error = parche.start()
        self.addCleanup(parche.stop)

    def tearDown(self):
        self.ventana.destroy()
        self._temporal.cleanup()

    def cargar(self, posicion: int, ruta: Path) -> None:
        tarjeta = self.ventana.tarjetas[posicion]
        tarjeta.seleccionar_archivo(ruta)
        tarjeta.cargar_video()

    def test_cp01_ca01_seleccion_muestra_ruta_y_habilita_carga(self):
        """HU-01 CA-01 / RF-01: al seleccionar el archivo se ve la ruta y se habilita Cargar."""
        tarjeta = self.ventana.tarjetas[1]
        self.assertFalse(tarjeta.boton_cargar.habilitado)
        ruta = crear_mp4(self.carpeta / "carril1.mp4")
        tarjeta.seleccionar_archivo(ruta)
        self.assertEqual(tarjeta.texto_ruta, str(ruta))
        self.assertTrue(tarjeta.boton_cargar.habilitado)

    def test_cp01_ca03_carga_muestra_metadatos(self):
        """HU-01 CA-03: tras cargar se muestran duración, fps y resolución."""
        self.cargar(1, crear_mp4(self.carpeta / "carril1.mp4"))
        texto = self.ventana.tarjetas[1].texto_metadatos
        self.assertIn("64x36", texto)
        self.assertIn(f"{FPS_PRUEBA:.2f} fps", texto)
        self.assertIn(formatear_tiempo(CUADROS_PRUEBA / FPS_PRUEBA), texto)

    def test_cp21_ca02_ca04_video_invalido_muestra_error_y_sigue_operativa(self):
        """HU-01 CA-02, CA-04 / RNF-05: .avi o mp4 corrupto → mensaje; se puede cargar otro."""
        for invalido in (crear_mp4(self.carpeta / "c.avi"), crear_corrupto(self.carpeta / "r.mp4")):
            self.cargar(1, invalido)
        self.assertEqual(self.mostrar_error.call_count, 2)
        self.assertIsNone(self.ventana.tarjetas[1].video)
        self.cargar(1, crear_mp4(self.carpeta / "carril1.mp4"))
        self.assertIsNotNone(self.ventana.tarjetas[1].video)

    def test_cp01_ca05_iniciar_se_habilita_solo_con_los_tres_videos(self):
        """HU-01 CA-05: la ejecución no se habilita hasta tener un video en cada carril."""
        for posicion in POSICIONES_CARRIL:
            self.assertFalse(self.ventana.boton_iniciar.habilitado)
            self.cargar(posicion, crear_mp4(self.carpeta / f"carril{posicion}.mp4"))
        self.assertTrue(self.ventana.boton_iniciar.habilitado)

    def test_cp01_ca06_fps_distintos_muestra_error_y_no_habilita(self):
        """HU-01 CA-06: con fps distintos se informa el error y no se habilita Iniciar."""
        for posicion, fps in zip(POSICIONES_CARRIL, (10.0, 10.0, 15.0)):
            self.cargar(posicion, crear_mp4(self.carpeta / f"carril{posicion}.mp4", fps=fps))
        self.mostrar_error.assert_called_once()
        self.assertFalse(self.ventana.boton_iniciar.habilitado)


if __name__ == "__main__":
    unittest.main()
