# Use for cython
import pyximport; pyximport.install()
from forecasting.air2water.cython_modules import Air2WaterSolvercn,Air2waterSolvereuler,Air2waterSolverrk2,Air2waterSolverrk4,Air2StreamSolvercn,Air2StreamSolvereuler,Air2StreamSolverrk2,Air2StreamSolverrk4

#Use for fortran
import os
import fmodpy
dir= os.path.dirname(os.path.realpath(__file__))
myflib = fmodpy.fimport(dir + os.sep + str("fortran_modules.f90"))

import numpy as np

class air2water:
    def __init__(self, Tw_solution,Ta_data,tt,a1,a2,a3,a4,a5,a6,a7,a8,version,solver,compiler,CFL):
        self.Tw_solution = Tw_solution
        self.Ta_data = Ta_data
        self.tt=tt
        self.a1 = a1
        self.a2 = a2
        self.a3 = a3
        self.a4 = a4
        self.a5 = a5
        self.a6 = a6
        self.a7 = a7
        self.a8 = a8
        self.version = version
        self.solver=solver
        self.CFL=CFL
        self.compiler=compiler
        self.Tmin = max(0, min(self.Tw_solution))
        self.Tmin = max(4, self.Tmin)
        self.Nt = len(self.Ta_data)  # Number of time steps
        self.dt = 1.0
        if np.isnan(self.Tw_solution[0]):
            self.Tw_solution[0] = self.Tmin
        else:
            pass

        self.Tw_solution = np.asarray(self.Tw_solution)  # .astype(np.float32) # remove astype(np.float32) for cython
        self.Ta_data = np.asarray(self.Ta_data)  # .astype(np.float32) # remove astype(np.float32) for cython

        self.a = np.asarray([self.a1, self.a2, self.a3, self.a4, self.a5, self.a6, self.a7,
                        self.a8])  # .astype(np.float32) # remove astype(np.float32) for cython

    def solve(self):
        if self.compiler=="cython":
            if self.solver=="cranknicolson":
                params = Air2WaterSolvercn(self.Tw_solution, self.Ta_data,
                                         self.version,
                                          self.tt, self.a, self.Tmin, self.Nt, self.dt)
                params.solve()
                return self.Tw_solution
            elif self.solver=="euler":
                params = Air2waterSolvereuler(self.Tw_solution, self.Ta_data,
                                         self.version, self.CFL,
                                          self.tt, self.a, self.Tmin, self.Nt, self.dt)
                params.solve()
                return self.Tw_solution
            elif self.solver=="rk2":
                params = Air2waterSolverrk2(self.Tw_solution, self.Ta_data,
                                              self.version, self.CFL,
                                              self.tt, self.a, self.Tmin, self.Nt, self.dt)
                params.solve()
                return self.Tw_solution
            elif self.solver=="rk4":
                params = Air2waterSolverrk4(self.Tw_solution, self.Ta_data,
                                            self.version, self.CFL,
                                            self.tt, self.a, self.Tmin, self.Nt, self.dt)
                params.solve()
                return self.Tw_solution
        elif self.compiler=="fortran":
            if self.solver=="cranknicolson":
                myflib.air2watercn_loop(self.Tw_solution, self.Ta_data,
                                self.version,
                                self.tt, self.a, self.Tmin, self.Nt, self.dt)
                return self.Tw_solution
            elif self.solver=="euler": ##Replace this with fortran code. This has been placed or else the code doesnot run.
                myflib.air2watereuler_loop(self.Tw_solution, self.Ta_data,
                                        self.version, self.CFL,
                                        self.tt, self.a, self.Tmin, self.Nt, self.dt)
                return self.Tw_solution
            elif self.solver=="rk2":
                myflib.air2waterrk2_loop(self.Tw_solution, self.Ta_data,
                                           self.version, self.CFL,
                                           self.tt, self.a, self.Tmin, self.Nt, self.dt)
                return self.Tw_solution
            elif self.solver=="rk4":
                myflib.air2waterrk4_loop(self.Tw_solution, self.Ta_data,
                                         self.version, self.CFL,
                                         self.tt, self.a, self.Tmin, self.Nt, self.dt)
                return self.Tw_solution

        else:
            print("Please mention whether to use cython or fortran compiler")
            exit()



class air2stream(air2water):
    def __init__(self, Tw_solution,Ta_data,Q,tt,a1,a2,a3,a4,a5,a6,a7,a8,version,solver,compiler):
        super().__init__(Tw_solution,Ta_data,tt,a1,a2,a3,a4,a5,a6,a7,a8,version,solver,compiler,CFL=0.9)
        self.Q= Q
        self.Q = np.asarray(self.Q)  # .astype(np.float32) # remove astype(np.float32) for cython
        self.Qmedia= np.nanmean(Q)

    def solve(self):

        if self.compiler=="cython":
            if self.solver=="cranknicolson":
                params = Air2StreamSolvercn(self.Tw_solution, self.Ta_data, self.Q, self.Qmedia,
                                         self.version,
                                          self.tt, self.a, self.Tmin, self.Nt, self.dt)
                params.solve()
                return self.Tw_solution
            elif self.solver=="euler":
                params = Air2StreamSolvereuler(self.Tw_solution, self.Ta_data, self.Q, self.Qmedia,
                                            self.version,
                                            self.tt, self.a, self.Tmin, self.Nt, self.dt)
                params.solve()
                return self.Tw_solution
            elif self.solver=="rk2":
                params = Air2StreamSolverrk2(self.Tw_solution, self.Ta_data, self.Q, self.Qmedia,
                                            self.version,
                                            self.tt, self.a, self.Tmin, self.Nt, self.dt)
                params.solve()
                return self.Tw_solution
            elif self.solver=="rk4":
                params = Air2StreamSolverrk4(self.Tw_solution, self.Ta_data, self.Q, self.Qmedia,
                                            self.version,
                                            self.tt, self.a, self.Tmin, self.Nt, self.dt)
                params.solve()
                return self.Tw_solution

        elif self.compiler=="fortran":
            if self.solver=="cranknicolson":
                myflib.air2streamcn_loop(self.Tw_solution, self.Ta_data, self.Q, self.Qmedia,
                                self.version,
                                self.tt, self.a, self.Tmin, self.Nt, self.dt)
                return self.Tw_solution
            elif self.solver == "euler":
                myflib.air2streameuler_loop(self.Tw_solution, self.Ta_data, self.Q, self.Qmedia,
                                         self.version,
                                         self.tt, self.a, self.Tmin, self.Nt, self.dt)
                return self.Tw_solution
            elif self.solver == "rk2":
                myflib.air2streamrk2_loop(self.Tw_solution, self.Ta_data, self.Q, self.Qmedia,
                                            self.version,
                                            self.tt, self.a, self.Tmin, self.Nt, self.dt)
                return self.Tw_solution
            elif self.solver == "rk4":
                myflib.air2streamrk4_loop(self.Tw_solution, self.Ta_data, self.Q, self.Qmedia,
                                          self.version,
                                          self.tt, self.a, self.Tmin, self.Nt, self.dt)
                return self.Tw_solution

        else:
            print("Please mention whether to use cython or fortran compiler")
            exit()

if __name__ == "__main__":
    import pandas as pd
    df= pd.read_csv("/home/dicam01/DEV/Work/air2water/data/stndrck_sat_cc.txt",delimiter="\t")
    a=[0.02, 0.006, 0.009,3.45,0.01,0.44,0.00,0.00]
    Y = df.iloc[:, 0].tolist()
    M = df.iloc[:, 1].tolist()
    D = df.iloc[:, 2].tolist()
    Ta_data = df.iloc[:, 3]
    Ta_data[Ta_data == -999] = np.nan
    Ta_data = Ta_data.tolist()
    Tw_solution = df.iloc[:, 4]
    Tw_solution[Tw_solution == -999] = np.nan
    Tw_solution = Tw_solution.tolist()
    air2_water_setup = air2water(Tw_solution,Ta_data,Y,M,D,a[0],a[1],a[2],a[3],a[4],a[5],a[6],a[7],8,"euler","cython")
    Tw_solution = air2_water_setup.solve()
    print(Tw_solution)
