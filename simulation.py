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
        arm_y = cy - PED_H + PED_R * 2 + 6
        pygame.draw.line(surface, self.colour, (cx, arm_y), (cx - 7, arm_y + 6), 2)
        pygame.draw.line(surface, self.colour, (cx, arm_y), (cx + 7, arm_y + 6), 2)

    def finished(self):
        return self.y > self.target_y if self.from_top else self.y < self.target_y


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