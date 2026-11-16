"""Pruebas de los tipos compartidos (modelos.py)."""

import unittest

from semaforo.modelos import POSICIONES_CARRIL, ActualizacionCarril, Clase, EstadoEjecucion


class TestModelos(unittest.TestCase):
    def test_mapeo_clases_coincide_con_indices_del_modelo(self):
        """RN-02 / CLAUDE.md §6: índice 0 = auto, 1 = camión, 2 = moto (orden de best.pt)."""
        self.assertEqual({c.value: c.descripcion for c in Clase},
                         {0: "auto", 1: "camion", 2: "moto"})

    def test_orden_de_presentacion_auto_moto_camion(self):
        """La interfaz muestra las clases como auto, moto, camión, sin importar el índice."""
        self.assertEqual([c.descripcion for c in Clase], ["auto", "moto", "camion"])

    def test_tres_carriles_en_posiciones_1_a_3(self):
        """RN-01: un video por carril, 3 carriles."""
        self.assertEqual(POSICIONES_CARRIL, (1, 2, 3))

    def test_demanda_es_suma_de_las_tres_clases(self):
        """CLAUDE.md §6: demanda de un carril = suma de las tres clases."""
        actualizacion = ActualizacionCarril(1, {Clase.AUTO: 4, Clase.MOTO: 2, Clase.CAMION: 1})
        self.assertEqual(actualizacion.demanda, 7)

    def test_estados_de_ejecucion_sin_pausada(self):
        """Figura 10 / Tabla 18: Creada, EnEjecucion, Finalizada o Abortada; sin Pausada."""
        self.assertEqual([e.value for e in EstadoEjecucion],
                         ["Creada", "EnEjecucion", "Finalizada", "Abortada"])


if __name__ == "__main__":
    unittest.main()
