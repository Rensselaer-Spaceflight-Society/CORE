"""Synthetic start/run/shutdown controller and plant interface (software tests only).

The controller is a state machine that consumes timestamped sensor samples and
returns actuator commands. Every command goes through HardwareOutputs, which is
DISABLED: enabling it raises, so this code cannot drive hardware. Thresholds come
from data/systems/signals.yaml 'illustrative_thresholds' and are simulation
values, not approved operating limits.

SyntheticPlant is an illustrative spool model (power ~ N^3 drag, fuel-driven
turbine power) used only to exercise the controller logic. It is NOT the CORE
engine model and must not be used for performance or limit setting.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import yaml

from core.records import ROOT

STATES = ('SAFE_OFF', 'PRECHECK', 'SPINUP', 'IGNITION', 'FUEL_RAMP', 'ASSIST', 'SELF_SUSTAIN_CHECK', 'RUN',
          'SHUTDOWN', 'FAULT')


class HardwareDisabled(RuntimeError):
    pass


class HardwareOutputs:
    """Command sink. Records commands; refuses to be enabled."""

    def __init__(self):
        self.history = []

    @property
    def enabled(self):
        return False

    def enable(self):
        raise HardwareDisabled('hardware outputs are disabled in this repository; no hardware control is approved')

    def write(self, t, cmds):
        self.history.append((t, dict(cmds)))


@dataclass
class Sample:
    value: float
    t: float
    valid: bool = True


def load_signals():
    return yaml.safe_load(open(ROOT / 'data/systems/signals.yaml', encoding='utf-8'))


@dataclass
class Sequence:
    """ILLUSTRATIVE sequence parameters (simulation only)."""
    spinup_rpm: float = 12000.0
    ignition_dwell_s: float = 1.5
    fuel_ramp_rate: float = 0.08          # fuel command per second
    assist_release_rpm: float = 40000.0   # unknown for CORE; below the map - illustrative
    idle_fuel_cmd: float = 0.35
    max_fuel_slew: float = 0.25           # per second
    self_sustain_check_s: float = 2.0
    shutdown_done_rpm: float = 3000.0


class Controller:
    REQUIRED = {'SPINUP': ('N',), 'IGNITION': ('N', 'EGT'), 'FUEL_RAMP': ('N', 'EGT'), 'ASSIST': ('N', 'EGT'),
                'SELF_SUSTAIN_CHECK': ('N', 'EGT'), 'RUN': ('N', 'EGT', 'P03', 'PF')}

    def __init__(self, seq=None, outputs=None):
        sig = load_signals()
        self.th = sig['illustrative_thresholds']
        self.ranges = {c['id']: c['range'] for c in sig['channels']}
        self.seq = seq or Sequence()
        self.out = outputs or HardwareOutputs()
        self.state = 'SAFE_OFF'
        self.t_state = 0.0
        self.fuel = 0.0
        self.fault = None
        self.egt_at_ignition = None
        self.log = []

    def _go(self, t, state, why=''):
        self.log.append((t, self.state, state, why))
        self.state, self.t_state = state, t

    def _validate(self, t, sensors, names):
        for n in names:
            s = sensors.get(n)
            if s is None:
                return f'{n}_MISSING'
            if not s.valid or not math.isfinite(s.value) or not math.isfinite(s.t):
                return f'{n}_INVALID'
            if s.t > t:
                return f'{n}_FUTURE_TIMESTAMP'
            if t - s.t > self.th['sensor_stale_s']:
                return f'{n}_STALE'
            lo, hi = self.ranges[n]
            if not lo <= s.value <= hi:
                return f'{n}_OUT_OF_RANGE'
        return None

    def _cmd(self, t, fuel_target, valve, igniter, starter, dt):
        target = min(max(fuel_target, 0.0), 1.0)                    # saturation
        step = self.seq.max_fuel_slew * dt
        self.fuel = min(max(target, self.fuel - step), self.fuel + step) if valve else 0.0
        cmds = dict(FUEL_CMD=self.fuel if valve else 0.0, VALVE_OPEN=bool(valve), IGNITER_ON=bool(igniter),
                    STARTER_CMD=min(max(starter, 0.0), 1.0))
        self.out.write(t, cmds)
        return cmds

    def step(self, t, dt, sensors, start=False, stop=False, estop=False):
        if not math.isfinite(t) or not math.isfinite(dt) or dt <= 0:
            self.fault = 'INVALID_TIME'
            self._go(t, 'FAULT', self.fault)
            return self._cmd(t, 0, False, False, 0, 0)
        st = self.state
        if estop and st == 'SAFE_OFF':
            return self._cmd(t, 0, False, False, 0, dt)
        if estop and st not in ('SAFE_OFF', 'FAULT'):
            self.fault = 'ESTOP'
            self._go(t, 'SHUTDOWN', 'e-stop')
        elif stop and st not in ('SAFE_OFF', 'SHUTDOWN', 'FAULT'):
            self._go(t, 'SHUTDOWN', 'operator stop')
        st = self.state
        if st in self.REQUIRED:
            bad = self._validate(t, sensors, self.REQUIRED[st])
            if bad:
                self.fault = bad
                self._go(t, 'SHUTDOWN', bad)
                st = self.state
            else:
                N, egt = sensors['N'].value, sensors.get('EGT', Sample(0, t)).value
                if N > self.th['overspeed_rpm']:
                    self.fault = 'OVERSPEED'
                    self._go(t, 'SHUTDOWN', 'overspeed')
                elif egt > self.th['egt_trip_K']:
                    self.fault = 'OVERTEMP'
                    self._go(t, 'SHUTDOWN', 'EGT trip')
                st = self.state
        N = sensors['N'].value if 'N' in sensors and sensors['N'].valid else 0.0
        egt = sensors['EGT'].value if 'EGT' in sensors and sensors['EGT'].valid else 0.0
        el = t - self.t_state
        if st == 'SAFE_OFF':
            if start:
                self.fault = None
                self._go(t, 'PRECHECK')
            return self._cmd(t, 0, False, False, 0, dt)
        if st == 'PRECHECK':
            bad = self._validate(t, sensors, ('N', 'EGT', 'PF'))
            if bad:
                self.fault = bad
                self._go(t, 'FAULT', bad)
            else:
                self._go(t, 'SPINUP')
            return self._cmd(t, 0, False, False, 0, dt)
        if st == 'SPINUP':
            if N >= self.seq.spinup_rpm:
                self.egt_at_ignition = egt
                self._go(t, 'IGNITION')
            return self._cmd(t, 0, False, False, 1.0, dt)
        if st == 'IGNITION':
            if el >= self.seq.ignition_dwell_s:
                self._go(t, 'FUEL_RAMP')
            return self._cmd(t, 0, False, True, 1.0, dt)
        if st == 'FUEL_RAMP':
            if egt - self.egt_at_ignition >= self.th['light_off_egt_rise_K']:
                self._go(t, 'ASSIST', 'light-off detected')
            elif el > self.th['light_off_timeout_s']:
                self.fault = 'FAILURE_TO_LIGHT'
                self._go(t, 'SHUTDOWN', 'no EGT rise')
                return self._cmd(t, 0, False, False, 0, dt)
            return self._cmd(t, min(self.seq.fuel_ramp_rate * el, self.seq.idle_fuel_cmd), True, True, 1.0, dt)
        if st == 'ASSIST':
            if N >= self.seq.assist_release_rpm:
                self._go(t, 'SELF_SUSTAIN_CHECK', 'starter released')
                return self._cmd(t, self.seq.idle_fuel_cmd, True, False, 0.0, dt)
            return self._cmd(t, self.seq.idle_fuel_cmd, True, False, 1.0, dt)
        if st == 'SELF_SUSTAIN_CHECK':
            if el >= self.seq.self_sustain_check_s:
                if N >= self.seq.assist_release_rpm * 0.95:
                    self._go(t, 'RUN', 'speed held without starter')
                else:
                    self.fault = 'NO_SELF_SUSTAIN'
                    self._go(t, 'SHUTDOWN', 'speed decayed without starter')
                    return self._cmd(t, 0, False, False, 0, dt)
            return self._cmd(t, self.seq.idle_fuel_cmd, True, False, 0.0, dt)
        if st == 'RUN':
            return self._cmd(t, self.seq.idle_fuel_cmd, True, False, 0.0, dt)
        if st == 'SHUTDOWN':
            if N <= self.seq.shutdown_done_rpm:
                self._go(t, 'FAULT' if self.fault else 'SAFE_OFF', 'spool stopped')
            return self._cmd(t, 0, False, False, 0, dt)
        return self._cmd(t, 0, False, False, 0, dt)   # FAULT: latched, everything off


@dataclass
class SyntheticPlant:
    """Illustrative spool + EGT model for logic tests (NOT the CORE engine)."""
    I: float = 1.2e-4
    k_drag: float = 3.0e-12       # W / rpm^3
    k_turb: float = 4.3e-7        # W / (fuel_cmd * rpm^2) when lit (idle equilibrium ~50 krpm)
    k_start: float = 0.30         # starter torque N m at full command (falls with speed)
    N: float = 0.0
    egt: float = 293.0
    lit: bool = False
    lights: bool = True
    tau_egt: float = 1.0

    def step(self, dt, cmds):
        w = max(self.N * 2 * math.pi / 60, 1e-3)
        if cmds['IGNITER_ON'] and cmds['VALVE_OPEN'] and cmds['FUEL_CMD'] > 0.05 and self.lights:
            self.lit = True
        if not cmds['VALVE_OPEN'] or cmds['FUEL_CMD'] <= 0.0:
            self.lit = False
        P_t = self.k_turb * cmds['FUEL_CMD'] * self.N ** 2 if self.lit else 0.0
        T_start = self.k_start * cmds['STARTER_CMD'] * max(0.0, 1 - self.N / 60000.0)
        P = T_start * w + P_t - self.k_drag * self.N ** 3
        self.N = max(self.N + P / (self.I * w) * dt * 60 / (2 * math.pi), 0.0) if self.N > 50 or P > 0 else 0.0
        egt_target = 293.0 + (600.0 * cmds['FUEL_CMD'] / 0.35 if self.lit else 0.0)
        self.egt += (egt_target - self.egt) * dt / self.tau_egt
        return self.N, self.egt


def simulate(plant, ctrl, t_end=40.0, dt=0.02, faults=None, stop_at=None):
    """Closed-loop run. faults: dict(name -> callable(t, sensors) -> sensors)."""
    t = 0.0
    cmds = dict(FUEL_CMD=0.0, VALVE_OPEN=False, IGNITER_ON=False, STARTER_CMD=0.0)
    trace = []
    while t < t_end:
        N, egt = plant.step(dt, cmds)
        sensors = dict(N=Sample(N, t), EGT=Sample(egt, t), P03=Sample(5000 + 0.00001 * N * N, t), PF=Sample(20000, t))
        for f in (faults or {}).values():
            sensors = f(t, sensors)
        cmds = ctrl.step(t, dt, sensors, start=(t < dt), stop=(stop_at is not None and t >= stop_at))
        trace.append((t, ctrl.state, N, egt, dict(cmds)))
        t += dt
    return trace
