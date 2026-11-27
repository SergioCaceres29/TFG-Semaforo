"""Pruebas de decision.py: prioridad (HU-05, CP-07) y generación de ambos planes (HU-06, CP-08)."""

import unittest

import semaforo.decision
from semaforo.decision import MotorDecision, agrupar_demanda, demanda_en_instante
from semaforo.modelos import Clase, EstadoSemaforo, EventoFase, Parametros, RegistroConteo, TipoPlan
from tests.auditoria import PROHIBIDOS_EN_PURO, modulos_importados

INTERVALO = 10
DURACION = 300
PARAMETROS = Parametros(umbral_demanda=5, umbral_confianza=0.5, intervalo_seg=INTERVALO,
                        verde_min=10, verde_max=28, amarillo=3)
SIN_ROJO = {1: 0.0, 2: 0.0, 3: 0.0}


class TestSeleccion(unittest.TestCase):
    def setUp(self):
        self.motor = MotorDecision(PARAMETROS)

    def test_cp07_ca01_candidatos_superan_umbral(self):
        """HU-05 CA-01 / RN-04: es candidato solo quien supera (>) el umbral; igualarlo no alcanza."""
        self.assertEqual(self.motor.seleccionar_carril_prioritario({1: 5, 2: 6, 3: 0}, SIN_ROJO), 2)
        self.assertIsNone(self.motor.seleccionar_carril_prioritario({1: 5, 2: 5, 3: 5}, SIN_ROJO))

    def test_cp07_ca02_prioridad_mayor_demanda(self):
        """HU-05 CA-02 / RN-04: entre los candidatos gana el de mayor demanda, aunque lleve menos en rojo."""
        tiempos_rojo = {1: 0.0, 2: 90.0, 3: 10.0}
        self.assertEqual(self.motor.seleccionar_carril_prioritario({1: 7, 2: 8, 3: 12}, tiempos_rojo), 3)

    def test_cp07_ca03_desempate_por_tiempo_en_rojo(self):
        """HU-05 CA-03 / RN-07: a igual demanda gana el de más tiempo acumulado en rojo."""
        tiempos_rojo = {1: 0.0, 2: 15.0, 3: 40.0}
        self.assertEqual(self.motor.seleccionar_carril_prioritario({1: 9, 2: 9, 3: 9}, tiempos_rojo), 3)
        self.assertEqual(self.motor.resolver_empate([1, 2], tiempos_rojo), 2)

    def test_cp07_ca03_empate_total_gana_menor_posicion(self):
        """HU-05 CA-03 (regla 7, 20/11/2026): empate en demanda y en rojo → menor posición."""
        tiempos_rojo = {1: 0.0, 2: 31.0, 3: 31.0}
        self.assertEqual(self.motor.seleccionar_carril_prioritario({1: 2, 2: 9, 3: 9}, tiempos_rojo), 2)
        self.assertEqual(self.motor.resolver_empate([3, 2], tiempos_rojo), 2)

    def test_cp07_ca04_sin_candidatos_ciclo_fijo(self):
        """HU-05 CA-04 / RN-08: sin candidatos se sigue el ciclo fijo 1 → 2 → 3 → 1."""
        self.assertIsNone(self.motor.seleccionar_carril_prioritario({1: 0, 2: 3, 3: 5}, SIN_ROJO))
        self.assertEqual([self.motor.aplicar_ciclo_por_defecto(p) for p in (1, 2, 3)], [2, 3, 1])


class TestDemandaRegistrada(unittest.TestCase):
    def setUp(self):
        conteos = [
            RegistroConteo(11, Clase.AUTO, 3, 0.0, 10.0),
            RegistroConteo(11, Clase.MOTO, 2, 0.0, 10.0),
            RegistroConteo(11, Clase.CAMION, 1, 0.0, 10.0),
            RegistroConteo(12, Clase.AUTO, 4, 0.0, 10.0),
            RegistroConteo(11, Clase.AUTO, 0, 10.0, 20.0),
            RegistroConteo(11, Clase.MOTO, 1, 10.0, 20.0),
        ]
        self.demanda = agrupar_demanda(conteos, {11: 1, 12: 2, 13: 3})

    def test_cp07_ca01_demanda_suma_las_tres_clases(self):
        """CLAUDE.md §6: la demanda de un carril es la suma de las tres clases del cuadro de cierre."""
        self.assertEqual(self.demanda[1], ((10.0, 6), (20.0, 1)))
        self.assertEqual(self.demanda[2], ((10.0, 4),))
        self.assertEqual(self.demanda[3], ())

    def test_cp07_ca01_demanda_ultimo_intervalo_cerrado(self):
        """HU-05 CA-01 / RN-11 (regla 1a): demanda del último intervalo con fin ≤ t_video; 0 antes del primero."""
        serie = self.demanda[1]
        self.assertEqual(demanda_en_instante(serie, 0.0), 0)
        self.assertEqual(demanda_en_instante(serie, 9.0), 0)
        self.assertEqual(demanda_en_instante(serie, 10.0), 6)
        self.assertEqual(demanda_en_instante(serie, 19.0), 6)
        self.assertEqual(demanda_en_instante(serie, 20.0), 1)
        self.assertEqual(demanda_en_instante(serie, 95.0), 1)
        self.assertEqual(demanda_en_instante(self.demanda[3], 50.0), 0)


class TestPureza(unittest.TestCase):
    def test_cp07_decision_sin_imports_prohibidos(self):
        """CLAUDE.md §2: decision.py es Python puro (sin cv2, I/O, base ni reloj) y solo usa modelos."""
        modulos = modulos_importados(semaforo.decision)
        self.assertFalse({m.split(".")[0] for m in modulos} & PROHIBIDOS_EN_PURO)
        propios = {m for m in modulos if m.startswith("semaforo")}
        self.assertLessEqual(propios, {"semaforo.modelos", "semaforo.control_fases"})


def serie(*demandas: int) -> tuple[tuple[float, int], ...]:
    """Serie de demanda con un valor por intervalo cerrado de INTERVALO segundos del video."""
    return tuple((float(INTERVALO * (k + 1)), demanda) for k, demanda in enumerate(demandas))


def constante(demanda: int) -> tuple[tuple[float, int], ...]:
    """Misma demanda en todos los intervalos del análisis."""
    return serie(*[demanda] * (DURACION // INTERVALO))


ESCENARIOS = {
    "sin_demanda": {1: constante(0), 2: constante(0), 3: constante(0)},
    "alta_en_2": {1: constante(0), 2: constante(20), 3: constante(0)},
    "empate_en_todos": {1: constante(9), 2: constante(9), 3: constante(9)},
    "alternante": {1: serie(*[12] * 6 + [0] * 24), 2: constante(3), 3: serie(*[0] * 6 + [15] * 24)},
}
"""Secuencias de demanda registrada completas (DURACION s) para recorrer los planes de punta a punta."""


def linea_de_tiempo(eventos: list[EventoFase]) -> dict[int, list[EstadoSemaforo | None]]:
    """Estado de cada carril en cada segundo [0, DURACION), reconstruido desde los eventos del plan."""
    linea = {p: [None] * DURACION for p in (1, 2, 3)}
    for evento in eventos:
        for t in range(evento.marca_tiempo, evento.marca_tiempo + evento.duracion):
            linea[evento.posicion][t] = evento.estado
    return linea


def de_carril(eventos: list[EventoFase], posicion: int) -> list[EventoFase]:
    """Eventos de un carril en orden de tiempo."""
    return sorted((e for e in eventos if e.posicion == posicion), key=lambda e: e.marca_tiempo)


class TestPlanes(unittest.TestCase):
    """HU-06 (RF-08, CP-08): ambos planes generados sobre secuencias de demanda completas."""

    def setUp(self):
        self.motor = MotorDecision(PARAMETROS)

    def planes(self):
        """Cada escenario con sus dos planes: (nombre, tipo, eventos)."""
        for nombre, demanda in ESCENARIOS.items():
            yield nombre, TipoPlan.RECOMENDADO, self.motor.generar_plan_recomendado(demanda, DURACION)
            yield nombre, TipoPlan.FIJO, self.motor.generar_plan_fijo(demanda, DURACION)

    def test_cp08_ca01_cada_carril_tiene_estado_en_todo_instante(self):
        """HU-06 CA-01 / RF-08: en cada segundo cada carril está en verde, amarillo o rojo, sin solapes."""
        for nombre, tipo, eventos in self.planes():
            with self.subTest(escenario=nombre, plan=tipo):
                self.assertTrue(all(e.tipo_plan is tipo for e in eventos))
                for posicion in (1, 2, 3):
                    propios = de_carril(eventos, posicion)
                    self.assertTrue(all(a.marca_tiempo + a.duracion == b.marca_tiempo
                                        for a, b in zip(propios, propios[1:])))
                for estados in linea_de_tiempo(eventos).values():
                    self.assertNotIn(None, estados)

    def test_cp08_ca02_verde_dentro_de_min_y_max(self):
        """HU-06 CA-02 / RN-05: ningún verde dura menos que verde_min ni más que verde_max (salvo el truncado final)."""
        for nombre, tipo, eventos in self.planes():
            with self.subTest(escenario=nombre, plan=tipo):
                for e in eventos:
                    if e.estado is EstadoSemaforo.VERDE:
                        self.assertLessEqual(e.duracion, PARAMETROS.verde_max)
                        if e.marca_tiempo + e.duracion < DURACION:
                            self.assertGreaterEqual(e.duracion, PARAMETROS.verde_min)

    def test_cp08_ca03_verde_pasa_por_amarillo_fijo(self):
        """HU-06 CA-03 / RN-06: verde → amarillo (duración fija) → rojo; nunca verde → rojo directo."""
        siguiente = {EstadoSemaforo.VERDE: EstadoSemaforo.AMARILLO, EstadoSemaforo.AMARILLO: EstadoSemaforo.ROJO,
                     EstadoSemaforo.ROJO: EstadoSemaforo.VERDE}
        for nombre, tipo, eventos in self.planes():
            for posicion in (1, 2, 3):
                with self.subTest(escenario=nombre, plan=tipo, carril=posicion):
                    propios = de_carril(eventos, posicion)
                    self.assertTrue(all(siguiente[a.estado] is b.estado for a, b in zip(propios, propios[1:])))
                    for e in propios:
                        if e.estado is EstadoSemaforo.AMARILLO and e.marca_tiempo + e.duracion < DURACION:
                            self.assertEqual(e.duracion, PARAMETROS.amarillo)

    def test_cp08_ca04_nunca_dos_verdes(self):
        """HU-06 CA-04 / RN-06 (regla 4): en cada segundo un solo carril fuera de rojo; el resto en rojo."""
        for nombre, tipo, eventos in self.planes():
            with self.subTest(escenario=nombre, plan=tipo):
                linea = linea_de_tiempo(eventos)
                for t in range(DURACION):
                    fuera_de_rojo = [p for p in (1, 2, 3) if linea[p][t] is not EstadoSemaforo.ROJO]
                    self.assertEqual(len(fuera_de_rojo), 1, f"t_sim = {t}")

    def test_cp08_ca05_ambos_planes_duran_lo_analizado(self):
        """HU-06 CA-05 (regla 11): cada carril cubre [0, duración] en ambos planes; el último evento se trunca."""
        for nombre, tipo, eventos in self.planes():
            for posicion in (1, 2, 3):
                with self.subTest(escenario=nombre, plan=tipo, carril=posicion):
                    propios = de_carril(eventos, posicion)
                    self.assertEqual(propios[0].marca_tiempo, 0)
                    self.assertEqual(propios[-1].marca_tiempo + propios[-1].duracion, DURACION)
                    self.assertEqual(sum(e.duracion for e in propios), DURACION)

    def test_cp08_plan_fijo_rota_1_2_3_con_verde_max(self):
        """RN-08: el plan FIJO da verde_max + amarillo a cada carril en orden 1 → 2 → 3 → 1."""
        eventos = self.motor.generar_plan_fijo(ESCENARIOS["alta_en_2"], DURACION)
        verdes = [(e.posicion, e.marca_tiempo) for e in eventos if e.estado is EstadoSemaforo.VERDE]
        turno = PARAMETROS.verde_max + PARAMETROS.amarillo
        self.assertEqual(verdes[:4], [(1, 0), (2, turno), (3, 2 * turno), (1, 3 * turno)])

    def test_cp08_sin_demanda_recomendado_igual_a_fijo(self):
        """RN-08 (reglas 3 y 9): si nadie supera el umbral, el RECOMENDADO sigue el ciclo fijo normal."""
        demanda = ESCENARIOS["sin_demanda"]
        sin_tipo = [[(e.posicion, e.estado, e.marca_tiempo, e.duracion, e.demanda_asociada) for e in plan]
                    for plan in (self.motor.generar_plan_recomendado(demanda, DURACION),
                                 self.motor.generar_plan_fijo(demanda, DURACION))]
        self.assertEqual(sin_tipo[0], sin_tipo[1])

    def test_cp08_recomendado_prioriza_mayor_demanda(self):
        """RF-07, RN-04: el carril con demanda sobre el umbral recibe más verde que en el plan FIJO."""
        demanda = ESCENARIOS["alta_en_2"]

        def verde_de_2(eventos):
            return sum(e.duracion for e in eventos if e.posicion == 2 and e.estado is EstadoSemaforo.VERDE)

        self.assertGreater(verde_de_2(self.motor.generar_plan_recomendado(demanda, DURACION)),
                           verde_de_2(self.motor.generar_plan_fijo(demanda, DURACION)))

    def test_cp08_ca02_cede_en_verde_max_al_siguiente_del_ciclo(self):
        """RN-05: el carril 2 llega a verde_max con la mayor demanda y aun así el verde pasa al 3."""
        eventos = self.motor.generar_plan_recomendado(ESCENARIOS["alta_en_2"], DURACION)
        verdes = [(e.posicion, e.marca_tiempo, e.duracion) for e in eventos if e.estado is EstadoSemaforo.VERDE]
        turno = PARAMETROS.verde_max + PARAMETROS.amarillo
        self.assertEqual(verdes[1], (2, turno, PARAMETROS.verde_max))
        self.assertEqual(verdes[2][:2], (3, 2 * turno))

    def test_cp08_empate_cede_tras_verde_min_y_reevalua(self):
        """RN-07 (regla 7): a igual demanda gana quien lleva más en rojo; el verde vigente cede al cumplir verde_min."""
        eventos = self.motor.generar_plan_recomendado(ESCENARIOS["empate_en_todos"], DURACION)
        verdes = [(e.posicion, e.duracion) for e in eventos if e.estado is EstadoSemaforo.VERDE]
        self.assertEqual(verdes[1], (2, PARAMETROS.verde_min))
        self.assertEqual(verdes[2][0], 1)

    def test_cp08_demanda_asociada_en_el_instante_del_video(self):
        """RF-12, RN-11: la demanda de cada evento es la del carril en su t_video, no en t_sim."""
        eventos = self.motor.generar_plan_fijo(ESCENARIOS["alta_en_2"], DURACION)
        primer_verde_2 = next(e for e in eventos if e.posicion == 2 and e.estado is EstadoSemaforo.VERDE)
        self.assertEqual(primer_verde_2.demanda_asociada, 0)
        primer_amarillo_2 = next(e for e in eventos if e.posicion == 2 and e.estado is EstadoSemaforo.AMARILLO)
        self.assertEqual(primer_amarillo_2.demanda_asociada, 20)


if __name__ == "__main__":
    unittest.main()
