import numpy as np
from dataclasses import dataclass
import matplotlib.pyplot as plt

# let's make a dataclass for a pressure vessel, say the combustion chamber.

@dataclass
class PressureVessel:
    thickness: float #m
    inner_diam: float #m
    pressure_int: float #Pa
    pressure_ext: float #pa


    def hoop(self):

        return (self.pressure_int - self.pressure_ext)*self.inner_diam*0.5/self.thickness




combustor = PressureVessel(1e-3,0.2,2e6,0)

print('Hoop Stress (Pa) = ', combustor.hoop())


@dataclass
class Shaft:

    applied_torque: float #nm
    radius: float #m

    def __post_init__(self):
        self.polar_moment_inertia = np.pi*


    def funct(self,extra):

        return