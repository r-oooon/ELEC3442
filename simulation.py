#!/usr/bin/env python3
"""
simulation.py — Pygame visual simulation of the pedestrian crossing.

Draws a top-down road with:
  • A marked crosswalk
  • Animated cars that flow when VEHICLE_GREEN / VEHICLE_AMBER, stop at red
  • Animated pedestrians that cross when PEDESTRIAN_CROSS, wait otherwise
  • A traffic light indicator synchronised to the FSM shared_state
  • A state label and live clock

Can be launched:
  1. From main.py (shared_state is passed in)        →  start_simulation()
  2. Standalone for demo (runs its own mock FSM loop) →  python3 simulation.py
"""

import sys
import os
import time
import math
import random
import threading

# ──────────────────────────────────────────────
# Pygame init (must happen before any pygame symbol is used)
# ──────────────────────────────────────────────
os.environ.setdefault("SDL_VIDEODRIVER", "x11")   # ensure X11 on Pi
import pygame
pygame.init()

# ──────────────────────────────────────────────
# Window / layout constants
# ──────────────────────────────────────────────
WIN_W, WIN_H = 900, 640
FPS = 30

# Colours
COL_GRASS      = (74, 140, 72)
COL_ROAD       = (60, 60, 60)
COL_ROAD_LINE  = (200, 200, 200)
COL_CROSSWALK  = (255, 255, 255)
COL_SIDEWALK   = (170, 170, 160)
COL_RED        = (220, 40, 40)
COL_AMBER      = (240, 180, 30)
COL_GREEN      = (40, 200, 60)
COL_OFF_LIGHT  = (50, 50, 50)
COL_CAR_BODY   = [(45, 100, 200), (200, 50, 50), (220, 200, 50),
                  (255, 255, 255), (100, 100, 100), (180, 100, 220)]
COL_PED_BODY   = (50, 50, 180)
COL_PED_HEAD   = (240, 200, 160)
COL_TEXT        = (255, 255, 255)
COL_PANEL      = (30, 30, 30)

# Road geometry (horizontal road across the middle)
ROAD_Y      = 240                       # top edge of road
ROAD_H      = 160                       # road height (two lanes)
LANE_H      = ROAD_H // 2
ROAD_CENTRE = ROAD_Y + ROAD_H // 2

# Crosswalk position (vertical stripe across the road)
CROSS_X     = WIN_W // 2 - 30          # left edge of crosswalk
CROSS_W     = 60                        # width of crosswalk zone
STRIPE_H    = 12
STRIPE_GAP  = 8

# Sidewalks
SIDEWALK_H  = 36

# Traffic-light box position (drawn to the right of crosswalk)
TL_X = CROSS_X + CROSS_W + 30
TL_Y = ROAD_Y - 110

# Car dimensions
CAR_W, CAR_H = 60, 30

# Pedestrian dimensions
PED_R = 8      # radius of head circle
PED_H = 28     # total sprite height

# Stop line for cars (just before the crosswalk)
STOP_LINE_X = CROSS_X - 10             # eastbound cars stop here (right edge)

# ──────────────────────────────────────────────
# Sprite classes
# ──────────────────────────────────────────────

class Car:
    """A simple rectangular car travelling left-to-right (top lane)
       or right-to-left (bottom lane)."""

    def __init__(self, lane):
        self.lane = lane                     # 0 = top (eastbound), 1 = bottom (westbound)
        self.colour = random.choice(COL_CAR_BODY)
        self.speed = random.uniform(2.0, 4.0)
        if self.lane == 0:
            self.x = -CAR_W - random.randint(0, 200)
            self.y = ROAD_Y + 15
            self.dir = 1                      # moving right
        else:
            self.x = WIN_W + random.randint(0, 200)
            self.y = ROAD_Y + LANE_H + 15
            self.dir = -1                     # moving left

    def update(self, cars_may_go):
        if cars_may_go:
            self.x += self.speed * self.dir
        else:
            # Stop before crosswalk if approaching it
            if self.dir == 1 and self.x + CAR_W < STOP_LINE_X:
                # Still before stop line — keep moving
                self.x += self.speed * self.dir
            elif self.dir == -1 and self.x > CROSS_X + CROSS_W + 10:
                self.x += self.speed * self.dir
            # else: stay put (stopped)

    def draw(self, surface):
        # Body
        rect = pygame.Rect(int(self.x), int(self.y), CAR_W, CAR_H)
        pygame.draw.rect(surface, self.colour, rect, border_radius=6)
        # Windshield
        if self.dir == 1:
            wr = pygame.Rect(int(self.x) + CAR_W - 16, int(self.y) + 4, 12, CAR_H - 8)
        else:
            wr = pygame.Rect(int(self.x) + 4, int(self.y) + 4, 12, CAR_H - 8)
        pygame.draw.rect(surface, (180, 220, 240), wr, border_radius=3)
        # Wheels
        for wy in [int(self.y) + 2, int(self.y) + CAR_H - 6]:
            for wx_off in [8, CAR_W - 14]:
                pygame.draw.rect(surface, (30, 30, 30),
                                 pygame.Rect(int(self.x) + wx_off, wy, 10, 5),
                                 border_radius=2)

    def off_screen(self):
        return self.x > WIN_W + 50 or self.x < -CAR_W - 50


class Pedestrian:
    """A simple stick-figure pedestrian that walks vertically across the road."""

    def __init__(self, from_top):
        self.from_top = from_top              # True = crossing top→bottom
        self.speed = random.uniform(1.2, 2.2)
        # Centre horizontally inside the crosswalk
        self.x = CROSS_X + CROSS_W // 2 + random.randint(-15, 15)
        if from_top:
            self.y = ROAD_Y - SIDEWALK_H - PED_H   # start above top sidewalk
            self.target_y = ROAD_Y + ROAD_H + SIDEWALK_H + PED_H
            self.dir = 1
        else:
            self.y = ROAD_Y + ROAD_H + SIDEWALK_H + PED_H
            self.target_y = ROAD_Y - SIDEWALK_H - PED_H
            self.dir = -1
        self.colour = (random.randint(30, 80), random.randint(30, 80),
                       random.randint(140, 220))
        self.walk_frame = random.random() * math.pi * 2  # phase offset for leg anim

    def update(self, peds_may_go):
        if peds_may_go:
            self.y += self.speed * self.dir
            self.walk_frame += 0.25
        else:
            # Wait at the edge of the road
            if self.from_top:
                if self.y < ROAD_Y - SIDEWALK_H // 2:
                    self.y += self.speed * self.dir    # still on sidewalk, approach
                    self.walk_frame += 0.25
            else:
                if self.y > ROAD_Y + ROAD_H + SIDEWALK_H // 2:
                    self.y += self.speed * self.dir
                    self.walk_frame += 0.25

    def draw(self, surface):
        cx, cy = int(self.x), int(self.y)
        # Head
        pygame.draw.circle(surface, COL_PED_HEAD, (cx, cy - PED_H + PED_R), PED_R)
        # Body
        pygame.draw.line(surface, self.colour, (cx, cy - PED_H + PED_R * 2),
                         (cx, cy - 6), 3)
        # Legs (animated)
        leg_swing = int(math.sin(self.walk_frame) * 6)
        pygame.draw.line(surface, self.colour, (cx, cy - 6),
                         (cx - leg_swing, cy + 2), 3)
        pygame.draw.line(surface, self.colour, (cx, cy - 6),
                         (cx + leg_swing, cy + 2), 3)
        # Arms
        arm_swing = int(math.sin(self.walk_frame + math.pi) * 5)
        arm_y = cy - PED_H + PED_R * 2 + 6
        pygame.draw.line(surface, self.colour, (cx, arm_y),
                         (cx - 7 - arm_swing, arm_y + 6), 2)
        pygame.draw.line(surface, self.colour, (cx, arm_y),
                         (cx + 7 + arm_swing, arm_y + 6), 2)

    def finished(self):
        if self.from_top:
            return self.y > self.target_y
        else:
            return self.y < self.target_y


# ──────────────────────────────────────────────
# Drawing helpers
# ──────────────────────────────────────────────

def draw_scene(surface, state_name, cars, peds, font_big, font_sm):
    """Render the full scene for one frame."""

    # ── Background / grass ──
    surface.fill(COL_GRASS)

    # ── Sidewalks ──
    pygame.draw.rect(surface, COL_SIDEWALK,
                     (0, ROAD_Y - SIDEWALK_H, WIN_W, SIDEWALK_H))
    pygame.draw.rect(surface, COL_SIDEWALK,
                     (0, ROAD_Y + ROAD_H, WIN_W, SIDEWALK_H))

    # ── Road ──
    pygame.draw.rect(surface, COL_ROAD, (0, ROAD_Y, WIN_W, ROAD_H))

    # Centre dashed line
    dash_len, gap = 30, 20
    for dx in range(0, WIN_W, dash_len + gap):
        pygame.draw.line(surface, COL_ROAD_LINE,
                         (dx, ROAD_CENTRE), (dx + dash_len, ROAD_CENTRE), 2)

    # ── Crosswalk stripes ──
    y = ROAD_Y
    while y + STRIPE_H <= ROAD_Y + ROAD_H:
        pygame.draw.rect(surface, COL_CROSSWALK,
                         (CROSS_X, y, CROSS_W, STRIPE_H))
        y += STRIPE_H + STRIPE_GAP

    # ── Cars ──
    for c in cars:
        c.draw(surface)

    # ── Pedestrians ──
    for p in peds:
        p.draw(surface)

    # ── Traffic light box ──
    _draw_traffic_light(surface, state_name)

    # ── Info panel ──
    _draw_info_panel(surface, state_name, font_big, font_sm)


def _draw_traffic_light(surface, state_name):
    """Draw a 3-bulb traffic light for vehicles and a walk/stop indicator
       for pedestrians."""
    # Housing
    housing = pygame.Rect(TL_X, TL_Y, 46, 120)
    pygame.draw.rect(surface, (20, 20, 20), housing, border_radius=8)
    pygame.draw.rect(surface, (80, 80, 80), housing, width=2, border_radius=8)
    # Pole
    pygame.draw.rect(surface, (80, 80, 80),
                     (TL_X + 19, TL_Y + 120, 8, ROAD_Y - TL_Y - 120))

    # Determine which bulbs are lit
    r_on = state_name in ('VEHICLE_RED', 'PEDESTRIAN_CROSS', 'PEDESTRIAN_CLEARANCE')
    a_on = state_name == 'VEHICLE_AMBER'
    g_on = state_name == 'VEHICLE_GREEN'

    cx = TL_X + 23
    bulb_r = 14
    for i, (colour_on, colour_off, is_on) in enumerate([
        (COL_RED,   COL_OFF_LIGHT, r_on),
        (COL_AMBER, COL_OFF_LIGHT, a_on),
        (COL_GREEN, COL_OFF_LIGHT, g_on),
    ]):
        cy = TL_Y + 22 + i * 34
        col = colour_on if is_on else colour_off
        pygame.draw.circle(surface, col, (cx, cy), bulb_r)
        # Glow effect when on
        if is_on:
            glow = pygame.Surface((bulb_r * 4, bulb_r * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*col, 50),
                               (bulb_r * 2, bulb_r * 2), bulb_r * 2)
            surface.blit(glow, (cx - bulb_r * 2, cy - bulb_r * 2))

    # Pedestrian signal (small box below)
    ped_box = pygame.Rect(TL_X + 3, TL_Y + 125, 40, 30)
    pygame.draw.rect(surface, (20, 20, 20), ped_box, border_radius=4)
    if state_name in ('PEDESTRIAN_CROSS', 'PEDESTRIAN_CLEARANCE'):
        # Walk — green figure
        if state_name == 'PEDESTRIAN_CLEARANCE':
            # Flashing effect
            show = (pygame.time.get_ticks() // 500) % 2 == 0
        else:
            show = True
        if show:
            pcx, pcy = TL_X + 23, TL_Y + 140
            pygame.draw.circle(surface, COL_GREEN, (pcx, pcy - 8), 4)
            pygame.draw.line(surface, COL_GREEN, (pcx, pcy - 4), (pcx, pcy + 2), 2)
            pygame.draw.line(surface, COL_GREEN, (pcx, pcy + 2), (pcx - 5, pcy + 8), 2)
            pygame.draw.line(surface, COL_GREEN, (pcx, pcy + 2), (pcx + 5, pcy + 8), 2)
    else:
        # Don't walk — red hand
        pcx, pcy = TL_X + 23, TL_Y + 140
        pygame.draw.circle(surface, COL_RED, (pcx, pcy - 4), 7)
        # Simple hand/stop symbol
        pygame.draw.line(surface, (180, 40, 40), (pcx - 3, pcy - 7),
                         (pcx + 3, pcy - 1), 2)
        pygame.draw.line(surface, (180, 40, 40), (pcx + 3, pcy - 7),
                         (pcx - 3, pcy - 1), 2)


def _draw_info_panel(surface, state_name, font_big, font_sm):
    """Overlay panel showing FSM state and instructions."""
    # Dark panel at bottom
    panel_h = 60
    panel = pygame.Surface((WIN_W, panel_h), pygame.SRCALPHA)
    panel.fill((*COL_PANEL, 210))
    surface.blit(panel, (0, WIN_H - panel_h))

    # State label
    friendly = {
        'STARTUP':               'Starting up…',
        'VEHICLE_GREEN':         'VEHICLE GREEN — Cars go',
        'VEHICLE_AMBER':         'VEHICLE AMBER — Caution',
        'VEHICLE_RED':           'VEHICLE RED — Cars stop',
        'PEDESTRIAN_CROSS':      'WALK — Pedestrians cross',
        'PEDESTRIAN_CLEARANCE':  'CLEARANCE — Hurry up!',
    }
    label = friendly.get(state_name, state_name)
    # Colour code the label
    if 'GREEN' in state_name:
        col = COL_GREEN
    elif 'AMBER' in state_name:
        col = COL_AMBER
    elif 'RED' in state_name:
        col = COL_RED
    elif 'CROSS' in state_name:
        col = COL_GREEN
    elif 'CLEARANCE' in state_name:
        col = COL_AMBER
    else:
        col = COL_TEXT

    txt = font_big.render(label, True, col)
    surface.blit(txt, (20, WIN_H - panel_h + 10))

    # Instructions
    hint = font_sm.render("Press SPACE = button press  |  Q / ESC = quit",
                          True, (160, 160, 160))
    surface.blit(hint, (20, WIN_H - panel_h + 38))

    # Clock
    t_str = time.strftime("%H:%M:%S")
    clock_txt = font_sm.render(t_str, True, COL_TEXT)
    surface.blit(clock_txt, (WIN_W - clock_txt.get_width() - 20,
                             WIN_H - panel_h + 10))


# ──────────────────────────────────────────────
# Main simulation loop
# ──────────────────────────────────────────────

def run_simulation(shared_state, stop_event):
    """
    Run the pygame window.  Reads shared_state['current_state'] each frame
    to stay in sync with the FSM.

    Parameters
    ----------
    shared_state : dict   (same dict used by fsm.py and button threads)
    stop_event   : threading.Event
    """
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("Smart Pedestrian Crossing — Simulation")
    clock = pygame.time.Clock()

    font_big = pygame.font.SysFont("dejavusans", 22, bold=True)
    font_sm  = pygame.font.SysFont("dejavusans", 14)

    cars = []
    peds = []

    car_spawn_timer = 0
    ped_spawn_timer = 0

    running = True
    while running and not stop_event.is_set():
        dt = clock.tick(FPS)

        # ── Events ──
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    running = False
                elif event.key == pygame.K_SPACE:
                    # Simulate a button press (Side A) via shared state
                    with shared_state['lock']:
                        shared_state['button_pressed'] = True
                        shared_state['button_side'] = 'A'
                        shared_state['press_time'] = time.time()
                        shared_state['input_type'] = 'simulation'

        # ── Read current FSM state ──
        with shared_state['lock']:
            state_name = shared_state['current_state']

        cars_may_go = state_name in ('VEHICLE_GREEN', 'VEHICLE_AMBER')
        peds_may_go = state_name in ('PEDESTRIAN_CROSS', 'PEDESTRIAN_CLEARANCE')

        # ── Spawn cars periodically when vehicles have green ──
        car_spawn_timer += dt
        if car_spawn_timer > 1200:   # every ~1.2 seconds
            car_spawn_timer = 0
            if len(cars) < 12:
                cars.append(Car(lane=random.choice([0, 1])))

        # ── Spawn pedestrians when crossing is active ──
        ped_spawn_timer += dt
        if peds_may_go and ped_spawn_timer > 1500:
            ped_spawn_timer = 0
            if len(peds) < 8:
                peds.append(Pedestrian(from_top=random.choice([True, False])))

        # ── Update sprites ──
        for c in cars:
            c.update(cars_may_go)
        cars = [c for c in cars if not c.off_screen()]

        for p in peds:
            p.update(peds_may_go)
        peds = [p for p in peds if not p.finished()]

        # ── Draw ──
        draw_scene(screen, state_name, cars, peds, font_big, font_sm)
        pygame.display.flip()

    pygame.quit()
    # If the user closed the pygame window, signal the whole system to stop
    stop_event.set()


def start_simulation(shared_state, stop_event):
    """Launch the simulation in a daemon thread (non-blocking)."""
    t = threading.Thread(
        target=run_simulation,
        args=(shared_state, stop_event),
        name="Simulation",
        daemon=True,
    )
    t.start()
    return t


# ──────────────────────────────────────────────
# Standalone mode — mock FSM that cycles through states
# ──────────────────────────────────────────────

def _mock_fsm(shared_state, stop_event):
    """Cycle through FSM states on a timer so the simulation can be
    previewed without any hardware."""
    from config import (MIN_GREEN_DURATION, AMBER_DURATION,
                        PRE_CROSS_RED_DURATION, PEDESTRIAN_CROSS_DURATION,
                        CLEARANCE_DURATION)

    phases = [
        ('VEHICLE_GREEN',         MIN_GREEN_DURATION),
        ('VEHICLE_AMBER',         AMBER_DURATION),
        ('VEHICLE_RED',           PRE_CROSS_RED_DURATION),
        ('PEDESTRIAN_CROSS',      PEDESTRIAN_CROSS_DURATION),
        ('PEDESTRIAN_CLEARANCE',  CLEARANCE_DURATION),
    ]

    while not stop_event.is_set():
        for phase, duration in phases:
            if stop_event.is_set():
                return
            with shared_state['lock']:
                shared_state['current_state'] = phase
            print(f"[mock-fsm] → {phase} ({duration}s)")
            # Interruptible sleep
            end = time.time() + duration
            while time.time() < end and not stop_event.is_set():
                time.sleep(0.1)


if __name__ == '__main__':
    print("Running simulation in standalone demo mode (mock FSM).")
    print("Press SPACE to simulate a button press.  Q or ESC to quit.\n")

    shared_state = {
        'lock':           threading.Lock(),
        'button_pressed': False,
        'button_side':    None,
        'press_time':     None,
        'input_type':     None,
        'current_state':  'VEHICLE_GREEN',
    }
    stop_event = threading.Event()

    # Run mock FSM in a background thread
    fsm_t = threading.Thread(target=_mock_fsm,
                             args=(shared_state, stop_event),
                             daemon=True)
    fsm_t.start()

    # Run simulation in the main thread (pygame prefers this)
    try:
        run_simulation(shared_state, stop_event)
    except KeyboardInterrupt:
        stop_event.set()
    print("Bye!")
