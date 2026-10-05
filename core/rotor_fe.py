"""Finite-element lateral rotordynamics of a stepped shaft with discs.

Rayleigh beam elements (Euler-Bernoulli bending, consistent translational mass,
consistent rotary inertia and gyroscopic matrices) in two lateral planes, rigid
discs (mass, diametral and polar inertia) at nodes, and isotropic linear bearings
(stiffness and viscous damping) on translational DOFs.

Two-plane DOFs [x, beta = dx/dz, y, alpha = dy/dz] are combined into complex
coordinates u = x + i y, phi = beta + i alpha (exact for isotropic supports):

    M u'' + (C - i Omega G) u' + K u = f

Disc gyroscopic rows (+Ip Omega alpha', -Ip Omega beta') become -i Omega Ip phi'.
Positive-frequency eigenvalues are forward whirl, negative are backward.
Shear deformation is neglected (Euler-Bernoulli): for short, thick sections the
model overestimates frequencies; the benchmark and mesh-convergence tests in
tests/test_rotor_fe.py quantify the discretisation part only.

This is a preliminary supported-rotor model: support stiffness and damping are
inputs with stated uncertainty, not measured bearing/housing coefficients.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.linalg import eig


@dataclass
class ShaftSection:
    z0: float           # start position along axis [m]
    length: float       # [m]
    od: float           # outer diameter [m]
    id: float = 0.0     # inner diameter [m]
    E: float = 205e9
    rho: float = 7850.0
    name: str = ''
    mass_only: bool = False   # contributes mass/inertia but no bending stiffness (e.g. a sleeve)

    @property
    def A(self):
        return math.pi / 4 * (self.od ** 2 - self.id ** 2)

    @property
    def I(self):
        return math.pi / 64 * (self.od ** 4 - self.id ** 4)


@dataclass
class Disc:
    z: float
    mass: float
    Ip: float           # polar inertia [kg m2]
    Id: float           # diametral inertia about its own CG [kg m2]
    name: str = ''


@dataclass
class Support:
    z: float
    k: float            # radial stiffness [N/m] (bearing in series with housing)
    c: float = 0.0      # viscous damping [N s/m]
    name: str = ''


@dataclass
class RotorModel:
    sections: list
    discs: list = field(default_factory=list)
    supports: list = field(default_factory=list)
    max_element_length: float = 0.005

    def __post_init__(self):
        if not self.sections:
            raise ValueError('rotor needs at least one shaft section')
        secs = sorted(self.sections, key=lambda s: s.z0)
        for a, b in zip(secs, secs[1:]):
            if abs(a.z0 + a.length - b.z0) > 1e-9:
                raise ValueError(f'shaft sections must be contiguous ({a.name} -> {b.name})')
        for s in secs:
            if s.length <= 0 or s.od <= 0 or not 0 <= s.id < s.od:
                raise ValueError(f'invalid shaft section {s.name}')
        self.sections = secs
        z_start, z_end = secs[0].z0, secs[-1].z0 + secs[-1].length
        for d in self.discs:
            if not z_start - 1e-9 <= d.z <= z_end + 1e-9:
                raise ValueError(f'disc {d.name} at {d.z} m is off the shaft')
        for sp in self.supports:
            if not z_start - 1e-9 <= sp.z <= z_end + 1e-9:
                raise ValueError(f'support {sp.name} at {sp.z} m is off the shaft')
            if sp.k <= 0 or sp.c < 0:
                raise ValueError(f'support {sp.name} needs positive stiffness')
        # node positions: section ends, disc and support positions, then subdivision
        pts = {round(z_start, 12), round(z_end, 12)}
        for s in secs:
            pts.add(round(s.z0, 12))
        for d in self.discs:
            pts.add(round(d.z, 12))
        for sp in self.supports:
            pts.add(round(sp.z, 12))
        pts = sorted(pts)
        nodes = []
        for a, b in zip(pts, pts[1:]):
            n = max(1, int(math.ceil((b - a) / self.max_element_length - 1e-9)))
            nodes.extend(a + (b - a) * i / n for i in range(n))
        nodes.append(pts[-1])
        self.z = np.array(nodes)
        self.n_nodes = len(nodes)
        self.ndof = 4 * self.n_nodes
        self._assemble()

    def _section_at(self, zm):
        for s in self.sections:
            if s.z0 - 1e-12 <= zm <= s.z0 + s.length + 1e-12:
                return s
        raise ValueError('element outside shaft')

    def node_index(self, z):
        i = int(np.argmin(abs(self.z - z)))
        if abs(self.z[i] - z) > 1e-9:
            raise ValueError(f'no node at z = {z}')
        return i

    def _assemble(self):
        """Planar matrices for complex lateral coordinates u = x + i y, phi = beta + i alpha.

        With isotropic supports the two-plane equations combine exactly into
            M u'' + (C - i Omega G) u' + K u = f
        (the disc gyroscopic rows +Ip Omega alpha' / -Ip Omega beta' become
        -i Omega Ip phi'). Eigenvalues s = i w with w > 0 are forward whirl,
        w < 0 backward whirl. Anisotropic supports are not representable here.
        """
        nd = 2 * self.n_nodes
        M = np.zeros((nd, nd)); K = np.zeros((nd, nd)); G = np.zeros((nd, nd)); C = np.zeros((nd, nd))
        for e in range(self.n_nodes - 1):
            L = self.z[e + 1] - self.z[e]
            s = self._section_at(0.5 * (self.z[e] + self.z[e + 1]))
            EI = 0.0 if s.mass_only else s.E * s.I
            rA, rI = s.rho * s.A, s.rho * s.I
            k = EI / L ** 3 * np.array([[12, 6 * L, -12, 6 * L], [6 * L, 4 * L * L, -6 * L, 2 * L * L],
                                        [-12, -6 * L, 12, -6 * L], [6 * L, 2 * L * L, -6 * L, 4 * L * L]])
            mt = rA * L / 420 * np.array([[156, 22 * L, 54, -13 * L], [22 * L, 4 * L * L, 13 * L, -3 * L * L],
                                          [54, 13 * L, 156, -22 * L], [-13 * L, -3 * L * L, -22 * L, 4 * L * L]])
            mr = rI / (30 * L) * np.array([[36, 3 * L, -36, 3 * L], [3 * L, 4 * L * L, -3 * L, -L * L],
                                           [-36, -3 * L, 36, -3 * L], [3 * L, -L * L, -3 * L, 4 * L * L]])
            idx = [2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3]
            K[np.ix_(idx, idx)] += k
            M[np.ix_(idx, idx)] += mt + mr
            G[np.ix_(idx, idx)] += 2 * mr      # polar = 2 x diametral for a circular section
        for d in self.discs:
            i = self.node_index(d.z)
            M[2 * i, 2 * i] += d.mass
            M[2 * i + 1, 2 * i + 1] += d.Id
            G[2 * i + 1, 2 * i + 1] += d.Ip
        for sp in self.supports:
            i = self.node_index(sp.z)
            K[2 * i, 2 * i] += sp.k
            C[2 * i, 2 * i] += sp.c
        self.ndof = nd
        self.M, self.K, self.G, self.C = M, K, G, C
        self._Minv = np.linalg.inv(M)

    # -- results ------------------------------------------------------------------
    def total_mass(self):
        return float(sum(s.rho * s.A * s.length for s in self.sections) + sum(d.mass for d in self.discs))

    def modes(self, speed_rpm=0.0, n=8):
        """Natural frequencies [rpm] at a spin speed, with whirl direction and damping."""
        Om = speed_rpm * 2 * math.pi / 60
        nd = self.ndof
        A = np.zeros((2 * nd, 2 * nd), dtype=complex)
        A[:nd, nd:] = np.eye(nd)
        A[nd:, :nd] = -self._Minv @ self.K
        A[nd:, nd:] = -self._Minv @ (self.C - 1j * Om * self.G)
        lam, vec = eig(A)
        out = []
        for j in range(len(lam)):
            w = lam[j].imag
            if abs(w) <= 1e-6:
                continue
            X = vec[:nd:2, j]
            k = int(np.argmax(np.abs(X)))
            zeta = -lam[j].real / abs(lam[j])
            out.append(dict(freq_rpm=abs(w) * 60 / (2 * math.pi), whirl='forward' if w > 0 else 'backward',
                            damping_ratio=zeta,
                            shape_x=np.real(X * np.exp(-1j * np.angle(X[k]))) / max(abs(X[k]), 1e-30)))
        out.sort(key=lambda m: m['freq_rpm'])
        return out[:n]

    def campbell(self, speeds_rpm, n=6):
        return [(N, self.modes(N, n)) for N in speeds_rpm]

    def critical_speeds(self, N_max_rpm, n_modes=4, n_grid=40):
        """Forward-whirl synchronous critical speeds (omega_f(N) = N) up to N_max."""
        grid = np.linspace(0.02 * N_max_rpm, N_max_rpm, n_grid)   # avoid zero-speed degeneracy

        def fwd(N):
            f = [m['freq_rpm'] for m in self.modes(N, 4 * n_modes) if m['whirl'] == 'forward'][:n_modes]
            return f + [np.inf] * (n_modes - len(f))

        fw = np.array([fwd(N) for N in grid])
        crit = []
        for k in range(n_modes):
            d = fw[:, k] - grid
            for i in range(len(grid) - 1):
                if np.isfinite(d[i]) and np.isfinite(d[i + 1]) and d[i] > 0 >= d[i + 1]:
                    from scipy.optimize import brentq
                    Nc = brentq(lambda N: fwd(N)[k] - N, grid[i], grid[i + 1], xtol=1.0, maxiter=30)
                    crit.append(dict(mode=k + 1, N_crit_rpm=Nc))
        return sorted(crit, key=lambda c: c['N_crit_rpm'])

    def unbalance_response(self, speed_rpm, unbalance):
        """Steady synchronous (forward) response to unbalances [(z, m*e [kg m], phase rad)].

        Returns orbit radius [m] at every node and dynamic bearing forces [N].
        """
        Om = speed_rpm * 2 * math.pi / 60
        F = np.zeros(self.ndof, dtype=complex)
        for z, me, ph in unbalance:
            F[2 * self.node_index(z)] += me * Om ** 2 * np.exp(1j * ph)
        D = self.K - Om ** 2 * (self.M - self.G) + 1j * Om * self.C
        q = np.linalg.solve(D, F)
        amp = np.abs(q[0::2])
        forces = {sp.name: float(abs(sp.k + 1j * Om * sp.c) * amp[self.node_index(sp.z)]) for sp in self.supports}
        return amp, forces
