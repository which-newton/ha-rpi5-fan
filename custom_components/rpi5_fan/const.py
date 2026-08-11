"""Constants for Raspberry Pi 5 Fan Control."""
from __future__ import annotations

DOMAIN = "rpi5_fan"

CONF_ALLOW_MANUAL = "allow_manual"
CONF_SCAN_SECONDS = "scan_seconds"

DEFAULT_SCAN_SECONDS = 15
# How long the governor may stay disabled without a fresh manual write before the
# watchdog puts the kernel back in charge. Deliberately short: this is the only
# thing standing between "Home Assistant crashed" and "the Pi has no thermal
# management at all".
MANUAL_WATCHDOG_SECONDS = 90

# Four active trip points. trip_point_0 is type=critical (110 C shutdown) and is
# NEVER touched — reading or writing it is out of scope for this integration.
NUM_TRIPS = 4

PRESET_QUIET = "quiet"
PRESET_BALANCED = "balanced"
PRESET_COOL = "cool"
PRESET_AGGRESSIVE = "aggressive"
PRESET_MANUAL = "manual"

# Trip temperatures in °C for each profile, coolest-first ordering enforced.
# `balanced` reproduces the Raspberry Pi 5 factory curve (50/60/67.5/75).
PROFILES: dict[str, tuple[int, int, int, int]] = {
    PRESET_QUIET: (55, 65, 72, 78),
    PRESET_BALANCED: (50, 60, 67, 75),
    PRESET_COOL: (45, 53, 60, 68),
    PRESET_AGGRESSIVE: (40, 47, 54, 61),
}

PRESETS = [PRESET_QUIET, PRESET_BALANCED, PRESET_COOL, PRESET_AGGRESSIVE, PRESET_MANUAL]

# Sanity bounds for user-set trip points. The lower bound stops someone pinning
# the fan on permanently; the upper bound keeps every trip well clear of the
# 110 C critical trip.
TRIP_MIN_C = 30
TRIP_MAX_C = 85
