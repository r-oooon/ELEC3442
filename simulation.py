#!/usr/bin/env python3
"""
simulation.py — Pygame visual simulation of the pedestrian crossing.
Updated with queuing logic, static animations, and improved crossing behavior.
"""

import sys
import os
import time
import math
import random
import threading

# ──────────────────────────────────────────────
# Pygame init
# ──────────────────────────────────────────────
os.environ.setdefault("SDL_VIDEODRIVER", "x11")
import pygame
pygame.init()

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────
WIN_W, WIN_H = 900, 640
FPS = 30

COL_GRASS = (74, 140, 72)
COL_ROAD = (60, 60, 60)
COL_ROAD_LINE = (200, 200, 200)
COL_CROSSWALK = (255, 255, 255)
COL_SIDEWALK = (170, 170, 160)
COL_RED = (220, 40, 40)
COL_AMBER = (240, 180, 30)
COL_GREEN = (40, 200, 60)
COL_OFF_LIGHT = (50, 50, 50)
COL_CAR_BODY = [(45, 100, 200), (200, 50, 50), (220, 200, 50),
                (255, 255, 255), (100, 100, 100), (180, 100, 220)]
COL_PED_BODY = (50, 50, 180)
COL_PED_HEAD = (240, 200, 160)
COL_TEXT = (255, 255, 255)
COL_PANEL = (30, 30, 30)

ROAD_Y = 240
ROAD_H = 160
LANE_H = ROAD_H // 2
ROAD_CENTRE = ROAD_Y + ROAD_H // 2
CROSS_X = WIN_W // 2 - 30
CROSS_W = 60
STRIPE_H = 12
STRIPE_GAP = 8
SIDEWALK_H = 36
TL_X = CROSS_X + CROSS_W + 30
TL_Y = ROAD_Y - 110
CAR_W, CAR_H = 60, 30
PED_R = 8
PED_H = 28
STOP_LINE_X = CROSS_X - 10


# ──────────────────────────────────────────────
# Sprite classes
# ──────────────────────────────────────────────

class Car:
    def __init__(self, lane):
        self.lane = lane
        self.colour = random.choice(COL_CAR_BODY)
        self.speed = random.uniform(2.0, 4.0)
        if self.lane == 0:
            self.x = -CAR_W - random.randint(0, 200)
            self.y = ROAD_Y + 15
            self.dir = 1
        else:
            self.x = WIN_W + random.randint(0, 200)
            self.y = ROAD_Y + LANE_H + 15
            self.dir = -1

    def update(self, cars_may_go, car_ahead=None):
        can_move = True

        # 1. FIX: Traffic Light & Stop Line Check
        if not cars_may_go:
            if self.dir == 1 and self.x + CAR_W >= STOP_LINE_X - 5 and self.x < STOP_LINE_X:
                can_move = False
            elif self.dir == -1 and self.x <= CROSS_X + CROSS_W + 15 and self.x > CROSS_X + CROSS_W:
                can_move = False

        # 2. FIX: Queuing Logic (check car ahead)
        if car_ahead:
            dist = 0
            if self.dir == 1:
                dist = car_ahead.x - (self.x + CAR_W)
            else:
                dist = self.x - (car_ahead.x + CAR_W)

            if dist < 15:  # Minimum gap between cars
                can_move = False

        if can_move:
            self.x += self.speed * self.dir

    def draw(self, surface):
        rect = pygame.Rect(int(self.x), int(self.y), CAR_W, CAR_H)
        pygame.draw.rect(surface, self.colour, rect, border_radius=6)
        if self.dir == 1:
            wr = pygame.Rect(int(self.x) + CAR_W - 16, int(self.y) + 4, 12, CAR_H - 8)
        else:
            wr = pygame.Rect(int(self.x) + 4, int(self.y) + 4, 12, CAR_H - 8)
        pygame.draw.rect(surface, (180, 220, 240), wr, border_radius=3)
        for wy in [int(self.y) + 2, int(self.y) + CAR_H - 6]:
            for wx_off in [8, CAR_W - 14]:
                pygame.draw.rect(surface, (30, 30, 30),
                                 pygame.Rect(int(self.x) + wx_off, wy, 10, 5),
                                 border_radius=2)

    def off_screen(self):
        return self.x > WIN_W + 100 or self.x < -CAR_W - 100


class Pedestrian:
    def __init__(self, from_top):
        self.from_top = from_top
        self.speed = random.uniform(1.2, 2.2)
        self.x = CROSS_X + CROSS_W // 2 + random.randint(-15, 15)
        if from_top:
            self.y = ROAD_Y - SIDEWALK_H - PED_H
            self.target_y = ROAD_Y + ROAD_H + SIDEWALK_H + PED_H
            self.dir = 1
        else:
            self.y = ROAD_Y + ROAD_H + SIDEWALK_H + PED_H
            self.target_y = ROAD_Y - SIDEWALK_H - PED_H
            self.dir = -1
        self.colour = (random.randint(30, 80), random.randint(30, 80),
                       random.randint(140, 220))

    def update(self, peds_may_go):
        # FIX: Ensure pedestrians finish crossing if they are already on the road
        is_on_road = ROAD_Y - 10 < self.y < ROAD_Y + ROAD_H + 10

        if peds_may_go or is_on_road:
            self.y += self.speed * self.dir
        else:
            # Still on sidewalk, approach the edge
            if self.from_top and self.y < ROAD_Y - SIDEWALK_H:
                self.y += self.speed * self.dir
            elif not self.from_top and self.y > ROAD_Y + ROAD_H + SIDEWALK_H:
                self.y += self.speed * self.dir

    def draw(self, surface):
        cx, cy = int(self.x), int(self.y)
        pygame.draw.circle(surface, COL_PED_HEAD, (cx, cy - PED_H + PED_R), PED_R)
        pygame.draw.line(surface, self.colour, (cx, cy - PED_H + PED_R * 2), (cx, cy - 6), 3)
        # FIX: Static legs (no animation)
        pygame.draw.line(surface, self.colour, (cx, cy - 6), (cx - 4, cy + 2), 3)
        pygame.draw.line(surface, self.colour, (cx, cy - 6), (cx + 4, cy + 2), 3)
        # Static arms
        arm_y = cy - 30
        pygame.draw.line(surface, self.colour, (cx, arm_y), (cx - 7, arm_y + 6), 2)
        pygame.draw.line(surface, self.colour, (cx, arm_y), (cx + 7, arm_y + 6), 2)

    def finished(self):
        return self.y > self.target_y if self.from_top else self.y < self.target_y

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
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("Smart Pedestrian Crossing — Simulation")
    clock = pygame.time.Clock()

    font_big = pygame.font.SysFont("dejavusans", 22, bold=True)
    font_sm = pygame.font.SysFont("dejavusans", 14)

    cars, peds = [], []
    car_spawn_timer, ped_spawn_timer = 0, 0

    while not stop_event.is_set():
        dt = clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                stop_event.set()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                with shared_state['lock']:
                    shared_state['button_pressed'] = True

        with shared_state['lock']:
            state_name = shared_state['current_state']

        cars_may_go = state_name in ('VEHICLE_GREEN', 'VEHICLE_AMBER')
        peds_may_go = state_name in ('PEDESTRIAN_CROSS', 'PEDESTRIAN_CLEARANCE')

        # Car Spawning
        car_spawn_timer += dt
        if car_spawn_timer > 1200 and len(cars) < 12:
            car_spawn_timer = 0
            cars.append(Car(lane=random.choice([0, 1])))

        # FIX: No spawning during flashing (PEDESTRIAN_CLEARANCE)
        ped_spawn_timer += dt
        if state_name == 'PEDESTRIAN_CROSS' and ped_spawn_timer > 1500 and len(peds) < 8:
            ped_spawn_timer = 0
            peds.append(Pedestrian(from_top=random.choice([True, False])))

        # Update Cars (with Queuing)
        # Sort by X to identify the "car ahead" in each lane
        lane0 = sorted([c for c in cars if c.lane == 0], key=lambda c: c.x, reverse=True)
        lane1 = sorted([c for c in cars if c.lane == 1], key=lambda c: c.x)

        for i, c in enumerate(lane0):
            c.update(cars_may_go, lane0[i - 1] if i > 0 else None)
        for i, c in enumerate(lane1):
            c.update(cars_may_go, lane1[i - 1] if i > 0 else None)

        cars = [c for c in cars if not c.off_screen()]

        for p in peds:
            p.update(peds_may_go)
        peds = [p for p in peds if not p.finished()]

        # Drawing (uses original drawing helper)
        from simulation import draw_scene
        draw_scene(screen, state_name, cars, peds, font_big, font_sm)
        pygame.display.flip()

    pygame.quit()
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
