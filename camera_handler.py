"""
camera_handler.py — Pi Camera presence detection via frame differencing.
Captures two frames, computes the absolute difference, and decides
whether a pedestrian is physically present at the crossing.
"""

import os
import time
from datetime import datetime

from config import (
    CAMERA_ENABLED, MOTION_THRESHOLD, CAMERA_WARMUP_TIME, SNAPSHOT_DIR
)

# ──────────────────────────────────────────────
# Lazy imports — only pulled in if camera is enabled
# ──────────────────────────────────────────────
_camera = None
_camera_available = False


def init_camera():
    """
    Initialise the Pi Camera.
    If the camera is unavailable the system continues with presence
    defaulting to True.
    """
    global _camera, _camera_available

    if not CAMERA_ENABLED:
        print("[camera] Camera disabled in config.")
        return

    try:
        from picamera2 import Picamera2
        _camera = Picamera2()
        _camera.configure(_camera.create_still_configuration())
        _camera.start()
        time.sleep(CAMERA_WARMUP_TIME)  # let auto-exposure settle
        _camera_available = True
        print("[camera] Pi Camera initialised.")
    except Exception as e:
        print(f"[camera] WARNING: Could not initialise camera: {e}")
        print("[camera] Presence will default to True for all events.")
        _camera_available = False


def release_camera():
    """Cleanly stop the camera."""
    global _camera, _camera_available
    if _camera_available and _camera is not None:
        try:
            _camera.stop()
            print("[camera] Camera released.")
        except Exception:
            pass
    _camera = None
    _camera_available = False


def detect_presence():
    """
    Use frame differencing to decide if a pedestrian is present.

    Returns
    -------
    (presence: bool, snapshot_path: str or None)
    """
    # Ensure snapshot directory exists
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)

    if not _camera_available:
        return True, None   # Assume present when camera unavailable

    try:
        import cv2
        import numpy as np

        # Capture two frames in quick succession
        frame1 = _camera.capture_array()
        time.sleep(0.2)
        frame2 = _camera.capture_array()

        # Convert to grayscale
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        # Absolute difference → threshold → count moving pixels
        diff = cv2.absdiff(gray1, gray2)
        _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
        motion_pixels = cv2.countNonZero(thresh)

        presence = motion_pixels >= MOTION_THRESHOLD

        # Save a timestamped snapshot (the second frame)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"snap_{timestamp_str}.jpg"
        snapshot_path = os.path.join(SNAPSHOT_DIR, filename)
        cv2.imwrite(snapshot_path, frame2)

        print(f"[camera] Motion pixels: {motion_pixels} | "
              f"Threshold: {MOTION_THRESHOLD} | "
              f"Presence: {presence}")

        return presence, snapshot_path

    except Exception as e:
        print(f"[camera] Detection error: {e}")
        return True, None   # Default to present on error
