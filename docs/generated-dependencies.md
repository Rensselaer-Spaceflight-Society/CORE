# Generated module dependencies

Generated from `reads` and `writes`; arrows mean information flow, not gas flow.

Regenerate with `python scripts/generate_dependencies.py`.

```mermaid
flowchart TD
    m01_cycle["m01_cycle: Design point cycle and station table"]
    m10_compressor["m10_compressor: Impeller sizing: exducer, inducer, blade width"]
    m11_diffuser["m11_diffuser: Radial diffuser: exit diameter, vane count, throat"]
    m12_ngv["m12_ngv: NGV throat area, vane count, exit swirl"]
    m13_turbine["m13_turbine: Turbine mean-line: diameters, blade height, count, mass"]
    m20_combustor["m20_combustor: Combustor: liner, zones, air splits, holes, vaporizers"]
    m24_combustor_checks["m24_combustor_checks: Frozen combustor diagnostic checks"]
    m30_shaft["m30_shaft: Shaft diameter, length, bearing span, torque"]
    m31_bearings["m31_bearings: Bearing DN, axial load, stiffness"]
    m32_rotordyn["m32_rotordyn: First bending critical and separation margin"]
    m33_turb_stress["m33_turb_stress: Blade centrifugal stress screening and AN^2"]
    m34_casing["m34_casing: Engine envelope: OD, length, dry mass"]
    m40_nozzle["m40_nozzle: Nozzle exit area, velocity, gross thrust"]
    m50_fuel["m50_fuel: Fuel flow, line sizing, pump pressure"]
    m01_cycle --> m10_compressor
    m01_cycle --> m11_diffuser
    m01_cycle --> m12_ngv
    m01_cycle --> m13_turbine
    m01_cycle --> m20_combustor
    m01_cycle --> m30_shaft
    m01_cycle --> m31_bearings
    m01_cycle --> m40_nozzle
    m01_cycle --> m50_fuel
    m10_compressor --> m11_diffuser
    m10_compressor --> m30_shaft
    m10_compressor --> m31_bearings
    m10_compressor --> m32_rotordyn
    m10_compressor --> m34_casing
    m11_diffuser --> m34_casing
    m13_turbine --> m12_ngv
    m13_turbine --> m30_shaft
    m13_turbine --> m31_bearings
    m13_turbine --> m32_rotordyn
    m13_turbine --> m33_turb_stress
    m13_turbine --> m34_casing
    m20_combustor --> m24_combustor_checks
    m20_combustor --> m30_shaft
    m20_combustor --> m34_casing
    m20_combustor --> m50_fuel
    m30_shaft --> m32_rotordyn
    m30_shaft --> m34_casing
    m31_bearings --> m32_rotordyn
    m34_casing --> m20_combustor
    m40_nozzle --> m34_casing
```

## Execution order

```text
  1. m01_cycle
  2. m10_compressor
  3. m11_diffuser
  4. m13_turbine
  5. m12_ngv
  6. m40_nozzle
  7. [iterate to convergence: m30_shaft, m34_casing, m20_combustor]
  8. m24_combustor_checks
  9. m31_bearings
 10. m32_rotordyn
 11. m33_turb_stress
 12. m50_fuel
```

Independent branches may be designed concurrently. No calibrated component-efficiency feedback currently exists.
