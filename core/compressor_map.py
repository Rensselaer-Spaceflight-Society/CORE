"""Compressor characteristic from a digitized or team-supplied map.

Each speed line is parameterised by beta in [0, 1]: 0 at the digitized surge end,
1 at the choke end, linear in corrected flow along the line. Between speed lines
the map is interpolated at constant beta, linearly in corrected speed. Nothing
is extrapolated: a speed outside the outermost lines or a beta outside [0, 1]
raises MapDomainError. Efficiency is the plotted isentropic efficiency.

Corrected quantities follow the map's own reference state:

    Q_corr = mdot * sqrt(T_in / T_ref) / (P_in / P_ref)
    N_corr = N / sqrt(T_in / T_ref)

Two surge-margin metrics are reported, both at constant corrected speed:

    SM_flow = 1 - Q_surge / Q_op                         (flow margin)
    SM_pr   = (PR_surge / PR_op) * (Q_op / Q_surge) - 1   (pressure-ratio margin)

Robustness cases may apply explicit offsets (flow scale, efficiency delta,
pressure-rise scale). They are reported with every result and never written
back into the digitized data.
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator

from core import gas, thermo
from core.records import ROOT, load_record, file_sha256

LB_MIN_TO_KG_S = 0.45359237 / 60.0


class MapDomainError(ValueError):
    """Requested point lies outside the supported map domain."""


@dataclass
class MapOffsets:
    flow_scale: float = 1.0      # multiplies corrected flow at fixed beta and speed
    eta_delta: float = 0.0       # added to isentropic efficiency
    pr_rise_scale: float = 1.0   # multiplies (PR - 1)
    reference_override: tuple | None = None  # (T_ref_K, P_ref_Pa) alternative convention

    def as_dict(self):
        return dict(flow_scale=self.flow_scale, eta_delta=self.eta_delta,
                    pr_rise_scale=self.pr_rise_scale, reference_override=self.reference_override)


@dataclass
class SpeedLine:
    n_corr: float
    q: np.ndarray            # corrected flow along line, kg/s, increasing
    pr: np.ndarray
    eta_q: np.ndarray        # anchor flows for efficiency, kg/s
    eta: np.ndarray
    eta_conf: list = field(default_factory=list)

    def __post_init__(self):
        if np.any(np.diff(self.q) <= 0):
            raise ValueError(f'speed line {self.n_corr}: flow must increase from surge to choke')
        if np.any(np.diff(self.eta_q) <= 0):
            raise ValueError(f'speed line {self.n_corr}: efficiency anchors must be ordered')
        self.q_s, self.q_c = float(self.q[0]), float(self.q[-1])
        self._pr = PchipInterpolator(self.q, self.pr)
        self._eta = PchipInterpolator(self.eta_q, self.eta)

    def at_beta(self, beta):
        q = self.q_s + beta * (self.q_c - self.q_s)
        qe = min(max(q, self.eta_q[0]), self.eta_q[-1])
        return q, float(self._pr(q)), float(self._eta(qe))


class CompressorMap:
    def __init__(self, record_path, offsets: MapOffsets | None = None):
        self.record = load_record(record_path)
        if self.record.data.get('record_type') != 'compressor_map':
            raise ValueError(f'{record_path}: not a compressor_map record')
        data_file = ROOT / self.record.data['data_file']
        self.data_file = data_file
        self.files = [self.record.path, data_file]
        self.offsets = offsets or MapOffsets()
        if self.offsets.reference_override:
            self.T_ref, self.P_ref = self.offsets.reference_override
        else:
            self.T_ref = self.record.si('reference_temperature')
            self.P_ref = self.record.si('reference_pressure')
        lines, eta = {}, {}
        with open(data_file, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                n = float(row['speed_line_rpm_corrected'])
                if row['record'] == 'line':
                    lines.setdefault(n, []).append((float(row['Q_corr_lb_min']), float(row['PR'])))
                elif row['record'] == 'eta':
                    eta.setdefault(n, []).append((float(row['Q_corr_lb_min']), float(row['eta_isen_tt']),
                                                  row['confidence']))
                else:
                    raise ValueError(f'unknown map record {row["record"]!r}')
        if set(lines) != set(eta):
            raise ValueError('every speed line needs both line and efficiency data')
        self.lines = []
        for n in sorted(lines):
            pts = sorted(lines[n]); e = sorted(eta[n])
            self.lines.append(SpeedLine(
                n, np.array([p[0] for p in pts]) * LB_MIN_TO_KG_S, np.array([p[1] for p in pts]),
                np.array([p[0] for p in e]) * LB_MIN_TO_KG_S, np.array([p[1] for p in e]),
                [p[2] for p in e]))
        self.n_min, self.n_max = self.lines[0].n_corr, self.lines[-1].n_corr
        self.eta_medium_max_speed = 100452.0

    def identity(self):
        return {str(Path(p).relative_to(ROOT).as_posix()): file_sha256(p) for p in self.files}

    # -- corrected conditions -------------------------------------------------
    def corrected_speed(self, N_rpm, T_in):
        thermo.positive(N=N_rpm, T_in=T_in)
        return N_rpm / math.sqrt(T_in / self.T_ref)

    def corrected_flow(self, mdot, T_in, P_in):
        thermo.positive(mdot=mdot, T_in=T_in, P_in=P_in)
        return mdot * math.sqrt(T_in / self.T_ref) / (P_in / self.P_ref)

    def actual_flow(self, q_corr, T_in, P_in):
        return q_corr * (P_in / self.P_ref) / math.sqrt(T_in / self.T_ref)

    # -- interpolation --------------------------------------------------------
    def _bracket(self, n_corr):
        if not math.isfinite(n_corr) or n_corr < self.n_min - 1e-9 or n_corr > self.n_max + 1e-9:
            raise MapDomainError(f'corrected speed {n_corr:,.0f} rpm outside digitized lines '
                                 f'{self.n_min:,.0f}-{self.n_max:,.0f} rpm; no extrapolation')
        for lo, hi in zip(self.lines, self.lines[1:]):
            if lo.n_corr <= n_corr <= hi.n_corr:
                return lo, hi, (n_corr - lo.n_corr) / (hi.n_corr - lo.n_corr)
        return self.lines[-1], self.lines[-1], 0.0

    def point(self, n_corr, beta):
        """(Q_corr kg/s, PR, eta) at corrected speed and beta, offsets applied."""
        if not math.isfinite(beta) or beta < -1e-12 or beta > 1 + 1e-12:
            raise MapDomainError(f'beta {beta:.4f} outside [0, 1] (surge/choke ends)')
        lo, hi, w = self._bracket(n_corr)
        q1, pr1, e1 = lo.at_beta(beta)
        q2, pr2, e2 = hi.at_beta(beta)
        q = (1 - w) * q1 + w * q2
        pr = (1 - w) * pr1 + w * pr2
        eta = (1 - w) * e1 + w * e2
        o = self.offsets
        q *= o.flow_scale
        pr = 1.0 + (pr - 1.0) * o.pr_rise_scale
        eta += o.eta_delta
        if not 0 < eta < 1:
            raise MapDomainError('efficiency offset produced an invalid efficiency')
        return q, pr, eta

    def surge_point(self, n_corr):
        q, pr, _ = self.point(n_corr, 0.0)
        return q, pr

    def surge_margins(self, n_corr, q_op, pr_op):
        qs, prs = self.surge_point(n_corr)
        return dict(SM_flow=1.0 - qs / q_op, SM_pr=(prs / pr_op) * (q_op / qs) - 1.0)

    def efficiency_confidence(self, n_corr):
        return 'medium' if n_corr <= self.eta_medium_max_speed + 1e-6 else 'low'

    def beta_for_flow(self, n_corr, q_corr):
        """Inverse along a corrected speed: beta giving corrected flow q_corr."""
        f = lambda b: self.point(n_corr, b)[0] - q_corr
        lo, hi = f(0.0), f(1.0)
        if lo > 0 or hi < 0:
            raise MapDomainError(f'corrected flow {q_corr:.4f} kg/s outside speed line at {n_corr:,.0f} rpm')
        return thermo.bisect(f, 0.0, 1.0, tol=1e-10)

    # -- thermodynamic state ------------------------------------------------------
    def operate(self, N_rpm, beta, T_in, P_in, R=287.05):
        """Physical operating point at shaft speed and beta with the given inlet total state."""
        n_corr = self.corrected_speed(N_rpm, T_in)
        q, pr, eta = self.point(n_corr, beta)
        mdot = self.actual_flow(q, T_in, P_in)
        T_out_s = thermo.isentropic_temperature(T_in, pr, R=R)
        w = (gas.h_air(T_out_s) - gas.h_air(T_in)) / eta
        T_out = thermo.temperature(gas.h_air(T_in) + w)
        sm = self.surge_margins(n_corr, q, pr)
        return dict(N_rpm=N_rpm, N_corr_rpm=n_corr, beta=beta, Q_corr_kg_s=q, PR=pr, eta=eta,
                    mdot_kg_s=mdot, T_out_K=T_out, P_out_Pa=P_in * pr, w_J_kg=w,
                    power_W=mdot * w, eta_confidence=self.efficiency_confidence(n_corr), **sm)


def default_map(offsets=None):
    return CompressorMap(ROOT / 'data/maps/gt3076r_compressor.yaml', offsets)
