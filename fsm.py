"""
fsm.py — Finite State Machine for the traffic light / pedestrian crossing.

States:
    VEHICLE_GREEN → VEHICLE_AMBER → VEHICLE_RED →
    PEDESTRIAN_CROSS → PEDESTRIAN_CLEARANCE → (back to VEHICLE_GREEN)

The FSM runs in its own dedicated thread and communicates with other
threads via a shared_state dict protected by a threading.Lock.
"""

import time
import threading

from config import (
    MIN_GREEN_DURATION,
    EXTRA_GREEN_DURATION,
    AMBER_DURATION,
    PRE_CROSS_RED_DURATION,
    PEDESTRIAN_CROSS_DURATION,
    CLEARANCE_DURATION,
    SENSEHAT_ENABLED,
    BUZZER_PIN,
    GPIO_ENABLED,
)

import display
import db_logger
import camera_handler


# ──────────────────────────────────────────────
# Optional buzzer support
# ──────────────────────────────────────────────
def _buzzer_beep(duration=0.15, pause=0.15, count=1):
    """Produce short beeps on the buzzer if GPIO is available."""
    if not GPIO_ENABLED:
        return
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUZZER_PIN, GPIO.OUT)
        for _ in range(count):
            GPIO.output(BUZZER_PIN, GPIO.HIGH)
            time.sleep(duration)
            GPIO.output(BUZZER_PIN, GPIO.LOW)
            time.sleep(pause)
    except Exception:
        pass  # Buzzer is optional


# ──────────────────────────────────────────────
# Environmental sensor helper
# ──────────────────────────────────────────────
def _read_environment():
    """
    Read temperature, humidity, and pressure from the SenseHAT.
    Returns (temp, hum, pres) or (None, None, None) if unavailable.
    """
    if not SENSEHAT_ENABLED:
        return None, None, None
    try:
        from sense_hat import SenseHat
        s = SenseHat()
        return s.get_temperature(), s.get_humidity(), s.get_pressure()
    except Exception as e:
        print(f"[fsm] Could not read environment: {e}")
        return None, None, None


# ──────────────────────────────────────────────
# Helper: interruptible sleep
# ──────────────────────────────────────────────
def _sleep(seconds, stop_event):
    """Sleep in small increments so we can react to stop_event."""
    end = time.time() + seconds
    while time.time() < end and not stop_event.is_set():
        time.sleep(0.1)


# ──────────────────────────────────────────────
# FSM thread entry point
# ──────────────────────────────────────────────
def fsm_loop(shared_state, stop_event):
    """
    Main FSM loop — runs until stop_event is set.

    shared_state keys used:
        'lock'            : threading.Lock
        'button_pressed'  : bool
        'button_side'     : str ('A' or 'B')
        'press_time'      : float (timestamp of the press)
        'input_type'      : str ('gpio_button' or 'joystick')
        'current_state'   : str (written by FSM, read by others)
        'last_press_id'   : int or None (DB row id for wait-time update)
    """
    print("[fsm] FSM thread started.")

    while not stop_event.is_set():
        try:
            # ───── VEHICLE_GREEN ─────
            with shared_state['lock']:
                shared_state['current_state'] = 'VEHICLE_GREEN'
            display.show_vehicle_green()
            phase_start = time.time()
            triggered = False

            # Enforce minimum green duration
            _sleep(MIN_GREEN_DURATION, stop_event)
            if stop_event.is_set():
                break

            # Check if button was pressed during minimum green
            with shared_state['lock']:
                if shared_state['button_pressed']:
                    triggered = True

            if not triggered:
                # Wait up to EXTRA_GREEN_DURATION, checking for button presses
                extra_end = time.time() + EXTRA_GREEN_DURATION
                while time.time() < extra_end and not stop_event.is_set():
                    with shared_state['lock']:
                        if shared_state['button_pressed']:
                            triggered = True
                            break
                    time.sleep(0.1)

            # Process the button press: camera check + environmental read + DB log
            press_row_id = None
            if triggered:
                with shared_state['lock']:
                    side = shared_state['button_side']
                    press_time = shared_state['press_time']
                    input_type = shared_state['input_type']
                    shared_state['button_pressed'] = False  # consume

                # Camera presence detection
                presence, snap_path = camera_handler.detect_presence()

                # Environmental sensors
                temp, hum, pres = _read_environment()

                # Log to database
                press_row_id = db_logger.log_button_press(
                    side=side,
                    input_type=input_type,
                    temperature=temp,
                    humidity=hum,
                    pressure=pres,
                    presence_detected=presence,
                    snapshot_path=snap_path,
                )

            phase_end = time.time()
            db_logger.log_phase('VEHICLE_GREEN', phase_start, phase_end,
                                triggered_by_button=triggered)

            if stop_event.is_set():
                break

            # ───── VEHICLE_AMBER ─────
            with shared_state['lock']:
                shared_state['current_state'] = 'VEHICLE_AMBER'
            display.show_vehicle_amber()
            phase_start = time.time()

            _sleep(AMBER_DURATION, stop_event)

            phase_end = time.time()
            db_logger.log_phase('VEHICLE_AMBER', phase_start, phase_end,
                                triggered_by_button=False)
            if stop_event.is_set():
                break

            # ───── VEHICLE_RED ─────
            with shared_state['lock']:
                shared_state['current_state'] = 'VEHICLE_RED'
            display.show_vehicle_red()
            phase_start = time.time()

            _sleep(PRE_CROSS_RED_DURATION, stop_event)

            phase_end = time.time()
            db_logger.log_phase('VEHICLE_RED', phase_start, phase_end,
                                triggered_by_button=False)
            if stop_event.is_set():
                break

            # ───── PEDESTRIAN_CROSS ─────
            with shared_state['lock']:
                shared_state['current_state'] = 'PEDESTRIAN_CROSS'
            display.show_pedestrian_cross()
            phase_start = time.time()

            # Update wait_time in DB (time from button press → crossing start)
            if press_row_id is not None and triggered:
                wait = phase_start - press_time
                db_logger.update_wait_time(press_row_id, wait)

            # Buzzer beeps during crossing phase
            _buzzer_beep(count=3)

            _sleep(PEDESTRIAN_CROSS_DURATION, stop_event)

            phase_end = time.time()
            db_logger.log_phase('PEDESTRIAN_CROSS', phase_start, phase_end,
                                triggered_by_button=False)
            if stop_event.is_set():
                break

            # ───── PEDESTRIAN_CLEARANCE ─────
            with shared_state['lock']:
                shared_state['current_state'] = 'PEDESTRIAN_CLEARANCE'
            phase_start = time.time()

            # Flashing display runs for the clearance duration
            display.show_pedestrian_clearance(CLEARANCE_DURATION, stop_event)

            phase_end = time.time()
            db_logger.log_phase('PEDESTRIAN_CLEARANCE', phase_start, phase_end,
                                triggered_by_button=False)

            # Discard any button presses that arrived during non-green phases
            with shared_state['lock']:
                shared_state['button_pressed'] = False

        except Exception as e:
            print(f"[fsm] ERROR in FSM loop: {e}")
            time.sleep(1)

    print("[fsm] FSM thread exiting.")


def start_fsm_thread(shared_state, stop_event):
    """Launch the FSM in a daemon thread."""
    t = threading.Thread(
        target=fsm_loop,
        args=(shared_state, stop_event),
        name="FSM",
        daemon=True,
    )
    t.start()
    return t
