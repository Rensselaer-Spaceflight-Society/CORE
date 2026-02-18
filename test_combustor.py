import pytest
from V5_CombustionChamber_Design import MicroJetCombustor, print_report


@pytest.fixture
def kj66_inputs():
    return {
        'casing_od_inch': 4.33,
        'wall_thickness_mm': 0.5,
        'pressure_ratio': 2.2,
        'compressor_efficiency': 0.74,
        'mass_flow_air_kg_s': 0.23,
        'target_tit_k': 1123.0
    }


@pytest.fixture
def custom_inputs():
    return {
        'casing_od_inch': 6.0,
        'wall_thickness_mm': 1.5,
        'pressure_ratio': 1.5,
        'compressor_efficiency': 0.94,
        'mass_flow_air_kg_s': 0.487,
        'target_tit_k': 900.0
    }


@pytest.fixture
def kj66_combustor(kj66_inputs):
    return MicroJetCombustor(kj66_inputs)


@pytest.fixture
def custom_combustor(custom_inputs):
    return MicroJetCombustor(custom_inputs)


class TestMicroJetCombustorInit:

    def test_inputs_stored(self, kj66_combustor, kj66_inputs):
        assert kj66_combustor.inputs == kj66_inputs

    def test_constants_initialized(self, kj66_combustor):
        assert kj66_combustor.R == 287.05
        assert kj66_combustor.GAMMA == 1.4

    def test_design_params_exist(self, kj66_combustor):
        params = kj66_combustor.DESIGN_PARAMS
        assert 'target_annulus_vel' in params
        assert 'target_tube_liq_vel' in params
        assert 'target_pressure_drop' in params
        assert 'discharge_coeff_hole' in params
        assert 'max_LD_ratio' in params

    def test_fuel_params_exist(self, kj66_combustor):
        fuel = kj66_combustor.FUEL
        assert fuel['LHV'] == 43.0e6
        assert fuel['STOICH_AFR'] == 14.7
        assert fuel['RHO_LIQ'] == 800.0
        assert fuel['T_BOIL'] == 450.0


class TestCpCalculation:

    def test_cp_at_room_temp(self, kj66_combustor):
        cp = kj66_combustor._get_cp(300)
        assert 1000 < cp < 1100

    def test_cp_at_high_temp(self, kj66_combustor):
        cp = kj66_combustor._get_cp(1500)
        assert cp > kj66_combustor._get_cp(300)

    def test_cp_clamped_low(self, kj66_combustor):
        cp_low = kj66_combustor._get_cp(100)
        cp_200 = kj66_combustor._get_cp(200)
        assert cp_low == cp_200

    def test_cp_clamped_high(self, kj66_combustor):
        cp_high = kj66_combustor._get_cp(3000)
        cp_2000 = kj66_combustor._get_cp(2000)
        assert cp_high == cp_2000


class TestThermodynamics:

    def test_thermodynamics_sets_pressure(self, kj66_combustor, kj66_inputs):
        kj66_combustor.thermodynamics()
        P_amb = 101325
        expected_P2 = P_amb * kj66_inputs['pressure_ratio']
        assert kj66_combustor.res['P2_Pa'] == pytest.approx(expected_P2, rel=1e-6)

    def test_thermodynamics_sets_temperature(self, kj66_combustor):
        kj66_combustor.thermodynamics()
        T2 = kj66_combustor.res['T2_K']
        assert T2 > 288.15

    def test_thermodynamics_sets_density(self, kj66_combustor):
        kj66_combustor.thermodynamics()
        rho2 = kj66_combustor.res['rho2']
        expected_rho = kj66_combustor.res['P2_Pa'] / (287.05 * kj66_combustor.res['T2_K'])
        assert rho2 == pytest.approx(expected_rho, rel=1e-6)

    def test_higher_pr_gives_higher_temp(self, kj66_inputs):
        low_pr_inputs = kj66_inputs.copy()
        low_pr_inputs['pressure_ratio'] = 1.5
        high_pr_inputs = kj66_inputs.copy()
        high_pr_inputs['pressure_ratio'] = 3.0

        low_combustor = MicroJetCombustor(low_pr_inputs)
        high_combustor = MicroJetCombustor(high_pr_inputs)

        low_combustor.thermodynamics()
        high_combustor.thermodynamics()

        assert high_combustor.res['T2_K'] > low_combustor.res['T2_K']


class TestMassFlowAndFuel:

    def test_air_mass_flow_from_input(self, kj66_combustor, kj66_inputs):
        kj66_combustor.thermodynamics()
        kj66_combustor.mass_flow_and_fuel()
        assert kj66_combustor.res['mdot_air'] == kj66_inputs['mass_flow_air_kg_s']

    def test_fuel_mass_flow_positive(self, kj66_combustor):
        kj66_combustor.thermodynamics()
        kj66_combustor.mass_flow_and_fuel()
        assert kj66_combustor.res['mdot_fuel'] > 0

    def test_afr_reasonable(self, kj66_combustor):
        kj66_combustor.thermodynamics()
        kj66_combustor.mass_flow_and_fuel()
        afr = kj66_combustor.res['overall_AFR']
        assert afr > 14.7

    def test_autoscale_mass_flow(self, kj66_inputs):
        inputs_no_flow = kj66_inputs.copy()
        inputs_no_flow['mass_flow_air_kg_s'] = None
        combustor = MicroJetCombustor(inputs_no_flow)
        combustor.thermodynamics()
        combustor.mass_flow_and_fuel()
        assert combustor.res['mdot_air'] > 0

    def test_higher_tit_needs_more_fuel(self, kj66_inputs):
        low_tit = kj66_inputs.copy()
        low_tit['target_tit_k'] = 900.0
        high_tit = kj66_inputs.copy()
        high_tit['target_tit_k'] = 1200.0

        low_combustor = MicroJetCombustor(low_tit)
        high_combustor = MicroJetCombustor(high_tit)

        low_combustor.thermodynamics()
        low_combustor.mass_flow_and_fuel()
        high_combustor.thermodynamics()
        high_combustor.mass_flow_and_fuel()

        assert high_combustor.res['mdot_fuel'] > low_combustor.res['mdot_fuel']


class TestZonalAnalysis:

    def test_air_splits_sum_to_total(self, kj66_combustor):
        kj66_combustor.thermodynamics()
        kj66_combustor.mass_flow_and_fuel()
        kj66_combustor.zonal_analysis()

        total = (kj66_combustor.res['split_primary'] +
                 kj66_combustor.res['split_secondary'] +
                 kj66_combustor.res['split_dilution'])
        assert total == pytest.approx(kj66_combustor.res['mdot_air'], rel=1e-6)

    def test_primary_zone_positive(self, kj66_combustor):
        kj66_combustor.thermodynamics()
        kj66_combustor.mass_flow_and_fuel()
        kj66_combustor.zonal_analysis()
        assert kj66_combustor.res['split_primary'] > 0

    def test_secondary_zone_positive(self, kj66_combustor):
        kj66_combustor.thermodynamics()
        kj66_combustor.mass_flow_and_fuel()
        kj66_combustor.zonal_analysis()
        assert kj66_combustor.res['split_secondary'] > 0

    def test_primary_temp_higher_than_inlet(self, kj66_combustor):
        kj66_combustor.thermodynamics()
        kj66_combustor.mass_flow_and_fuel()
        kj66_combustor.zonal_analysis()
        assert kj66_combustor.res['T_primary_zone_est'] > kj66_combustor.res['T2_K']


class TestMechanicalGeometry:

    def test_liner_smaller_than_casing(self, kj66_combustor):
        kj66_combustor.run()
        assert kj66_combustor.res['liner_od_mm'] < kj66_combustor.res['casing_id_mm']

    def test_liner_id_smaller_than_od(self, kj66_combustor):
        kj66_combustor.run()
        assert kj66_combustor.res['liner_id_mm'] < kj66_combustor.res['liner_od_mm']

    def test_annulus_gap_positive(self, kj66_combustor):
        kj66_combustor.run()
        assert kj66_combustor.res['annulus_gap_mm'] > 0

    def test_chamber_length_respects_ld_ratio(self, kj66_combustor):
        kj66_combustor.run()
        expected_length = kj66_combustor.res['liner_od_mm'] * kj66_combustor.DESIGN_PARAMS['max_LD_ratio']
        assert kj66_combustor.res['chamber_length_mm'] == pytest.approx(expected_length, rel=1e-6)


class TestVaporizerTubes:

    def test_even_number_of_tubes(self, kj66_combustor):
        kj66_combustor.run()
        assert kj66_combustor.res['vap_n'] % 2 == 0

    def test_tube_od_greater_than_id(self, kj66_combustor):
        kj66_combustor.run()
        assert kj66_combustor.res['vap_od_mm'] > kj66_combustor.res['vap_id_mm']

    def test_minimum_tube_id(self, kj66_combustor):
        kj66_combustor.run()
        assert kj66_combustor.res['vap_id_mm'] >= 4.0

    def test_vapor_exit_velocity_positive(self, kj66_combustor):
        kj66_combustor.run()
        assert kj66_combustor.res['vap_exit_velocity'] > 0


class TestHoleSizing:

    def test_primary_holes_positive(self, kj66_combustor):
        kj66_combustor.run()
        assert kj66_combustor.res['holes_pri_qty'] > 0
        assert kj66_combustor.res['holes_pri_mm'] > 0

    def test_secondary_holes_positive(self, kj66_combustor):
        kj66_combustor.run()
        assert kj66_combustor.res['holes_sec_qty'] > 0
        assert kj66_combustor.res['holes_sec_mm'] > 0

    def test_dilution_holes_exist_when_needed(self, kj66_combustor):
        kj66_combustor.run()
        if kj66_combustor.res['split_dilution'] > 0:
            assert kj66_combustor.res['holes_dil_mm'] > 0

    def test_primary_holes_twice_vaporizer_count(self, kj66_combustor):
        kj66_combustor.run()
        assert kj66_combustor.res['holes_pri_qty'] == kj66_combustor.res['vap_n'] * 2


class TestIntegration:

    def test_full_run_completes(self, kj66_combustor):
        results = kj66_combustor.run()
        assert results is not None
        assert len(results) > 0

    def test_run_returns_all_expected_keys(self, kj66_combustor):
        results = kj66_combustor.run()
        expected_keys = [
            'P2_Pa', 'T2_K', 'rho2',
            'mdot_air', 'mdot_fuel', 'overall_AFR',
            'split_primary', 'split_secondary', 'split_dilution',
            'liner_od_mm', 'liner_id_mm', 'chamber_length_mm',
            'vap_n', 'vap_od_mm', 'vap_id_mm',
            'holes_pri_qty', 'holes_pri_mm',
            'holes_sec_qty', 'holes_sec_mm',
            'holes_dil_qty', 'holes_dil_mm'
        ]
        for key in expected_keys:
            assert key in results, f"Missing key: {key}"

    def test_kj66_realistic_values(self, kj66_combustor):
        results = kj66_combustor.run()
        assert 200000 < results['P2_Pa'] < 250000
        assert 0.003 < results['mdot_fuel'] < 0.008
        assert results['liner_od_mm'] < 110

    def test_custom_combustor_runs(self, custom_combustor):
        results = custom_combustor.run()
        assert results is not None

    def test_print_report_no_error(self, kj66_combustor, kj66_inputs, capsys):
        results = kj66_combustor.run()
        print_report(results, kj66_inputs)
        captured = capsys.readouterr()
        assert 'Reverse Flow Combustor' in captured.out


class TestEdgeCases:

    def test_low_pressure_ratio(self, kj66_inputs):
        inputs = kj66_inputs.copy()
        inputs['pressure_ratio'] = 1.1
        combustor = MicroJetCombustor(inputs)
        results = combustor.run()
        assert results['P2_Pa'] > 101325

    def test_high_efficiency_compressor(self, kj66_inputs):
        inputs = kj66_inputs.copy()
        inputs['compressor_efficiency'] = 0.99
        combustor = MicroJetCombustor(inputs)
        results = combustor.run()
        assert results['T2_K'] > 288.15

    def test_thin_wall_thickness(self, kj66_inputs):
        inputs = kj66_inputs.copy()
        inputs['wall_thickness_mm'] = 0.1
        combustor = MicroJetCombustor(inputs)
        results = combustor.run()
        assert results['liner_od_mm'] < results['casing_id_mm']

    def test_large_casing(self, kj66_inputs):
        inputs = kj66_inputs.copy()
        inputs['casing_od_inch'] = 12.0
        inputs['mass_flow_air_kg_s'] = 1.0
        combustor = MicroJetCombustor(inputs)
        results = combustor.run()
        assert results['liner_od_mm'] < 12 * 25.4
