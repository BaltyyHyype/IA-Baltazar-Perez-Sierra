import os
import csv
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pygame
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler


import matplotlib

try:
    matplotlib.use("TkAgg")
except Exception:
    try:
        matplotlib.use("Qt5Agg")
    except Exception:
        pass  # Usa el backend por defecto
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401, necesario para activar 3D en matplotlib


plt.ion()


# Ventana base y factor de escala
BASE_W, BASE_H = 1080, 720
WINDOW_FRACTION = 0.97
EXTRA_SCALE = 1.1


@dataclass
class Sample:
    velocidad_bala: float
    distancia: float
    altura_bala: float       
    vel_jugador_y: float      
    estado_jugador: int       
    frames_en_estado: int     
    accion: int               


class Juego:
    def __init__(self) -> None:
        pygame.init()

        # Ventana fija sin redimensionamiento automático
        
        self._flags = 0
        self._fullscreen = False

        # Tamaño fijo de ventana
        start_w = BASE_W
        start_h = BASE_H
        self.pantalla = pygame.display.set_mode((start_w, start_h), self._flags)
        pygame.display.set_caption("Juego: Bala + salto + agacharse + MLP")


        self.BLANCO = (255, 255, 255)
        self.NEGRO = (0, 0, 0)
        self.GRIS = (200, 200, 200)
        self.AMARILLO = (255, 220, 120)
        self.VERDE_CHIDO = (50, 255, 150)


        self.corriendo = True
        self.modo_auto = False
        self.score = 0

        # Datos / modelo
        self.datos_modelo: List[Sample] = []
        self.modelo: Optional[MLPClassifier] = None
        self.scaler: Optional[StandardScaler] = None
        self.modelo_entrenado = False
        
        # Caso especial: cuando solo hay una clase en los datos
        self.clase_unica: Optional[int] = None
        # Debug / info del modelo en tiempo real
        self.ultima_accion_predicha: Optional[int] = None
        self.ultima_proba: Optional[float] = None

        # Parámetros de decisión
        self.decision_window = 500
        self.decision_record_every = 3
        self._decision_frame_counter = 0

        # Geometría / física (se rellenan en _apply_resolution)
        self.w, self.h = start_w, start_h
        self.scale = 1.0
        self.margin = 50
        self.ground_y = self.h - 100
        self.player_size = (32, 48)
        self.bullet_size = (16, 16)
        self.ship_size = (64, 64)
        # Velocidad de desplazamiento del fondo
        self.fondo_speed = 3

        self.salto = False
        self.en_suelo = True
        self.salto_vel_inicial = 15.0
        self.gravedad = 1.0
        self.salto_vel = self.salto_vel_inicial

        # Agacharse: el jugador reduce su hitbox a la mitad inferior
        self.agachado = False
        # Indica si la bala actual viaja a altura alta (hay que agacharse) o baja (hay que saltar)
        self.bala_alta = False

        self.current_frame = 0
        self.frame_speed = 10
        self.frame_count = 0

        # Velocidad base de la bala
        self.velocidad_bala = -12
        self.bala_disparada = False

        # Seguimiento dinámico del jugador
        self._jugador_y_prev: float = 0.0
        self._vel_jugador_y: float = 0.0
        self._estado_actual: int = 0       # 0=parado, 1=saltando, 2=agachado
        self._frames_en_estado: int = 0

        self.fondo_x1 = 0
        self.fondo_x2 = start_w

        self._apply_resolution(start_w, start_h, reset_positions=True)
        self._reset_estado_juego()

    # ----------------- resolución / assets -----------------
    def _apply_resolution(self, w: int, h: int, reset_positions: bool) -> None:
        self.w, self.h = int(w), int(h)

        self.scale = min(self.w / BASE_W, self.h / BASE_H) * EXTRA_SCALE
        self.scale = max(1.0, self.scale)

        self.margin = int(50 * self.scale)
        ground_offset = int(100 * self.scale)
        self.ground_y = self.h - ground_offset

        self.player_size = (int(32 * self.scale), int(48 * self.scale))
        self.bullet_size = (int(16 * self.scale), int(16 * self.scale))
        self.ship_size = (int(64 * self.scale), int(64 * self.scale))
        self.fondo_speed = max(1, int(2 * self.scale))

        self.salto_vel_inicial = 15 * self.scale
        self.gravedad = 1 * self.scale
        self.salto_vel = self.salto_vel_inicial

        self.decision_window = int(500 * self.scale)

        self.fuente = pygame.font.SysFont("Arial", int(24 * self.scale))
        self.fuente_chica = pygame.font.SysFont("Arial", int(18 * self.scale))

        self._cargar_assets()

        if reset_positions or not hasattr(self, "jugador"):
            self.jugador = pygame.Rect(self.margin, self.ground_y, self.player_size[0], self.player_size[1])
            self.bala = pygame.Rect(
                self.w - self.margin,
                self._bala_y_baja(),
                self.bullet_size[0],
                self.bullet_size[1],
            )
            self.nave = pygame.Rect(
                self.w - int(100 * self.scale),
                self.ground_y,
                self.ship_size[0],
                self.ship_size[1],
            )

    def _cargar_assets(self) -> None:
        def safe_load(path: str, size: Tuple[int, int], fallback_color=(200, 200, 200, 255)) -> pygame.Surface:
            try:
                img = pygame.image.load(path).convert_alpha()
                return pygame.transform.smoothscale(img, size)
            except Exception:
                surf = pygame.Surface(size, pygame.SRCALPHA)
                surf.fill(fallback_color)
                return surf

        base = os.path.dirname(__file__)
        self.jugador_frames = [
            safe_load(os.path.join(base, "assets/sprites/mono_frame_1.png"), self.player_size),
            safe_load(os.path.join(base, "assets/sprites/mono_frame_2.png"), self.player_size),
            safe_load(os.path.join(base, "assets/sprites/mono_frame_3.png"), self.player_size),
            safe_load(os.path.join(base, "assets/sprites/mono_frame_4.png"), self.player_size),
        ]
        self.bala_img = safe_load(
            os.path.join(base, "assets/sprites/purple_ball.png"),
            self.bullet_size,
            (160, 120, 255, 255),
        )
        self.fondo_img = safe_load(
            os.path.join(base, "assets/game/fondo2.png"),
            (self.w, self.h),
            (40, 40, 40, 255),
        )
        self.nave_img = safe_load(
            os.path.join(base, "assets/game/ufo.png"),
            self.ship_size,
            (140, 255, 200, 255),
        )
        self.fondo_menu_img = safe_load(
            os.path.join(base, "assets/game/fondodemenu.png"),
            (self.w, self.h),
            (20, 40, 30, 255),
        )

    def _toggle_fullscreen(self) -> None:
        self._fullscreen = not self._fullscreen
        if self._fullscreen:
            info = pygame.display.Info()
            w = info.current_w or self.w
            h = info.current_h or self.h
            self.pantalla = pygame.display.set_mode((w, h), pygame.FULLSCREEN)
            self._apply_resolution(w, h, reset_positions=True)
        else:
            self.pantalla = pygame.display.set_mode((BASE_W, BASE_H), self._flags)
            self._apply_resolution(BASE_W, BASE_H, reset_positions=True)
        self._reset_estado_juego()

    # ----------------- estado juego / modelo -----------------
    def _reset_estado_juego(self) -> None:
        self.jugador.x = self.margin
        self.jugador.y = self.ground_y
        self.jugador.width = self.player_size[0]
        self.jugador.height = self.player_size[1]
        self.nave.x, self.nave.y = self.w - int(100 * self.scale), self.ground_y
        self.bala.x = self.w - self.margin
        self.bala.y = self._bala_y_baja()
        self.bala_disparada = False
        self.velocidad_bala = int(-10 * self.scale)
        self.salto = False
        self.en_suelo = True
        self.salto_vel = self.salto_vel_inicial
        self.agachado = False
        self.bala_alta = False
        self._decision_frame_counter = 0
        self.fondo_x1 = 0
        self.fondo_x2 = self.w

        # Resetear seguimiento dinámico
        self._jugador_y_prev = float(self.ground_y)
        self._vel_jugador_y = 0.0
        self._estado_actual = 0
        self._frames_en_estado = 0
        self.score = 0

    def _reset_modelo(self) -> None:
        self.modelo = None
        self.scaler = None
        self.modelo_entrenado = False
        self.clase_unica = None

    # ----------------- alturas de bala -----------------
    def _bala_y_baja(self) -> int:
        return self.ground_y + self.player_size[1] - self.bullet_size[1]

    def _bala_y_alta(self) -> int:
        return self.ground_y + int(4 * self.scale)

    # ----------------- bala / salto / agacharse -----------------
    def disparar_bala(self) -> None:
        if not self.bala_disparada:
            self.velocidad_bala = int(random.randint(-12, -6) * self.scale)
            self.bala_alta = random.random() < 0.5
            self.bala.y = self._bala_y_alta() if self.bala_alta else self._bala_y_baja()
            self.bala_disparada = True

    def reset_bala(self) -> None:
        self.bala.x = self.w - self.margin
        self.bala_disparada = False
        self.bala_alta = False

    def iniciar_salto(self) -> None:
        if self.en_suelo and not self.agachado:
            self.salto = True
            self.en_suelo = False

    def manejar_salto(self) -> None:
        if self.salto:
            self.jugador.y -= int(self.salto_vel)
            self.salto_vel -= self.gravedad
            if self.jugador.y >= self.ground_y:
                self.jugador.y = self.ground_y
                self.salto = False
                self.salto_vel = self.salto_vel_inicial
                self.en_suelo = True

    def iniciar_agacharse(self) -> None:
        if self.en_suelo and not self.salto:
            if not self.agachado:
                self.agachado = True
                self.jugador.y = self.ground_y + self.player_size[1] // 2
                self.jugador.height = self.player_size[1] // 2

    def terminar_agacharse(self) -> None:
        if self.agachado:
            self.agachado = False
            self.jugador.y = self.ground_y
            self.jugador.height = self.player_size[1]

    # ----------------- seguimiento dinámico -----------------
    def _actualizar_estado_dinamico(self) -> None:
        self._vel_jugador_y = float(self.jugador.y) - self._jugador_y_prev
        self._jugador_y_prev = float(self.jugador.y)

        if self.salto or not self.en_suelo:
            nuevo_estado = 1
        elif self.agachado:
            nuevo_estado = 2
        else:
            nuevo_estado = 0

        if nuevo_estado == self._estado_actual:
            self._frames_en_estado += 1
        else:
            self._estado_actual = nuevo_estado
            self._frames_en_estado = 0

    # ----------------- export / gráficas -----------------
    def exportar_datos_csv(self) -> str:
        if not self.datos_modelo:
            return "No hay datos para exportar."

        base = os.path.dirname(__file__)
        ruta = os.path.join(base, "datos_mlp.csv")

        try:
            with open(ruta, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "velocidad_bala", "distancia", "altura_bala",
                    "vel_jugador_y", "estado_jugador", "frames_en_estado",
                    "accion",
                ])
                for s in self.datos_modelo:
                    writer.writerow([
                        s.velocidad_bala, s.distancia, s.altura_bala,
                        s.vel_jugador_y, s.estado_jugador, s.frames_en_estado,
                        s.accion,
                    ])
        except Exception as e:
            return f"Error al guardar CSV: {e}"

        return f"CSV guardado en datos_mlp.csv ({len(self.datos_modelo)} filas)."

    def graficar_datos_2d(self) -> str:
        if not self.datos_modelo:
            return "No hay datos para graficar."

        xs = [s.distancia for s in self.datos_modelo]
        ys = [s.velocidad_bala for s in self.datos_modelo]
        _col = {0: "blue", 1: "green", 2: "red"}
        cs = [_col.get(s.accion, "gray") for s in self.datos_modelo]
        ms = ["^" if s.altura_bala == 1.0 else "o" for s in self.datos_modelo]

        fig_num = plt.figure("Datos MLP - 2D", figsize=(9, 6)).number
        plt.figure(fig_num)
        plt.clf()
        ax = plt.gca()

        for x, y, c, m in zip(xs, ys, cs, ms):
            ax.scatter(x, y, c=c, marker=m, alpha=0.6, edgecolors="k", s=35)

        legend = [
            Line2D([0], [0], marker="o", color="w", markerfacecolor="blue",  markersize=9, label="0 - nada"),
            Line2D([0], [0], marker="o", color="w", markerfacecolor="green", markersize=9, label="1 - salto"),
            Line2D([0], [0], marker="o", color="w", markerfacecolor="red",   markersize=9, label="2 - agachado"),
            Line2D([0], [0], marker="o", color="w", markerfacecolor="gray",  markersize=9, label="bala baja ○"),
            Line2D([0], [0], marker="^", color="w", markerfacecolor="gray",  markersize=9, label="bala alta ▲"),
        ]
        ax.legend(handles=legend, loc="upper right", fontsize=9)
        ax.set_xlabel("Distancia jugador-bala")
        ax.set_ylabel("Velocidad bala")
        ax.set_title("Datos entrenamiento MLP 2D")
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show(block=False)
        plt.draw()

        return "Mostrando gráfica 2D interactiva."

    def graficar_datos_3d(self) -> str:
        if not self.datos_modelo:
            return "No hay datos para graficar."

        xs = [s.distancia for s in self.datos_modelo]
        ys = [s.velocidad_bala for s in self.datos_modelo]
        zs = [s.altura_bala for s in self.datos_modelo]
        _col = {0: "blue", 1: "green", 2: "red"}
        cs = [_col.get(s.accion, "gray") for s in self.datos_modelo]

        fig = plt.figure("Datos MLP - 3D", figsize=(9, 6))
        plt.clf()
        ax = fig.add_subplot(111, projection="3d")
        ax.scatter(xs, ys, zs, c=cs, alpha=0.6, edgecolors="k", s=30)
        ax.set_xlabel("Distancia")
        ax.set_ylabel("Velocidad bala")
        ax.set_zlabel("Altura bala (0=baja, 1=alta)")
        ax.set_title("Datos MLP 3D  (azul=nada, verde=salto, rojo=agachado)")
        plt.tight_layout()
        plt.show(block=False)
        plt.draw()

        return "Mostrando gráfica 3D interactiva."

    # ----------------- datos / ML -----------------
    def registrar_decision_manual(self) -> None:
        if not self.bala_disparada:
            self.datos_modelo.append(Sample(
                velocidad_bala=0.0,
                distancia=float(self.w),
                altura_bala=1.0 if self.bala_alta else 0.0,
                vel_jugador_y=self._vel_jugador_y,
                estado_jugador=self._estado_actual,
                frames_en_estado=self._frames_en_estado,
                accion=0,
            ))
            return

        distancia = float(abs(self.jugador.x - self.bala.x))
        altura_bala = 1.0 if self.bala_alta else 0.0

        if self.salto or not self.en_suelo:
            accion = 1
        elif self.agachado:
            accion = 2
        else:
            accion = 0

        self.datos_modelo.append(Sample(
            velocidad_bala=float(self.velocidad_bala),
            distancia=distancia,
            altura_bala=altura_bala,
            vel_jugador_y=self._vel_jugador_y,
            estado_jugador=self._estado_actual,
            frames_en_estado=self._frames_en_estado,
            accion=accion,
        ))

    def entrenar_modelo(self) -> Tuple[bool, str]:
        samples = list(self.datos_modelo)
        if len(samples) < 80:
            return False, "Necesitas más datos (>= 80). Juega en MANUAL."

        nada = [s for s in samples if s.accion == 0]
        saltar = [s for s in samples if s.accion == 1]
        agachar = [s for s in samples if s.accion == 2]

        
        total_movimientos = len(saltar) + len(agachar)
        
        if total_movimientos > 0:
            umbral_ruido = 0.15 
            porcentaje_salto = len(saltar) / total_movimientos
            porcentaje_agachar = len(agachar) / total_movimientos


            if porcentaje_salto < umbral_ruido and len(saltar) > 0:
                samples = [s for s in samples if s.accion != 1]
                saltar = []
                print("se tiene que saltar mas para capturar la inforacion")

            if porcentaje_agachar < umbral_ruido and len(agachar) > 0:
                samples = [s for s in samples if s.accion != 2]
                agachar = []
                print("se tiene que agachar mas para capturar la informacion")

        # ── Oversampling de inicios ──.     desba
        def oversamplear_inicios(grupo: List[Sample]) -> List[Sample]:
            inicios = [s for s in grupo if s.estado_jugador == 0]
            sostenidos = [s for s in grupo if s.estado_jugador != 0]
            if not inicios or not sostenidos:
                return grupo
            factor = max(1, len(sostenidos) // len(inicios))
            inicios_ampliados = inicios * factor
            return inicios_ampliados + sostenidos

        if saltar:
            saltar = oversamplear_inicios(saltar)
        if agachar:
            agachar = oversamplear_inicios(agachar)

        # ── Balanceo dinámico entre las clases sobrevivientes ──
        grupos = [g for g in [nada, saltar, agachar] if len(g) > 0]
        if not grupos:
            return False, "No hay datos válidos tras aplicar el filtro."
            
        min_size = min(len(g) for g in grupos)

        nada = random.sample(nada, min(len(nada), min_size)) if nada else []
        saltar = random.sample(saltar, min(len(saltar), min_size)) if saltar else []
        agachar = random.sample(agachar, min(len(agachar), min_size)) if agachar else []

        samples = nada + saltar + agachar
        random.shuffle(samples)

        X = [[
            s.velocidad_bala, s.distancia, s.altura_bala, s.vel_jugador_y,
            float(s.estado_jugador), float(s.frames_en_estado)

        ] for s in samples]


        
        y = [s.accion for s in samples]
        clases = sorted(set(y))

        if len(clases) < 2:
            self._reset_modelo()
            self.clase_unica = int(clases[0])
            self.modelo_entrenado = True
            nombres = {0: "NADA", 1: "SALTAR", 2: "AGACHARSE"}
            return True, f"Modelo filtrado: siempre {nombres[self.clase_unica]}."

        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
        except ValueError:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_test = scaler.transform(X_test)

        clf = MLPClassifier(
            hidden_layer_sizes=(32, 16),
            activation="relu",
            solver="adam",
            max_iter=500000,
            random_state=42,
        )

        clf.fit(X_train, y_train)

        acc = clf.score(X_test, y_test)

        self._reset_modelo()
        self.scaler = scaler
        self.modelo = clf # guar pesso
        self.modelo_entrenado = True
        return True, f"MLP entrenado correctamente. Accuracy ≈ {acc:.3f}"

    def decision_auto_accion(self) -> int:
        if not self.modelo_entrenado:
            return 0
        if not self.bala_disparada:
            return 0

        distancia = float(abs(self.jugador.x - self.bala.x))
        altura_bala = 1.0 if self.bala_alta else 0.0

        if self.clase_unica is not None and self.modelo is None:
            self.ultima_accion_predicha = self.clase_unica
            self.ultima_proba = 1.0
            return self.clase_unica

        if self.modelo is None or self.scaler is None:
            return 0

        X = [[
            float(self.velocidad_bala),
            distancia,
            altura_bala,
            self._vel_jugador_y,
            float(self._estado_actual),
            float(self._frames_en_estado),
        ]]
        Xs = self.scaler.transform(X)
        pred = int(self.modelo.predict(Xs)[0])
        if hasattr(self.modelo, "predict_proba"):
            probas = self.modelo.predict_proba(Xs)[0]
            self.ultima_proba = float(max(probas))
        else:
            self.ultima_proba = None
        self.ultima_accion_predicha = pred
        return pred

    # ----------------- menú -----------------
    def _dibujar_menu(self, msg: str = "") -> None:
        self.pantalla.blit(self.fondo_menu_img, (0, 0))
        capa_oscura = pygame.Surface((self.w, self.h))
        capa_oscura.fill(self.NEGRO)
        capa_oscura.set_alpha(140) 
        self.pantalla.blit(capa_oscura, (0, 0))

        titulo = self.fuente.render("MENÚ", True, self.BLANCO)
        self.pantalla.blit(titulo, (self.w // 2 - titulo.get_width() // 2, int(60 * self.scale)))

        opciones = [
            "M - Manual (reinicia dataset y borra modelo)",
            "A - Auto (usa MLP; sin modelo NO actúa)",
            "T - Entrenar MLP",
            "C - Exportar datos a CSV",
            "G - Gráfica 2D  |  H - Gráfica 3D",
            "F - Fullscreen (toggle)",
            "Q - Salir",
            "",
        ]
        x0 = int(80 * self.scale)
        y = int(130 * self.scale)
        line_h = self.fuente.get_linesize()
        pad = max(6, int(6 * self.scale))
        for op in opciones:
            color = self.GRIS if op == "" else self.BLANCO
            t = self.fuente.render(op, True, color)
            self.pantalla.blit(t, (x0, y))
            y += line_h + pad

        y += int(8 * self.scale)
        estado = [
            f"Memoria: {len(self.datos_modelo)} | Modelo: {'sí' if self.modelo_entrenado else 'no'}",
            f"Resolución: {self.w}x{self.h} | scale≈{self.scale:.2f} | ventana_decisión≈{self.decision_window}",
        ]
        for line in estado:
            t = self.fuente_chica.render(line, True, self.GRIS)
            self.pantalla.blit(t, (x0, y))
            y += self.fuente_chica.get_linesize()

        if msg:
            mm = self.fuente_chica.render(msg, True, self.AMARILLO)
            self.pantalla.blit(mm, (x0, y + int(12 * self.scale)))

        pygame.display.flip()

    def mostrar_menu(self) -> None:
        msg = ""
        esperando = True
        self._decision_frame_counter = 0
        while esperando and self.corriendo:
            self._dibujar_menu(msg)
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.corriendo = False
                    esperando = False
                    break
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_m:
                        self.modo_auto = False
                        self.datos_modelo.clear()
                        self._reset_modelo()
                        self._reset_estado_juego()
                        esperando = False
                        break
                    if e.key == pygame.K_a:
                        if not self.modelo_entrenado:
                            msg = "Primero entrena el MLP (T) en esta sesión."
                        else:
                            self.modo_auto = True
                            self._reset_estado_juego()
                            esperando = False
                            break
                    if e.key == pygame.K_t:
                        ok, info = self.entrenar_modelo()
                        msg = info if ok else f"Error: {info}"
                    if e.key == pygame.K_c:
                        msg = self.exportar_datos_csv()
                    if e.key == pygame.K_g:
                        msg = self.graficar_datos_2d()
                    if e.key == pygame.K_h:
                        msg = self.graficar_datos_3d()
                    if e.key == pygame.K_f:
                        self._toggle_fullscreen()
                    if e.key == pygame.K_q:
                        self.corriendo = False
                        esperando = False
                        return

    # ----------------- render / loop -----------------
    def _update_frame(self) -> None:
        self.fondo_x1 -= self.fondo_speed
        self.fondo_x2 -= self.fondo_speed
        if self.fondo_x1 <= -self.w:
            self.fondo_x1 = self.w
        if self.fondo_x2 <= -self.w:
            self.fondo_x2 = self.w
        self.pantalla.blit(self.fondo_img, (self.fondo_x1, 0))
        self.pantalla.blit(self.fondo_img, (self.fondo_x2, 0))

        self.frame_count += 1
        if self.frame_count >= self.frame_speed:
            self.current_frame = (self.current_frame + 1) % len(self.jugador_frames)
            self.frame_count = 0

        if self.agachado:
            frame_agachado = pygame.transform.scale(
                self.jugador_frames[self.current_frame],
                (self.player_size[0], self.player_size[1] // 2),
            )
            self.pantalla.blit(frame_agachado, (self.jugador.x, self.jugador.y))
        else:
            self.pantalla.blit(self.jugador_frames[self.current_frame], (self.jugador.x, self.jugador.y))

        self.pantalla.blit(self.nave_img, (self.nave.x, self.nave.y))

        if self.bala_disparada:
            self.bala.x += self.velocidad_bala
        if self.bala.x < -self.bullet_size[0]:
            self.score += 1  
            self.reset_bala()
            if self.agachado:
                self.terminar_agacharse()

        self.pantalla.blit(self.bala_img, (self.bala.x, self.bala.y))

        if self.jugador.colliderect(self.bala):
            self._reset_estado_juego()

        if self.modelo_entrenado and self.modo_auto and self.ultima_accion_predicha is not None:
            nombres = {0: "nada", 1: "salto", 2: "agachar"}
            nombre = nombres.get(self.ultima_accion_predicha, "?")
            proba_txt = f"  p={self.ultima_proba:.2f}" if self.ultima_proba is not None else ""
            txt = self.fuente_chica.render(f"acción={nombre}{proba_txt}", True, self.AMARILLO)
            self.pantalla.blit(txt, (10, 10))

        if self.bala_disparada:
            if self.bala_alta:
                aviso = self.fuente_chica.render("▲ BALA ALTA", True, (255, 100, 100))
            else:
                aviso = self.fuente_chica.render("▼ BALA BAJA", True, (100, 200, 255))
            self.pantalla.blit(aviso, (10, 35 if self.modo_auto else 10))

        fuente_gigante = pygame.font.SysFont("Arial", int(48 * self.scale), bold=True)
        texto_score = f"SCORE: {self.score}"
        score_surface = fuente_gigante.render(texto_score, True, self.VERDE_CHIDO)
        
        pos_x = (self.w // 2) - (score_surface.get_width() // 2)
        pos_y = int(20 * self.scale)  
        
        score_sombra = fuente_gigante.render(texto_score, True, self.NEGRO)
        self.pantalla.blit(score_sombra, (pos_x + 3, pos_y + 3)) 
        self.pantalla.blit(score_surface, (pos_x, pos_y))

    def loop(self) -> None:
        reloj = pygame.time.Clock()
        self.mostrar_menu()

        agachar_presionado = False

        while self.corriendo:
            self._actualizar_estado_dinamico()

            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.corriendo = False
                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_q:
                        self.corriendo = False
                    elif e.key in (pygame.K_ESCAPE, pygame.K_p):
                        self._reset_estado_juego()
                        self.terminar_agacharse()
                        self.mostrar_menu()
                        agachar_presionado = False
                    elif e.key == pygame.K_f:
                        self._toggle_fullscreen()
                    elif not self.modo_auto:
                        if e.key == pygame.K_SPACE and self.en_suelo and not self.agachado:
                            self.iniciar_salto()
                        elif e.key in (pygame.K_DOWN, pygame.K_s) and self.en_suelo:
                            agachar_presionado = True
                            self.iniciar_agacharse()
                elif e.type == pygame.KEYUP:
                    if not self.modo_auto and e.key in (pygame.K_DOWN, pygame.K_s):
                        agachar_presionado = False
                        self.terminar_agacharse()

            if not self.corriendo:
                break

            # ── Modo AUTO ─────────────────────────────────────────────────────
            if self.modo_auto:
                accion = self.decision_auto_accion()

                if accion == 1:
                    if self.en_suelo and not self.agachado:
                        self.iniciar_salto()
                elif accion == 2:
                    if self.en_suelo and not self.salto:
                        self.iniciar_agacharse()
                else:  # accion == 0 (nada)
                    if not self.salto and self.agachado:
                        self.terminar_agacharse()

            else:
                # ── Modo MANUAL ───────────────────────────────────────────────
                self.registrar_decision_manual()

                if not agachar_presionado and self.agachado and self.en_suelo and not self.salto:
                    self.terminar_agacharse()

            if self.salto:
                self.manejar_salto()

            if not self.bala_disparada:
                self.disparar_bala()

            self._update_frame()
            pygame.display.flip()
            reloj.tick(45)

        pygame.quit()


def main() -> None:
    Juego().loop()


if __name__ == "__main__":
    main()