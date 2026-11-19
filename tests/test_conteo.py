"""Pruebas de conteo.py (HU-04, RF-06, RN-03) con detecciones simuladas (sin el modelo)."""

import unittest

from semaforo.conteo import ContadorZonas
from semaforo.modelos import Clase, Deteccion, ErrorConfiguracion, RegistroConteo, Zona

INTERVALO = 10
CUADRADO = ((0, 50), (100, 50), (100, 100), (0, 100))
"""Zona de y = 50 a 100 y x = 0 a 100 (píxeles del video)."""
ZONAS = {
    1: Zona("Ruta 14 norte", CUADRADO, id_zona=11),
    2: Zona("Ruta 14 sur", CUADRADO, id_zona=12),
    3: Zona("Sagrado Corazón", ((200, 0), (300, 0), (300, 40), (200, 40)), id_zona=13),
}


def vehiculo(clase: Clase, x_centro: float, y_inferior: float, alto: float = 20) -> Deteccion:
    """Detección cuya caja tiene su centro inferior en (x_centro, y_inferior)."""
    return Deteccion(clase, 0.9, x_centro - 10, y_inferior - alto, x_centro + 10, y_inferior)


def tiempos(fps: float, segundos: float) -> list[float]:
    """Marcas de tiempo t = n / fps de los cuadros de un video de `segundos` de duración."""
    return [n / fps for n in range(int(segundos * fps))]


class TestPertenencia(unittest.TestCase):
    def setUp(self):
        self.contador = ContadorZonas(ZONAS, INTERVALO)

    def test_cp06_ca01_cuenta_dentro_y_descarta_fuera(self):
        """HU-04 CA-01 / RF-06: se cuenta lo que está dentro de la zona y se descarta lo demás."""
        self.contador.acumular_por_intervalo(0.0, {1: [vehiculo(Clase.AUTO, 50, 80),
                                                       vehiculo(Clase.MOTO, 150, 80),
                                                       vehiculo(Clase.CAMION, 50, 30)]})
        self.assertEqual(self.contador.obtener_demanda_por_carril()[1],
                         {Clase.AUTO: 1, Clase.MOTO: 0, Clase.CAMION: 0})

    def test_cp06_ca01_punto_de_referencia_es_el_centro_inferior(self):
        """CLAUDE.md §6: cuenta el centro inferior de la caja, no su centro."""
        centro_fuera_pie_dentro = Deteccion(Clase.AUTO, 0.9, 40, 0, 60, 60)  # centro (50, 30), pie (50, 60)
        centro_dentro_pie_fuera = Deteccion(Clase.MOTO, 0.9, 40, 40, 60, 120)  # centro (50, 80), pie (50, 120)
        zona = ZONAS[1]
        self.assertTrue(self.contador.evaluar_pertenencia(centro_fuera_pie_dentro, zona))
        self.assertFalse(self.contador.evaluar_pertenencia(centro_dentro_pie_fuera, zona))

    def test_cp06_ca01_punto_en_el_borde_cuenta_como_dentro(self):
        """CLAUDE.md §6: cv2.pointPolygonTest >= 0, el borde de la zona cuenta como dentro."""
        self.assertTrue(self.contador.evaluar_pertenencia(vehiculo(Clase.AUTO, 100, 75), ZONAS[1]))
        self.assertTrue(self.contador.evaluar_pertenencia(vehiculo(Clase.AUTO, 50, 100), ZONAS[1]))

    def test_cp06_ca01_cada_video_se_evalua_solo_contra_su_zona(self):
        """HU-04 CA-01: las detecciones del video del carril 3 no se evalúan contra la zona del carril 1."""
        en_zona_1 = vehiculo(Clase.AUTO, 50, 80)
        self.contador.acumular_por_intervalo(0.0, {3: [en_zona_1]})
        demanda = self.contador.obtener_demanda_por_carril()
        self.assertEqual(demanda[1][Clase.AUTO], 0)
        self.assertEqual(demanda[3][Clase.AUTO], 0)

    def test_cp06_zona_sin_id_da_error_controlado(self):
        """RN-09: la zona debe estar guardada (con id_zona) para asociarle los conteos."""
        zonas = {**ZONAS, 2: Zona("Ruta 14 sur", CUADRADO)}
        with self.assertRaises(ErrorConfiguracion):
            ContadorZonas(zonas, INTERVALO)


class TestConsolidacionPorIntervalo(unittest.TestCase):
    def setUp(self):
        self.contador = ContadorZonas(ZONAS, INTERVALO)

    def test_cp06_ca02_sin_registros_antes_del_cierre(self):
        """HU-04 CA-02: antes del cuadro de cierre no se consolida nada."""
        for t in tiempos(10.0, INTERVALO):
            self.assertEqual(self.contador.acumular_por_intervalo(t, {1: [vehiculo(Clase.AUTO, 50, 80)]}), [])

    def test_cp06_ca02_consolida_por_zona_y_clase_al_cierre(self):
        """HU-04 CA-02 / RF-06: al cierre, un registro por zona y clase (las ausentes con 0)."""
        detecciones = {1: [vehiculo(Clase.AUTO, 30, 80), vehiculo(Clase.AUTO, 70, 80)],
                       2: [vehiculo(Clase.MOTO, 50, 60)],
                       3: [vehiculo(Clase.CAMION, 250, 30)]}
        registros = self.contador.acumular_por_intervalo(float(INTERVALO), detecciones)
        self.assertEqual(len(registros), 9)
        cantidades = {(r.id_zona, r.clase): r.cantidad for r in registros}
        self.assertEqual(cantidades[(11, Clase.AUTO)], 2)
        self.assertEqual(cantidades[(12, Clase.MOTO)], 1)
        self.assertEqual(cantidades[(13, Clase.CAMION)], 1)
        self.assertEqual(sum(cantidades.values()), 4)
        self.assertTrue(all((r.intervalo_inicio, r.intervalo_fin) == (0.0, 10.0) for r in registros))

    def test_cp06_ca03_vehiculo_en_cuadros_consecutivos_cuenta_una_vez(self):
        """HU-04 CA-03 / RN-03: un auto detenido en la zona todo el intervalo cuenta una sola vez."""
        detenido = {1: [vehiculo(Clase.AUTO, 50, 80)]}
        registros = []
        for t in tiempos(10.0, INTERVALO + 1):
            registros += self.contador.acumular_por_intervalo(t, detenido)
        self.assertIn(RegistroConteo(11, Clase.AUTO, 1, 0.0, 10.0), registros)

    def test_cp06_ca03_cuenta_la_ocupacion_del_cuadro_de_cierre(self):
        """RN-03: un vehículo que salió de la zona antes del cierre no suma en ese intervalo."""
        for t in tiempos(10.0, INTERVALO):
            self.contador.acumular_por_intervalo(t, {1: [vehiculo(Clase.MOTO, 50, 80)]})
        registros = self.contador.acumular_por_intervalo(float(INTERVALO), {1: []})
        self.assertIn(RegistroConteo(11, Clase.MOTO, 0, 0.0, 10.0), registros)

    def test_cp06_ca02_intervalos_consecutivos_con_limites_exactos(self):
        """HU-04 CA-02: cierra en el primer cuadro con t ≥ fin; el último intervalo incompleto se descarta."""
        fps = 29.97
        cuadros_de_cierre = []
        limites = []
        for n, t in enumerate(tiempos(fps, 35)):
            registros = self.contador.acumular_por_intervalo(t, {})
            if registros:
                cuadros_de_cierre.append(n)
                limites.append((registros[0].intervalo_inicio, registros[0].intervalo_fin))
        self.assertEqual(cuadros_de_cierre, [300, 600, 900])
        self.assertEqual(limites, [(0.0, 10.0), (10.0, 20.0), (20.0, 30.0)])


class TestPrecisionDelConteo(unittest.TestCase):
    @unittest.skip("Manual: requiere el conteo manual de referencia (QA) y RF-15; se mide al cierre")
    def test_cp18_ca04_precision_frente_al_conteo_manual(self):
        """HU-04 CA-04 / RNF-02: precisión ≥ 90 % frente al conteo manual en los videos de validación.

        Procedimiento: contar a mano, en el cuadro de cierre de cada intervalo, los vehículos por clase dentro
        de cada zona (mismo criterio que RN-03); cargarlo con RF-15 y comparar con los conteos de la ejecución.
        """


if __name__ == "__main__":
    unittest.main()
