#!/usr/bin/env python3
"""
main.py — Entry point for the Smart Pedestrian Crossing system.
Initialises all subsystems, launches threads, and waits for Ctrl-C to shut down.
"""

import threading
import time
import signal
import sys
from dashboard_server import app

# Project modules
import db_logger
import display
import camera_handler
from button_handler import setup_gpio, cleanup_gpio, start_button_threads
from joystick_handler import start_joystick_thread
from fsm import start_fsm_thread
from config import SIMULATION_ENABLED


def start_dashboard_thread(stop_event):
    def run():
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

    t = threading.Thread(target=run, name="Dashboard", daemon=True)
    t.start()
    return t


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
    threads = []

    dash_thread = start_dashboard_thread(stop_event)
    threads.append(dash_thread)
    print("[main] Dashboard server started at http://localhost:5000")

    # ── Initialisation ──
    print("\n[main] Initialising subsystems...")
    db_logger.init_db()
    display.init_display()
    camera_handler.init_camera()
    setup_gpio()

    # ── Launch threads ──
    print("[main] Starting threads...")

    btn_threads = start_button_threads(shared_state, stop_event)
    threads.extend(btn_threads)

    joy_thread = start_joystick_thread(shared_state, stop_event)
    threads.append(joy_thread)

    fsm_thread = start_fsm_thread(shared_state, stop_event)
    threads.append(fsm_thread)

    # ── Optional: pygame simulation window ──
    if SIMULATION_ENABLED:
        from simulation import start_simulation, run_simulation
        # Pygame strongly prefers to run on the main thread on some platforms.
        # We'll launch it on a thread here; if that causes issues on macOS,
        # swap to running run_simulation() on main and move the wait-loop
        # into a thread instead.
        sim_thread = start_simulation(shared_state, stop_event)
        threads.append(sim_thread)
        print("[main] Simulation window launched.")

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
