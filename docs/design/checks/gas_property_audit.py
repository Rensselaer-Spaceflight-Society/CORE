"""Independent gas-property audit (T09): NIST-JANAF Shomate species data vs core/gas.py.

Reference data: NIST Chemistry WebBook Shomate coefficients (Chase 1998, NIST-JANAF
Thermochemical Tables, 4th ed.), accessed 2026-10-04 for N2, O2, CO2, H2O; Ar taken as a
monatomic ideal gas (cp = 20.786 J/mol K). Dry air: 78.084 % N2, 20.946 % O2, 0.934 % Ar,
0.036 % CO2 (by mole). Products: frozen complete lean combustion of a kerosene surrogate
C12H23 (H/C 1.917) - NO dissociation, NO equilibrium chemistry; this checks the
sensible-property surrogate only and says nothing about flame stability.

Run:  python docs/design/checks/gas_property_audit.py
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from core import gas   # noqa: E402

SHOMATE = {   # (Tmin, Tmax, A, B, C, D, E)
    'N2': [(100, 500, 28.98641, 1.853978, -9.647459, 16.63537, 0.000117),
           (500, 2000, 19.50583, 19.88705, -8.598535, 1.369784, 0.527601)],
    'O2': [(100, 700, 31.32234, -20.23531, 57.86644, -36.50624, -0.007374),
           (700, 2000, 30.03235, 8.772972, -3.988133, 0.788313, -0.741599)],
    'CO2': [(298, 1200, 24.99735, 55.18696, -33.69137, 7.948387, -0.136638),
            (1200, 6000, 58.16639, 2.720074, -0.492289, 0.038844, -6.447293)],
    'H2O': [(500, 1700, 30.09200, 6.832514, 6.793435, -2.534480, 0.082139),
            (1700, 6000, 41.96426, 8.622053, -1.499780, 0.098119, -11.15764)],
}
M = {'N2': 28.0134, 'O2': 31.9988, 'CO2': 44.0095, 'H2O': 18.01528, 'Ar': 39.948}
AIR = {'N2': 0.78084, 'O2': 0.20946, 'Ar': 0.00934, 'CO2': 0.00036}


def cp_species(sp, T):
    if sp == 'Ar':
        return 20.786
    for lo, hi, A, B, C, D, E in SHOMATE[sp]:
        if lo <= T <= hi or (sp == 'H2O' and T < 500 and lo == 500) or (sp == 'CO2' and T < 298 and lo == 298):
            t = T / 1000.0
            return A + B * t + C * t * t + D * t ** 3 + E / (t * t)
    raise ValueError(f'{sp} outside Shomate range at {T} K')


def mixture_cp_mass(moles, T):
    m = sum(n * M[s] for s, n in moles.items())
    return sum(n * cp_species(s, T) for s, n in moles.items()) / m * 1000.0   # J/kg K


def products(far):
    """Moles per mole of air for frozen complete combustion of C12H23 at fuel/air mass ratio far."""
    M_air = sum(x * M[s] for s, x in AIR.items())
    M_fuel = 12 * 12.011 + 23 * 1.008
    n_fuel = far * M_air / M_fuel
    p = dict(AIR)
    p['CO2'] += 12 * n_fuel
    p['H2O'] = 11.5 * n_fuel
    p['O2'] -= (12 + 23 / 4) * n_fuel
    if p['O2'] < 0:
        raise ValueError('rich mixture not covered')
    return p


def main():
    rows = []
    for T in (300, 400, 600, 800, 900, 1000, 1150, 1300, 1500):
        ref_air = mixture_cp_mass(AIR, T)
        row = dict(T_K=T, cp_air_repo=gas.cp_air(T), cp_air_ref=ref_air, air_err_pct=100 * (gas.cp_air(T) / ref_air - 1))
        for f in (0.0139, 0.022):
            ref = mixture_cp_mass(products(f), T)
            row[f'cp_prod_ref_f{f}'] = ref
            row[f'cp_prod_repo_f{f}'] = gas.cp_products(T, f)
            row[f'prod_err_pct_f{f}'] = 100 * (gas.cp_products(T, f) / ref - 1)
        rows.append(row)
    # consequence for turbine work at the PD-1 design point: enthalpy drop 853.6 -> 812.5 K at FAR 0.0139
    def h_ref(T, f, T0=298.15, n=400):
        return sum(mixture_cp_mass(products(f), T0 + (T - T0) * (i + 0.5) / n) for i in range(n)) * (T - T0) / n
    f = 0.0139
    dh_ref = h_ref(853.6, f) - h_ref(812.5, f)
    dh_repo = gas.h_products(853.6, f) - gas.h_products(812.5, f)
    out = dict(rows=rows, turbine_dh_check=dict(T_in_K=853.6, T_out_K=812.5, far=f, dh_repo_J_kg=dh_repo, dh_ref_J_kg=dh_ref,
                                                err_pct=100 * (dh_repo / dh_ref - 1)),
               basis='NIST-JANAF Shomate (Chase 1998); frozen complete lean combustion of C12H23; no dissociation')
    print(json.dumps(out, indent=1))
    return out


if __name__ == '__main__':
    main()
