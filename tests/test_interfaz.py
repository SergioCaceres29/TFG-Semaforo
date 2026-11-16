"""Pruebas del esqueleto de la interfaz que no necesitan abrir la ventana.

El esqueleto es un adelanto del Sprint 0 y no cubre todavía ningún CA; los CP de
HU-01, HU-02 y HU-07 se agregan cuando se implementen esas HU.
"""

import unittest

from semaforo.interfaz import (
    LUZ_APAGADA,
    LUZ_ENCENDIDA,
    SimuladorDemostracion,
    color_luz,
    formatear_tiempo,
    rectangulo_video,
)
from semaforo.modelos import CambioFase, EstadoEjecucion, EstadoSemaforo, ProgresoEjecucion


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


if __name__ == "__main__":
    unittest.main()
