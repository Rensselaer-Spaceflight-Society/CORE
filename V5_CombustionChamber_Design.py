import math

class MicroJetCombustor:
    def __init__(self, inputs):
        self.inputs = inputs
        self.res = {}
        self.R = 287.05
        self.GAMMA = 1.4
        
        self.DESIGN_PARAMS = {
            'target_annulus_vel': 35.0,  # m/s (Low to ensure even feed)
            'target_tube_liq_vel': 3.0,  # m/s (To prevent vapor lock/dribble)
            'target_pressure_drop': 0.04, # 4% dP across liner
            'discharge_coeff_hole': 0.60, # sharo edge hol asmp.
            'max_LD_ratio': 1.65          # L?D for shaft stability
        }
        # Fuel (Jet-A / Kerosene)
        self.FUEL = {
            "LHV": 43.0e6,
            "STOICH_AFR": 14.7,  # theoretical perf burn
            "RHO_LIQ": 800.0,
            "T_BOIL": 450.0      # K (aprox vap. T)
        }
    def _get_cp(self, T_kelvin):
        T = max(200, min(T_kelvin, 2000))
        cp = 950 + (0.21 * T) 
        return cp

    def thermodynamics(self): #air entering comb.
        P_amb = 101325
        T_amb = 288.15
        PR = self.inputs['pressure_ratio']
        eff_c = self.inputs['compressor_efficiency']
        P2 = P_amb * PR #compressor exit
        T2_iso = T_amb * (PR**((self.GAMMA - 1)/self.GAMMA))
        T2 = T_amb + (T2_iso - T_amb) / eff_c
        
        rho2 = P2 / (self.R * T2)
        self.res['P2_Pa'] = P2
        self.res['T2_K'] = T2
        self.res['rho2'] = rho2

    def mass_flow_and_fuel(self):
        if self.inputs.get('mass_flow_air_kg_s') is not None: #air mass flow
            m_air = self.inputs['mass_flow_air_kg_s']
        else: 
            ref_od = 0.1524 # based on 6 in case
            ref_flow = 0.45 
            m_air = ref_flow * ((self.inputs['casing_od_inch']*0.0254)**2 / ref_od**2)
        target_tit = self.inputs['target_tit_k'] #fuel flow
        T2 = self.res['T2_K']
        T_avg = (target_tit + T2) / 2
        cp_avg = self._get_cp(T_avg)
        comb_eff = 0.96
        energy_req = m_air * cp_avg * (target_tit - T2)
        m_fuel = energy_req / (self.FUEL['LHV'] * comb_eff)
        self.res['mdot_air'] = m_air
        self.res['mdot_fuel'] = m_fuel
        self.res['overall_AFR'] = m_air / m_fuel
        self.res['cp_used'] = cp_avg

    def zonal_analysis(self): #air split calc
        m_fuel = self.res['mdot_fuel']
        stoich = self.FUEL['STOICH_AFR']
        m_air_total = self.res['mdot_air']
        
        phi_primary = 1.6
        m_air_pri = (m_fuel * stoich) / phi_primary
        
        phi_secondary_target = 0.6 
        
        m_air_cumulative_target = (m_fuel * stoich) / phi_secondary_target #air required to hit phi=.6
        m_air_sec = m_air_cumulative_target - m_air_pri
        m_air_dil = m_air_total - m_air_pri - m_air_sec #dil. zone
        if m_air_dil < 0:
            m_air_dil = 0
            m_air_sec = m_air_total - m_air_pri
        self.res['split_primary'] = m_air_pri
        self.res['split_secondary'] = m_air_sec
        self.res['split_dilution'] = m_air_dil
        #temp est.
        cp_flame = self._get_cp(2000)
        T_inlet = self.res['T2_K']
        m_fuel_burned = m_air_pri / stoich 
        Q_zone1 = m_fuel_burned * self.FUEL['LHV']
        m_total_zone1 = m_air_pri + m_fuel
        delta_T = Q_zone1 / (m_total_zone1 * cp_flame)
        self.res['T_primary_zone_est'] = T_inlet + delta_T

    def mechanical_geometry(self):
        """
        Sizes Casing/Liner based on velocity heuristics and wall thickness
        """
        od_m = self.inputs['casing_od_inch'] * 0.0254
        wall_m = self.inputs['wall_thickness_mm'] / 1000.0
        casing_id = od_m - (2 * wall_m)
        #annulus vel. sizing
        v_ann = self.DESIGN_PARAMS['target_annulus_vel']
        area_annulus = self.res['mdot_air'] / (self.res['rho2'] * v_ann)
        r_casing = casing_id / 2 #liner outer rad.
        r_liner = math.sqrt(r_casing**2 - (area_annulus / math.pi))
        liner_od = r_liner * 2
        liner_id = liner_od - (2 * wall_m)
        length = liner_od * self.DESIGN_PARAMS['max_LD_ratio']
        self.res['casing_id_mm'] = casing_id * 1000
        self.res['liner_od_mm'] = liner_od * 1000
        self.res['liner_id_mm'] = liner_id * 1000
        self.res['chamber_length_mm'] = length * 1000
        self.res['annulus_gap_mm'] = (casing_id - liner_od) / 2 * 1000

    def vaporizer_tubes(self):
        """
        sizes candy canes
        """
        circumference = math.pi * self.res['liner_id_mm']
        n_tubes = int(circumference / 35.0) #pitch is ~35mm
        if n_tubes % 2 != 0: n_tubes += 1
        m_fuel_per_tube = self.res['mdot_fuel'] / n_tubes
        #vel. sizing
        rho_fuel = self.FUEL['RHO_LIQ']
        target_v = self.DESIGN_PARAMS['target_tube_liq_vel']
        area_internal = m_fuel_per_tube / (rho_fuel * target_v)
        id_tube = math.sqrt(area_internal / math.pi) * 2
        id_tube = max(id_tube, 0.004) #min 4mm
        od_tube = id_tube + 0.001 #added thickness must be standard tube thickness
        #vapor exit vel. check
        rho_vapor = self.res['P2_Pa'] / (self.R * self.FUEL['T_BOIL'])
        v_exit_vapor = m_fuel_per_tube / (rho_vapor * (math.pi*(id_tube/2)**2))
        self.res['vap_n'] = n_tubes
        self.res['vap_od_mm'] = od_tube * 1000
        self.res['vap_id_mm'] = id_tube * 1000
        self.res['vap_exit_velocity'] = v_exit_vapor
        self.res['vap_bend_radius_mm'] = (od_tube * 1000) * 1.5

    def hole_sizing(self):
        """
        Gives hole dia. based on pressure drops.
        """
        dP = self.res['P2_Pa'] * self.DESIGN_PARAMS['target_pressure_drop']
        Cd = self.DESIGN_PARAMS['discharge_coeff_hole']
        flow_factor = Cd * math.sqrt(2 * self.res['rho2'] * dP)
        A_pri = self.res['split_primary'] / flow_factor #areas of holes
        A_sec = self.res['split_secondary'] / flow_factor
        A_dil = self.res['split_dilution'] / flow_factor
        n_pri = self.res['vap_n'] * 2 #hole geom
        d_pri = math.sqrt(4 * (A_pri/n_pri) / math.pi)
        n_sec = self.res['vap_n']
        d_sec = math.sqrt(4 * (A_sec/n_sec) / math.pi)
        n_dil = self.res['vap_n']
        d_dil = math.sqrt(4 * (A_dil/n_dil) / math.pi)
        self.res['holes_pri_qty'] = n_pri
        self.res['holes_pri_mm'] = d_pri * 1000
        self.res['holes_sec_qty'] = n_sec
        self.res['holes_sec_mm'] = d_sec * 1000
        self.res['holes_dil_qty'] = n_dil
        self.res['holes_dil_mm'] = d_dil * 1000

    def run(self):
        self.thermodynamics()
        self.mass_flow_and_fuel()
        self.zonal_analysis()
        self.mechanical_geometry()
        self.vaporizer_tubes()
        self.hole_sizing()
        return self.res

def print_report(res, original_inputs):
    print("\n")
    print(f"Reverse Flow Combustor (Rev 8 - Variable Cp)")
    print(f"\n[1] Thermo")
    print(f"   Inlet Temp (T2):  {res['T2_K']:.0f} K")
    print(f"   Target TIT:       {original_inputs['target_tit_k']} K")
    print(f"   Est. Pilot Temp:  {res['T_primary_zone_est']:.0f} K (Rich Zone)")
    print(f"   Cp (Avg Used):    {res['cp_used']:.1f} J/kgK")
    print(f"\n[2] Flow Budget")
    print(f"   Total Air:        {res['mdot_air']:.3f} kg/s")
    print(f"   Total Fuel:       {res['mdot_fuel']*1000:.1f} g/s")
    print(f"   Air Split:        Pri: {res['split_primary']/res['mdot_air']:.1%} | Sec: {res['split_secondary']/res['mdot_air']:.1%} | Dil: {res['split_dilution']/res['mdot_air']:.1%}")
    if res['split_dilution'] <= 0:
        print(f"   *** Zero dilution air. Engine runs too hot for target TIT.")
    print(f"\n[3] Geometry (Based on {original_inputs['casing_od_inch']}\" OD)")
    print(f"   Liner OD:         {res['liner_od_mm']:.1f} mm")
    print(f"   Liner ID:         {res['liner_id_mm']:.1f} mm")
    print(f"   Annulus Gap:      {res['annulus_gap_mm']:.1f} mm")
    print(f"   Length:           {res['chamber_length_mm']:.1f} mm")
    print(f"\n[4] Mixing + Injection")
    print(f"   Vaporizers:       {res['vap_n']} tubes")
    print(f"   Tube Dims:        {res['vap_od_mm']:.1f}mm OD / {res['vap_id_mm']:.1f}mm ID")
    print(f"   Vapor Velocity:   {res['vap_exit_velocity']:.1f} m/s")
    print(f"NOTE: Although we want this to be 50-80m/s to prevent flashback, this doesn't  account\n\
for crimping the exits of the fuel tubes (essestially making small nozzles that will accelerate\n\
the fuel to ~2.5x its velocity). For ref: {res['vap_exit_velocity']/.4:.1f} m/s")
    print(f"\n[5] Hole Sizing")
    print(f"   Primary:          {res['holes_pri_qty']} x {res['holes_pri_mm']:.1f} mm")
    print(f"   Secondary:        {res['holes_sec_qty']} x {res['holes_sec_mm']:.1f} mm")
    print(f"   Dilution:         {res['holes_dil_qty']} x {res['holes_dil_mm']:.1f} mm")
    print()
#--#--#_#_#
#############
user_inputs = {
    'casing_od_inch': 6.0,
    'wall_thickness_mm': 1.5,
    'pressure_ratio': 1.5,
    'compressor_efficiency': 0.94,
    'mass_flow_air_kg_s': .487, # set none for autoscale
    'target_tit_k': 900.0} # max temp for steel (accounting for F.S.)
kj66_inputs = {
    'casing_od_inch': 4.33, #110mm
    'wall_thickness_mm': 0.5,
    'pressure_ratio': 2.2, #typical op. point (max ~2.4)
    'compressor_efficiency': 0.74, #cons est
    'mass_flow_air_kg_s': 0.23, #.22-.24
    'target_tit_k': 1123.0 #K
}
#user_inputs=kj66_inputs
#def compare_kj66()

if __name__ == "__main__":
    print("-"*60)
    print("-"*60)
    print("-"*60)
    KEYS = ['casing_od_inch', 'wall_thickness_mm', 'pressure_ratio',
            'compressor_efficiency', 'mass_flow_air_kg_s', 'target_tit_k']

    auto_manual = input(f"Enter '1' to manually input values. Any other key will "
                        f"use default values in program: ")

    if auto_manual == "1":
        print("\nEnter values separated by spaces in this order:")
        print("  casing_od_inch | wall_thickness_mm | pressure_ratio | "
              "compressor_efficiency | mass_flow_air_kg_s | target_tit_k")
        print("  Example: 6.0 1.5 1.5 0.94 0.487 900.0")
        print("  (Enter nothing for mass_flow_air_kg_s to use autoscale)\n")

        while True:
            raw = input("Enter: ").strip().split()
            if len(raw) != len(KEYS):
                print(f"Expected {len(KEYS)} values, got {len(raw)}. Please try again.")
                continue
            try:
                parsed = [float(v) if v.lower() != 'none' else None for v in raw]
                break
            except ValueError:
                print("Invalid input — ensure all values are numbers. Try again.")

        chosen_inputs = dict(zip(KEYS, parsed))
        print(f"\nUsing inputs: {chosen_inputs}")
    else:
        chosen_inputs = user_inputs
        print(f"\nUsing default inputs: {chosen_inputs}")

    model = MicroJetCombustor(chosen_inputs)
    results = model.run()
    print_report(results, chosen_inputs)
    print()
    CL=False
    while CL==False:
        close=input("Pressing X, Q, 5, or just Enter to close this window, results will not be saved: ")
        close_list=["x","X","Q","q","5",""]
        if close in close_list:
            break