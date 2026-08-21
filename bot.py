from __future__ import annotations

import ctypes
import time
from pathlib import Path

import cv2
import keyboard
import numpy as np

import win32api
import win32con
import win32gui
import win32ui
import psutil
import win32process

# =========================================================
# CONFIGURACION
# =========================================================

WINDOW_TITLE = "PokeMMO"

# Movimiento
MOVE_LEFT = "a"
MOVE_RIGHT = "d"

WALK_SECONDS = 1.5

# Controles globales del bot
PAUSE_KEY = "f8"
EXIT_KEY = "f9"
DEBUG_KEY = "f7"

# Frecuencia de deteccion
POLL_INTERVAL = 0.07

# ---------------------------------------------------------
# DETECCION
# ---------------------------------------------------------

BATTLE_MATCH_THRESHOLD = 0.68
HORDE_MATCH_THRESHOLD = 0.70
PP_ZERO_MATCH_THRESHOLD = 0.82

TEMPLATE_SCALES = (
    0.55,
    0.60,
    0.65,
    0.70,
    0.75,
    0.80,
    0.85,
    0.90,
    0.95,
    1.00,
    1.05,
    1.10,
    1.15,
    1.20,
    1.25,
    1.30,
    1.35,
    1.40,
)

# ---------------------------------------------------------
# TIEMPOS
# ---------------------------------------------------------

# LUCHA -> movimientos
AFTER_BATTLE_CLICK = 0.70

# movimiento -> posible seleccion de objetivo
AFTER_MOVE_CLICK_BEFORE_HORDE = 0.40

# cuanto esperamos a que aparezca la casilla de horda
HORDE_DETECTION_TIMEOUT = 1.30

# despues del doble click de horda
AFTER_HORDE_DOUBLE_CLICK = 1.30

# combate normal
AFTER_NORMAL_MOVE = 1.50

# evita repetir acciones
ATTACK_COOLDOWN = 1.40

DEBUG_INTERVAL = 1.0

# Confirmacion de vuelta al mundo tras un combate
BATTLE_END_TIMEOUT = 8.0
WORLD_CONFIRMATIONS = 3
WORLD_CHECK_INTERVAL = 0.15

# Seleccion automatica de movimiento segun PP
# Offsets relativos al tamano de la ventana cliente.
MOVE_COLUMN_OFFSET_RATIO = 0.155
MOVE_ROW_OFFSET_RATIO = 0.073
PP_CHECK_WAIT = 0.10


# =========================================================
# ARCHIVOS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

BATTLE_TEMPLATE_PATH = (
    BASE_DIR / "battle_button.png"
)

HORDE_TEMPLATE_PATH = (
    BASE_DIR / "horde_empty.png"
)

PP_ZERO_TEMPLATE_PATH = (
    BASE_DIR / "pp_zero.png"
)


# =========================================================
# WINDOWS
# =========================================================

# PrintWindow flag.
PW_RENDERFULLCONTENT = 0x00000002


# =========================================================
# CARGA DE PLANTILLAS
# =========================================================

def load_template(path: Path) -> np.ndarray:
    image = cv2.imread(
        str(path),
        cv2.IMREAD_GRAYSCALE,
    )

    if image is None:
        raise FileNotFoundError(
            f"No se pudo cargar: {path}"
        )

    print(
        f"Plantilla cargada: "
        f"{path.name} "
        f"({image.shape[1]}x{image.shape[0]})"
    )

    return image


BATTLE_TEMPLATE = load_template(
    BATTLE_TEMPLATE_PATH
)

HORDE_TEMPLATE = load_template(
    HORDE_TEMPLATE_PATH
)

PP_ZERO_TEMPLATE = load_template(
    PP_ZERO_TEMPLATE_PATH
)


# =========================================================
# BUSCAR POKEMMO
# =========================================================

def find_pokemmo_window() -> int:
    candidates = []

    print("\nBuscando ventanas de PokeMMO...")
    print("-----------------------------------------")

    def callback(hwnd, extra):
        if not win32gui.IsWindow(hwnd):
            return

        try:
            title = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)

            _, pid = win32process.GetWindowThreadProcessId(hwnd)

            process_name = ""

            try:
                process = psutil.Process(pid)
                process_name = process.name()
            except Exception:
                pass

            try:
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                width = right - left
                height = bottom - top
            except Exception:
                width = 0
                height = 0

            search_text = (
                title
                + " "
                + class_name
                + " "
                + process_name
            ).lower()

            if (
                "pokemmo" in search_text
                or "pokemon" in search_text
            ):
                print(
                    f"HWND={hwnd} | "
                    f"PID={pid} | "
                    f"EXE='{process_name}' | "
                    f"TITLE='{title}' | "
                    f"CLASS='{class_name}' | "
                    f"{width}x{height}"
                )

            if width < 400 or height < 300:
                return

            score = 0

            if "pokemmo" in title.lower():
                score += 100

            if "pokemmo" in process_name.lower():
                score += 100

            if "pokemmo" in class_name.lower():
                score += 50

            if "pokemon" in title.lower():
                score += 40

            if "java" in process_name.lower():
                score += 10

            if win32gui.IsWindowVisible(hwnd):
                score += 5

            if score > 0:
                candidates.append(
                    (
                        score,
                        hwnd,
                        title,
                        process_name,
                        class_name,
                        width,
                        height,
                    )
                )

        except Exception:
            pass

    win32gui.EnumWindows(
        callback,
        None,
    )

    if not candidates:
        print("\nNo se encontro automaticamente.")
        print("Mostrando ventanas grandes para diagnostico:\n")

        def debug_callback(hwnd, extra):
            try:
                if not win32gui.IsWindow(hwnd):
                    return

                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                width = right - left
                height = bottom - top

                if width < 600 or height < 400:
                    return

                title = win32gui.GetWindowText(hwnd)
                _, pid = win32process.GetWindowThreadProcessId(hwnd)

                try:
                    exe = psutil.Process(pid).name()
                except Exception:
                    exe = "?"

                class_name = win32gui.GetClassName(hwnd)

                print(
                    f"HWND={hwnd} | "
                    f"EXE='{exe}' | "
                    f"TITLE='{title}' | "
                    f"CLASS='{class_name}' | "
                    f"{width}x{height}"
                )

            except Exception:
                pass

        win32gui.EnumWindows(
            debug_callback,
            None,
        )

        raise RuntimeError(
            "No se encontro PokeMMO automaticamente. "
            "Mira la lista de ventanas mostrada arriba."
        )

    candidates.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    (
        score,
        hwnd,
        title,
        exe,
        class_name,
        width,
        height,
    ) = candidates[0]

    print("\nPokeMMO encontrado:")
    print(f"  HWND   : {hwnd}")
    print(f"  EXE    : {exe}")
    print(f"  TITULO : {title}")
    print(f"  CLASE  : {class_name}")
    print(f"  TAMANO : {width}x{height}")
    print(f"  SCORE  : {score}")

    return hwnd

# =========================================================
# INFORMACION DE VENTANA
# =========================================================

def get_client_size(
    hwnd: int,
) -> tuple[int, int]:

    left, top, right, bottom = (
        win32gui.GetClientRect(hwnd)
    )

    return (
        right - left,
        bottom - top,
    )


def is_window_minimized(
    hwnd: int,
) -> bool:

    return bool(
        win32gui.IsIconic(hwnd)
    )


# =========================================================
# CAPTURA DE POKEMMO EN SEGUNDO PLANO
# =========================================================

def capture_window_client(
    hwnd: int,
) -> np.ndarray:

    if not win32gui.IsWindow(hwnd):
        raise RuntimeError(
            "La ventana de PokeMMO ya no existe."
        )

    if is_window_minimized(hwnd):
        raise RuntimeError(
            "PokeMMO esta minimizado. "
            "Dejalo abierto aunque este detras "
            "de otras ventanas."
        )

    # Tamaño completo de la ventana
    win_left, win_top, win_right, win_bottom = (
        win32gui.GetWindowRect(hwnd)
    )

    win_width = win_right - win_left
    win_height = win_bottom - win_top

    if win_width <= 0 or win_height <= 0:
        raise RuntimeError(
            "Tamano invalido de la ventana."
        )

    # Posicion del area cliente respecto al escritorio
    client_left_screen, client_top_screen = (
        win32gui.ClientToScreen(
            hwnd,
            (0, 0),
        )
    )

    client_width, client_height = (
        get_client_size(hwnd)
    )

    # Offset cliente dentro de ventana
    offset_x = (
        client_left_screen
        - win_left
    )

    offset_y = (
        client_top_screen
        - win_top
    )

    # DC de la ventana
    hwnd_dc = win32gui.GetWindowDC(
        hwnd
    )

    src_dc = win32ui.CreateDCFromHandle(
        hwnd_dc
    )

    mem_dc = src_dc.CreateCompatibleDC()

    bitmap = win32ui.CreateBitmap()

    bitmap.CreateCompatibleBitmap(
        src_dc,
        win_width,
        win_height,
    )

    mem_dc.SelectObject(
        bitmap
    )

    try:
        # PrintWindow puede capturar una ventana
        # aunque haya otra delante.
        result = ctypes.windll.user32.PrintWindow(
            hwnd,
            mem_dc.GetSafeHdc(),
            PW_RENDERFULLCONTENT,
        )

        # Algunos sistemas/apps funcionan mejor
        # sin PW_RENDERFULLCONTENT.
        if result != 1:
            result = ctypes.windll.user32.PrintWindow(
                hwnd,
                mem_dc.GetSafeHdc(),
                0,
            )

        if result != 1:
            raise RuntimeError(
                "PrintWindow no pudo capturar PokeMMO."
            )

        bmp_info = bitmap.GetInfo()

        bmp_bits = bitmap.GetBitmapBits(
            True
        )

        image = np.frombuffer(
            bmp_bits,
            dtype=np.uint8,
        )

        image = image.reshape(
            (
                bmp_info["bmHeight"],
                bmp_info["bmWidth"],
                4,
            )
        )

        # Cortamos solo el area cliente.
        client = image[
            offset_y:
            offset_y + client_height,

            offset_x:
            offset_x + client_width
        ]

        if client.size == 0:
            raise RuntimeError(
                "No se pudo extraer "
                "el area cliente."
            )

        # Bitmap de Windows viene BGRA
        gray = cv2.cvtColor(
            client,
            cv2.COLOR_BGRA2GRAY,
        )

        return gray.copy()

    finally:
        win32gui.DeleteObject(
            bitmap.GetHandle()
        )

        mem_dc.DeleteDC()
        src_dc.DeleteDC()

        win32gui.ReleaseDC(
            hwnd,
            hwnd_dc,
        )


# =========================================================
# MATCH MULTIESCALA
# =========================================================

def find_template_multiscale(
    frame: np.ndarray,
    template: np.ndarray,
    threshold: float,
) -> tuple[
    bool,
    float,
    tuple[int, int] | None,
    tuple[int, int] | None,
    float | None,
]:

    best_score = -1.0
    best_location = None
    best_size = None
    best_scale = None

    template_h, template_w = (
        template.shape
    )

    for scale in TEMPLATE_SCALES:

        new_w = int(
            template_w * scale
        )

        new_h = int(
            template_h * scale
        )

        if (
            new_w < 8
            or new_h < 8
        ):
            continue

        if (
            new_w > frame.shape[1]
            or new_h > frame.shape[0]
        ):
            continue

        if scale < 1.0:
            interpolation = cv2.INTER_AREA
        else:
            interpolation = cv2.INTER_CUBIC

        resized = cv2.resize(
            template,
            (new_w, new_h),
            interpolation=interpolation,
        )

        result = cv2.matchTemplate(
            frame,
            resized,
            cv2.TM_CCOEFF_NORMED,
        )

        _, score, _, location = (
            cv2.minMaxLoc(result)
        )

        if score > best_score:
            best_score = float(score)
            best_location = location
            best_size = (
                new_w,
                new_h,
            )
            best_scale = scale

    if best_score < threshold:
        return (
            False,
            best_score,
            None,
            None,
            best_scale,
        )

    return (
        True,
        best_score,
        best_location,
        best_size,
        best_scale,
    )


# =========================================================
# DETECTORES
# =========================================================

def detect_battle_menu(
    hwnd: int,
):

    frame = capture_window_client(
        hwnd
    )

    return find_template_multiscale(
        frame,
        BATTLE_TEMPLATE,
        BATTLE_MATCH_THRESHOLD,
    )


def detect_horde_target(
    hwnd: int,
):

    frame = capture_window_client(
        hwnd
    )

    return find_template_multiscale(
        frame,
        HORDE_TEMPLATE,
        HORDE_MATCH_THRESHOLD,
    )


# =========================================================
# PP DE MOVIMIENTOS
# =========================================================

def get_move_positions(
    first_x: int,
    first_y: int,
    move_size: tuple[int, int],
) -> list[tuple[int, int]]:

    move_w, move_h = move_size

    # Los 4 movimientos forman una rejilla 2x2.
    # Usamos el tamaño real detectado del botón LUCHA para
    # calcular los saltos, así se adapta mejor a la escala.
    col_offset = max(
        120,
        int(move_w * 1.04),
    )

    row_offset = max(
        35,
        int(move_h * 1.12),
    )

    return [
        (first_x, first_y),
        (first_x + col_offset, first_y),
        (first_x, first_y + row_offset),
        (first_x + col_offset, first_y + row_offset),
    ]


def detect_pp_zero_in_move(
    hwnd: int,
    move_x: int,
    move_y: int,
    move_size: tuple[int, int],
) -> tuple[bool, float]:

    frame = capture_window_client(hwnd)

    frame_h, frame_w = frame.shape
    move_w, move_h = move_size

    # Buscamos "PP: 0 /" en TODA la caja del movimiento,
    # no solo en una franja. Esto evita fallos por offsets
    # verticales distintos entre resoluciones/zoom.
    pad_x = max(8, int(move_w * 0.08))
    pad_y = max(6, int(move_h * 0.15))

    x1 = max(
        0,
        move_x - move_w // 2 - pad_x,
    )

    x2 = min(
        frame_w,
        move_x + move_w // 2 + pad_x,
    )

    y1 = max(
        0,
        move_y - move_h // 2 - pad_y,
    )

    y2 = min(
        frame_h,
        move_y + move_h // 2 + pad_y,
    )

    crop = frame[
        y1:y2,
        x1:x2,
    ]

    if crop.size == 0:
        return False, -1.0

    (
        detected,
        score,
        location,
        size,
        scale,
    ) = find_template_multiscale(
        crop,
        PP_ZERO_TEMPLATE,
        PP_ZERO_MATCH_THRESHOLD,
    )

    return detected, score


def choose_move_with_pp(
    hwnd: int,
    first_x: int,
    first_y: int,
    move_size: tuple[int, int],
) -> bool:

    positions = get_move_positions(
        first_x,
        first_y,
        move_size,
    )

    print(
        f"[PP] Revisando movimientos... "
        f"(umbral zero={PP_ZERO_MATCH_THRESHOLD:.2f})"
    )

    for index, (x, y) in enumerate(
        positions,
        start=1,
    ):

        pp_zero, score = detect_pp_zero_in_move(
            hwnd,
            x,
            y,
            move_size,
        )

        print(
            f"[PP] Movimiento {index}: "
            f"zero={pp_zero} score={score:.3f}"
        )

        if pp_zero:
            print(
                f"[PP] Movimiento {index} sin PP, "
                "probando siguiente..."
            )
            continue

        print(
            f"[PP] Usando movimiento {index} "
            f"x={x} y={y}"
        )

        window_click(
            hwnd,
            x,
            y,
        )

        return True

    print(
        "[PP] Los 4 movimientos parecen estar a 0 PP."
    )

    return False


# =========================================================
# TECLAS SOLO PARA POKEMMO
# =========================================================

def get_vk(
    key: str,
) -> int:

    key = key.upper()

    if len(key) == 1:
        return ord(key)

    raise ValueError(
        f"Tecla no soportada: {key}"
    )


def make_key_lparam(
    vk: int,
    key_up: bool = False,
) -> int:

    scan_code = (
        win32api.MapVirtualKey(
            vk,
            0,
        )
    )

    # repeat count = 1
    lparam = 1

    # scan code
    lparam |= (
        scan_code << 16
    )

    if key_up:
        # previous key state
        lparam |= (
            1 << 30
        )

        # transition state
        lparam |= (
            1 << 31
        )

    return lparam


def window_key_down(
    hwnd: int,
    key: str,
) -> None:

    vk = get_vk(key)

    lparam = make_key_lparam(
        vk,
        False,
    )

    win32api.PostMessage(
        hwnd,
        win32con.WM_KEYDOWN,
        vk,
        lparam,
    )


def window_key_up(
    hwnd: int,
    key: str,
) -> None:

    vk = get_vk(key)

    lparam = make_key_lparam(
        vk,
        True,
    )

    win32api.PostMessage(
        hwnd,
        win32con.WM_KEYUP,
        vk,
        lparam,
    )


def release_movement(
    hwnd: int | None = None,
) -> None:

    keyboard.release(
        MOVE_LEFT
    )

    keyboard.release(
        MOVE_RIGHT
    )
# =========================================================
# RATON SOLO PARA POKEMMO
# =========================================================

def make_mouse_lparam(
    x: int,
    y: int,
) -> int:

    return win32api.MAKELONG(
        int(x),
        int(y),
    )


def window_click(
    hwnd: int,
    x: int,
    y: int,
) -> None:

    lparam = make_mouse_lparam(
        x,
        y,
    )

    # Movemos el cursor virtual de la ventana.
    # NO mueve tu raton fisico.
    win32api.PostMessage(
        hwnd,
        win32con.WM_MOUSEMOVE,
        0,
        lparam,
    )

    win32api.PostMessage(
        hwnd,
        win32con.WM_LBUTTONDOWN,
        win32con.MK_LBUTTON,
        lparam,
    )

    time.sleep(
        0.025
    )

    win32api.PostMessage(
        hwnd,
        win32con.WM_LBUTTONUP,
        0,
        lparam,
    )


def window_double_click(
    hwnd: int,
    x: int,
    y: int,
) -> None:

    window_click(
        hwnd,
        x,
        y,
    )

    time.sleep(
        0.10
    )

    window_click(
        hwnd,
        x,
        y,
    )


# =========================================================
# CENTRO DE TEMPLATE
# =========================================================

def get_detected_center(
    location: tuple[int, int],
    size: tuple[int, int],
) -> tuple[int, int]:

    x, y = location

    width, height = size

    return (
        x + width // 2,
        y + height // 2,
    )


# =========================================================
# DEBUG
# =========================================================

def save_debug_screen(
    hwnd: int,
) -> None:

    frame = capture_window_client(
        hwnd
    )

    filename = (
        BASE_DIR
        / "debug_pokemmo.png"
    )

    cv2.imwrite(
        str(filename),
        frame,
    )

    print(
        "\n[DEBUG] Guardado:"
    )

    print(
        filename
    )


# =========================================================
# CAMINAR
# =========================================================

def walk_one_step(
    hwnd: int,
    direction: str,
) -> bool:

    previous_hwnd = win32gui.GetForegroundWindow()
    movement_started = False

    try:
        # Traer PokeMMO al frente solo durante el movimiento real.
        if win32gui.GetForegroundWindow() != hwnd:
            try:
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(
                        hwnd,
                        win32con.SW_RESTORE,
                    )

                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.10)

            except Exception as e:
                print(
                    f"[FOCUS] Error activando PokeMMO: {e}"
                )

        print(
            f"[MOVE] >>> {direction.upper()}"
        )

        keyboard.press(direction)
        movement_started = True

        deadline = (
            time.time()
            + WALK_SECONDS
        )

        while time.time() < deadline:

            if keyboard.is_pressed(
                EXIT_KEY
            ):
                return True

            (
                battle,
                score,
                location,
                size,
                scale,
            ) = detect_battle_menu(
                hwnd
            )

            if battle:
                print(
                    "\n[COMBATE DURANTE MOVIMIENTO] "
                    f"score={score:.3f} "
                    f"scale={scale} "
                    f"pos={location}"
                )

                return True

            time.sleep(
                POLL_INTERVAL
            )

        return False

    finally:

        if movement_started:
            keyboard.release(
                direction
            )

            print(
                f"[MOVE] <<< {direction.upper()}"
            )

        # Devolver el foco a la aplicacion que estabas usando.
        if (
            previous_hwnd
            and previous_hwnd != hwnd
            and win32gui.IsWindow(
                previous_hwnd
            )
        ):
            try:
                time.sleep(0.05)
                win32gui.SetForegroundWindow(
                    previous_hwnd
                )
            except Exception:
                pass

# =========================================================
# ESPERAR HORDA
# =========================================================

def wait_for_horde_target(
    hwnd: int,
    timeout: float,
):

    deadline = (
        time.time()
        + timeout
    )

    best_score = -1.0

    while time.time() < deadline:

        if keyboard.is_pressed(
            EXIT_KEY
        ):
            return (
                False,
                best_score,
                None,
                None,
                None,
            )

        (
            detected,
            score,
            location,
            size,
            scale,
        ) = detect_horde_target(
            hwnd
        )

        best_score = max(
            best_score,
            score,
        )

        if detected:

            print(
                "[HORDA] Detectada "
                f"score={score:.3f} "
                f"scale={scale} "
                f"pos={location}"
            )

            return (
                detected,
                score,
                location,
                size,
                scale,
            )

        time.sleep(
            POLL_INTERVAL
        )

    print(
        "[HORDA] No detectada "
        f"| mejor score="
        f"{best_score:.3f}"
    )

    return (
        False,
        best_score,
        None,
        None,
        None,
    )


# =========================================================
# ESPERAR VUELTA AL MUNDO
# =========================================================

def wait_until_back_to_world(
    hwnd: int,
    timeout: float = BATTLE_END_TIMEOUT,
) -> bool:

    print("[WORLD] Esperando volver al mundo...")

    deadline = (
        time.time()
        + timeout
    )

    confirmations = 0

    while time.time() < deadline:

        if keyboard.is_pressed(
            EXIT_KEY
        ):
            return False

        (
            battle,
            score,
            location,
            size,
            scale,
        ) = detect_battle_menu(
            hwnd
        )

        if battle:
            confirmations = 0
        else:
            confirmations += 1

            if confirmations >= WORLD_CONFIRMATIONS:
                print(
                    "[WORLD] Mundo confirmado "
                    f"(score={score:.3f})"
                )
                return True

        time.sleep(
            WORLD_CHECK_INTERVAL
        )

    print(
        "[WORLD] Timeout esperando mundo; "
        "se reintentara movimiento igualmente."
    )

    return False

# =========================================================
# ATAQUE
# =========================================================

def attack(
    hwnd: int,
    battle_location: tuple[int, int],
    battle_size: tuple[int, int],
) -> None:

    release_movement(
        hwnd
    )

    print(
        "\n================================"
    )

    # -----------------------------------------------------
    # LUCHA
    # -----------------------------------------------------

    battle_x, battle_y = (
        get_detected_center(
            battle_location,
            battle_size,
        )
    )

    print(
        "[1] CLICK LUCHA "
        f"x={battle_x} "
        f"y={battle_y}"
    )

    window_click(
        hwnd,
        battle_x,
        battle_y,
    )

    time.sleep(
        AFTER_BATTLE_CLICK
    )

    # -----------------------------------------------------
    # MOVIMIENTO CON PP DISPONIBLE
    # -----------------------------------------------------

    print(
        "[2] BUSCANDO MOVIMIENTO CON PP..."
    )

    time.sleep(
        PP_CHECK_WAIT
    )

    move_selected = choose_move_with_pp(
        hwnd,
        battle_x,
        battle_y,
        battle_size,
    )

    if not move_selected:
        print(
            "[PP] No se pudo seleccionar ningun movimiento."
        )

        time.sleep(
            AFTER_MOVE_CLICK_BEFORE_HORDE
        )

        return

    time.sleep(
        AFTER_MOVE_CLICK_BEFORE_HORDE
    )

    # -----------------------------------------------------
    # HORDA
    # -----------------------------------------------------

    print(
        "[3] COMPROBANDO HORDA..."
    )

    (
        horde,
        horde_score,
        horde_location,
        horde_size,
        horde_scale,
    ) = wait_for_horde_target(
        hwnd,
        HORDE_DETECTION_TIMEOUT,
    )

    if (
        horde
        and horde_location is not None
        and horde_size is not None
    ):

        target_x, target_y = (
            get_detected_center(
                horde_location,
                horde_size,
            )
        )

        print(
            "[4] DOBLE CLICK HORDA "
            f"x={target_x} "
            f"y={target_y}"
        )

        window_double_click(
            hwnd,
            target_x,
            target_y,
        )

        time.sleep(
            AFTER_HORDE_DOUBLE_CLICK
        )

        print(
            "[5] OBJETIVO HORDA ENVIADO"
        )

    else:

        print(
            "[4] COMBATE NORMAL"
        )

        time.sleep(
            AFTER_NORMAL_MOVE
        )

    print(
        "[6] ESPERANDO FIN DEL COMBATE..."
    )

    wait_until_back_to_world(
        hwnd
    )

    print(
        "[7] VOLVIENDO AL MOVIMIENTO"
    )

    print(
        "================================\n"
    )


# =========================================================
# MAIN
# =========================================================

def main() -> None:

    print(
        "Pokemon bot - modo ventana"
    )

    print(
        f"Buscando ventana: "
        f"{WINDOW_TITLE}"
    )

    hwnd = find_pokemmo_window()

    title = win32gui.GetWindowText(
        hwnd
    )

    client_width, client_height = (
        get_client_size(
            hwnd
        )
    )

    print(
        f"Ventana encontrada:"
    )

    print(
        f"  HWND: {hwnd}"
    )

    print(
        f"  Titulo: {title}"
    )

    print(
        f"  Cliente: "
        f"{client_width}x{client_height}"
    )

    print()

    print(
        f"{PAUSE_KEY.upper()} "
        "= pausar/reanudar"
    )

    print(
        f"{EXIT_KEY.upper()} "
        "= salir"
    )

    print(
        f"{DEBUG_KEY.upper()} "
        "= captura debug"
    )

    print()

    print(
        "Puedes cambiar a otra ventana."
    )

    print(
        "No minimices PokeMMO."
    )

    print(
        "Inicio en 3 segundos..."
    )

    time.sleep(
        3
    )

    paused = False

    pause_latch = False
    debug_latch = False

    direction = (
        MOVE_LEFT
    )

    last_debug = 0.0
    last_attack = 0.0

    while True:

        # -------------------------------------------------
        # COMPROBAR QUE POKEMMO SIGUE ABIERTO
        # -------------------------------------------------

        if not win32gui.IsWindow(
            hwnd
        ):
            print(
                "\nPokeMMO se ha cerrado."
            )
            break

        # -------------------------------------------------
        # SALIR
        # -------------------------------------------------

        if keyboard.is_pressed(
            EXIT_KEY
        ):
            break

        # -------------------------------------------------
        # PAUSA
        # -------------------------------------------------

        pause_pressed = (
            keyboard.is_pressed(
                PAUSE_KEY
            )
        )

        if (
            pause_pressed
            and not pause_latch
        ):

            paused = not paused

            release_movement(
                hwnd
            )

            print(
                "\nPAUSADO"
                if paused
                else "\nREANUDADO"
            )

        pause_latch = (
            pause_pressed
        )

        if paused:

            time.sleep(
                0.10
            )

            continue

        # -------------------------------------------------
        # DEBUG
        # -------------------------------------------------

        debug_pressed = (
            keyboard.is_pressed(
                DEBUG_KEY
            )
        )

        if (
            debug_pressed
            and not debug_latch
        ):

            save_debug_screen(
                hwnd
            )

        debug_latch = (
            debug_pressed
        )

        # -------------------------------------------------
        # DETECTAR LUCHA
        # -------------------------------------------------

        (
            battle,
            score,
            location,
            size,
            scale,
        ) = detect_battle_menu(
            hwnd
        )

        now = time.time()

        if (
            now - last_debug
            >= DEBUG_INTERVAL
        ):

            print(
                f"battle="
                f"{str(battle):5s} "
                f"| score={score:.3f} "
                f"| scale={scale} "
                f"| pos={location}"
            )

            last_debug = (
                now
            )

        # -------------------------------------------------
        # COMBATE
        # -------------------------------------------------

        if (
            battle
            and location is not None
            and size is not None
        ):

            release_movement(
                hwnd
            )

            if (
                now - last_attack
                >= ATTACK_COOLDOWN
            ):

                print(
                    "\nCOMBATE DETECTADO "
                    f"score={score:.3f}"
                )

                attack(
                    hwnd,
                    location,
                    size,
                )

                last_attack = (
                    time.time()
                )

            else:

                time.sleep(
                    POLL_INTERVAL
                )

            continue

        # -------------------------------------------------
        # MUNDO
        # -------------------------------------------------

        print(
            f"[WORLD] Caminando {direction.upper()}"
        )

        battle_found = (
            walk_one_step(
                hwnd,
                direction,
            )
        )

        if battle_found:

            release_movement(
                hwnd
            )

            time.sleep(
                0.10
            )

            continue

        if direction == MOVE_LEFT:
            direction = MOVE_RIGHT
        else:
            direction = MOVE_LEFT

        time.sleep(
            0.05
        )

    release_movement(
        hwnd
    )

    print(
        "\nBot detenido."
    )


# =========================================================
# INICIO
# =========================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print(
            "\nBot detenido con Ctrl+C."
        )

    except Exception as e:

        print(
            f"\nERROR: {e}"
        )