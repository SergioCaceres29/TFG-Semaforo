"""Pruebas de decision.py (HU-05, RF-07, RN-04, RN-07, RN-08, RN-11) sobre demanda simulada."""

import ast
import unittest
from pathlib import Path

import semaforo.decision
from semaforo.decision import MotorDecision, agrupar_demanda, demanda_en_instante
from semaforo.modelos import Clase, RegistroConteo

UMBRAL = 5
SIN_ROJO = {1: 0.0, 2: 0.0, 3: 0.0}


class TestSeleccion(unittest.TestCase):
    def setUp(self):
        self.motor = MotorDecision(UMBRAL)

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
        arbol = ast.parse(Path(semaforo.decision.__file__).read_text(encoding="utf-8"))
        modulos = {alias.name for nodo in ast.walk(arbol) if isinstance(nodo, ast.Import) for alias in nodo.names}
        modulos |= {nodo.module for nodo in ast.walk(arbol) if isinstance(nodo, ast.ImportFrom)}
        prohibidos = {"cv2", "numpy", "sqlite3", "time", "datetime", "ultralytics", "torch", "pathlib", "os"}
        self.assertFalse({m.split(".")[0] for m in modulos} & prohibidos)
        propios = {m for m in modulos if m.startswith("semaforo")}
        self.assertLessEqual(propios, {"semaforo.modelos", "semaforo.control_fases"})


if __name__ == "__main__":
    unittest.main()
