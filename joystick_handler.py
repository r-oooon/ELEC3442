"""
joystick_handler.py — SenseHAT joystick detection thread.
Joystick UP  → pedestrian request from Side A
Joystick DOWN → pedestrian request from Side B
"""

import time
import threading

from config import SENSEHAT_ENABLED, DEBOUNCE_MS


def _joystick_thread(shared_state, stop_event):
    """
    Listen for SenseHAT joystick events and translate them
    into the same shared button-press flag used by GPIO buttons.
    """
    if not SENSEHAT_ENABLED:
        print("[joystick] SenseHAT disabled — joystick thread idle.")
        while not stop_event.is_set():
            time.sleep(0.5)
        return

    try:
        from sense_hat import SenseHat
        sense = SenseHat()
    except Exception as e:
        print(f"[joystick] WARNING: Could not init SenseHAT for joystick: {e}")
        while not stop_event.is_set():
            time.sleep(0.5)
        return

    debounce_s = DEBOUNCE_MS / 1000.0
    last_press_time = 0.0

    print("[joystick] Joystick thread started.")

    while not stop_event.is_set():
        try:
            # get_events() returns a list of InputEvent objects since last call
            events = sense.stick.get_events()
            for event in events:
                if event.action != 'pressed':
                    continue

                side = None
                if event.direction == 'up':
                    side = 'A'
                elif event.direction == 'down':
                    side = 'B'

                if side is None:
                    continue  # Ignore left / right / middle

                now = time.time()
                if (now - last_press_time) >= debounce_s:
                    last_press_time = now
                    with shared_state['lock']:
                        shared_state['button_pressed'] = True
                        shared_state['button_side'] = side
                        shared_state['press_time'] = now
                        shared_state['input_type'] = 'joystick'
                    print(f"[joystick] Side {side} request via joystick "
                          f"({event.direction})")

            time.sleep(0.05)  # Avoid busy-wait

        except Exception as e:
            print(f"[joystick] Error: {e}")
            time.sleep(1)


def start_joystick_thread(shared_state, stop_event):
    """Launch the joystick listener as a daemon thread."""
    t = threading.Thread(
        target=_joystick_thread,
        args=(shared_state, stop_event),
        name="Joystick",
        daemon=True,
    )
    t.start()
    return t
