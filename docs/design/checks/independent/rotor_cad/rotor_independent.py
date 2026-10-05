"""Independent rotordynamics check for PD-1 (Phase 2 audit, fork D).

Does NOT import core.rotor_fe, core.assembly, core.cad_export, core.exports,
core.figures or modules.*.  Rotor geometry is read from the run outputs
(assembly_stack.json: shaft sections, rotating masses, bearings) and the shaft
material from data/components/materials.yaml.  Independent methods:

  A  hand mass properties             vs cad_bundle ROT_* / SH01_MASS
  B  rigid 2-DOF rotor (translation + tilt, gyroscopic, damped springs)
  C  own lumped-mass Euler-Bernoulli beam model (diagonal mass, complex whirl
     coordinates, damped supports, gyroscopic) - different discretisation
     from the run's consistent-mass FE
  D  Myklestad-Prohl transfer matrices, synchronous forward whirl, undamped
  E  separation margin, support-stiffness sensitivity and threshold stiffness
  F  unbalance (ISO G2.5) orbit vs the run's orbit check
Validation of C and D on closed-form cases runs first.

Usage (repo root):  python rotor_independent.py [run_or_snapshot_folder]
Exit 1 if a like-for-like comparison differs by more than TOL.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import yaml
from scipy.optimize import brentq

TOL = 0.01
RUN = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('docs/design/results/pd1-jm85')
RPM = 60.0 / (2.0 * math.pi)
fails = []


def line(name, indep, repo, tol=TOL, info=False, unit=''):
    if repo is None or indep is None:
        print(f'{name:<64} indep={indep} repo={repo} {"INFO" if info else "OPEN"}')
        return
    d = (indep - repo) / repo if repo else (indep - repo)
    tag = 'INFO' if info else ('PASS' if abs(d) <= tol else 'DIFF')
    if tag == 'DIFF':
        fails.append(name)
    print(f'{name:<64} indep={indep:<14.6g} repo={repo:<14.6g} diff={100 * d:+8.3f}% {tag} {unit}')


# ---------------------------------------------------------------- inputs
stack = json.loads((RUN / 'assembly_stack.json').read_text())
rd = json.loads((RUN / 'rotordynamics.json').read_text())
cad = {p['name']: p for p in json.loads((RUN / 'cad' / 'cad_bundle.json').read_text())['parameters']}
checks = {c['name']: c for c in json.loads((RUN / 'candidate_checks.json').read_text())}
mats = yaml.safe_load(Path('data/components/materials.yaml').read_text())['parameters']
case = yaml.safe_load(Path('config/cases/pd1-jm85.yaml').read_text())
E = mats['s4140_E']['value'] * 1e9
RHO = mats['s4140_rho']['value']
N_LOW, N_HIGH = case['operating']['steady_range_rpm']
SECS = [(s['z0_m'], s['length_m'], s['od_m'], s['name']) for s in stack['shaft_sections']]
DISCS = [(m['x_m'], m['mass_kg'], m['Ip_kg_m2'], m['Id_kg_m2'], m['name']) for m in stack['rotating_masses']]
SUPS = [(b['x_m'], b['k_N_m'], b['c_N_s_m'], b['name']) for b in stack['bearings']]
FE_CRIT = [c['N_crit_rpm'] for c in rd['critical_speeds']]
print(f'run folder: {RUN}   steady range {N_LOW}-{N_HIGH} rpm   E={E:.4g} Pa rho={RHO}')
print(f'supports: {[(round(x * 1e3, 3), k, c) for x, k, c, _ in SUPS]}')
print(f'run FE critical speeds: {[round(c, 1) for c in FE_CRIT]}   separation {rd["separation_frac"]:.5f}')

# ---------------------------------------------------------------- A  mass properties
for a, b in zip(SECS, SECS[1:]):
    if abs(a[0] + a[1] - b[0]) > 1e-9:
        fails.append('shaft sections not contiguous')
        print('DIFF shaft sections not contiguous', a[3], b[3])
ms = [RHO * math.pi / 4 * d * d * L for z0, L, d, _ in SECS]
m_shaft = sum(ms)
m_tot = m_shaft + sum(d[1] for d in DISCS)
xcg = (sum(mi * (z0 + L / 2) for mi, (z0, L, d, _) in zip(ms, SECS)) + sum(d[1] * d[0] for d in DISCS)) / m_tot
Ip_tot = sum(mi * d * d / 8 for mi, (z0, L, d, _) in zip(ms, SECS)) + sum(d[2] for d in DISCS)
It_cg = (sum(mi * (d * d / 16 + L * L / 12) + mi * (z0 + L / 2 - xcg) ** 2 for mi, (z0, L, d, _) in zip(ms, SECS))
         + sum(dd[3] + dd[1] * (dd[0] - xcg) ** 2 for dd in DISCS))
summ = stack['summary']
print('\n[A] mass properties (hand: solid cylinders + rigid discs)')
line('shaft mass [kg] vs SH01_MASS', m_shaft, cad['SH01_MASS']['value'], tol=1e-4)
line('rotor mass [kg] vs ROT_MASS', m_tot, cad['ROT_MASS']['value'], tol=1e-4)
line('rotor CG x [mm] vs ROT_CG_X', xcg * 1e3, cad['ROT_CG_X']['value'], tol=1e-4)
line('rotor polar inertia [kg m2] vs stack rotor_Ip_kg_m2', Ip_tot, summ['rotor_Ip_kg_m2'], tol=1e-4)
line('rotor polar inertia [kg m2] vs ROT_IP (bundle, rounded)', Ip_tot, cad['ROT_IP']['value'], tol=0.005)
line('bearing span [mm]', (SUPS[1][0] - SUPS[0][0]) * 1e3, summ['bearing_span_m'] * 1e3, tol=1e-6)
print(f'    diametral inertia about CG (not exported by the run) It = {It_cg:.4e} kg m2; Ip/It = {Ip_tot / It_cg:.3f}')
# hand check of the small rotating parts (ring formula)
ring = lambda od, idd, L: 7850 * math.pi / 4 * (od * od - idd * idd) * L
hand = {'compressor nut': ring(0.010, 0.006, 0.006), 'turbine nut': ring(0.013, 0.008, 0.007),
        'front seal sleeve': ring(0.013, 0.006, 0.005), 'rear spacer': ring(0.0135, 0.010, 0.004),
        'front bearing inner ring + balls (share)': 0.45 * ring(0.026, 0.010, 0.008) * 0.5}
for d in DISCS:
    if d[4] in hand:
        line(f'  part mass [kg] {d[4][:40]}', hand[d[4]], d[1], tol=1e-6)


# ---------------------------------------------------------------- generic whirl eigen-analysis
def whirl_modes(M, C, G, K, N_rpm):
    """Complex whirl coordinates: M q'' + (C - i W G) q' + K q = 0. Returns forward/backward modes."""
    W = N_rpm / RPM
    n = M.shape[0]
    Minv = np.linalg.inv(M)
    A = np.zeros((2 * n, 2 * n), dtype=complex)
    A[:n, n:] = np.eye(n)
    A[n:, :n] = -Minv @ K
    A[n:, n:] = -Minv @ (C - 1j * W * G)
    lam = np.linalg.eigvals(A)
    out = []
    for l in lam:
        if abs(l.imag) <= 1e-6:
            continue   # overdamped (real) roots are not whirl modes
        out.append((abs(l.imag) * RPM, 'F' if l.imag > 0 else 'B', -l.real / abs(l)))
    return sorted(out)


def forward(model, N, kmax=4):
    return [f for f, w, z in whirl_modes(*model, N) if w == 'F'][:kmax]


def crossings(model, N_max, kmax=4, n_grid=36):
    grid = np.linspace(0.02 * N_max, N_max, n_grid)
    fw = []
    for N in grid:
        f = forward(model, N, kmax)
        fw.append(f + [np.inf] * (kmax - len(f)))
    fw = np.array(fw)
    out = []
    for k in range(kmax):
        d = fw[:, k] - grid
        for i in range(len(grid) - 1):
            if np.isfinite(d[i]) and np.isfinite(d[i + 1]) and d[i] > 0 >= d[i + 1]:
                g = lambda N: (forward(model, N, kmax) + [np.inf] * kmax)[k] - N
                out.append(brentq(g, grid[i], grid[i + 1], xtol=0.5))
    return sorted(out)


# ---------------------------------------------------------------- B  rigid rotor
def rigid_model(k=None, c=None):
    a = [x - xcg for x, *_ in SUPS]
    ks = [k if k is not None else s[1] for s in SUPS]
    cs = [c if c is not None else s[2] for s in SUPS]
    M = np.diag([m_tot, It_cg]).astype(complex)
    G = np.diag([0.0, Ip_tot]).astype(complex)
    K = np.array([[sum(ks), sum(kk * aa for kk, aa in zip(ks, a))],
                  [sum(kk * aa for kk, aa in zip(ks, a)), sum(kk * aa * aa for kk, aa in zip(ks, a))]], dtype=complex)
    C = np.array([[sum(cs), sum(cc * aa for cc, aa in zip(cs, a))],
                  [sum(cc * aa for cc, aa in zip(cs, a)), sum(cc * aa * aa for cc, aa in zip(cs, a))]], dtype=complex)
    return M, C, G, K


# ---------------------------------------------------------------- C  lumped-mass beam
def nodes_for(h):
    z_start, z_end = SECS[0][0], SECS[-1][0] + SECS[-1][1]
    pts = {round(z_start, 12), round(z_end, 12)} | {round(s[0], 12) for s in SECS} \
        | {round(d[0], 12) for d in DISCS} | {round(s[0], 12) for s in SUPS}
    pts = sorted(pts)
    z = []
    for a, b in zip(pts, pts[1:]):
        n = max(1, math.ceil((b - a) / h - 1e-9))
        z.extend(a + (b - a) * i / n for i in range(n))
    z.append(pts[-1])
    return np.array(z)


def section_at(zm):
    for z0, L, d, name in SECS:
        if z0 - 1e-12 <= zm <= z0 + L + 1e-12:
            return d
    raise ValueError(zm)


def idx(z, x):
    i = int(np.argmin(abs(z - x)))
    assert abs(z[i] - x) < 1e-9, (x, z[i])
    return i


def lumped_model(h=0.002, k=None, c=None):
    z = nodes_for(h)
    n = len(z)
    nd = 2 * n
    M = np.zeros((nd, nd)); K = np.zeros((nd, nd)); G = np.zeros((nd, nd)); C = np.zeros((nd, nd))
    for e in range(n - 1):
        L = z[e + 1] - z[e]
        d = section_at(0.5 * (z[e] + z[e + 1]))
        A, I = math.pi / 4 * d * d, math.pi / 64 * d ** 4
        EI = E * I
        ke = EI / L ** 3 * np.array([[12, 6 * L, -12, 6 * L], [6 * L, 4 * L * L, -6 * L, 2 * L * L],
                                     [-12, -6 * L, 12, -6 * L], [6 * L, 2 * L * L, -6 * L, 4 * L * L]])
        ii = [2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3]
        K[np.ix_(ii, ii)] += ke
        for j in (e, e + 1):                      # diagonal (lumped) mass, half element to each node
            M[2 * j, 2 * j] += RHO * A * L / 2
            M[2 * j + 1, 2 * j + 1] += RHO * I * L / 2 + RHO * A * L / 2 * (L / 2) ** 2 / 3
            G[2 * j + 1, 2 * j + 1] += 2 * RHO * I * L / 2
    for x, m, ip, idd, name in DISCS:
        j = idx(z, x)
        M[2 * j, 2 * j] += m
        M[2 * j + 1, 2 * j + 1] += idd
        G[2 * j + 1, 2 * j + 1] += ip
    for x, kk, cc, name in SUPS:
        j = idx(z, x)
        K[2 * j, 2 * j] += kk if k is None else k
        C[2 * j, 2 * j] += cc if c is None else c
    return (M.astype(complex), C.astype(complex), G.astype(complex), K.astype(complex)), z


# ---------------------------------------------------------------- D  transfer matrices (synchronous, undamped)
def tmm_stations(h=0.001, k=None):
    z = nodes_for(h)
    n = len(z)
    m = np.zeros(n); Id = np.zeros(n); Ip = np.zeros(n); ks = np.zeros(n)
    EIs = []
    for e in range(n - 1):
        L = z[e + 1] - z[e]
        d = section_at(0.5 * (z[e] + z[e + 1]))
        A, I = math.pi / 4 * d * d, math.pi / 64 * d ** 4
        EIs.append((L, E * I))
        for j in (e, e + 1):
            m[j] += RHO * A * L / 2
            Id[j] += RHO * I * L / 2 + RHO * A * L / 2 * (L / 2) ** 2 / 3
            Ip[j] += 2 * RHO * I * L / 2
    for x, mm, ip, idd, name in DISCS:
        j = idx(z, x); m[j] += mm; Id[j] += idd; Ip[j] += ip
    for x, kk, cc, name in SUPS:
        j = idx(z, x); ks[j] += kk if k is None else k
    return z, m, Id, Ip, ks, EIs


def tmm_det(st, w, W):
    """Boundary determinant for whirl frequency w and spin W [rad/s]; free-free ends."""
    z, m, Id, Ip, ks, EIs = st
    S = np.array([[1.0, 0.0], [0.0, 1.0], [0.0, 0.0], [0.0, 0.0]])   # columns: y=1, theta=1; M=V=0
    for j in range(len(z)):
        y, th, Mo, V = S
        Mo = Mo - (Id[j] * w * w - Ip[j] * W * w) * th
        V = V + (m[j] * w * w - ks[j]) * y
        S = np.array([y, th, Mo, V])
        if j < len(EIs):
            L, EI = EIs[j]
            y, th, Mo, V = S
            S = np.array([y + th * L + (Mo * L * L / 2 + V * L ** 3 / 6) / EI,
                          th + (Mo * L + V * L * L / 2) / EI, Mo + V * L, V])
            S = S / np.max(np.abs(S))       # scale to avoid overflow (sign of det unchanged)
    return S[2, 0] * S[3, 1] - S[2, 1] * S[3, 0]


def tmm_roots(st, lo, hi, step, synchronous=True):
    f = (lambda N: tmm_det(st, N / RPM, N / RPM)) if synchronous else (lambda N: tmm_det(st, N / RPM, 0.0))
    grid = np.arange(lo, hi + step, step)
    vals = [f(N) for N in grid]
    roots = []
    for i in range(len(grid) - 1):
        if vals[i] == 0 or vals[i] * vals[i + 1] < 0:
            roots.append(brentq(f, grid[i], grid[i + 1], xtol=0.2))
    return roots


# ---------------------------------------------------------------- validation on closed forms
print('\n[V] method validation against closed-form cases')
_save = (SECS, DISCS, SUPS)
Lb, db = 0.3, 0.02
SECS = [(0.0, Lb, db, 'beam')]
DISCS = []
SUPS = [(0.0, 1e13, 0.0, 'a'), (Lb, 1e13, 0.0, 'b')]
EI_b, rA_b = E * math.pi / 64 * db ** 4, RHO * math.pi / 4 * db * db
f_ss = (math.pi / Lb) ** 2 * math.sqrt(EI_b / rA_b) * RPM          # Euler-Bernoulli pinned-pinned, non-rotating
st = tmm_stations(0.002)
r = tmm_roots(st, 1000, 1.3 * f_ss, 200, synchronous=False)
line('TMM pinned-pinned uniform beam, mode 1 (non-rotating) [rpm]', r[0] if r else None, f_ss, tol=0.005)
mod, zz = lumped_model(0.002)
fr = [f for f, w, zt in whirl_modes(*mod, 0.0) if w == 'F']
line('lumped beam pinned-pinned uniform beam, mode 1 [rpm]', fr[0], f_ss, tol=0.005)
# overhung disc on a massless cantilever: synchronous forward critical with gyroscopic moment (closed form)
Lc, dc, md, Ipd, Idd = 0.05, 0.008, 0.2, 2.0e-4, 1.0e-4
EIc = E * math.pi / 64 * dc ** 4
a11, a12, a22 = Lc ** 3 / (3 * EIc), Lc ** 2 / (2 * EIc), Lc / EIc
# tip force F = m W^2 y and tip couple C = (Id - Ip) W^2 th (synchronous forward whirl, D'Alembert)
# [y; th] = A [F; C]  ->  det(I - W^2 A diag(m, Id - Ip)) = 0  ->  1 - c2 W^2 + c4 W^4 = 0
qa, qb = md, (Idd - Ipd)
c2 = a11 * qa + a22 * qb
c4 = (a11 * a22 - a12 * a12) * qa * qb
disc_ = math.sqrt(c2 * c2 - 4 * c4)
roots_w2 = [r_ for r_ in ((c2 - disc_) / (2 * c4), (c2 + disc_) / (2 * c4)) if r_ > 0]
W_cf = math.sqrt(min(roots_w2)) * RPM
SECS = [(0.0, Lc, dc, 'cantilever')]
DISCS = [(Lc, md, Ipd, Idd, 'disc')]
SUPS = [(0.0, 1e14, 0.0, 'clamp-y')]
st = tmm_stations(0.001)
# emulate a clamp: very stiff translational spring plus a very stiff rotational restraint via a short stiff stub
z_, m_, Id_, Ip_, ks_, EIs_ = st
m_[:] = 0.0; Id_[:] = 0.0; Ip_[:] = 0.0
m_[-1], Id_[-1], Ip_[-1] = md, Idd, Ipd
Id_[0] = 0.0


def det_clamped(Wr):
    S = np.array([[0.0], [0.0], [1.0], [0.0]])
    S2 = np.array([[0.0], [0.0], [0.0], [1.0]])
    S = np.hstack([S, S2])
    for j in range(len(z_)):
        y, th, Mo, V = S
        Mo = Mo - (Id_[j] * Wr * Wr - Ip_[j] * Wr * Wr) * th
        V = V + (m_[j] * Wr * Wr) * y
        S = np.array([y, th, Mo, V])
        if j < len(EIs_):
            L, EI = EIs_[j]
            y, th, Mo, V = S
            S = np.array([y + th * L + (Mo * L * L / 2 + V * L ** 3 / 6) / EI, th + (Mo * L + V * L * L / 2) / EI,
                          Mo + V * L, V])
    return S[2, 0] * S[3, 1] - S[2, 1] * S[3, 0]


grid = np.arange(1000, 3 * W_cf, 100)
vals = [det_clamped(N / RPM) for N in grid]
rt = [brentq(lambda N: det_clamped(N / RPM), grid[i], grid[i + 1]) for i in range(len(grid) - 1) if vals[i] * vals[i + 1] < 0]
line('TMM overhung gyroscopic disc on cantilever, synchronous fwd [rpm]', rt[0] if rt else None, W_cf, tol=0.002)
SECS, DISCS, SUPS = _save

# ---------------------------------------------------------------- PD-1 results
Nmax = 1.5 * N_HIGH
print('\n[B] rigid two-DOF rotor (flexibility of the shaft ignored)')
rig = rigid_model()
rc = crossings(rig, Nmax)
for i, cv in enumerate(rc):
    line(f'rigid damped crossing {i + 1} vs FE crossing {i + 1} [rpm]', cv, FE_CRIT[i] if i < len(FE_CRIT) else None, info=True)
rc0 = crossings(rigid_model(c=0.0), Nmax)
print(f'    rigid UNDAMPED synchronous criticals: {[round(v) for v in rc0]} rpm')
z0 = whirl_modes(*rig, 2040.0)
print(f'    rigid modes at 2,040 rpm (freq rpm, whirl, zeta): {[(round(f), w, round(zt, 3)) for f, w, zt in z0]}')

print('\n[C] own lumped-mass beam model, damped supports, gyroscopic (definition as run: damped fwd whirl = N)')
res_C = {}
for h in (0.003, 0.0015):
    mod, zz = lumped_model(h)
    res_C[h] = crossings(mod, Nmax)
    print(f'    h={h * 1e3:.1f} mm  nodes={len(zz)}  crossings={[round(v, 1) for v in res_C[h]]}')
cC = res_C[0.0015]
for i, cv in enumerate(cC):
    line(f'lumped-beam crossing {i + 1} vs FE crossing {i + 1} [rpm]', cv, FE_CRIT[i] if i < len(FE_CRIT) else None)
modn, zz = lumped_model(0.0015)
for N in (2040.0, 102000.0):
    fw = [(round(f), w, round(zt, 3)) for f, w, zt in whirl_modes(*modn, N)][:8]
    print(f'    modes at {N:.0f} rpm: {fw}')
camp0 = rd['campbell'][0]
print(f'    run Campbell at {camp0["N_rpm"]:.0f} rpm: {[(round(q["freq_rpm"]), q["whirl"][0].upper(), round(q["damping_ratio"], 3)) for q in camp0["modes"]]}')
for i, cv in enumerate(cC):
    ms_ = [(f, w, zt) for f, w, zt in whirl_modes(*modn, cv) if w == 'F']
    m_ = min(ms_, key=lambda q: abs(q[0] - cv))
    fe_z = rd['mode_shapes'][i]['damping_ratio'] if i < len(rd['mode_shapes']) else None
    line(f'damping ratio of crossing mode {i + 1}', m_[2], fe_z, tol=0.03)
c_und = crossings(lumped_model(0.003, c=0.0)[0], Nmax)
print(f'    UNDAMPED (c=0) lumped-beam (h=3 mm) synchronous criticals: {[round(v, 1) for v in c_und]} rpm')

print('\n[D] Myklestad-Prohl transfer matrices, synchronous forward whirl, undamped supports')
st = tmm_stations(0.001)
rD = tmm_roots(st, 1000, 60000, 100) + tmm_roots(st, 60000 + 1e-6, 140000, 300)
rD = sorted(set(round(v, 1) for v in rD))
print(f'    TMM synchronous undamped criticals: {rD}')
bend = [v for v in rD if v > 60000]
line('TMM first bending synchronous critical (UNDAMPED) vs FE mode 3 (damped c=1000) [rpm]', bend[0] if bend else None,
     FE_CRIT[2] if len(FE_CRIT) > 2 else None, info=True)
print('    (not like-for-like: the run crossing includes the assumed support damping; like-for-like damped value in [C])')
line('TMM vs own lumped-beam (c=0) bending critical [rpm]', bend[0] if bend else None, c_und[-1] if c_und else None, tol=0.003)
rig_tmm = [v for v in rD if v < 60000]
for i, v in enumerate(rig_tmm):
    line(f'TMM rigid-mode undamped critical {i + 1} vs lumped-beam c=0 [rpm]', v, c_und[i] if i < len(c_und) else None, tol=0.003)
rD0 = tmm_roots(st, 1000, 140000, 200, synchronous=False)
print(f'    TMM NON-ROTATING undamped natural frequencies: {[round(v) for v in rD0]} rpm')
# simple overhung-disc estimate (hand): rigid pinned bearings, unit-load flexibility at the compressor CG
xb1, xb2 = SUPS[0][0], SUPS[1][0]
xw = [d[0] for d in DISCS if d[4] == 'compressor wheel'][0]
m_over = sum(d[1] for d in DISCS if d[0] < xb1)
xs = np.linspace(SECS[0][0], xb2, 20001)
EIx = np.array([E * math.pi / 64 * section_at(x) ** 4 for x in xs])
a = xb1 - xw; Lsp = xb2 - xb1
mom = np.where(xs < xw, 0.0, np.where(xs < xb1, xs - xw, a * (xb2 - xs) / Lsp))   # unit load at the wheel CG
flex = np.trapezoid(mom * mom / EIx, xs)
f_simple = math.sqrt(1 / (flex * m_over)) * RPM
print(f'    simple overhung estimate: overhang mass {m_over:.4f} kg, flexibility {flex * 1e6:.3f} um/N -> {f_simple:.0f} rpm '
      f'(non-rotating, rigid pinned bearings; compare with the zero-speed flexible mode, not the 88 krpm synchronous one)')
k1, k2 = SUPS[0][1], SUPS[1][1]
R1, R2 = (a + Lsp) / Lsp, a / Lsp                     # bearing reactions for a unit load at the wheel CG
flex_s = flex + R1 * R1 / k1 + R2 * R2 / k2           # add the bearing compliance seen at the wheel
f_soft = math.sqrt(1 / (flex_s * m_over)) * RPM
print(f'    same with the 2 N/um bearing compliance added: flexibility {flex_s * 1e6:.3f} um/N -> {f_soft:.0f} rpm. '
      f'These single-mass estimates bracket the zero-speed flexible mode but cannot reproduce the gyroscopically '
      f'stiffened synchronous value (expected accuracy no better than +/-50 %).')

print('\n[E] separation margin and support-stiffness sensitivity')
sep = lambda crits: min(max(N_LOW - c, c - N_HIGH, 0.0) / N_HIGH for c in crits)
line('separation from own lumped-beam crossings (run definition)', sep(cC), rd['separation_frac'])
if 'critical-speed separation (FE, all modes, 1.5 x max search)' in checks:
    line('candidate check value vs rotordynamics.json', checks['critical-speed separation (FE, all modes, 1.5 x max search)']['value'],
         rd['separation_frac'], tol=1e-9)
print(f'    run definition: sep = min_c max(N_low-Nc, Nc-N_high, 0)/N_high ; binding mode = {min(cC, key=lambda c: max(N_LOW - c, c - N_HIGH, 0))} rpm')
for row in rd['support_stiffness_sensitivity']:
    kk = row['k_N_m']
    mine = crossings(lumped_model(0.003, k=kk)[0], Nmax)
    print(f'    k={kk / 1e6:.1f} N/um  run={[round(v) for v in row["critical_speeds"]]}  own={[round(v) for v in mine]}')
    for i, v in enumerate(row['critical_speeds']):
        line(f'  k={kk / 1e6:.0f} N/um crossing {i + 1}', mine[i] if i < len(mine) else None, v, tol=0.015)
mk1, _ = lumped_model(0.003, k=1e6)
print(f'    k=1 N/um, c=1000: modes at 9,000 rpm {[(round(f), w, round(zt, 2)) for f, w, zt in whirl_modes(*mk1, 9000.0)][:4]} '
      f'(one rigid mode is critically damped, zeta ~1 with a damped frequency < 1 krpm, so it never meets N: '
      f'that is why only two criticals are listed at 1 N/um)')


# Threshold support stiffness: same crossing list and separation definition as the run (all forward
# crossings up to 1.5 N_high), coarse k sweep then linear interpolation of the separation to 0.20.
for c in (0.0, 1000.0):
    rows = []
    for k in (2.0e6, 3.0e6, 3.5e6, 4.0e6, 4.5e6, 5.0e6):
        cr = crossings(lumped_model(0.003, k=k, c=c)[0], Nmax)
        rows.append((k, sep(cr), cr))
        print(f'    c={c:5.0f} k={k / 1e6:3.1f} N/um: crossings {[round(v) for v in cr]} rpm, separation {sep(cr):.3f}')
        if sep(cr) < 0.2:
            break
    for (k0, s0, _), (k1, s1, _) in zip(rows, rows[1:]):
        if s0 >= 0.2 > s1:
            print(f'    -> separation falls below 0.20 at k* ~ {(k0 + (0.2 - s0) * (k1 - k0) / (s1 - s0)) / 1e6:.2f} N/um '
                  f'(c = {c:.0f} N s/m; linear interpolation)')

print('\n[F] unbalance response (G2.5 at N_high, both wheels, in phase / opposed)')
e = rd['unbalance']['grade_G_mm_s'] * 1e-3 / (N_HIGH / RPM)
line('eccentricity [m]', e, rd['unbalance']['eccentricity_m'], tol=1e-9)
mod, zz = lumped_model(0.0015)
Mm, Cm, Gm, Km = mod
cw = [d for d in DISCS if d[4] == 'compressor wheel'][0]
tw = [d for d in DISCS if d[4] == 'turbine wheel'][0]
jc, jt = idx(zz, cw[0]), idx(zz, tw[0])
amps = {}
for N in np.linspace(0.05 * N_HIGH, 1.2 * N_HIGH, 47):
    W = N / RPM
    for lab, ph in (('in_phase', 0.0), ('opposed', math.pi)):
        F = np.zeros(Mm.shape[0], dtype=complex)
        F[2 * jc] += cw[1] * e * W * W
        F[2 * jt] += tw[1] * e * W * W * np.exp(1j * ph)
        q = np.linalg.solve(Km - W * W * (Mm - Gm) + 1j * W * Cm, F)
        amps[(round(N, 3), lab)] = (abs(q[2 * jt]), float(np.max(np.abs(q[0::2]))))
lim = 1.05 * N_HIGH
mine_max = max(v[0] for (N, lab), v in amps.items() if N <= lim)
run_max = max(r['amp_turbine_m'] for r in rd['unbalance']['response'] if r['N_rpm'] <= lim)
line('max turbine orbit <= 1.05 N_high [m]', mine_max, run_max, tol=0.02)
chk = 'turbine orbit at G2.5 unbalance vs 1/3 cold tip clearance'
if chk in checks:
    line('candidate check value vs rotordynamics.json max', checks[chk]['value'], run_max, tol=1e-9)
for lab in ('in_phase', 'opposed'):
    rr = sorted((r['N_rpm'], r['max_amp_m']) for r in rd['unbalance']['response'] if r['case'] == lab)
    peaks = [(round(rr[i][0]), rr[i][1]) for i in range(1, len(rr) - 1) if rr[i][1] > rr[i - 1][1] and rr[i][1] > rr[i + 1][1]]
    print(f'    run response {lab}: interior local maxima of max orbit = {peaks or "none"}; '
          f'amplitude rises monotonically to {rr[-1][1]:.3e} m at {rr[-1][0]:.0f} rpm' if not peaks else
          f'    run response {lab}: interior local maxima = {peaks}')

print('\n[G] sensitivity of the criticals and separation to the ASSUMED support damping (case range 300-3000 N s/m)')
for c in (300.0, 3000.0, 2000.0):
    cr = crossings(lumped_model(0.003, c=c)[0], Nmax)
    print(f'    k=2 N/um c={c:6.0f} N s/m: crossings {[round(v) for v in cr]} rpm  separation {sep(cr):.3f}'
          f'{"  < 0.20" if sep(cr) < 0.2 else ""}')
print('    (c=0 and c=1000 at k=2 N/um are the first rows of the threshold sweep above)')

print('\nSUMMARY:', 'all like-for-like comparisons within tolerance' if not fails else f'{len(fails)} difference(s): {fails}')
sys.exit(1 if fails else 0)
