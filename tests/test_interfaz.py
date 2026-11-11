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
    EstadoReproduccion,
    InterfazPrincipal,
    SimuladorDemostracion,
    color_luz,
    formatear_tiempo,
    rectangulo_video,
)
from semaforo.nucleo import crear_gestor_zonas
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
        """RF-16: el semáforo muestra un único estado."""
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


class VentanaOculta(unittest.TestCase):
    """Ventana del operador oculta, con base en memoria y mensajes de error interceptados."""

    def setUp(self):
        try:
            self.ventana = InterfazPrincipal(crear_gestor_zonas(":memory:"))
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


class TestCargaVideos(VentanaOculta):
    """HU-01 desde la ventana del operador."""

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

    def test_cp16_pausar_y_detener_solo_cambian_la_reproduccion(self):
        """HU-09 CA-03 / RF-16: pausar, reanudar y detener actúan sobre la reproducción.

        Demostración provisional: verifica el estado de la interfaz; que la base no
        cambie se prueba cuando exista GestorDemostracion (HU-09).
        """
        for posicion in POSICIONES_CARRIL:
            self.cargar(posicion, crear_mp4(self.carpeta / f"carril{posicion}.mp4"))
        self.ventana.boton_iniciar.invoke()
        self.assertIs(self.ventana.estado_reproduccion, EstadoReproduccion.REPRODUCIENDO)
        self.ventana.alternar_pausa()
        self.assertIs(self.ventana.estado_reproduccion, EstadoReproduccion.PAUSADA)
        self.ventana.alternar_pausa()
        self.assertIs(self.ventana.estado_reproduccion, EstadoReproduccion.REPRODUCIENDO)
        self.ventana.detener_demo()
        self.assertIs(self.ventana.estado_reproduccion, EstadoReproduccion.DETENIDA)
        self.assertTrue(self.ventana.boton_iniciar.habilitado)


class TestZonasVirtuales(VentanaOculta):
    """HU-02 desde la ventana del operador, con un video cargado en cada carril."""

    TRIANGULO = ((100, 100), (1800, 100), (960, 1000))

    def setUp(self):
        super().setUp()
        for posicion in POSICIONES_CARRIL:
            self.cargar(posicion, crear_mp4(self.carpeta / f"carril{posicion}.mp4",
                                            ancho=1920, alto=1080, cuadros=3))

    def trazar(self, posicion: int, nombre: str, vertices=TRIANGULO):
        editor = self.ventana.tarjetas[posicion].abrir_editor_zona()
        for x, y in vertices:
            editor.agregar_vertice(x, y)
        editor.nombre_carril = nombre
        editor.confirmar()
        return editor

    def test_cp02_ca01_editor_dibuja_poligono_y_pide_nombre(self):
        """HU-02 CA-01 / RF-02: los vértices marcados forman el polígono; se pide el nombre."""
        tarjeta = self.ventana.tarjetas[1]
        self.assertTrue(tarjeta.boton_zona.habilitado)
        editor = tarjeta.abrir_editor_zona()
        for x, y in self.TRIANGULO:
            editor.agregar_vertice(x, y)
        self.assertEqual(editor.vertices, list(self.TRIANGULO))
        self.assertTrue(editor.lienzo.find_withtag("poligono"))
        self.assertTrue(editor.entrada_nombre.winfo_exists())
        editor.destroy()

    def test_cp02_ca02_ca03_confirmar_guarda_la_zona_del_carril(self):
        """HU-02 CA-03: al confirmar, la zona queda asociada al video del carril."""
        self.trazar(1, "Ruta 14")
        tarjeta = self.ventana.tarjetas[1]
        self.assertEqual(tarjeta.zona.vertices, self.TRIANGULO)
        self.assertIn("Ruta 14", tarjeta.texto_titulo)
        self.mostrar_error.assert_not_called()

    def test_cp02_ca02_nombre_repetido_o_pocos_vertices_no_se_guarda(self):
        """HU-02 CA-02: nombre repetido entre carriles o < 3 vértices → mensaje, sin guardar."""
        self.trazar(1, "Norte")
        repetido = self.trazar(2, "norte")
        corto = self.trazar(3, "Sur", vertices=self.TRIANGULO[:2])
        self.assertEqual(self.mostrar_error.call_count, 2)
        self.assertIsNone(self.ventana.tarjetas[2].zona)
        self.assertIsNone(self.ventana.tarjetas[3].zona)
        self.assertTrue(repetido.winfo_exists() and corto.winfo_exists())

    def test_cp02_ca04_editar_vertice_conserva_las_otras_zonas(self):
        """HU-02 CA-04: se mueve un vértice de una zona sin tocar las demás."""
        self.trazar(1, "Norte")
        self.trazar(2, "Sur")
        editor = self.ventana.tarjetas[1].abrir_editor_zona()
        self.assertEqual(editor.vertices, list(self.TRIANGULO))
        editor.mover_vertice(0, 300, 300)
        editor.confirmar()
        self.assertEqual(self.ventana.tarjetas[1].zona.vertices[0], (300, 300))
        self.assertEqual(self.ventana.tarjetas[2].zona.vertices, self.TRIANGULO)

    def test_cp02_ca04_eliminar_una_zona_conserva_las_demas(self):
        """HU-02 CA-04: se elimina la zona de un carril sin redefinir las otras."""
        self.trazar(1, "Norte")
        self.trazar(2, "Sur")
        with mock.patch("semaforo.interfaz.messagebox.askyesno", return_value=True):
            self.ventana.tarjetas[1].eliminar_zona()
        self.assertIsNone(self.ventana.tarjetas[1].zona)
        self.assertFalse(self.ventana.tarjetas[1].boton_eliminar_zona.habilitado)
        self.assertEqual(self.ventana.tarjetas[2].zona.nombre_carril, "Sur")

    def test_cp03_zona_guardada_reaparece_al_volver_a_cargar_el_video(self):
        """RF-03: al recargar el mismo video su zona se recupera sin redefinirla."""
        self.trazar(1, "Norte")
        self.cargar(1, self.carpeta / "carril1.mp4")
        self.assertEqual(self.ventana.tarjetas[1].zona.nombre_carril, "Norte")


if __name__ == "__main__":
    unittest.main()
