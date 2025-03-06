import numpy as np
from typing import List, Tuple
from forecasting.air2water.calibrators.spotpy_params_air2water_air2stream import spot_setup
import pandas as pd

class pso_oop:
    def __init__(self, objective_function, db_file, db_format, par_min: List[float], par_max: List[float],
                 swarm_size: int, maxiter: int, n_parameters: int = 8,
                 w_max: float = 0.9, w_min: float = 0.4,
                 phip: float = 2.0, phig: float = 2.0,
                 min_eff_index: float = 0.0, minstep: float = 0.001, threshold=10.0):
        """
        Initialize PSO parameters
        """
        self.db_file = db_file
        self.dbformat = db_format
        self.n_particles = swarm_size
        self.n_parameters = n_parameters
        self.objective_function = objective_function
        self.n_runs = maxiter
        self.par_min = np.array(par_min)
        self.par_max = np.array(par_max)
        self.w_max = w_max
        self.w_min = w_min
        self.c1 = phip
        self.c2 = phig
        self.min_eff_index = min_eff_index
        self.norm_min = minstep
        self.threshold=threshold

    def run(self) -> Tuple[np.ndarray, float]:

        df3 = []
        spotpyreaderlist = []

        """
        Run the PSO algorithm
        Returns:
            Tuple of (best parameters, best fitness)
        """
        print(f'N. particles = {self.n_particles}, N. run = {self.n_runs}')

        # Initialize particles
        x = np.random.uniform(0, 1, (self.n_parameters, self.n_particles))
        v = np.random.uniform(0, 1, (self.n_parameters, self.n_particles))
        pbest = np.zeros_like(x)
        fit = np.zeros(self.n_particles)
        fitbest = np.zeros(self.n_particles)

        # Scale parameters to their ranges
        for j in range(self.n_parameters):
            dx_max = self.par_max[j] - self.par_min[j]
            dv_max = 1.0 * dx_max
            x[j, :] = x[j, :] * dx_max + self.par_min[j]
            v[j, :] = v[j, :] * dv_max
            pbest[j, :] = x[j, :]

        # Initialize fitness
        for k in range(self.n_particles):
            parameters = x[:, k].copy()

            fit[k] = self.objective_function(parameters)
            fitbest[k] = fit[k]

        # Find initial global best
        best_idx = np.nanargmax(fit)
        gbest = x[:, best_idx].copy()
        foptim = fit[best_idx]

        # Main loop
        w = self.w_max
        dw = (self.w_max - self.w_min) / self.n_runs

        for i in range(self.n_runs):
            for k in range(self.n_particles):
                r = np.random.uniform(0, 1, 2 * self.n_parameters)
                status = 0

                # Update velocity and position
                for j in range(self.n_parameters):
                    v[j, k] = (w * v[j, k] +
                               self.c1 * r[j] * (pbest[j, k] - x[j, k]) +
                               self.c2 * r[j + self.n_parameters] * (gbest[j] - x[j, k]))
                    x[j, k] = x[j, k] + v[j, k]

                    # Absorbing wall boundary conditions
                    if x[j, k] > self.par_max[j]:
                        if j == 5:  # Special case for parameter 6 (0-based index)
                            x[j, k] = x[j, k] - np.floor(x[j, k])
                        else:
                            x[j, k] = self.par_max[j]
                            v[j, k] = 0.0
                            status = 1

                    if x[j, k] < self.par_min[j]:
                        if j == 5:  # Special case for parameter 6 (0-based index)
                            x[j, k] = np.ceil(abs(x[j, k])) - abs(x[j, k])
                        else:
                            x[j, k] = self.par_min[j]
                            v[j, k] = 0.0
                            status = 1

                # Compute new performance
                if status == 0:
                    parameters = x[:, k].copy()

                    fit[k] = self.objective_function(parameters)
                else:
                    fit[k] = -1e30

                # Update particle best
                if fit[k] > fitbest[k]:
                    fitbest[k] = fit[k]
                    pbest[:, k] = x[:, k]

            # Update global best
            best_idx = np.nanargmax(fitbest)
            if fitbest[best_idx] > foptim:
                gbest = pbest[:, best_idx].copy()
                foptim = fitbest[best_idx]

            # Update inertia weight
            w = w - dw

            # Progress reporting
            if i >= 10 and i % (self.n_runs // 10) == 0:
                print(f'{100.0 * i / self.n_runs:.1f}% done. Minimum objective function: {abs(foptim)}. Parameters: {abs(gbest)}')
                spot_setup.save(self,abs(foptim), gbest)
                glist = gbest
                newlist = []
                newlist.append(abs(foptim))
                for number in glist:
                    newlist.append(number)
                df3.append(newlist)
                spotpyreaderlist.append(tuple(newlist))

            # Early stopping condition
            count = 0
            for k in range(self.n_particles):
                norm = np.sqrt(np.sum(
                    ((pbest[:, k] - gbest) / (self.par_max - self.par_min)) ** 2
                ))
                if norm < self.norm_min:
                    count += 1

            if count >= 0.90 * self.n_particles:
                print('- Warning: PSO has been exit')
                break

        print(f'Calibration: objective function = {abs(foptim)}')

        if self.dbformat == "ram":
            return gbest, abs(foptim), df3, spotpyreaderlist
        else:
            return gbest, abs(foptim)


# Example usage:
if __name__ == "__main__":
    import fnmatch
    from air2water.IO.yaml_parser import read_yaml
    from spotpy.parameter import Uniform  # ,logNormal,Normal
    import math
    from air2water.core import air2stream, air2water
    import cProfile
    import sys
    from datetime import datetime
    #from air2water.calibrators.PSO_source import pso_oop
    # from air2water.calibrators.PSO_A2WS import pso_oop_new
    from air2water.calibrators.spotpy_params_air2water_air2stream import spot_setup
    from pycup.integrate import SpotpySetupConverter
    import time
    import spotpy
    import matplotlib.pyplot as plt
    import numpy as np
    import sqlite3
    import pandas as pd
    import os
    import fnmatch
    from air2water.IO.yaml_parser import read_yaml
    from spotpy.parameter import Uniform  # ,logNormal,Normal
    import math
    from air2water.core import air2stream, air2water
    import cProfile
    import sys
    from datetime import datetime


    class FilteredStdout:
        def __init__(self, file):
            self.file = file

        def write(self, message):
            self.file.write(message)

        def flush(self):
            if not self.file.closed:
                self.file.flush()


    def objective_function(x):
        # Replace this with your actual objective function
        sim = spot_setup.simulation(x)
        eval = spot_setup.evaluation()
        return spot_setup.objectivefunction(sim, eval)


    def evaluation(self):
        solution = np.array(self.Tw_solution)
        return list(solution)[366:]


    def simulation_air2water_log(self, x):
        # Here the model is actualy startet with one paramter combination
        params = air2water(self.Tw_solution, self.Ta_data, self.tt, x[0], 10 ** x[1], 10 ** x[2], x[3], x[4],
                           x[5], x[6], x[7], self.version, self.solver, self.compiler, self.CFL)
        # if self.mode2 != "forward":
        #     if x[5] > self.parameters[5].maxbound:
        #         x[5] = x[5] - np.floor(x[5])
        #     if x[5] < self.parameters[5].minbound:
        #         x[5] = np.ceil(np.abs(x[5])) - np.abs(x[5])
        data = params.solve()
        sim = []
        for val in data:
            sim.append(val)
        # The first year of simulation data is ignored (warm-up)
        return sim[366:]


    def simulation_air2stream(self, x):
        # Here the model is actualy startet with one paramter combination
        params = air2stream(self.Tw_solution, self.Ta_data, self.Q, self.tt, x[0],  # 10**
                            x[1],  # 10**
                            x[2], x[3], x[4], x[5], x[6], x[7], self.version, self.solver, self.compiler)
        # if self.mode2 != "forward":
        #     if x[5] > self.parameters[5].maxbound:
        #         x[5] = x[5] - np.floor(x[5])
        #     if x[5] < self.parameters[5].minbound:
        #         x[5] = np.ceil(np.abs(x[5])) - np.abs(x[5])
        data = params.solve()
        sim = []
        for val in data:
            sim.append(val)
        # The first year of simulation data is ignored (warm-up)
        solution = np.array(sim)
        return list(solution)[366:]


    owd = os.getcwd()
    file2 = ''
    # Air2water
    for file in os.listdir('.' + os.sep + str('config')):
        if fnmatch.fnmatch(file, 'parameters_depth=*m.yaml'):
            file2 = file
    '''
    #Air2stream
    for file in os.listdir('.' + os.sep + str('config')):
        if fnmatch.fnmatch(file, 'parameters_air2stream.yaml'):
            file2 = file
    '''
    filepath = str(owd + os.sep + str('config') + os.sep + file2)
    all_parameters1 = read_yaml(filepath)
    all_parameters = all_parameters1['Optimizer']['parameters']
    all_parameters_names = list(all_parameters.keys())
    a1 = globals()[all_parameters.get(all_parameters_names[0], {}).get('distribution')](name=all_parameters_names[0],
                                                                                        low=all_parameters.get('a1',
                                                                                                               {}).get(
                                                                                            'low'),
                                                                                        high=all_parameters.get('a1',
                                                                                                                {}).get(
                                                                                            'high'))
    # Air2water
    a2 = globals()[all_parameters.get(all_parameters_names[1], {}).get('distribution')](name=all_parameters_names[1],
                                                                                        low=math.log10(
                                                                                            all_parameters.get(
                                                                                                all_parameters_names[1],
                                                                                                {}).get('low')),
                                                                                        high=math.log10(
                                                                                            all_parameters.get(
                                                                                                all_parameters_names[1],
                                                                                                {}).get(
                                                                                                'high')))  # Search in logarithmic space
    a3 = globals()[all_parameters.get(all_parameters_names[2], {}).get('distribution')](name=all_parameters_names[2],
                                                                                        low=math.log10(
                                                                                            all_parameters.get(
                                                                                                all_parameters_names[1],
                                                                                                {}).get('low')),
                                                                                        high=math.log10(
                                                                                            all_parameters.get(
                                                                                                all_parameters_names[1],
                                                                                                {}).get(
                                                                                                'high')))  # Search in logarithmic space
    '''
    #Air2stream
    a2 = globals()[all_parameters.get(all_parameters_names[1], {}).get('distribution')](
        name=all_parameters_names[1],
        low=
        all_parameters.get(
            all_parameters_names[
                1],
            {}).get('low'),
        high=
        all_parameters.get(
            all_parameters_names[
                1],
            {}).get(
            'high'))  # Search in logarithmic space
    a3 = globals()[all_parameters.get(all_parameters_names[2], {}).get('distribution')](
        name=all_parameters_names[2],
        low=all_parameters.get(
            all_parameters_names[2],
            {}).get('low'),
        high=all_parameters.get(
            all_parameters_names[2],
            {}).get(
            'high'))
    '''
    a4 = globals()[all_parameters.get(all_parameters_names[3], {}).get('distribution')](name=all_parameters_names[3],
                                                                                        low=all_parameters.get(
                                                                                            all_parameters_names[3],
                                                                                            {}).get('low'),
                                                                                        high=all_parameters.get(
                                                                                            all_parameters_names[3],
                                                                                            {}).get('high'))
    a5 = globals()[all_parameters.get(all_parameters_names[4], {}).get('distribution')](name=all_parameters_names[4],
                                                                                        low=all_parameters.get(
                                                                                            all_parameters_names[4],
                                                                                            {}).get('low'),
                                                                                        high=all_parameters.get(
                                                                                            all_parameters_names[4],
                                                                                            {}).get('high'))
    a6 = globals()[all_parameters.get(all_parameters_names[5], {}).get('distribution')](name=all_parameters_names[5],
                                                                                        low=all_parameters.get(
                                                                                            all_parameters_names[5],
                                                                                            {}).get('low'),
                                                                                        high=all_parameters.get(
                                                                                            all_parameters_names[5],
                                                                                            {}).get('high'))
    a7 = globals()[all_parameters.get(all_parameters_names[6], {}).get('distribution')](name=all_parameters_names[6],
                                                                                        low=all_parameters.get(
                                                                                            all_parameters_names[6],
                                                                                            {}).get('low'),
                                                                                        high=all_parameters.get(
                                                                                            all_parameters_names[6],
                                                                                            {}).get('high'))
    a8 = globals()[all_parameters.get(all_parameters_names[7], {}).get('distribution')](name=all_parameters_names[7],
                                                                                        low=all_parameters.get(
                                                                                            all_parameters_names[7],
                                                                                            {}).get('low'),
                                                                                        high=all_parameters.get(
                                                                                            all_parameters_names[7],
                                                                                            {}).get('high'))
    parameters = [a1, a2, a3, a4, a5, a6, a7, a8]

    # Air2water
    df = np.loadtxt(owd + os.sep + "data" + os.sep + "stndrck_sat_cc.txt")
    '''
    #Air2stream
    df = np.loadtxt(owd + os.sep + "data" + os.sep + "SIO_2011_cc.txt")
    '''
    # To replicate the first year of data so that we dont loose data
    Y = df[:, 0]
    M = df[:, 1]
    D = df[:, 2]
    date = [datetime(int(y), int(m), int(d)) for y, m, d in zip(Y, M, D)]
    tt = np.asarray([d.timetuple().tm_yday / 366 for d in date])
    initial_rows = df[:366].copy()
    df = np.concatenate([initial_rows, df])
    spot_setup.evaluation = evaluation
    # Air2water
    spot_setup.simulation = simulation_air2water_log
    spot_setup = spot_setup(parameters, model="air2water", df=df, tt=tt, db_file="SCEUA_hymod.db", optimizer="PSO",
                            threshold=None, solver="cranknicolson", compiler="fortran", mode2="calibration", version=8)
    '''
    ##Air2stream
    spot_setup.simulation= simulation_air2stream()
    spot_setup.Q = df[:, 5]
    spot_setup.Q[spot_setup.Q == -999] = np.nan
    spot_setup.Q = spot_setup.Q.tolist()
    Q_mean = np.nanmean(spot_setup.Q)
    spot_setup = spot_setup(parameters,model="air2stream",df=df,tt=tt,db_file="SCEUA_hymod.db",optimizer="PSO", threshold=None, solver="cranknicolson",compiler="fortran",mode2="calibration",version=8)
    '''
    s = SpotpySetupConverter()
    s.convert(spot_setup)
    # core=[1,2,3,4,5,6,7,8,9,10]
    o = [0.0, 0.1, 0.5, 1.0]  # 0.01,0.1,0.5,1.0
    mins = [1e-5, 1e-4, 1e-3]  # 1e-3,1e-4,1e-5
    php = [1.0, 2.0]  # 1.0,2.0
    ss = [1000, 2000]  # 1000,2000
    '''Working Code

    # Define objective function
    def objective_function(x):
        # Replace with your objective function
        return -np.sum(x ** 2)  # Simple example: minimize sum of squares
    '''
    # Example setup
    n_runs = 2000
    n_particles = 2000
    n_params = 8
    param_min = s.lb
    param_max = s.ub
    # Create and run PSO
    for n in range(30):
        start_time = time.time()
        pr = cProfile.Profile()
        pr.enable()
        PSO_init = pso_oop(
            swarm_size=n_particles,
            db_file=spot_setup.db_file,
            db_format="ram",
            maxiter=n_runs,
            n_parameters=n_params,
            par_min=param_min,
            par_max=param_max,
            objective_function=objective_function
        )
        best_parameters, best_fitness, _, _ = PSO_init.run()
        pr.disable()
        pr.print_stats(sort="calls")
        total_time = np.array([time.time() - start_time])[0]
        result_list = [total_time, best_fitness, n]
        output_file_path = owd + os.sep + str(
            f'03.10_PSO_own_a2w_all.txt')  # Change fortran/cython in core.py

        # Check if the file already exists
        if os.path.exists(output_file_path):
            # If the file exists, append a new line with the total_time
            with open(output_file_path, 'a') as file:
                np.savetxt(file, [result_list], fmt='%.10f')
        else:
            # If the file doesn't exist, create a new file with the total_time
            with open(output_file_path, 'w') as file:
                np.savetxt(file, [result_list], fmt='%.10f')