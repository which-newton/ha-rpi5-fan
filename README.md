# Raspberry Pi 5 Fan Control for Home Assistant

Live fan-curve control for the **Raspberry Pi 5's 4-pin fan header** — the Active
Cooler, the official case fan, or the fan on an M.2 HAT+ — from inside Home
Assistant. Adjust the thresholds with sliders and watch the fan respond, the way
you would in a PC's BIOS.

[![hacs](https://img.shields.io/badge/HACS-custom-41BDF5.svg)](https://hacs.xyz)

## Why this exists

Every other Home Assistant fan integration for the Pi drives a **GPIO-wired fan
with software PWM**. None of them can touch the Pi 5's dedicated fan header,
because that fan is owned by the kernel's `pwm-fan` driver and steered by the
thermal governor.

That matters if a HAT is involved: on an M.2 HAT+ the same airflow cools the
**NVMe**, and the stock curve does not start the fan until **50 °C**. The drive
often wants it sooner.

## It keeps the kernel as the safety net

This is the important design decision. There are two ways to control this fan:

| Approach | What it does | Risk |
|---|---|---|
| **Rewrite trip points** *(what this uses)* | Retunes the curve the governor enforces | **None** — the kernel stays in charge, so the last curve keeps being enforced even if Home Assistant dies |
| Write raw PWM | Requires `thermal_zone/mode = disabled` | A crashed HA leaves the machine with **no thermal management at all** |

So the default control surface is the curve, not the fan speed. Raw fixed-speed
control exists but is **off by default**, and when enabled it is guarded by a
watchdog that hands the fan back to the kernel after 90 seconds without a new
value — and also on reload, on removal, and on unload.

The critical trip (`type=critical`, 110 °C — the thermal-shutdown threshold) is
never read or written.

## Entities

| Entity | Purpose |
|---|---|
| `fan.raspberry_pi_5_fan` | Preset curve profiles; measured duty cycle as percentage |
| `select.…_profile` | Quiet / Balanced / Cool / Aggressive / Manual |
| `number.…_fan_level_N_threshold` | **The live curve editor** — one slider per fan level |
| `sensor.…_speed` | Fan RPM |
| `sensor.…_duty_cycle` | Current PWM as % |
| `sensor.…_cpu_temperature` | Thermal zone temperature |
| `sensor.…_governor` | `enabled` / `disabled` (diagnostic) |
| `binary_sensor.…_manual_control_active` | **Problem** class — on while the kernel is not protecting the machine |

### Profiles

| Profile | Fan level thresholds |
|---|---|
| Quiet | 55 / 65 / 72 / 78 °C |
| **Balanced** | 50 / 60 / 67 / 75 °C — the Raspberry Pi factory curve |
| Cool | 45 / 53 / 60 / 68 °C |
| Aggressive | 40 / 47 / 54 / 61 °C |

Selecting a profile also returns the governor to `enabled`, because a profile
*is* a governor-managed curve.

## Installation

**HACS** → ⋮ → Custom repositories → add this repo as an **Integration** →
install → restart → *Settings → Devices & Services → Add Integration → Raspberry
Pi 5 Fan Control*.

Or copy `custom_components/rpi5_fan/` into your `config/custom_components/` and
restart.

## Requirements and limitations

**Home Assistant OS is the tested target.** Verified on HA OS 16.2 / core 2026.8.1
on a Pi 5 with an M.2 HAT+: the core container can write the thermal zone's trip
points with no add-on and no extra privileges.

**Home Assistant Container may be read-only.** If `/sys` is mounted read-only the
integration still reports temperature, RPM and duty cycle, but the controls
appear unavailable and a warning is logged. It degrades rather than failing.

**What this cannot change live:**

- **Hysteresis** — `trip_point_*_hyst` returns `EACCES` at runtime even though it
  advertises `-rw-r--r--`. Settable only at boot, via `dtparam=fan_tempN_hyst` in
  `config.txt`.
- **The PWM duty for each level** — also boot-only, via `dtparam=fan_tempN_speed`.
  This integration changes *when* each level engages, not *how hard* it blows.

To change either, add to `config.txt` and reboot:

```ini
dtparam=fan_temp0=40000
dtparam=fan_temp0_hyst=3000
dtparam=fan_temp0_speed=100
# …fan_temp1 / fan_temp2 / fan_temp3 likewise
```

Trip points set through this integration are **not persistent across reboots** on
their own — the kernel re-reads the device tree at boot. Either mirror your
preferred curve in `config.txt`, or re-apply the profile from an HA automation on
`homeassistant_start`.

## Notes for anyone reading the code

`hwmon` indices are **not stable across reboots** — on the development machine
`pwmfan` was `hwmon1` one morning and `hwmon3` the same afternoon. Nothing here
hard-codes an index; discovery matches on `hwmon*/name`.

Trip temperatures are sorted ascending before writing, because the kernel's
`step_wise` governor assumes monotonically increasing trips and an out-of-order
set produces a curve that never reaches its upper levels.

## Licence

MIT
