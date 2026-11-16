"""Punto de entrada: python -m semaforo."""

import logging

from semaforo.interfaz import iniciar_interfaz


def main() -> None:
    """Configura el registro de eventos y abre la interfaz del operador."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    iniciar_interfaz()


if __name__ == "__main__":
    main()
