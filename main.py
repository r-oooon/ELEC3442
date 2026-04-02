#!/usr/bin/env python3
"""
main.py — Entry point for the Smart Pedestrian Crossing system.
Initialises all subsystems, launches threads, and waits for Ctrl-C to shut down.
"""

import threading
import time
import signal
import sys

# Project modules
import db_logger
import display
import camera_handler
from button_handler import setup_gpio, cleanup_gpio, start_button_threads
from joystick_handler import start_joystick_thread
from fsm import start_fsm_thread


def main():
    print("=" * 55)
    print("  Smart Pedestrian Crossing & Traffic Flow Logger")
    print("=" * 55)

    # ── Shared state between all threads ──
    shared_state = {
        'lock':            threading.Lock(),
        'button_pressed':  False,
        'button_side':     None,
        'press_time':      None,
        'input_type':      None,
        'current_state':   'STARTUP',
        'last_press_id':   None,
    }

    # Global stop event for graceful shutdown
    stop_event = threading.Event()

    # ── Initialisation ──
    print("\n[main] Initialising subsystems...")
    db_logger.init_db()
    display.init_display()
    camera_handler.init_camera()
    setup_gpio()

    # ── Launch threads ──
    print("\n[main] Starting threads...")
    threads = []

    btn_threads = start_button_threads(shared_state, stop_event)
    threads.extend(btn_threads)

    joy_thread = start_joystick_thread(shared_state, stop_event)
    threads.append(joy_thread)

    fsm_thread = start_fsm_thread(shared_state, stop_event)
    threads.append(fsm_thread)

    print(f"[main] {len(threads)} threads running. Press Ctrl-C to stop.\n")

    # ── Wait for shutdown ──
    try:
        while not stop_event.is_set():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[main] KeyboardInterrupt received — shutting down...")
    finally:
        # Signal all threads to stop
        stop_event.set()

        # Give threads a moment to finish their current iteration
        time.sleep(1)

        # Cleanup hardware
        display.clear_display()
        camera_handler.release_camera()
        cleanup_gpio()

        print("[main] System shut down cleanly. Goodbye!")


if __name__ == "__main__":
    main()
