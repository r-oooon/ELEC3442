#!/usr/bin/env python3
"""
analytics.py — Standalone visualization script.
Reads from crossing.db and generates five charts saved as PNG files
in the charts/ directory.  Can be run on any machine with
Python 3 + matplotlib + sqlite3 (no hardware required).

Usage:
    python3 analytics.py            # Generate all charts
    python3 analytics.py --no-show  # Save PNGs without displaying
"""

import os
import sys
import sqlite3
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

from config import DB_PATH, CHARTS_DIR

# If running headless (SSH without X11), use Agg backend
if '--no-show' in sys.argv or os.environ.get('DISPLAY') is None:
    matplotlib.use('Agg')


# ──────────────────────────────────────────────
# Data loaders
# ──────────────────────────────────────────────
def _load_button_presses():
    """Return all button_presses rows as a list of dicts."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM button_presses ORDER BY timestamp"
        ).fetchall()
    return [dict(r) for r in rows]


def _load_phases():
    """Return all phase_log rows as a list of dicts."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM phase_log ORDER BY start_time"
        ).fetchall()
    return [dict(r) for r in rows]


# ──────────────────────────────────────────────
# Chart 1: Hourly Demand Bar Chart
# ──────────────────────────────────────────────
def chart_hourly_demand(presses):
    """Bar chart of button presses grouped by hour of day."""
    hours = [p['hour'] for p in presses if p['hour'] is not None]
    counts = [0] * 24
    for h in hours:
        counts[h] += 1

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(range(24), counts, color='steelblue', edgecolor='white')
    ax.set_xlabel('Hour of Day')
    ax.set_ylabel('Number of Button Presses')
    ax.set_title('Pedestrian Demand by Hour of Day')
    ax.set_xticks(range(24))
    ax.set_xlim(-0.5, 23.5)
    fig.tight_layout()

    path = os.path.join(CHARTS_DIR, 'chart1_hourly_demand.png')
    fig.savefig(path, dpi=150)
    print(f"  Saved: {path}")
    return fig


# ──────────────────────────────────────────────
# Chart 2: Ghost Press Rate by Hour
# ──────────────────────────────────────────────
def chart_ghost_press_rate(presses):
    """Grouped bar chart: genuine vs ghost presses per hour."""
    genuine = [0] * 24
    ghost   = [0] * 24
    for p in presses:
        h = p['hour']
        if h is None:
            continue
        if p['presence_detected']:
            genuine[h] += 1
        else:
            ghost[h] += 1

    x = np.arange(24)
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - width / 2, genuine, width, label='Genuine', color='seagreen')
    ax.bar(x + width / 2, ghost,   width, label='Ghost',   color='tomato')
    ax.set_xlabel('Hour of Day')
    ax.set_ylabel('Number of Presses')
    ax.set_title('Genuine vs Ghost Presses by Hour')
    ax.set_xticks(x)
    ax.legend()
    fig.tight_layout()

    path = os.path.join(CHARTS_DIR, 'chart2_ghost_press_rate.png')
    fig.savefig(path, dpi=150)
    print(f"  Saved: {path}")
    return fig


# ──────────────────────────────────────────────
# Chart 3: Crossing Frequency vs Temperature
# ──────────────────────────────────────────────
def chart_temp_vs_frequency(presses):
    """Scatter plot of press count vs temperature with trend line."""
    temps = [p['temperature'] for p in presses
             if p['temperature'] is not None]

    if not temps:
        print("  [chart3] No temperature data — skipping.")
        return None

    # Bin temperatures to nearest degree for frequency
    from collections import Counter
    rounded = [round(t) for t in temps]
    freq = Counter(rounded)
    x = sorted(freq.keys())
    y = [freq[t] for t in x]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(x, y, color='coral', s=60, zorder=3)

    # Linear trend line
    if len(x) >= 2:
        z = np.polyfit(x, y, 1)
        poly = np.poly1d(z)
        x_line = np.linspace(min(x), max(x), 100)
        ax.plot(x_line, poly(x_line), '--', color='grey', label='Trend')
        ax.legend()

    ax.set_xlabel('Temperature (°C)')
    ax.set_ylabel('Number of Presses')
    ax.set_title('Crossing Frequency vs Temperature')
    fig.tight_layout()

    path = os.path.join(CHARTS_DIR, 'chart3_temp_frequency.png')
    fig.savefig(path, dpi=150)
    print(f"  Saved: {path}")
    return fig


# ──────────────────────────────────────────────
# Chart 4: Phase Duration Over Time
# ──────────────────────────────────────────────
def chart_phase_duration(phases):
    """
    Line chart of VEHICLE_GREEN durations over time.
    Points where green was cut short by a button press are annotated.
    """
    greens = [p for p in phases if p['phase'] == 'VEHICLE_GREEN']
    if not greens:
        print("  [chart4] No VEHICLE_GREEN phases logged — skipping.")
        return None

    indices = range(1, len(greens) + 1)
    durations = [g['duration'] for g in greens]
    triggered = [g['triggered_by_button'] for g in greens]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(list(indices), durations, '-o', color='forestgreen',
            markersize=5, label='Green Duration')

    # Highlight button-triggered shortening
    for i, (dur, trig) in enumerate(zip(durations, triggered)):
        if trig:
            ax.annotate('btn', (i + 1, dur),
                        textcoords='offset points', xytext=(0, 10),
                        ha='center', fontsize=8, color='red')

    ax.set_xlabel('Green Phase Sequence')
    ax.set_ylabel('Duration (seconds)')
    ax.set_title('VEHICLE_GREEN Phase Duration Over Time')
    ax.legend()
    fig.tight_layout()

    path = os.path.join(CHARTS_DIR, 'chart4_phase_duration.png')
    fig.savefig(path, dpi=150)
    print(f"  Saved: {path}")
    return fig


# ──────────────────────────────────────────────
# Chart 5: Wait Time Distribution Histogram
# ──────────────────────────────────────────────
def chart_wait_time(presses):
    """Histogram of pedestrian wait times (button press → crossing start)."""
    waits = [p['wait_time'] for p in presses
             if p['wait_time'] is not None]

    if not waits:
        print("  [chart5] No wait time data — skipping.")
        return None

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(waits, bins=15, color='mediumpurple', edgecolor='white')
    ax.axvline(np.mean(waits), color='red', linestyle='--',
               label=f'Mean = {np.mean(waits):.1f}s')
    ax.set_xlabel('Wait Time (seconds)')
    ax.set_ylabel('Frequency')
    ax.set_title('Pedestrian Wait Time Distribution')
    ax.legend()
    fig.tight_layout()

    path = os.path.join(CHARTS_DIR, 'chart5_wait_time.png')
    fig.savefig(path, dpi=150)
    print(f"  Saved: {path}")
    return fig


# ──────────────────────────────────────────────
# Master function
# ──────────────────────────────────────────────
def generate_all():
    """Produce all five charts from the current database."""
    os.makedirs(CHARTS_DIR, exist_ok=True)

    print(f"\nLoading data from {DB_PATH} ...")
    presses = _load_button_presses()
    phases  = _load_phases()
    print(f"  {len(presses)} button presses, {len(phases)} phase entries.\n")

    if not presses and not phases:
        print("No data in the database yet. Run the system first!")
        return

    print("Generating charts:")
    figs = []
    figs.append(chart_hourly_demand(presses))
    figs.append(chart_ghost_press_rate(presses))
    figs.append(chart_temp_vs_frequency(presses))
    figs.append(chart_phase_duration(phases))
    figs.append(chart_wait_time(presses))

    print(f"\nAll charts saved to {CHARTS_DIR}/")

    if '--no-show' not in sys.argv:
        plt.show()


if __name__ == '__main__':
    generate_all()
