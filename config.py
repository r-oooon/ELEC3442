"""
config.py — Central configuration for Smart Pedestrian Crossing system.
All tuneable constants live here for easy adjustment during development and demo.
"""

import os

# ──────────────────────────────────────────────
# Hardware enable flags (set False to run without that hardware)
# ──────────────────────────────────────────────
GPIO_ENABLED = True
SENSEHAT_ENABLED = True
CAMERA_ENABLED = True

# ──────────────────────────────────────────────
# GPIO Pin Assignments
# ──────────────────────────────────────────────
BUTTON_A_PIN = 17          # Side A push-button (BCM numbering)
BUTTON_B_PIN = 27          # Side B push-button (BCM numbering)
BUZZER_PIN = 22            # Optional audible crossing buzzer

# ──────────────────────────────────────────────
# FSM Timing (seconds)
# ──────────────────────────────────────────────
MIN_GREEN_DURATION = 10    # Minimum green before a button press can trigger amber
EXTRA_GREEN_DURATION = 15  # How long to stay green if no button pressed after min
AMBER_DURATION = 3         # Fixed amber warning phase
PRE_CROSS_RED_DURATION = 2 # Red pause before pedestrians get walk signal
PEDESTRIAN_CROSS_DURATION = 8   # Walk signal duration
CLEARANCE_DURATION = 3     # Flashing clearance warning

# ──────────────────────────────────────────────
# Button Debounce
# ──────────────────────────────────────────────
DEBOUNCE_MS = 300          # Minimum milliseconds between accepted presses

# ──────────────────────────────────────────────
# Camera / Motion Detection
# ──────────────────────────────────────────────
MOTION_THRESHOLD = 500     # Minimum changed pixels to count as "presence"
CAMERA_WARMUP_TIME = 1.0   # Seconds to let camera auto-expose on startup

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "crossing.db")
SNAPSHOT_DIR = os.path.join(BASE_DIR, "snapshots")
CHARTS_DIR = os.path.join(BASE_DIR, "charts")
