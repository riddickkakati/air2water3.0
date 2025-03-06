import numpy as np


def shuffle(arr):
    """
    Shuffle array in place
    """
    return np.random.permutation(arr)


def latin_hypercube_sampling(n_run, n_par, parmin, parmax, objective_func, min_eff_index=-999):
    """
    Latin Hypercube sampling

    Args:
        n_run: Number of samples
        n_par: Number of parameters
        parmin: Array of lower bounds for each parameter
        parmax: Array of upper bounds for each parameter
        objective_func: Function to evaluate samples
        min_eff_index: Minimum efficiency index threshold
    """
    print(f'N. run = {n_run}')

    # Initialize tracking variables
    gbest = np.zeros(n_par)
    foptim = -999
    ii = 0

    # Initialize permutation matrix
    permut = np.zeros((n_run, n_par), dtype=int)

    # Initialize and shuffle permutation matrix
    for j in range(n_par):
        permut[:, j] = np.arange(1, n_run + 1)
        permut[:, j] = shuffle(permut[:, j])

    # Main sampling loop
    for i in range(n_run):
        par = np.zeros(n_par)

        # Generate parameters using Latin Hypercube sampling
        for j in range(n_par):
            r = np.random.random()  # Random number between 0 and 1
            r = r + (permut[i, j] - 1.0)  # Add stratified sampling offset
            r = r / n_run  # Normalize to [0,1]

            # Scale to parameter bounds
            par[j] = parmin[j] + (parmax[j] - parmin[j]) * r


        # Evaluate objective function
        eff_index = objective_func(par)
        fit = eff_index

        # Store if above threshold
        if eff_index >= min_eff_index:
            ii += 1
            # Here you would write to file if needed:
            # write_results(par, eff_index)

        # Update best solution if improved
        if fit > foptim:
            foptim = fit
            gbest = par.copy()

        # Progress reporting
        if i >= 10 and i % (n_run // 10) == 0:
            print(f'{100.0 * i / n_runs:.1f}% done. Minimum objective function: {abs(foptim)}. Parameters: {abs(gbest)}')

    print(f'Calibration: objective function = {abs(foptim)}')

    return gbest, foptim


# Example usage:


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

    from air2water.calibrators.PSO_source import pso_oop
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

    start_time = time.time()

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




    # Example objective function
    def example_objective(params):
        return -np.sum((params - 0.5) ** 2)  # Simple quadratic function
    
    '''

    # Setup parameters
    n_runs = 4000000
    n_params = 8


    # Parameters to apply log transformation (indices 1 and 2)
    #log_params = [1, 2]


    # Run Monte Carlo sampling
    best_params, best_fitness = latin_hypercube_sampling(
        n_run=n_runs,
        n_par=n_params,
        parmin= s.lb,
        parmax= s.ub,
        objective_func=objective_function
    )

    print("\nResults:")
    print(f"Best parameters: {best_params}")
    print(f"Best fitness: {best_fitness}")

    print(np.array([time.time() - start_time])[0])