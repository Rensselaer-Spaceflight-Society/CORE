"""Provenance-carrying component records, check results and file fingerprints.

The scalar module state stays numeric (see core/module.py). Everything that
needs a source, a unit, an evidence basis, a table or a coordinate list lives
in a versioned YAML/CSV record under data/ and is read through this module.

Evidence basis is part of every parameter, so a report can never present a
catalog dimension, a calculation and a guess as the same kind of fact:

    supplied     dimension or property printed on a supplier drawing/listing,
                 or measured on the actual part
    reference    primary-source reference information applied by analogy
                 (e.g. a related wheel's published map); applicability stated
    calculated   derived in this repository from stated inputs
    design       a CORE candidate design choice (free parameter of a part CORE makes)
    assumption   provisional engineering assumption or proxy; needs evidence
    unresolved   value not available; must come from analysis, test or supplier

A parameter with value None must be `unresolved`. Reading an unresolved value
through `si()` raises MissingInput: missing data is never silently zero.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 1
BASES = ('supplied', 'reference', 'calculated', 'design', 'assumption', 'unresolved')
CHECK_STATUS = ('pass', 'fail', 'unknown', 'not_applicable')

# unit -> (quantity type, factor to SI)
UNITS = {
    'm': ('length', 1.0), 'mm': ('length', 1e-3), 'in': ('length', 0.0254), 'um': ('length', 1e-6),
    'm2': ('area', 1.0), 'mm2': ('area', 1e-6),
    'm3': ('volume', 1.0), 'mm3': ('volume', 1e-9),
    'deg': ('angle', math.pi / 180.0), 'rad': ('angle', 1.0),
    'count': ('count', 1.0), '-': ('ratio', 1.0),
    'kg': ('mass', 1.0), 'g': ('mass', 1e-3),
    'kg_m2': ('inertia', 1.0), 'kg_mm2': ('inertia', 1e-6),
    'kg_m3': ('density', 1.0),
    'K': ('temperature', 1.0),
    'Pa': ('pressure', 1.0), 'kPa': ('pressure', 1e3), 'MPa': ('pressure', 1e6), 'GPa': ('pressure', 1e9),
    'N': ('force', 1.0), 'Nm': ('torque', 1.0),
    'N_m': ('stiffness', 1.0), 'N_um': ('stiffness', 1e6), 'N_s_m': ('damping', 1.0),
    'cSt': ('kinematic_viscosity', 1e-6), 'W_m2K': ('heat_transfer', 1.0),
    'rpm': ('speed', 1.0), 'm_s': ('velocity', 1.0),
    'kg_s': ('mass_flow', 1.0), 'lb_min': ('mass_flow', 0.45359237 / 60.0),
    'W': ('power', 1.0), 'kW': ('power', 1e3),
    'per_K': ('expansion', 1.0), 'J_kgK': ('specific_heat', 1.0), 'W_mK': ('conductivity', 1.0),
    'USD': ('currency', 1.0), 'CHF': ('currency_foreign', 1.0), 'EUR': ('currency_foreign', 1.0),
    'h': ('time', 3600.0), 's': ('time', 1.0),
    'V': ('voltage', 1.0), 'A': ('current', 1.0),
}


class RecordError(Exception):
    """Malformed record, unknown unit, missing source, duplicate identity."""


class MissingInput(RecordError):
    """A required value is unresolved. Callers must not substitute zero."""


def file_sha256(path):
    """Content hash with line endings normalised so Windows/Linux agree."""
    data = Path(path).read_bytes()
    if Path(path).suffix.lower() in ('.yaml', '.yml', '.csv', '.json', '.md', '.py', '.txt'):
        data = data.replace(b'\r\n', b'\n')
    return hashlib.sha256(data).hexdigest()


def fingerprint(paths, extra=None):
    """Deterministic identity of a set of files (path names + contents) and
    optional extra settings. Timestamps never enter."""
    h = hashlib.sha256()
    for p in sorted({Path(p).resolve() for p in paths}):
        try:
            rel = p.relative_to(ROOT).as_posix()
        except ValueError:
            rel = p.name
        h.update(rel.encode())
        h.update(file_sha256(p).encode())
    if extra is not None:
        h.update(yaml.safe_dump(extra, sort_keys=True).encode())
    return h.hexdigest()


def _check_parameter(cid, name, p, source_ids):
    if not isinstance(p, dict):
        raise RecordError(f'{cid}.{name}: parameter must be a mapping')
    for key in ('value', 'unit', 'basis'):
        if key not in p:
            raise RecordError(f'{cid}.{name}: missing "{key}"')
    if p['unit'] not in UNITS:
        raise RecordError(f'{cid}.{name}: unknown unit {p["unit"]!r}')
    if p['basis'] not in BASES:
        raise RecordError(f'{cid}.{name}: basis must be one of {BASES}')
    v = p['value']
    if v is None:
        if p['basis'] != 'unresolved':
            raise RecordError(f'{cid}.{name}: null value must have basis "unresolved"')
    else:
        if p['basis'] == 'unresolved':
            raise RecordError(f'{cid}.{name}: unresolved parameter must not carry a value')
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise RecordError(f'{cid}.{name}: value must be a finite number or null')
        if UNITS[p['unit']][0] == 'count' and (v < 0 or int(v) != v):
            raise RecordError(f'{cid}.{name}: count must be a nonnegative integer')
    if p['basis'] in ('supplied', 'reference'):
        src = p.get('source')
        if not src or src not in source_ids:
            raise RecordError(f'{cid}.{name}: {p["basis"]} value needs a source id from source_documents')
    rng = p.get('range')
    if rng is not None:
        if (not isinstance(rng, (list, tuple)) or len(rng) != 2
                or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in rng) or rng[0] > rng[1]):
            raise RecordError(f'{cid}.{name}: range must be [low, high]')


class Record:
    """One validated component/source record."""

    def __init__(self, data, path=None):
        self.path = Path(path) if path else None
        self.data = data
        if data.get('schema_version') != SCHEMA_VERSION:
            raise RecordError(f'{path}: schema_version must be {SCHEMA_VERSION}')
        for key in ('record_type', 'component_id', 'title'):
            if not data.get(key):
                raise RecordError(f'{path}: missing {key}')
        self.id = data['component_id']
        sources = data.get('source_documents') or []
        ids = [s.get('id') for s in sources]
        if len(ids) != len(set(ids)) or not all(ids):
            raise RecordError(f'{self.id}: source_documents ids must be unique and non-empty')
        for s in sources:
            if not s.get('accessed') and s.get('kind') != 'internal':
                raise RecordError(f'{self.id}: source {s.get("id")} needs an access date')
        self.sources = {s['id']: s for s in sources}
        self.parameters = data.get('parameters') or {}
        for name, p in self.parameters.items():
            _check_parameter(self.id, name, p, self.sources)

    # -- access ---------------------------------------------------------
    def param(self, name):
        if name not in self.parameters:
            raise MissingInput(f'{self.id}: parameter {name!r} is not defined')
        return self.parameters[name]

    def si(self, name):
        """Value converted to SI; raises MissingInput if unresolved."""
        p = self.param(name)
        if p['value'] is None:
            raise MissingInput(f'{self.id}.{name} is unresolved: {p.get("note", "no value supplied")}')
        if p['unit'] in ('CHF', 'EUR'):
            raise RecordError(f'{self.id}.{name}: foreign list price is not a USD quantity')
        return float(p['value']) * UNITS[p['unit']][1]

    def si_range(self, name):
        p = self.param(name)
        rng = p.get('range')
        if rng is None:
            v = self.si(name)
            return v, v
        f = UNITS[p['unit']][1]
        return rng[0] * f, rng[1] * f

    def basis(self, name):
        return self.param(name)['basis']

    def has_value(self, name):
        return name in self.parameters and self.parameters[name]['value'] is not None

    def unresolved(self):
        return sorted(n for n, p in self.parameters.items() if p['value'] is None)

    def summary_rows(self):
        for n, p in self.parameters.items():
            yield dict(component=self.id, parameter=n, value=p['value'], unit=p['unit'],
                       basis=p['basis'], source=p.get('source'), range=p.get('range'),
                       note=p.get('note', ''))


def load_record(path):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    with open(path, encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise RecordError(f'{path}: not a mapping')
    return Record(data, path)


def load_records(paths):
    recs = {}
    for p in paths:
        r = load_record(p)
        if r.id in recs:
            raise RecordError(f'duplicate component_id {r.id!r} in {p} and {recs[r.id].path}')
        recs[r.id] = r
    return recs


class Check:
    """One screening result. A missing prerequisite yields 'unknown', never 'pass'."""

    __slots__ = ('name', 'status', 'value', 'limit', 'margin', 'unit', 'criterion', 'basis', 'reason')

    def __init__(self, name, status, value=None, limit=None, unit='', criterion='', basis='', reason=''):
        if status not in CHECK_STATUS:
            raise ValueError(f'check status must be one of {CHECK_STATUS}')
        if status == 'pass' and (value is None or (isinstance(value, float) and not math.isfinite(value))):
            raise ValueError(f'{name}: a pass needs a finite evaluated value')
        self.name, self.status, self.value, self.limit = name, status, value, limit
        self.unit, self.criterion, self.basis, self.reason = unit, criterion, basis, reason
        self.margin = None
        if isinstance(value, (int, float)) and isinstance(limit, (int, float)) and limit != 0:
            self.margin = (limit - value) / abs(limit) if criterion.startswith('<=') else (value - limit) / abs(limit)

    @classmethod
    def compare(cls, name, value, op, limit, unit='', basis='', reason=''):
        if value is None or limit is None or not all(math.isfinite(x) for x in (value, limit)):
            return cls(name, 'unknown', value, limit, unit, f'{op} {limit}', basis,
                       reason or 'prerequisite value unavailable')
        ok = value <= limit if op == '<=' else value >= limit
        return cls(name, 'pass' if ok else 'fail', value, limit, unit, f'{op} {limit}', basis, reason)

    def as_dict(self):
        return {k: getattr(self, k) for k in self.__slots__}
