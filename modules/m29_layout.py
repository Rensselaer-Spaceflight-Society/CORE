"""M29: explicit axial assembly stack for a fixed-geometry candidate.

Candidate module set only. Replaces proportional length estimates with actual
component faces: compressor wheel, backplate, bearings, combustor, NGV, turbine,
nozzle. Positions are cold, from the compressor wheel backface (x positive aft).
core/assembly.build_stack is the single implementation; the CAD exporter calls
the same function with the final state, so exported faces equal these scalars.
"""
from core.module import module
from core import assembly


@module(
    tier=4,
    title="Assembly stack: faces, bearing and rotor positions, rotor mass",
    owner="STRUCT-3", second="TURBO-4",
    status="draft",
    reads=assembly.STACK_READS,
    writes=["x_front_bearing_m", "x_rear_bearing_m", "x_turbine_disc_m", "x_compressor_cg_m",
            "x_ngv_le_m", "x_nozzle_exit_m", "x_inlet_lip_m", "x_shaft_front_m", "x_shaft_rear_m",
            "m_rotor_kg", "x_rotor_cg_m", "Ip_rotor_kg_m2", "m_shaft_stack_kg", "stack_checks_failed_count"],
    notes="Preliminary layout from component records and design choices; clamped-joint stiffness, "
          "fits and thermal growth are screened in core/assembly.py, not analysed by FEA.",
    case_sets=("candidate",),
)
def m29_layout(s):
    st = assembly.build_stack(assembly.params_from_state(s))
    x = st['x']
    return {
        "x_front_bearing_m": x['fb_c'], "x_rear_bearing_m": x['rb_c'], "x_turbine_disc_m": x['tw_c'],
        "x_compressor_cg_m": x['cw_cg'], "x_ngv_le_m": x['ngv_le'], "x_nozzle_exit_m": x['nozzle_exit'],
        "x_inlet_lip_m": x['inlet_lip'], "x_shaft_front_m": x['shaft_front'], "x_shaft_rear_m": x['shaft_rear'],
        "m_rotor_kg": st['rotor_mass_kg'], "x_rotor_cg_m": st['rotor_cg_x_m'], "Ip_rotor_kg_m2": st['rotor_Ip_kg_m2'],
        "m_shaft_stack_kg": st['shaft_mass_kg'],
        "stack_checks_failed_count": float(sum(c.status == 'fail' for c in st['checks'])),
    }
