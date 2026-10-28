"""Interfaz del operador (tkinter): barra lateral de módulos y panel de los 3 carriles.

Esqueleto visual (adelanto del Sprint 0). Mientras no exista `GestorEjecucion`,
los semáforos se alimentan con `SimuladorDemostracion`. Ambos publican los mismos
mensajes de `modelos.py` en `InterfazPrincipal.cola`, así que conectar el motor
real no requiere cambiar la interfaz.
"""

from __future__ import annotations

import ctypes
import logging
import queue
import random
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from semaforo.modelos import (
    NUM_CARRILES,
    POSICIONES_CARRIL,
    ActualizacionCarril,
    CambioFase,
    Clase,
    EstadoEjecucion,
    EstadoSemaforo,
    MensajeInterfaz,
    ProgresoEjecucion,
)

registro = logging.getLogger(__name__)

# --- Apariencia ----------------------------------------------------------------
FUENTE = "Segoe UI"
COLOR_FONDO = "#14161b"
COLOR_BARRA = "#0d0f13"
COLOR_TARJETA = "#1c1f26"
COLOR_SUPERFICIE = "#252932"
COLOR_SUPERFICIE_HOVER = "#2f3440"
COLOR_TEXTO = "#e8eaf0"
COLOR_TEXTO_SUAVE = "#8b93a5"
COLOR_ACENTO = "#4f8cff"
COLOR_ACENTO_HOVER = "#6b9fff"
COLOR_CARCASA = "#0a0b0e"
COLOR_VIDEO = "#101217"

LUZ_ENCENDIDA = {
    EstadoSemaforo.ROJO: "#ff4d4d",
    EstadoSemaforo.AMARILLO: "#ffc233",
    EstadoSemaforo.VERDE: "#2ee66b",
}
LUZ_APAGADA = {
    EstadoSemaforo.ROJO: "#3a1717",
    EstadoSemaforo.AMARILLO: "#3a2f12",
    EstadoSemaforo.VERDE: "#123a20",
}
ORDEN_LUCES = (EstadoSemaforo.ROJO, EstadoSemaforo.AMARILLO, EstadoSemaforo.VERDE)

COLOR_EJECUCION = {
    EstadoEjecucion.CREADA: COLOR_TEXTO_SUAVE,
    EstadoEjecucion.EN_EJECUCION: LUZ_ENCENDIDA[EstadoSemaforo.VERDE],
    EstadoEjecucion.PAUSADA: LUZ_ENCENDIDA[EstadoSemaforo.AMARILLO],
    EstadoEjecucion.FINALIZADA: COLOR_ACENTO,
    EstadoEjecucion.ABORTADA: LUZ_ENCENDIDA[EstadoSemaforo.ROJO],
}
ETIQUETA_EJECUCION = {
    EstadoEjecucion.CREADA: "Sin ejecutar",
    EstadoEjecucion.EN_EJECUCION: "En ejecución",
    EstadoEjecucion.PAUSADA: "Pausada",
    EstadoEjecucion.FINALIZADA: "Finalizada",
    EstadoEjecucion.ABORTADA: "Detenida",
}
ETIQUETA_CLASE = {Clase.AUTO: "Autos", Clase.MOTO: "Motos", Clase.CAMION: "Camiones"}

DPI_BASE = 96
RELACION_VIDEO = 16 / 9
ANCHO_SEMAFORO = 64
ALTO_SEMAFORO = 176
ANCHO_BARRA_LATERAL = 230
TAMANO_VENTANA = "1500x860"
TAMANO_MINIMO = (1200, 720)
PERIODO_COLA_MS = 50

# --- Demostración (provisional, se reemplaza por GestorEjecucion) ---------------
DEMO_TICK_MS = 100
DEMO_PASO_SEG = 0.5
DEMO_DURACION_SEG = 180.0
DEMO_VERDE_SEG = 12.0
DEMO_AMARILLO_SEG = 3.0
DEMO_TICKS_POR_INTERVALO = 10
DEMO_MAX_POR_CLASE = 6
DEMO_SEMILLA = 2026


@dataclass(frozen=True)
class Modulo:
    """Entrada de la barra lateral."""

    clave: str
    titulo: str
    descripcion: str


MODULOS = (
    Modulo("panel", "Panel de carriles", ""),
    Modulo("videos", "Videos y zonas",
           "Sprint 1 · HU-01, HU-02 — Carga de los tres mp4 (uno por carril) "
           "y trazado de la zona virtual sobre el primer cuadro de cada video."),
    Modulo("parametros", "Parámetros",
           "Sprint 1 · RF-10 — Umbral de demanda, umbral de confianza, intervalo "
           "de evaluación, verde mínimo, verde máximo y amarillo."),
    Modulo("ejecucion", "Ejecución",
           "Sprint 4 · CU-02, RF-16 — Procesamiento real de los tres videos: "
           "iniciar, pausar y detener sin perder registros."),
    Modulo("resultados", "Resultados",
           "Sprint 4 · HU-08, RF-12 — Conteos por intervalo y eventos de fase "
           "de cada ejecución."),
    Modulo("validacion", "Validación",
           "Cierre · RF-15 — Carga del conteo manual y cálculo de error y "
           "precisión por carril y clase."),
    Modulo("exportar", "Exportar CSV",
           "Cierre · RF-14 — Exportación de los conteos a CSV (utf-8-sig)."),
)


def color_luz(luz: EstadoSemaforo, estado_actual: EstadoSemaforo) -> str:
    """RF-09: solo la luz del estado vigente se ve encendida."""
    return LUZ_ENCENDIDA[luz] if luz is estado_actual else LUZ_APAGADA[luz]


def formatear_tiempo(segundos: float) -> str:
    """Segundos del video en formato mm:ss."""
    minutos, resto = divmod(int(segundos), 60)
    return f"{minutos:02d}:{resto:02d}"


def rectangulo_video(ancho: int, alto: int) -> tuple[int, int, int, int]:
    """Mayor rectángulo 16:9 centrado dentro de un área de ancho × alto."""
    ancho_video = min(ancho, round(alto * RELACION_VIDEO))
    alto_video = round(ancho_video / RELACION_VIDEO)
    x = (ancho - ancho_video) // 2
    y = (alto - alto_video) // 2
    return x, y, x + ancho_video, y + alto_video


class SimuladorDemostracion:
    """Fuente provisional de mensajes para mostrar la interfaz sin el motor real.

    Rota el verde 1 → 2 → 3 con tiempos fijos y conteos aleatorios. NO aplica
    RN-04..RN-08: lo reemplaza `GestorEjecucion` cuando existan HU-05 y HU-06.
    """

    def __init__(self, duracion: float = DEMO_DURACION_SEG, semilla: int = DEMO_SEMILLA) -> None:
        self._duracion = duracion
        self._azar = random.Random(semilla)
        self._n_tick = 0
        self._ultimos_estados: dict[int, EstadoSemaforo] | None = None

    @property
    def marca_tiempo(self) -> float:
        """Segundos del video simulado."""
        return min(self._n_tick * DEMO_PASO_SEG, self._duracion)

    @property
    def terminado(self) -> bool:
        return self.marca_tiempo >= self._duracion

    @staticmethod
    def estados_en(marca_tiempo: float) -> dict[int, EstadoSemaforo]:
        """Estados de los carriles en un instante del ciclo de demostración."""
        vuelta, resto = divmod(marca_tiempo, DEMO_VERDE_SEG + DEMO_AMARILLO_SEG)
        activo = POSICIONES_CARRIL[int(vuelta) % NUM_CARRILES]
        estado_activo = EstadoSemaforo.VERDE if resto < DEMO_VERDE_SEG else EstadoSemaforo.AMARILLO
        return {p: estado_activo if p == activo else EstadoSemaforo.ROJO for p in POSICIONES_CARRIL}

    def avanzar(self) -> list[MensajeInterfaz]:
        """Avanza un paso de video y devuelve los mensajes que publicaría el núcleo."""
        self._n_tick += 1
        t = self.marca_tiempo
        mensajes: list[MensajeInterfaz] = []
        estados = self.estados_en(t)
        if estados != self._ultimos_estados:
            mensajes.append(CambioFase(t, estados))
            self._ultimos_estados = estados
        if (self._n_tick - 1) % DEMO_TICKS_POR_INTERVALO == 0:
            mensajes.extend(self._conteos_aleatorios())
        estado = EstadoEjecucion.FINALIZADA if self.terminado else EstadoEjecucion.EN_EJECUCION
        mensajes.append(ProgresoEjecucion(t, self._duracion, estado))
        return mensajes

    def _conteos_aleatorios(self) -> list[ActualizacionCarril]:
        return [
            ActualizacionCarril(p, {c: self._azar.randint(0, DEMO_MAX_POR_CLASE) for c in Clase})
            for p in POSICIONES_CARRIL
        ]


class BotonPlano(tk.Button):
    """Botón plano con efecto al pasar el mouse; deshabilitado se ve gris."""

    def __init__(self, padre: tk.Misc, texto: str, comando: Callable[[], None],
                 primario: bool = False) -> None:
        self._fondo = COLOR_ACENTO if primario else COLOR_SUPERFICIE
        self._fondo_hover = COLOR_ACENTO_HOVER if primario else COLOR_SUPERFICIE_HOVER
        super().__init__(
            padre, text=texto, command=comando, font=(FUENTE, 10, "bold" if primario else "normal"),
            bg=self._fondo, fg=COLOR_TEXTO, activebackground=self._fondo_hover,
            activeforeground=COLOR_TEXTO, disabledforeground=COLOR_TEXTO_SUAVE,
            relief="flat", bd=0, padx=14, pady=6, cursor="hand2",
        )
        self.bind("<Enter>", lambda _evento: self._pintar(hover=True))
        self.bind("<Leave>", lambda _evento: self._pintar(hover=False))

    @property
    def habilitado(self) -> bool:
        return self["state"] != "disabled"

    def habilitar(self, habilitado: bool) -> None:
        """Activa o desactiva el botón y ajusta su color."""
        self.configure(state="normal" if habilitado else "disabled",
                       cursor="hand2" if habilitado else "arrow")
        self._pintar(hover=False)

    def _pintar(self, hover: bool) -> None:
        if not self.habilitado:
            self.configure(bg=COLOR_SUPERFICIE)
        else:
            self.configure(bg=self._fondo_hover if hover else self._fondo)


class SemaforoVisual(tk.Canvas):
    """RF-08, RF-09: semáforo de un carril con tres luces."""

    def __init__(self, padre: tk.Misc, escala: float) -> None:
        ancho, alto = round(ANCHO_SEMAFORO * escala), round(ALTO_SEMAFORO * escala)
        super().__init__(padre, width=ancho, height=alto, bg=COLOR_TARJETA, highlightthickness=0)
        self._luces: dict[EstadoSemaforo, int] = {}
        self._halos: dict[EstadoSemaforo, int] = {}
        self._dibujar(ancho, alto, escala)
        self.mostrar_estado(EstadoSemaforo.ROJO)

    def _dibujar(self, ancho: int, alto: int, escala: float) -> None:
        margen = round(8 * escala)
        radio_borde = round(14 * escala)
        self._rectangulo_redondeado(1, 1, ancho - 1, alto - 1, radio_borde)
        diametro = ancho - 2 * margen
        separacion = (alto - 3 * diametro) / 4
        grosor_halo = max(2, round(2 * escala))
        for i, luz in enumerate(ORDEN_LUCES):
            y = separacion + i * (diametro + separacion)
            caja = (margen, y, margen + diametro, y + diametro)
            self._halos[luz] = self.create_oval(*caja, outline=COLOR_CARCASA, width=grosor_halo)
            interior = grosor_halo + round(2 * escala)
            self._luces[luz] = self.create_oval(
                caja[0] + interior, caja[1] + interior, caja[2] - interior, caja[3] - interior, width=0,
            )

    def _rectangulo_redondeado(self, x1: float, y1: float, x2: float, y2: float, r: float) -> None:
        puntos = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
                  x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        self.create_polygon(puntos, smooth=True, fill=COLOR_CARCASA, outline="")

    def mostrar_estado(self, estado: EstadoSemaforo) -> None:
        """Enciende la luz del estado recibido y apaga las demás."""
        for luz in ORDEN_LUCES:
            self.itemconfigure(self._luces[luz], fill=color_luz(luz, estado))
            halo = LUZ_ENCENDIDA[luz] if luz is estado else COLOR_CARCASA
            self.itemconfigure(self._halos[luz], outline=halo)


class TarjetaCarril(tk.Frame):
    """Tarjeta de un carril: video, semáforo, conteo por clase y acciones."""

    def __init__(self, padre: tk.Misc, posicion: int, escala: float) -> None:
        super().__init__(padre, bg=COLOR_TARJETA, highlightthickness=2,
                         highlightbackground=COLOR_TARJETA, padx=14, pady=12)
        self.posicion = posicion
        self.ruta_video: Path | None = None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._crear_encabezado()
        self._crear_cuerpo(escala)
        self._crear_conteos()
        self._crear_acciones()

    def _crear_encabezado(self) -> None:
        encabezado = tk.Frame(self, bg=COLOR_TARJETA)
        encabezado.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        tk.Label(encabezado, text=f"Carril {self.posicion}", font=(FUENTE, 13, "bold"),
                 bg=COLOR_TARJETA, fg=COLOR_TEXTO).pack(side="left")
        self._etiqueta_estado = tk.Label(encabezado, font=(FUENTE, 9, "bold"), bg=COLOR_SUPERFICIE,
                                         padx=10, pady=2)
        self._etiqueta_estado.pack(side="right")

    def _crear_cuerpo(self, escala: float) -> None:
        cuerpo = tk.Frame(self, bg=COLOR_TARJETA)
        cuerpo.grid(row=1, column=0, sticky="nsew")
        cuerpo.columnconfigure(0, weight=1)
        cuerpo.rowconfigure(0, weight=1)
        self._lienzo_video = tk.Canvas(cuerpo, bg=COLOR_TARJETA, highlightthickness=0,
                                       height=round(ALTO_SEMAFORO * escala))
        self._lienzo_video.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self._lienzo_video.bind("<Configure>", lambda _e: self._dibujar_video())
        self.semaforo = SemaforoVisual(cuerpo, escala)
        self.semaforo.grid(row=0, column=1)

    def _crear_conteos(self) -> None:
        fila = tk.Frame(self, bg=COLOR_TARJETA)
        fila.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        self._valores: dict[str, tk.Label] = {}
        etiquetas = [*ETIQUETA_CLASE.values(), "Demanda"]
        for i, nombre in enumerate(etiquetas):
            fila.columnconfigure(i, weight=1, uniform="conteo")
            celda = tk.Frame(fila, bg=COLOR_SUPERFICIE, padx=8, pady=6)
            celda.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0))
            tk.Label(celda, text=nombre, font=(FUENTE, 8), bg=COLOR_SUPERFICIE,
                     fg=COLOR_TEXTO_SUAVE).pack(anchor="w")
            valor = tk.Label(celda, text="—", font=(FUENTE, 15, "bold"), bg=COLOR_SUPERFICIE,
                             fg=COLOR_TEXTO)
            valor.pack(anchor="w")
            self._valores[nombre] = valor

    def _crear_acciones(self) -> None:
        fila = tk.Frame(self, bg=COLOR_TARJETA)
        fila.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        BotonPlano(fila, "Cargar mp4", self._seleccionar_video).pack(side="left")
        zona = BotonPlano(fila, "Trazar zona", lambda: None)
        zona.habilitar(False)
        zona.pack(side="left", padx=(8, 0))

    def _seleccionar_video(self) -> None:
        """HU-01 (parcial): elegir el mp4 del carril; la apertura se valida en HU-01."""
        seleccion = filedialog.askopenfilename(
            title=f"Video del carril {self.posicion}", filetypes=[("Video MP4", "*.mp4")],
        )
        if not seleccion:
            return
        ruta = Path(seleccion)
        if ruta.suffix.lower() != ".mp4":
            messagebox.showerror("Video no admitido", f"«{ruta.name}» no es un archivo mp4 (RN-01).")
            return
        self.ruta_video = ruta
        registro.info("Carril %d: video seleccionado %s", self.posicion, ruta)
        self._dibujar_video()

    def _dibujar_video(self) -> None:
        lienzo = self._lienzo_video
        lienzo.delete("all")
        x1, y1, x2, y2 = rectangulo_video(lienzo.winfo_width(), lienzo.winfo_height())
        lienzo.create_rectangle(x1, y1, x2, y2, fill=COLOR_VIDEO, outline=COLOR_SUPERFICIE)
        centro_x, centro_y = (x1 + x2) / 2, (y1 + y2) / 2
        if self.ruta_video is None:
            titulo, detalle = "Sin video", "Cargá el mp4 de este carril"
        else:
            titulo, detalle = self.ruta_video.name, "Vista previa disponible con HU-01"
        lienzo.create_text(centro_x, centro_y - 10, text=titulo, fill=COLOR_TEXTO,
                           font=(FUENTE, 11, "bold"), width=max(x2 - x1 - 20, 1))
        lienzo.create_text(centro_x, centro_y + 14, text=detalle, fill=COLOR_TEXTO_SUAVE,
                           font=(FUENTE, 9))

    def mostrar_estado(self, estado: EstadoSemaforo) -> None:
        """RF-09 CA-03: refleja el estado del carril en el semáforo, la etiqueta y el borde."""
        color = LUZ_ENCENDIDA[estado]
        self.semaforo.mostrar_estado(estado)
        self._etiqueta_estado.configure(text=estado.value, fg=color)
        self.configure(highlightbackground=color if estado is EstadoSemaforo.VERDE else COLOR_TARJETA)

    def mostrar_conteo(self, actualizacion: ActualizacionCarril) -> None:
        """RF-09 CA-02: conteo vigente por clase y demanda total del carril."""
        for clase, nombre in ETIQUETA_CLASE.items():
            self._valores[nombre].configure(text=str(actualizacion.conteo.get(clase, 0)))
        self._valores["Demanda"].configure(text=str(actualizacion.demanda))


class InterfazPrincipal(tk.Tk):
    """Ventana principal del operador (CU-01, CU-02, CU-03)."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Semáforo inteligente · Cambyreta")
        self.geometry(TAMANO_VENTANA)
        self.minsize(*TAMANO_MINIMO)
        self.configure(bg=COLOR_FONDO)
        self.escala = self.winfo_fpixels("1i") / DPI_BASE
        self.cola: queue.Queue[MensajeInterfaz] = queue.Queue()
        self._simulador: SimuladorDemostracion | None = None
        self._pausado = False
        self._tick_pendiente: str | None = None
        self._configurar_estilos()
        self._crear_barra_lateral()
        self._crear_contenido()
        self.mostrar_vista("panel")
        self._mostrar_estado_ejecucion(EstadoEjecucion.CREADA)
        self.after(PERIODO_COLA_MS, self._procesar_cola)

    # --- Construcción ---------------------------------------------------------
    def _configurar_estilos(self) -> None:
        estilo = ttk.Style(self)
        estilo.theme_use("clam")
        estilo.configure("Semaforo.Horizontal.TProgressbar", troughcolor=COLOR_SUPERFICIE,
                         background=COLOR_ACENTO, bordercolor=COLOR_SUPERFICIE,
                         lightcolor=COLOR_ACENTO, darkcolor=COLOR_ACENTO,
                         thickness=round(6 * self.escala))

    def _crear_barra_lateral(self) -> None:
        barra = tk.Frame(self, bg=COLOR_BARRA, width=round(ANCHO_BARRA_LATERAL * self.escala))
        barra.pack(side="left", fill="y")
        barra.pack_propagate(False)
        tk.Label(barra, text="Semáforo", font=(FUENTE, 17, "bold"), bg=COLOR_BARRA,
                 fg=COLOR_TEXTO).pack(anchor="w", padx=22, pady=(24, 0))
        tk.Label(barra, text="Ruta 14 · Cambyreta", font=(FUENTE, 9), bg=COLOR_BARRA,
                 fg=COLOR_TEXTO_SUAVE).pack(anchor="w", padx=22, pady=(0, 24))
        self._entradas_menu: dict[str, tuple[tk.Frame, tk.Frame, tk.Label]] = {}
        for modulo in MODULOS:
            self._crear_entrada_menu(barra, modulo)
        tk.Label(barra, text="Prototipo · TFG UNAE", font=(FUENTE, 8), bg=COLOR_BARRA,
                 fg=COLOR_TEXTO_SUAVE).pack(side="bottom", anchor="w", padx=22, pady=18)

    def _crear_entrada_menu(self, barra: tk.Frame, modulo: Modulo) -> None:
        entrada = tk.Frame(barra, bg=COLOR_BARRA, cursor="hand2")
        entrada.pack(fill="x", padx=10, pady=1)
        indicador = tk.Frame(entrada, bg=COLOR_BARRA, width=3)
        indicador.pack(side="left", fill="y")
        texto = tk.Label(entrada, text=modulo.titulo, font=(FUENTE, 10), bg=COLOR_BARRA,
                         fg=COLOR_TEXTO_SUAVE, anchor="w", padx=12, pady=9)
        texto.pack(side="left", fill="x", expand=True)
        for widget in (entrada, texto):
            widget.bind("<Button-1>", lambda _e, clave=modulo.clave: self.mostrar_vista(clave))
            widget.bind("<Enter>", lambda _e, clave=modulo.clave: self._resaltar_menu(clave, True))
            widget.bind("<Leave>", lambda _e, clave=modulo.clave: self._resaltar_menu(clave, False))
        self._entradas_menu[modulo.clave] = (entrada, indicador, texto)

    def _crear_contenido(self) -> None:
        contenido = tk.Frame(self, bg=COLOR_FONDO, padx=24, pady=20)
        contenido.pack(side="left", fill="both", expand=True)
        encabezado = tk.Frame(contenido, bg=COLOR_FONDO)
        encabezado.pack(fill="x", pady=(0, 16))
        self._titulo_vista = tk.Label(encabezado, font=(FUENTE, 18, "bold"), bg=COLOR_FONDO,
                                      fg=COLOR_TEXTO)
        self._titulo_vista.pack(side="left")
        tk.Label(encabezado, text="Demostración con tiempos fijos · el motor de decisión "
                                  "se conecta en HU-05 y HU-06",
                 font=(FUENTE, 9), bg=COLOR_FONDO, fg=COLOR_TEXTO_SUAVE).pack(side="left", padx=18)
        self._etiqueta_ejecucion = tk.Label(encabezado, font=(FUENTE, 9, "bold"),
                                            bg=COLOR_SUPERFICIE, padx=12, pady=4)
        self._etiqueta_ejecucion.pack(side="right")
        apilado = tk.Frame(contenido, bg=COLOR_FONDO)
        apilado.pack(fill="both", expand=True)
        apilado.rowconfigure(0, weight=1)
        apilado.columnconfigure(0, weight=1)
        self._vistas: dict[str, tk.Frame] = {"panel": self._crear_vista_panel(apilado)}
        for modulo in MODULOS[1:]:
            self._vistas[modulo.clave] = self._crear_vista_pendiente(apilado, modulo)
        for vista in self._vistas.values():
            vista.grid(row=0, column=0, sticky="nsew")

    def _crear_vista_panel(self, padre: tk.Frame) -> tk.Frame:
        vista = tk.Frame(padre, bg=COLOR_FONDO)
        vista.rowconfigure(0, weight=1)
        self.tarjetas: dict[int, TarjetaCarril] = {}
        for i, posicion in enumerate(POSICIONES_CARRIL):
            vista.columnconfigure(i, weight=1, uniform="tarjeta")
            tarjeta = TarjetaCarril(vista, posicion, self.escala)
            tarjeta.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 14, 0))
            tarjeta.mostrar_estado(EstadoSemaforo.ROJO)
            self.tarjetas[posicion] = tarjeta
        self._crear_barra_control(vista).grid(row=1, column=0, columnspan=NUM_CARRILES,
                                              sticky="ew", pady=(16, 0))
        return vista

    def _crear_barra_control(self, padre: tk.Frame) -> tk.Frame:
        barra = tk.Frame(padre, bg=COLOR_TARJETA, padx=16, pady=12)
        self._boton_iniciar = BotonPlano(barra, "▶  Iniciar simulación", self._iniciar_demo,
                                         primario=True)
        self._boton_iniciar.pack(side="left")
        self._boton_pausar = BotonPlano(barra, "⏸  Pausar", self._alternar_pausa)
        self._boton_pausar.pack(side="left", padx=(8, 0))
        self._boton_detener = BotonPlano(barra, "■  Detener", self._detener_demo)
        self._boton_detener.pack(side="left", padx=(8, 0))
        self._etiqueta_tiempo = tk.Label(barra, text="00:00 / 00:00", font=(FUENTE, 11, "bold"),
                                         bg=COLOR_TARJETA, fg=COLOR_TEXTO)
        self._etiqueta_tiempo.pack(side="right")
        self._progreso = ttk.Progressbar(barra, style="Semaforo.Horizontal.TProgressbar",
                                         length=round(200 * self.escala), maximum=1.0)
        self._progreso.pack(side="right", padx=(0, 14))
        self._actualizar_botones(EstadoEjecucion.CREADA)
        return barra

    def _crear_vista_pendiente(self, padre: tk.Frame, modulo: Modulo) -> tk.Frame:
        vista = tk.Frame(padre, bg=COLOR_FONDO)
        tarjeta = tk.Frame(vista, bg=COLOR_TARJETA, padx=28, pady=24)
        tarjeta.pack(fill="x", anchor="n")
        tk.Label(tarjeta, text="Módulo en desarrollo", font=(FUENTE, 9, "bold"), bg=COLOR_TARJETA,
                 fg=LUZ_ENCENDIDA[EstadoSemaforo.AMARILLO]).pack(anchor="w")
        tk.Label(tarjeta, text=modulo.titulo, font=(FUENTE, 15, "bold"), bg=COLOR_TARJETA,
                 fg=COLOR_TEXTO).pack(anchor="w", pady=(6, 4))
        tk.Label(tarjeta, text=modulo.descripcion, font=(FUENTE, 10), bg=COLOR_TARJETA,
                 fg=COLOR_TEXTO_SUAVE, justify="left",
                 wraplength=round(720 * self.escala)).pack(anchor="w")
        return vista

    # --- Navegación -----------------------------------------------------------
    def mostrar_vista(self, clave: str) -> None:
        """Muestra el módulo elegido en la barra lateral."""
        self._vista_actual = clave
        self._vistas[clave].tkraise()
        titulos = {m.clave: m.titulo for m in MODULOS}
        self._titulo_vista.configure(text=titulos[clave])
        for otra in self._entradas_menu:
            self._resaltar_menu(otra, False)

    def _resaltar_menu(self, clave: str, hover: bool) -> None:
        entrada, indicador, texto = self._entradas_menu[clave]
        activa = clave == self._vista_actual
        fondo = COLOR_SUPERFICIE if activa or hover else COLOR_BARRA
        entrada.configure(bg=fondo)
        texto.configure(bg=fondo, fg=COLOR_TEXTO if activa or hover else COLOR_TEXTO_SUAVE,
                        font=(FUENTE, 10, "bold" if activa else "normal"))
        indicador.configure(bg=COLOR_ACENTO if activa else fondo)

    # --- Recepción de mensajes del núcleo ---------------------------------------
    def _procesar_cola(self) -> None:
        """Vacía la cola en el hilo de tkinter (nunca se tocan widgets desde otro hilo)."""
        try:
            while True:
                self._aplicar_mensaje(self.cola.get_nowait())
        except queue.Empty:
            pass
        self.after(PERIODO_COLA_MS, self._procesar_cola)

    def _aplicar_mensaje(self, mensaje: MensajeInterfaz) -> None:
        match mensaje:
            case CambioFase(estados=estados):
                self.mostrar_estados(estados)
            case ActualizacionCarril():
                self.tarjetas[mensaje.posicion].mostrar_conteo(mensaje)
            case ProgresoEjecucion():
                self._mostrar_progreso(mensaje)

    def mostrar_estados(self, estados: dict[int, EstadoSemaforo]) -> None:
        """RF-09 CA-03: punto de conexión con el motor; muestra el estado de cada carril."""
        for posicion, estado in estados.items():
            self.tarjetas[posicion].mostrar_estado(estado)

    def _mostrar_progreso(self, progreso: ProgresoEjecucion) -> None:
        self._etiqueta_tiempo.configure(
            text=f"{formatear_tiempo(progreso.marca_tiempo)} / {formatear_tiempo(progreso.duracion)}")
        self._progreso.configure(value=progreso.marca_tiempo / progreso.duracion)
        if not self._pausado:
            self._mostrar_estado_ejecucion(progreso.estado)

    def _mostrar_estado_ejecucion(self, estado: EstadoEjecucion) -> None:
        self._etiqueta_ejecucion.configure(text=f"●  {ETIQUETA_EJECUCION[estado]}",
                                           fg=COLOR_EJECUCION[estado])
        self._actualizar_botones(estado)

    def _actualizar_botones(self, estado: EstadoEjecucion) -> None:
        activa = estado in (EstadoEjecucion.EN_EJECUCION, EstadoEjecucion.PAUSADA)
        self._boton_iniciar.habilitar(not activa)
        self._boton_pausar.habilitar(activa)
        self._boton_pausar.configure(text="▶  Reanudar" if self._pausado else "⏸  Pausar")
        self._boton_detener.habilitar(activa)

    # --- Demostración ---------------------------------------------------------
    def _iniciar_demo(self) -> None:
        self._simulador = SimuladorDemostracion()
        self._pausado = False
        self._programar_tick()

    def _programar_tick(self) -> None:
        self._tick_pendiente = self.after(DEMO_TICK_MS, self._tick_demo)

    def _tick_demo(self) -> None:
        if self._simulador is None or self._pausado:
            return
        for mensaje in self._simulador.avanzar():
            self.cola.put(mensaje)
        if not self._simulador.terminado:
            self._programar_tick()

    def _cancelar_tick(self) -> None:
        if self._tick_pendiente is not None:
            self.after_cancel(self._tick_pendiente)
            self._tick_pendiente = None

    def _alternar_pausa(self) -> None:
        self._pausado = not self._pausado
        estado = EstadoEjecucion.PAUSADA if self._pausado else EstadoEjecucion.EN_EJECUCION
        self._mostrar_estado_ejecucion(estado)
        if self._pausado:
            self._cancelar_tick()
        else:
            self._programar_tick()

    def _detener_demo(self) -> None:
        self._cancelar_tick()
        self._simulador = None
        self._pausado = False
        self._mostrar_estado_ejecucion(EstadoEjecucion.ABORTADA)


def _activar_dpi() -> None:
    """Evita que Windows escale la ventana como mapa de bits (texto borroso)."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        registro.debug("No se pudo activar el modo DPI (no es Windows 8.1+).")


def iniciar_interfaz() -> None:
    """Abre la ventana principal y entrega el control al bucle de tkinter."""
    _activar_dpi()
    InterfazPrincipal().mainloop()
