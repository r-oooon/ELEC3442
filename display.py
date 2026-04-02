"""
display.py — SenseHAT 8×8 LED matrix display functions.
Each FSM state maps to a distinct visual pattern on the matrix.
"""

import time
import threading

from config import SENSEHAT_ENABLED

# ──────────────────────────────────────────────
# Colour constants (R, G, B)
# ──────────────────────────────────────────────
OFF   = (0, 0, 0)
RED   = (255, 0, 0)
GREEN = (0, 255, 0)
AMBER = (255, 165, 0)
WHITE = (255, 255, 255)

# ──────────────────────────────────────────────
# 8×8 Pixel art patterns (flattened 64-element lists)
# Each row is left-to-right, rows go top-to-bottom.
# ──────────────────────────────────────────────
O = OFF
G = GREEN
R = RED
A = AMBER
W = WHITE

# Vehicle green — bottom 4 rows filled green
VEHICLE_GREEN_PATTERN = [
    O, O, O, O, O, O, O, O,
    O, O, O, O, O, O, O, O,
    O, O, O, O, O, O, O, O,
    O, O, O, O, O, O, O, O,
    G, G, G, G, G, G, G, G,
    G, G, G, G, G, G, G, G,
    G, G, G, G, G, G, G, G,
    G, G, G, G, G, G, G, G,
]

# Vehicle amber — middle 4 rows filled amber
VEHICLE_AMBER_PATTERN = [
    O, O, O, O, O, O, O, O,
    O, O, O, O, O, O, O, O,
    A, A, A, A, A, A, A, A,
    A, A, A, A, A, A, A, A,
    A, A, A, A, A, A, A, A,
    A, A, A, A, A, A, A, A,
    O, O, O, O, O, O, O, O,
    O, O, O, O, O, O, O, O,
]

# Vehicle red — top 4 rows filled red
VEHICLE_RED_PATTERN = [
    R, R, R, R, R, R, R, R,
    R, R, R, R, R, R, R, R,
    R, R, R, R, R, R, R, R,
    R, R, R, R, R, R, R, R,
    O, O, O, O, O, O, O, O,
    O, O, O, O, O, O, O, O,
    O, O, O, O, O, O, O, O,
    O, O, O, O, O, O, O, O,
]

# Walking figure — simple pixel-art pedestrian in green
WALK_FIGURE = [
    O, O, O, G, G, O, O, O,   # head
    O, O, O, G, G, O, O, O,
    O, O, G, G, G, G, O, O,   # arms out
    O, O, O, G, G, O, O, O,   # torso
    O, O, O, G, G, O, O, O,
    O, O, G, O, O, G, O, O,   # legs apart
    O, G, O, O, O, O, G, O,
    G, O, O, O, O, O, O, G,
]

# Startup / idle pattern — gentle white border
STARTUP_PATTERN = [
    W, W, W, W, W, W, W, W,
    W, O, O, O, O, O, O, W,
    W, O, O, O, O, O, O, W,
    W, O, O, O, O, O, O, W,
    W, O, O, O, O, O, O, W,
    W, O, O, O, O, O, O, W,
    W, O, O, O, O, O, O, W,
    W, W, W, W, W, W, W, W,
]

# ──────────────────────────────────────────────
# SenseHAT wrapper (no-op if hardware disabled)
# ──────────────────────────────────────────────
_sense = None


def init_display():
    """Initialise the SenseHAT display. Call once at startup."""
    global _sense
    if not SENSEHAT_ENABLED:
        print("[display] SenseHAT disabled in config — using stub.")
        return
    try:
        from sense_hat import SenseHat
        _sense = SenseHat()
        _sense.low_light = True
        _sense.set_pixels(STARTUP_PATTERN)
        print("[display] SenseHAT initialised.")
    except Exception as e:
        print(f"[display] WARNING: Could not initialise SenseHAT: {e}")
        print("[display] Falling back to stub mode.")


def _set_pixels(pattern):
    """Set all 64 pixels at once (safe if SenseHAT unavailable)."""
    if _sense:
        _sense.set_pixels(pattern)


def clear_display():
    """Blank the matrix."""
    if _sense:
        _sense.clear()


# ──────────────────────────────────────────────
# Public state-display functions
# ──────────────────────────────────────────────
def show_vehicle_green():
    _set_pixels(VEHICLE_GREEN_PATTERN)


def show_vehicle_amber():
    _set_pixels(VEHICLE_AMBER_PATTERN)


def show_vehicle_red():
    _set_pixels(VEHICLE_RED_PATTERN)


def show_pedestrian_cross():
    _set_pixels(WALK_FIGURE)


def show_pedestrian_clearance(duration, stop_event):
    """
    Flash the walking figure on/off at ~1 Hz for `duration` seconds.
    Stops early if stop_event is set (allows clean shutdown).
    """
    end_time = time.time() + duration
    toggle = True
    while time.time() < end_time and not stop_event.is_set():
        if toggle:
            _set_pixels(WALK_FIGURE)
        else:
            clear_display()
        toggle = not toggle
        # Sleep in small increments so we can react to stop_event quickly
        for _ in range(5):
            if stop_event.is_set():
                return
            time.sleep(0.1)


def show_startup():
    _set_pixels(STARTUP_PATTERN)
