"""
button_handler.py — GPIO push-button detection threads (one per button).
Each thread polls its pin with software debouncing and communicates
button presses to the FSM via a shared lock-protected flag.
"""

import time
import threading

from config import (
    GPIO_ENABLED, BUTTON_A_PIN, BUTTON_B_PIN, DEBOUNCE_MS
)

# Conditional import — allows running on non-Pi machines
if GPIO_ENABLED:
    try:
        import RPi.GPIO as GPIO
    except ImportError:
        GPIO_ENABLED_RUNTIME = False
        print("[button_handler] WARNING: RPi.GPIO not available. "
              "Button threads will be no-ops.")
    else:
        GPIO_ENABLED_RUNTIME = True
else:
    GPIO_ENABLED_RUNTIME = False


def setup_gpio():
    """Configure GPIO pins for the two push-buttons with pull-down resistors."""
    if not GPIO_ENABLED_RUNTIME:
        return
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_A_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(BUTTON_B_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    print(f"[button_handler] GPIO set up: A=BCM{BUTTON_A_PIN}, B=BCM{BUTTON_B_PIN}")


def cleanup_gpio():
    """Release GPIO resources. Call on program exit."""
    if GPIO_ENABLED_RUNTIME:
        GPIO.cleanup()
        print("[button_handler] GPIO cleaned up.")


def _button_thread(pin, side, shared_state, stop_event):
    """
    Polling loop for one physical button.

    Parameters
    ----------
    pin : int          BCM pin number
    side : str         'A' or 'B'
    shared_state : dict
        Must contain:
            'lock'           : threading.Lock
            'button_pressed' : bool
            'button_side'    : str
            'press_time'     : float or None
    stop_event : threading.Event
        Set this to gracefully stop the thread.
    """
    debounce_s = DEBOUNCE_MS / 1000.0
    last_press_time = 0.0

    print(f"[button_handler] Thread started for Side {side} (GPIO {pin})")

    while not stop_event.is_set():
        try:
            if not GPIO_ENABLED_RUNTIME:
                # No hardware — just sleep and loop
                time.sleep(0.5)
                continue

            if GPIO.input(pin) == GPIO.HIGH:
                now = time.time()
                if (now - last_press_time) >= debounce_s:
                    last_press_time = now
                    with shared_state['lock']:
                        shared_state['button_pressed'] = True
                        shared_state['button_side'] = side
                        shared_state['press_time'] = now
                        shared_state['input_type'] = 'gpio_button'
                    print(f"[button_handler] Side {side} button pressed (GPIO {pin})")

            # Small sleep to avoid busy-waiting
            time.sleep(0.05)

        except Exception as e:
            print(f"[button_handler] Error in Side {side} thread: {e}")
            time.sleep(1)


def start_button_threads(shared_state, stop_event):
    """
    Launch daemon threads for both buttons and return a list of the threads.
    """
    threads = []
    for pin, side in [(BUTTON_A_PIN, 'A'), (BUTTON_B_PIN, 'B')]:
        t = threading.Thread(
            target=_button_thread,
            args=(pin, side, shared_state, stop_event),
            name=f"Button-{side}",
            daemon=True,
        )
        t.start()
        threads.append(t)
    return threads
