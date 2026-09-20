"""Pure mechanics helpers for the structures lessons. Standard library only.

Every function here is deterministic, side-effect free and rejects its own
invalid domain with a ValueError carrying a sentence a beginner can act on.
The runtime turns that ValueError into an `invalid_inputs` record instead of a
plausible-looking number, which is the behaviour we want: a wrong answer that
looks right is worse than no answer.

NOTHING IN THIS FILE IS AN ALLOWABLE, A MARGIN OR AN APPROVAL. These are
textbook screening formulae for teaching. Their results are tagged `computed`
and still require the structures lead, Safety and (for anything fabricated)
the shop/welding authority.

Conventions used throughout:
  * SI internally. Lesson questions are asked in mm / kPa / N*m because that is
    what drawings and datasheets use; the adapters below convert once, in one
    visible place, and the conversion is written into each Calculation.method.
  * Pressure is always a DIFFERENCE across the wall, p_i - p_o, following the
    Air Force Flight Dynamics Laboratory Stress Analysis Manual Sec. 8.3.1.
    A gauge pressure is only the same thing as (p_i - p_o) when the outside is
    at exactly the reference ambient. Say which you have.
"""

import math

# Air Force Flight Dynamics Laboratory, "Stress Analysis Manual", Oct 1986,
# Sec. 8.3.1: "Thin pressure vessels are those for which the ratio of the least
# radius of curvature of the wall to its thickness is greater than ten."
THIN_WALL_MIN_R_OVER_T = 10.0

PA_PER_KPA = 1000.0
M_PER_MM = 0.001


def _positive(name, value, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number.")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite; NaN and infinity are not evidence.")
    if value < 0 or (value == 0 and not allow_zero):
        raise ValueError(
            f"{name} must be greater than zero. A wall with zero or negative "
            "thickness is not a geometry error you can divide by - check the "
            "drawing, and record UNKNOWN if you do not have the dimension."
        )
    return float(value)


def _finite(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number.")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite; NaN and infinity are not evidence.")
    return float(value)


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------

def mean_radius_m(inner_diameter_mm, thickness_mm):
    """Mid-wall radius in m. r_mean = ID/2 + t/2, the AFFDL 8.3.1 convention."""
    d = _positive("Inner diameter", inner_diameter_mm)
    t = _positive("Wall thickness", thickness_mm)
    return (d + t) * M_PER_MM / 2.0


def inner_radius_m(inner_diameter_mm):
    """Inner radius in m. This is the convention the existing structures
    object-example.py used (inner_diam * 0.5); kept so the two agree."""
    return _positive("Inner diameter", inner_diameter_mm) * M_PER_MM / 2.0


def r_over_t(inner_diameter_mm, thickness_mm):
    """Mid-wall radius / thickness. Compare against THIN_WALL_MIN_R_OVER_T."""
    t = _positive("Wall thickness", thickness_mm)
    return mean_radius_m(inner_diameter_mm, thickness_mm) / (t * M_PER_MM)


def thin_wall_applicable(inner_diameter_mm, thickness_mm):
    return r_over_t(inner_diameter_mm, thickness_mm) > THIN_WALL_MIN_R_OVER_T


# --------------------------------------------------------------------------
# Pressure difference across a wall
# --------------------------------------------------------------------------

def delta_p_pa(p_internal_abs_kpa, p_external_abs_kpa):
    """(p_i - p_o) in Pa from two ABSOLUTE pressures in kPa.

    Both inputs absolute means the student has to say what the outside of the
    wall sees, which is the step people skip. Subtracting ambient from an
    absolute internal pressure is how you get gauge; entering a gauge pressure
    here with 0 outside is the same number only if 'gauge' really was measured
    against this ambient.
    """
    p_i = _positive("Internal absolute pressure", p_internal_abs_kpa, allow_zero=True)
    p_o = _positive("External absolute pressure", p_external_abs_kpa, allow_zero=True)
    return (p_i - p_o) * PA_PER_KPA


def _tension_delta_p(p_internal_abs_kpa, p_external_abs_kpa):
    dp = delta_p_pa(p_internal_abs_kpa, p_external_abs_kpa)
    if dp <= 0:
        raise ValueError(
            "The outside pressure is not lower than the inside, so this wall is "
            "not in internal-pressure tension. Net EXTERNAL pressure is a "
            "buckling/stability problem, not a thin-wall hoop-tension problem, "
            "and it is not covered by this lesson. Record the case and take it "
            "to the structures lead."
        )
    return dp


# --------------------------------------------------------------------------
# Thin-wall membrane stress
# --------------------------------------------------------------------------

def hoop_stress_pa(p_internal_abs_kpa, p_external_abs_kpa, inner_diameter_mm, thickness_mm):
    """sigma_h = (p_i - p_o) * r_mean / t   [AFFDL Stress Analysis Manual 8.3.1]"""
    dp = _tension_delta_p(p_internal_abs_kpa, p_external_abs_kpa)
    t = _positive("Wall thickness", thickness_mm)
    return dp * mean_radius_m(inner_diameter_mm, thickness_mm) / (t * M_PER_MM)


def hoop_stress_inner_radius_pa(p_internal_abs_kpa, p_external_abs_kpa,
                                inner_diameter_mm, thickness_mm):
    """Same formula on the INNER radius, as the existing object-example.py wrote it.

    Kelly, Solid Mechanics Part I Sec. 7.3: the characteristic radius "could be
    the inner radius, the outer radius, or the average of the two - results for
    all three should be close." The gap between this and the mean-radius result
    is an honest measure of how much the thin-wall idealisation is worth here.
    """
    dp = _tension_delta_p(p_internal_abs_kpa, p_external_abs_kpa)
    t = _positive("Wall thickness", thickness_mm)
    return dp * inner_radius_m(inner_diameter_mm) / (t * M_PER_MM)


def axial_stress_closed_end_pa(p_internal_abs_kpa, p_external_abs_kpa,
                               inner_diameter_mm, thickness_mm):
    """sigma_a = (p_i - p_o) * r_mean / (2t), CLOSED ends only.

    This is exactly half the hoop stress, and the assumption behind it is that
    the pressure end load is reacted by this same wall. An open-ended duct, or
    a wall whose end load is carried by a separate flange, tie bolts or the
    shaft, does not see it. Say which arrangement you are drawing.
    """
    return hoop_stress_pa(p_internal_abs_kpa, p_external_abs_kpa,
                          inner_diameter_mm, thickness_mm) / 2.0


# --------------------------------------------------------------------------
# Section properties: three different things people call "I"
# --------------------------------------------------------------------------

def second_moment_area_solid_round_m4(diameter_mm):
    """AREA second moment about a diameter, I = pi*d^4/64. Units m^4. Bending."""
    d = _positive("Diameter", diameter_mm) * M_PER_MM
    return math.pi * d ** 4 / 64.0


def second_moment_area_tube_m4(outer_diameter_mm, inner_diameter_mm):
    """I = pi*(do^4 - di^4)/64 for a hollow round section. Units m^4."""
    do = _positive("Outer diameter", outer_diameter_mm) * M_PER_MM
    di = _positive("Inner diameter", inner_diameter_mm, allow_zero=True) * M_PER_MM
    if di >= do:
        raise ValueError("Inner diameter must be smaller than the outer diameter.")
    return math.pi * (do ** 4 - di ** 4) / 64.0


def polar_moment_area_solid_round_m4(diameter_mm):
    """POLAR area second moment, J = pi*d^4/32 = 2I. Units m^4. Torsion."""
    return 2.0 * second_moment_area_solid_round_m4(diameter_mm)


def polar_moment_area_tube_m4(outer_diameter_mm, inner_diameter_mm):
    """J = pi*(do^4 - di^4)/32 for a hollow round section. Units m^4."""
    return 2.0 * second_moment_area_tube_m4(outer_diameter_mm, inner_diameter_mm)


def mass_moment_inertia_solid_cylinder_kg_m2(mass_kg, diameter_mm):
    """MASS moment of inertia about the spin axis, I = m*r^2/2. Units kg*m^2.

    Different quantity, different units, different job. This one sets stored
    rotor energy (0.5*I*omega^2 in the DP-2 screen) and angular acceleration.
    It never appears in M*y/I or T*r/J.
    """
    m = _positive("Mass", mass_kg)
    r = _positive("Diameter", diameter_mm) * M_PER_MM / 2.0
    return 0.5 * m * r ** 2


# --------------------------------------------------------------------------
# Bending and torsion
# --------------------------------------------------------------------------

def bending_stress_pa(moment_nm, distance_mm, second_moment_m4):
    """sigma = M*y/I. y is measured from the NEUTRAL AXIS, not from the surface
    you happened to put the ruler on. Sign is dropped: this is the magnitude at
    a distance y, tension on one side and compression on the other."""
    m = _finite("Bending moment", moment_nm)
    y = _positive("Distance from the neutral axis", distance_mm) * M_PER_MM
    i = _positive("Second moment of area", second_moment_m4)
    return abs(m) * y / i


def bending_stress_solid_round_pa(moment_nm, diameter_mm):
    """Outer-fibre bending stress in a solid round bar: y = d/2, I = pi*d^4/64."""
    return bending_stress_pa(moment_nm, _positive("Diameter", diameter_mm) / 2.0,
                             second_moment_area_solid_round_m4(diameter_mm))


def torsional_shear_pa(torque_nm, radius_mm, polar_moment_m4):
    """tau = T*r/J, elastic, round section, no stress concentration."""
    t = _finite("Torque", torque_nm)
    r = _positive("Radius", radius_mm) * M_PER_MM
    j = _positive("Polar second moment of area", polar_moment_m4)
    return abs(t) * r / j


def torsional_shear_solid_round_pa(torque_nm, diameter_mm):
    """Surface shear in a solid round shaft: tau = 16*T/(pi*d^3).

    Same relation M30 uses to size the shaft from `tau_allow_shaft_Pa`, written
    the other way round. Rearranging it does not make the allowable correct.
    """
    return torsional_shear_pa(torque_nm, _positive("Diameter", diameter_mm) / 2.0,
                              polar_moment_area_solid_round_m4(diameter_mm))


def midspan_deflection_simple_central_load_m(load_n, span_mm, modulus_gpa, second_moment_m4):
    """delta = P*L^3/(48*E*I): SIMPLY SUPPORTED span, SINGLE CENTRAL load.

    Use it only after the supports and the load position have actually been
    stated. Change either one and the 48 changes with it (192 for built-in
    ends, 3 for a cantilever tip load). Elastic, small deflection, no shear
    deformation, uniform section, room-temperature E unless you say otherwise.
    """
    p = _finite("Load", load_n)
    length = _positive("Span", span_mm) * M_PER_MM
    e = _positive("Elastic modulus", modulus_gpa) * 1.0e9
    i = _positive("Second moment of area", second_moment_m4)
    return abs(p) * length ** 3 / (48.0 * e * i)


# --------------------------------------------------------------------------
# Fabrication arithmetic (Track B)
# --------------------------------------------------------------------------

def coupon_stock_area_mm2(coupon_length_mm, coupon_width_mm, coupon_count, scrap_percent):
    """Sheet area to buy for a coupon matrix, including a stated scrap allowance.

    Nesting, edge trim, clamp land and the piece you ruin setting the machine up
    are what the scrap allowance is for. It is an allowance you chose, not a
    measured yield, and it is not a quotation.
    """
    length = _positive("Coupon length", coupon_length_mm)
    width = _positive("Coupon width", coupon_width_mm)
    if isinstance(coupon_count, bool) or not isinstance(coupon_count, (int, float)):
        raise ValueError("Coupon count must be a number.")
    if not math.isfinite(coupon_count) or coupon_count < 1 or coupon_count != int(coupon_count):
        raise ValueError("Use a whole number of coupons, at least 1.")
    scrap = _positive("Scrap allowance", scrap_percent, allow_zero=True)
    return length * width * int(coupon_count) * (1.0 + scrap / 100.0)


def cash_stock_cost_usd(stock_price_usd, shipping_usd):
    """Cash only: price + shipping, one currency, one quote.

    Excludes taxes, duties, tooling, consumables and shop time. Confirmed
    in-kind coverage is deliberately NOT subtracted here - donated material is
    recorded on its own line so it cannot be counted twice, once as a saving
    and again as a discount.
    """
    price = _positive("Stock price", stock_price_usd, allow_zero=True)
    shipping = _positive("Shipping", shipping_usd, allow_zero=True)
    return price + shipping


def stack_tolerance_mm(*tolerances_mm):
    """Worst-case arithmetic stack: the sum of the absolute tolerances.

    Worst case, not RSS. RSS assumes independent, centred, normally distributed
    variation and a tolerable escape rate; welding distortion is a systematic
    bias, not a random one, so worst case is the right first screen here.
    """
    if not tolerances_mm:
        raise ValueError("Give at least one tolerance to stack.")
    return sum(abs(_finite("Tolerance", value)) for value in tolerances_mm)


def radial_clearance_after_stack_mm(nominal_clearance_mm, *tolerances_mm):
    """Clearance left after the worst-case stack eats into it. May be negative;
    a negative number means interference, and it is returned, not clipped."""
    nominal = _finite("Nominal radial clearance", nominal_clearance_mm)
    return nominal - stack_tolerance_mm(*tolerances_mm)
