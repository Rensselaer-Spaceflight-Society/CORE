"""Typed CAD parameter bundle for the team's native CAD, and its reader/validator.

Unlike the legacy cad_dims.csv (every value x 1000), each parameter carries an
explicit quantity type and unit; conversion is per type:

    length  m -> mm (x1000)      area  m2 -> mm2 (x1e6)      angle  deg (no conversion)
    count   integer (no conversion)    mass  kg    inertia  kg m2    ratio  -
Every parameter also carries: part id, reference temperature (cold 293 K unless
stated), evidence basis, source, proposed tolerance with its reason, and status.

read_bundle() re-reads the files and checks schema, unique names, required
fields, unit/type consistency, integer counts and that the bundle's design
fingerprint matches an expected one (stale exports are rejected).
"""
from __future__ import annotations

import csv
import io
import json
import math

SCHEMA = 1
TYPES = {'length': ('mm', 1e3), 'area': ('mm2', 1e6), 'angle': ('deg', 1.0), 'count': ('count', 1.0),
         'mass': ('kg', 1.0), 'inertia': ('kg_m2', 1.0), 'ratio': ('-', 1.0), 'temperature': ('K', 1.0),
         'stiffness': ('N/um', 1e-6)}
REQUIRED = ('name', 'part_id', 'quantity_type', 'value', 'unit', 'reference_temperature_K', 'basis', 'source',
            'tolerance', 'status')
BASES = ('supplied', 'reference', 'calculated', 'design', 'assumption', 'unresolved')
STATUSES = ('fixed purchased geometry', 'provisional design', 'calculated from model', 'unresolved - do not model',
            'envelope only')


class BundleError(Exception):
    pass


class Bundle:
    def __init__(self, fingerprint, case_id):
        self.fingerprint, self.case_id = fingerprint, case_id
        self.params, self.interfaces, self.patterns, self.sections = [], [], {}, {}
        self._names = set()

    def add(self, name, part_id, qtype, value_si, basis, source, tolerance='general ISO 2768-m',
            tol_reason='not functionally critical', status='provisional design', ref_T=293.0, note=''):
        if qtype not in TYPES:
            raise BundleError(f'{name}: unknown quantity type {qtype}')
        if name in self._names:
            raise BundleError(f'duplicate CAD parameter name {name}')
        if basis not in BASES:
            raise BundleError(f'{name}: basis {basis} invalid')
        unit, f = TYPES[qtype]
        if value_si is None:
            if basis != 'unresolved':
                raise BundleError(f'{name}: missing value must be marked unresolved')
            value = None
            status = 'unresolved - do not model'
        else:
            if not math.isfinite(value_si):
                raise BundleError(f'{name}: non-finite value')
            value = int(round(value_si)) if qtype == 'count' else round(value_si * f, 6)
            if qtype == 'count' and abs(value - value_si) > 1e-9:
                raise BundleError(f'{name}: count must be an integer')
        self._names.add(name)
        self.params.append(dict(name=name, part_id=part_id, quantity_type=qtype, value=value, unit=unit,
                                reference_temperature_K=ref_T, basis=basis, source=source, tolerance=tolerance,
                                tolerance_reason=tol_reason, status=status, note=note))

    def interface(self, iid, part_a, part_b, feature, x_m=None, d_m=None, relation='', note=''):
        self.interfaces.append(dict(interface_id=iid, part_a=part_a, part_b=part_b, feature=feature,
                                    x_mm=None if x_m is None else round(x_m * 1e3, 4),
                                    diameter_mm=None if d_m is None else round(d_m * 1e3, 4),
                                    relation=relation, note=note))

    def to_json(self, frame, notes):
        return dict(schema_version=SCHEMA, release_status='PRELIMINARY - NOT FOR MANUFACTURE',
                    case_id=self.case_id, design_fingerprint=self.fingerprint, frame=frame,
                    unit_policy={k: v[0] for k, v in TYPES.items()}, notes=notes,
                    parameters=self.params, interfaces=self.interfaces, patterns=self.patterns, sections=self.sections)

    def to_csv(self):
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator='\n')
        cols = list(REQUIRED) + ['tolerance_reason', 'note']
        w.writerow(cols)
        for p in self.params:
            w.writerow([p[c] for c in cols])
        return buf.getvalue()


def read_bundle(path, expected_fingerprint=None):
    """Validate an exported bundle. Returns the parsed dict; raises BundleError."""
    with open(path, encoding='utf-8') as f:
        b = json.load(f)
    if b.get('schema_version') != SCHEMA:
        raise BundleError('wrong schema version')
    if expected_fingerprint is not None and b.get('design_fingerprint') != expected_fingerprint:
        raise BundleError('stale bundle: design fingerprint differs from the current design')
    names = set()
    for p in b['parameters']:
        missing = [k for k in REQUIRED if k not in p]
        if missing:
            raise BundleError(f'{p.get("name")}: missing {missing}')
        if p['name'] in names:
            raise BundleError(f'duplicate parameter {p["name"]}')
        names.add(p['name'])
        if p['quantity_type'] not in TYPES or TYPES[p['quantity_type']][0] != p['unit']:
            raise BundleError(f'{p["name"]}: unit {p["unit"]} inconsistent with type {p["quantity_type"]}')
        if p['value'] is None and p['basis'] != 'unresolved':
            raise BundleError(f'{p["name"]}: null value not marked unresolved')
        if p['quantity_type'] == 'count' and p['value'] is not None and int(p['value']) != p['value']:
            raise BundleError(f'{p["name"]}: non-integer count')
    return b
