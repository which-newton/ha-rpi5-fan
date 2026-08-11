"""Raw sysfs access for the Raspberry Pi 5 fan and thermal zone.

Everything in here is blocking file I/O and must be called from an executor.

WHAT THIS TALKS TO
    The Pi 5's dedicated 4-pin fan header, driven by the kernel `pwm-fan` driver
    and steered by the thermal governor. This is NOT a GPIO software-PWM fan —
    every other Home Assistant fan integration for the Pi targets those, which is
    why none of them can control the official cooler or the Active Cooler on an
    M.2 HAT+.

WRITABILITY, verified on HA OS 16.2 / core 2026.8.1 from inside the core
container (no add-on, no extra privileges):

    thermal_zone/trip_point_{1..4}_temp   writable at runtime
    thermal_zone/trip_point_*_hyst        EACCES at runtime despite -rw-r--r--,
                                         settable only via config.txt dtparam
    thermal_zone/trip_point_0_*           type=critical, 110 C — never touched
    hwmon*/pwm1                           writable (0-255)
    hwmon*/pwm1_enable                    writable (1=manual, 2=governor)
    thermal_zone/mode                     writable (enabled|disabled)

WHY TRIP POINTS ARE THE DEFAULT CONTROL SURFACE
    Retuning trip points leaves the kernel governor in charge, so the curve last
    written keeps being enforced even if Home Assistant dies. Driving pwm1
    directly requires `mode=disabled`, and a crashed HA would then leave the
    machine with no thermal management at all. Manual mode therefore has to be
    opted into and is guarded by a watchdog.

hwmon indices are NOT stable across reboots (pwmfan was hwmon1 then hwmon3 on the
same machine within a day), so nothing here hard-codes an index.
"""
from __future__ import annotations

import glob
import logging
import os
from dataclasses import dataclass

_LOGGER = logging.getLogger(__name__)

THERMAL_GLOB = "/sys/class/thermal/thermal_zone*"
HWMON_GLOB = "/sys/class/hwmon/hwmon*"
FAN_HWMON_NAME = "pwmfan"
CPU_ZONE_TYPES = ("cpu-thermal", "cpu_thermal")

PWM_MAX = 255
PWM_ENABLE_MANUAL = 1
PWM_ENABLE_GOVERNOR = 2


class NotSupported(Exception):
    """Raised when this machine has no Pi 5 style pwm-fan thermal setup."""


def _read(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read().strip()
    except OSError:
        return None


def _read_int(path: str) -> int | None:
    raw = _read(path)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _write(path: str, value: str) -> bool:
    """Write and report success. Never raises — callers decide what a failure means."""
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(value)
        return True
    except OSError as err:
        _LOGGER.debug("write %s = %s failed: %s", path, value, err)
        return False


@dataclass(frozen=True)
class Paths:
    """Resolved sysfs locations for this machine."""

    zone: str
    hwmon: str
    active_trips: tuple[int, ...]  # trip indices with type == "active"

    @property
    def temp(self) -> str:
        return f"{self.zone}/temp"

    @property
    def mode(self) -> str:
        return f"{self.zone}/mode"

    @property
    def pwm(self) -> str:
        return f"{self.hwmon}/pwm1"

    @property
    def pwm_enable(self) -> str:
        return f"{self.hwmon}/pwm1_enable"

    @property
    def rpm(self) -> str:
        return f"{self.hwmon}/fan1_input"

    def trip_temp(self, index: int) -> str:
        return f"{self.zone}/trip_point_{index}_temp"


def discover() -> Paths:
    """Locate the CPU thermal zone and the pwm-fan hwmon, or raise NotSupported."""
    zone = None
    for candidate in sorted(glob.glob(THERMAL_GLOB)):
        if (_read(f"{candidate}/type") or "") in CPU_ZONE_TYPES:
            zone = candidate
            break
    if zone is None:
        raise NotSupported("no cpu-thermal thermal zone found")

    hwmon = None
    for candidate in sorted(glob.glob(HWMON_GLOB)):
        if (_read(f"{candidate}/name") or "") == FAN_HWMON_NAME:
            hwmon = candidate
            break
    if hwmon is None:
        raise NotSupported(
            "no 'pwmfan' hwmon found — this integration drives the Pi 5 fan header, "
            "not a GPIO-wired fan"
        )

    # Only 'active' trips steer the fan. A 'critical' trip is the shutdown
    # threshold and must never be rewritten.
    active: list[int] = []
    for index in range(16):
        trip_type = _read(f"{zone}/trip_point_{index}_type")
        if trip_type is None:
            continue
        if trip_type == "active":
            active.append(index)
    if not active:
        raise NotSupported(f"{zone} exposes no active trip points")

    _LOGGER.debug("discovered zone=%s hwmon=%s active_trips=%s", zone, hwmon, active)
    return Paths(zone=zone, hwmon=hwmon, active_trips=tuple(active))


def writable(paths: Paths) -> bool:
    """True when trip points can actually be written on this install.

    Home Assistant Container installs frequently mount /sys read-only, in which
    case the integration still reports temperature and RPM but cannot control
    anything. Checked with os.access rather than a probe write so nothing is
    changed as a side effect of setup.
    """
    if not paths.active_trips:
        return False
    return os.access(paths.trip_temp(paths.active_trips[0]), os.W_OK)


def read_state(paths: Paths) -> dict:
    """One consistent snapshot per poll."""
    trips_mc = [_read_int(paths.trip_temp(i)) for i in paths.active_trips]
    pwm = _read_int(paths.pwm)
    return {
        "temp_c": (lambda v: v / 1000 if v is not None else None)(_read_int(paths.temp)),
        "rpm": _read_int(paths.rpm),
        "pwm": pwm,
        "pwm_percent": (round(pwm / PWM_MAX * 100) if pwm is not None else None),
        "pwm_enable": _read_int(paths.pwm_enable),
        "governor": (_read(paths.mode) or "unknown"),
        # °C, in the same order as paths.active_trips
        "trips_c": [None if v is None else round(v / 1000) for v in trips_mc],
    }


def set_trips(paths: Paths, temps_c: list[int]) -> bool:
    """Write the active trip temperatures. Governor stays in charge.

    Values are sorted ascending before writing: the kernel's step_wise governor
    assumes monotonically increasing trips, and an out-of-order set produces a
    curve that never reaches its upper levels.
    """
    ordered = sorted(int(t) for t in temps_c)
    ok = True
    for index, temp_c in zip(paths.active_trips, ordered, strict=False):
        if not _write(paths.trip_temp(index), str(int(temp_c) * 1000)):
            ok = False
    return ok


def governor_enabled(paths: Paths, enabled: bool) -> bool:
    """Hand the fan back to the kernel, or take it away."""
    if enabled:
        # Order matters: re-arm the governor's own control of the PWM first, then
        # re-enable the zone, so there is no window where neither is steering.
        _write(paths.pwm_enable, str(PWM_ENABLE_GOVERNOR))
        return _write(paths.mode, "enabled")
    _write(paths.mode, "disabled")
    return _write(paths.pwm_enable, str(PWM_ENABLE_MANUAL))


def set_pwm(paths: Paths, percent: int) -> bool:
    """Set raw fan PWM as a percentage. Requires the governor to be disabled.

    Callers must have taken manual control first; otherwise the governor will
    overwrite this on its next evaluation and the change appears to silently
    do nothing.
    """
    percent = max(0, min(100, int(percent)))
    return _write(paths.pwm, str(round(percent / 100 * PWM_MAX)))
