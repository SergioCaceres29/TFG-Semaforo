"""Pruebas de control_fases.py (HU-06, RF-08, RN-05, RN-06, RN-11): máquina de estados en segundos de simulación."""

import unittest

import semaforo.control_fases
from semaforo.control_fases import ControladorSemaforo
from semaforo.modelos import EstadoSemaforo, Parametros
from tests.auditoria import PROHIBIDOS_EN_PURO, modulos_importados

PARAMETROS = Parametros(umbral_demanda=5, umbral_confianza=0.5, intervalo_seg=10,
                        verde_min=10, verde_max=28, amarillo=3)
VERDE, AMARILLO, ROJO = EstadoSemaforo.VERDE, EstadoSemaforo.AMARILLO, EstadoSemaforo.ROJO


def correr_hasta(controlador: ControladorSemaforo, t_sim: int) -> None:
    """Avanza de a 1 s procesando los vencimientos, y deja el controlador en t_sim con ese segundo ya verificado."""
    while controlador.t_sim < t_sim:
        controlador.verificar_tiempos()
        controlador.avanzar()
    controlador.verificar_tiempos()


class TestControlador(unittest.TestCase):
    def setUp(self):
        self.controlador = ControladorSemaforo(PARAMETROS)

    def test_cp08_ca01_arranca_con_carril_1_en_verde(self):
        """HU-06 CA-01 (regla 3): en t_sim = 0 el carril 1 está en verde y los otros en rojo."""
        self.assertEqual(self.controlador.obtener_estados(), {1: VERDE, 2: ROJO, 3: ROJO})
        self.assertEqual([(c.marca_tiempo, c.posicion, c.estado) for c in self.controlador.cambios],
                         [(0, 1, VERDE), (0, 2, ROJO), (0, 3, ROJO)])

    def test_cp08_ca02_no_cambia_antes_de_verde_min(self):
        """HU-06 CA-02 / RN-05: ninguna transición antes del verde mínimo."""
        correr_hasta(self.controlador, PARAMETROS.verde_min - 1)
        self.assertFalse(self.controlador.solicitar_transicion(2))
        self.assertEqual(self.controlador.obtener_estados()[1], VERDE)
        correr_hasta(self.controlador, PARAMETROS.verde_min)
        self.assertTrue(self.controlador.solicitar_transicion(2))
        self.assertEqual(self.controlador.obtener_estados(), {1: AMARILLO, 2: ROJO, 3: ROJO})

    def test_cp08_ca02_no_transiciona_hacia_el_mismo_carril(self):
        """RN-04: si el elegido ya tiene el verde, lo conserva (verde extendido)."""
        correr_hasta(self.controlador, PARAMETROS.verde_min)
        self.assertFalse(self.controlador.solicitar_transicion(1))
        self.assertEqual(self.controlador.obtener_estados()[1], VERDE)

    def test_cp08_ca02_cede_en_verde_max_al_siguiente_del_ciclo(self):
        """HU-06 CA-02 / RN-05: al cumplir verde_max cede en ese instante, y el verde pasa al siguiente del ciclo."""
        correr_hasta(self.controlador, PARAMETROS.verde_max - 1)
        self.assertEqual(self.controlador.obtener_estados()[1], VERDE)
        correr_hasta(self.controlador, PARAMETROS.verde_max)
        self.assertEqual(self.controlador.obtener_estados()[1], AMARILLO)
        turno = PARAMETROS.verde_max + PARAMETROS.amarillo
        correr_hasta(self.controlador, 3 * turno)
        self.assertEqual(self.controlador.obtener_estados(), {1: VERDE, 2: ROJO, 3: ROJO})
        verdes = [c.posicion for c in self.controlador.cambios if c.estado is VERDE]
        self.assertEqual(verdes, [1, 2, 3, 1])

    def test_cp08_ca03_verde_pasa_por_amarillo_fijo(self):
        """HU-06 CA-03 / RN-06: verde → amarillo de duración fija → rojo, y recién entonces verde al entrante."""
        correr_hasta(self.controlador, PARAMETROS.verde_min)
        self.controlador.solicitar_transicion(3)
        correr_hasta(self.controlador, PARAMETROS.verde_min + PARAMETROS.amarillo - 1)
        self.assertEqual(self.controlador.obtener_estados(), {1: AMARILLO, 2: ROJO, 3: ROJO})
        self.assertFalse(self.controlador.solicitar_transicion(2))
        correr_hasta(self.controlador, PARAMETROS.verde_min + PARAMETROS.amarillo)
        self.assertEqual(self.controlador.obtener_estados(), {1: ROJO, 2: ROJO, 3: VERDE})

    def test_cp08_t_video_congelado_en_rojo(self):
        """RN-11: t_video avanza solo en verde o amarillo; en rojo queda congelado y nunca supera t_sim."""
        correr_hasta(self.controlador, PARAMETROS.verde_min)
        self.controlador.solicitar_transicion(2)
        correr_hasta(self.controlador, 40)
        salida = PARAMETROS.verde_min + PARAMETROS.amarillo
        self.assertEqual(self.controlador.t_video, {1: salida, 2: 40 - salida, 3: 0})
        self.assertTrue(all(t <= self.controlador.t_sim for t in self.controlador.t_video.values()))

    def test_cp08_tiempo_en_rojo_se_reinicia_al_pasar_a_verde(self):
        """RN-07 (regla 8): segundos de t_sim desde que el carril pasó a rojo; 0 mientras no está en rojo."""
        correr_hasta(self.controlador, PARAMETROS.verde_min)
        self.controlador.solicitar_transicion(2)
        correr_hasta(self.controlador, 20)
        salida = PARAMETROS.verde_min + PARAMETROS.amarillo
        self.assertEqual(self.controlador.tiempos_rojo(), {1: 20 - salida, 2: 0, 3: 20})

    def test_cp08_control_fases_sin_imports_prohibidos(self):
        """CLAUDE.md §2: control_fases.py es Python puro y solo importa modelos."""
        modulos = modulos_importados(semaforo.control_fases)
        self.assertFalse({m.split(".")[0] for m in modulos} & PROHIBIDOS_EN_PURO)
        self.assertLessEqual({m for m in modulos if m.startswith("semaforo")}, {"semaforo.modelos"})


if __name__ == "__main__":
    unittest.main()
