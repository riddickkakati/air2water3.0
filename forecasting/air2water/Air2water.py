import pyswarms as ps
from .calibrators.PSO_python_riddick_sebastiano import pso_oop
from .calibrators.PSO_A2WS import pso_oop_new
from .calibrators.spotpy_params_air2water_air2stream import spot_setup
import pycup as cp
from pycup.integrate import SpotpySetupConverter
from pycup.integrate import SpotpyDbConverter
import time
import spotpy
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from io import BytesIO
import numpy as np
import sqlite3
import pandas as pd
import os
import yaml
import fnmatch
from .IO.yaml_parser import read_yaml
import shutil
from spotpy.parameter import Uniform  # ,logNormal,Normal
import math
from .IO.Interpolator import YearlyDataProcessor
from sklearn.model_selection import train_test_split
from .core import air2stream, air2water
from datetime import datetime
from .calibrators.Parameters import Air2WaterParameters
from django.conf import settings

from spotpy.algorithms import sceua
from spotpy.algorithms import abc  # Artificial Bee Colony
from spotpy.algorithms import dds  # Dynamically Dimensioned Search algorithm
from spotpy.algorithms import demcz  # Differential Evolution Markov Chain
from spotpy.algorithms import dream  # DiffeRential Evolution Adaptive Metropolis
from spotpy.algorithms import fast  # Fourier Amplitude Sensitivity Test
from spotpy.algorithms import fscabc  # Fitness Scaling Artificial Bee Colony
from spotpy.algorithms import lhs  # Latin Hypercube Sampling
from spotpy.algorithms import list_sampler  # Samples from  given spotpy database
from spotpy.algorithms import mc  # Monte Carlo
from spotpy.algorithms import mcmc  # Metropolis Markov Chain Monte Carlo
from spotpy.algorithms import mle  # Maximum Likelihood Estimation
# from spotpy.algorithms import nsgaii
from spotpy.algorithms import padds  # Pareto Archived - Dynamicallly Dimensioned Search algorithm
from spotpy.algorithms import rope  # RObust Parameter Estimation
from spotpy.algorithms import sa  # Simulated annealing
from spotpy.algorithms import sceua  # Shuffled Complex Evolution

from .IO.Send_emails import send_email


def simulation_air2water_log_pyswarms(self, x):
    # Here the model is actualy startet with one paramter combination
    params = air2water(self.Tw_solution, self.Ta_data, self.tt, x[0], 10 ** x[1], 10 ** x[2], x[3], x[4],
                       x[5], x[6], x[7], self.version, self.solver, self.compiler, self.CFL)

    # if self.mode2!="forward":
    #     if x[5]>self.parameters[5].maxbound:
    #         x[5] = x[5] - np.floor(x[5])
    #     if x[5]<self.parameters[5].minbound:
    #         x[5] = np.ceil(np.abs(x[5]))-np.abs(x[5])

    data = params.solve()
    sim = []
    for val in data:
        sim.append(val)
    # The first year of simulation data is ignored (warm-up)
    solution = np.array(sim)
    if not self.interpolate_use_rmse:
        solution = solution[self.df[:, 5] == 0]

    if self.df.shape[1] > 6:
        if self.mode2 != "validation":
            solution = solution[self.df[:, 6] == 1]
        if self.mode2 == "validation":
            solution = solution[self.df[:, 6] == 2]

    return list(solution)[366:]


def simulation_air2water_no_log_pyswarms(self, x):
    # Here the model is actualy startet with one paramter combination
    params = air2water(self.Tw_solution, self.Ta_data, self.tt, x[0], x[1], x[2], x[3], x[4],
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
    solution = np.array(sim)
    if not self.interpolate_use_rmse:
        solution = solution[self.df[:, 5] == 0]

    if self.df.shape[1] > 6:
        if self.mode2 != "validation":
            solution = solution[self.df[:, 6] == 1]
        if self.mode2 == "validation":
            solution = solution[self.df[:, 6] == 2]

    return list(solution)[366:]


def simulation_air2stream_pyswarms(self, x):
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
    if not self.interpolate_use_rmse:
        solution = solution[self.df[:, 6] == 0]

    if self.df.shape[1] > 7:
        if self.mode2 != "validation":
            solution = solution[self.df[:, 7] == 1]
        if self.mode2 == "validation":
            solution = solution[self.df[:, 7] == 2]

    return list(solution)[366:]


def simulation_air2water_log(self, x):
    # Here the model is actualy startet with one paramter combination
    params = air2water(self.Tw_solution, self.Ta_data, self.tt, x[0], 10 ** x[1], 10 ** x[2], x[3], x[4],
                       x[5], x[6], x[7], self.version, self.solver, self.compiler, self.CFL)

    # if self.mode2!="forward":
    #     if x[5]>self.parameters[5].maxbound:
    #         x[5] = x[5] - np.floor(x[5])
    #     if x[5]<self.parameters[5].minbound:
    #         x[5] = np.ceil(np.abs(x[5]))-np.abs(x[5])

    data = params.solve()
    sim = []
    for val in data:
        sim.append(val)
    # The first year of simulation data is ignored (warm-up)
    solution = np.array(sim)
    if not self.interpolate_use_rmse:
        solution = solution[self.df[:, 5] == 0]

    if self.df.shape[1] > 6:
        if self.mode2 != "validation":
            solution = solution[self.df[:, 6] == 1]
        elif self.mode2 == "validation":
            solution = solution[self.df[:, 6] == 2]

    return list(solution)[366:]


def simulation_air2water_no_log(self, x):
    # Here the model is actualy startet with one paramter combination
    params = air2water(self.Tw_solution, self.Ta_data, self.tt, x[0], x[1], x[2], x[3], x[4],
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
    solution = np.array(sim)
    if not self.interpolate_use_rmse:
        solution = solution[self.df[:, 5] == 0]

    if self.df.shape[1] > 6:
        if self.mode2 != "validation":
            solution = solution[self.df[:, 6] == 1]
        if self.mode2 == "validation":
            solution = solution[self.df[:, 6] == 2]

    return list(solution)[366:]


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
    if not self.interpolate_use_rmse:
        solution = solution[self.df[:, 6] == 0]

    if self.df.shape[1] > 7:
        if self.mode2 != "validation":
            solution = solution[self.df[:, 7] == 1]
        if self.mode2 == "validation":
            solution = solution[self.df[:, 7] == 2]

    return list(solution)[366:]


def evaluation_air2water(self):
    solution = np.array(self.Tw_solution)
    if not self.interpolate_use_rmse:
        solution = solution[self.df[:, 5] == 0]

    if self.df.shape[1] > 6:
        if self.mode2 != "validation":
            solution = solution[self.df[:, 6] == 1]
        if self.mode2 == "validation":
            solution = solution[self.df[:, 6] == 2]

    return list(solution)[366:]


def evaluation_air2stream(self):
    solution = np.array(self.Tw_solution)
    if not self.interpolate_use_rmse:
        solution = solution[self.df[:, 6] == 0]

    if self.df.shape[1] > 7:
        if self.mode2 != "validation":
            solution = solution[self.df[:, 7] == 1]
        if self.mode2 == "validation":
            solution = solution[self.df[:, 7] == 2]

    return list(solution)[366:]


def dottyplots(df, theoritical_bounds, parameter_low, parameter_high, final_rmse, error_metric, user_id, group_id, sim_id):
    owd = settings.MEDIA_ROOT
    #column_order = list(df.columns)
    #column_order.insert(0, column_order.pop(-1))
    #df = df[column_order]

    # Renaming the plots as a1 to a8
    fig, axs = plt.subplots(2, 4, figsize=(15, 10))  # 2 rows, 4 columns of subplots

    # Plot each subplot and rename
    for i in range(8):
        row, col = i // 4, i % 4
        axs[row, col].plot(np.array(df.iloc[:,i]), np.array(df.iloc[:,8]), 'o', color='r')  # 'o' for dot style
        axs[row, col].plot(theoritical_bounds[0, i], final_rmse, 'o', color='g')
        axs[row, col].plot(theoritical_bounds[1, i], final_rmse, 'o', color='b')  # 'o' for dot style
        axs[row, col].plot(parameter_low[i], final_rmse, 'o', color='k')
        axs[row, col].plot(parameter_high[i], final_rmse, 'o', color='k')
        axs[row, col].set_title(f'a{i + 1}')  # Rename as a1, a2, ..., a8

    for ax in axs.flat:
        if error_metric == "RMSE":
            ax.set(xlabel='Parameter Value', ylabel='RMSE')
        elif error_metric == "NS":
            ax.set(xlabel='Parameter Value', ylabel='NSE')
        elif error_metric == "KGE":
            ax.set(xlabel='Parameter Value', ylabel='KGE')

    custom_lines = [Line2D([0], [0], marker='o', color='red', lw=2),
                    Line2D([0], [0], marker='o', color='black', lw=2),
                    Line2D([0], [0], marker='o', color='green', lw=2),
                    Line2D([0], [0], marker='o', color='blue', lw=2)]
    plt.figlegend(custom_lines,
                  ['PSO iterations', 'Physical bounds', 'Regression 6 parameters', 'Regression 4 parameters'],
                  loc='lower center', ncol=4, frameon=False)
    plt.subplots_adjust(hspace=0.3, wspace=0.4, bottom=0.1)

    # Save the plot to BytesIO object
    plt.savefig(f"{owd}/results/{user_id}_{group_id}/dottyplots_{sim_id}.png", dpi=100)
    plt.close()  # Close the plot to avoid displaying it

    return

class Air2water_OOP:
    owd = settings.MEDIA_ROOT
    # owd = os.getcwd() #Activate this for running in PyCharm
    #owd = "/home/dicam01/DEV/Work/air2water"  # Activate this for fastapi

    def objective_function_pyswarm(self, x):
        # Replace this with your actual objective function
        sim = self.spot_setup.simulation(x)
        eval = self.spot_setup.evaluation()

        return self.spot_setup.objectivefunction(sim, eval)

    def objective_function_pycup(self, x):
        # Replace this with your actual objective function
        sim = self.spot_setup.simulation(x)
        eval = self.spot_setup.evaluation()

        fitness = self.spot_setup.objectivefunction(sim, eval)
        result = np.array(sim).reshape(1, -1)

        return fitness, result

    def datetimecalc(self, dfinput):
        Y = dfinput[:, 0]
        M = dfinput[:, 1]
        D = dfinput[:, 2]
        date = [datetime(int(y), int(m), int(d)) for y, m, d in zip(Y, M, D)]
        return date, np.asarray([d.timetuple().tm_yday / 366 for d in date])

    def __init__(self, user_id=0, group_id=0, uuid=None, spot_setup=spot_setup, warmup_year=True, interpolate=True, n_data_interpolate=7, Tmin=np.nan,
                 validation_required=False, percent=10,
                 model="air2water", version= 8, core=1, depth=14.0, swarmsize=20, phi1=2.0, phi2=2.0, omega1=0.9, omega2 = 0.4, maxiter=20,
                 numbersim=2000, missing_data_threshold=30, method='SpotPY', mode="calibration", error="RMSE", kge_button=True, rmse_button=True,
                 ns_button=True, db_file="SCEUA_hymod.db",
                 optimizer="PSO", solver="cranknicolson", compiler="fortran", CFL=0.9, databaseformat="custom",
                 computeparametersranges="Yes", computeparameters="No", interpolate_use_rmse=True,
                 parameter_ranges=str(owd + os.sep + str('config') + os.sep + 'parameters_depth=14m.yaml'),
                 forward_parameters=str(owd + os.sep + str('config') + os.sep + 'parameters_forward.yaml'),
                 air2waterusercalibrationpath=str(owd + os.sep + "data" + os.sep + "stndrck_sat_cc.txt"),
                 air2streamusercalibrationpath=str(owd + os.sep + "data" + os.sep + "SIO_2011_cc.txt"),
                 air2wateruservalidationpath=str(owd + os.sep + "data" + os.sep + "stndrck_sat_cv.txt"),
                 air2streamuservalidationpath=str(owd + os.sep + "data" + os.sep + "SIO_2011_cv.txt"),
                 log_flag=1, results_file_name="results.db", resampling_frequency_days=1,
                 resampling_frequency_weeks=1, email_send=0, sim_id=0, email_list=['riddick.kakati@unitn.it']):

        self.user_id = user_id
        self.group_id = group_id
        self.model = model
        self.uuid = uuid
        self.spot_setup = spot_setup
        self.warmup_year= warmup_year
        self.interpolate = interpolate
        self.n_data_interpolate = n_data_interpolate
        self.Tmin=Tmin
        self.validation_required = validation_required  # Whether to use seperate files for calibration and validation or let algorithm split the data. Set it to true for algorithm based split.
        self.percent=percent
        self.missing_data_threshold=missing_data_threshold
        self.depth = depth
        self.swarmsize = swarmsize
        self.phi1 = phi1
        self.phi2 = phi2
        self.omega1 = omega1
        self.omega2 = omega2
        self.maxiter = maxiter
        self.numbersim = numbersim
        self.core = core
        self.method = method
        self.mode = mode
        self.error = error
        self.version= version
        self.RMSE_button = rmse_button
        self.KGE_button = kge_button
        self.NS_button = ns_button
        self.db_file = db_file
        self.optimizer = optimizer
        self.solver = solver
        self.compiler = compiler
        self.CFL = CFL
        self.interpolate_use_rmse = interpolate_use_rmse
        self.databaseformat = databaseformat
        self.computeparametersranges = computeparametersranges
        self.computeparameters = computeparameters
        self.parameter_ranges = parameter_ranges
        self.forward_parameters = forward_parameters
        self.air2waterusercalibrationpath = air2waterusercalibrationpath
        self.air2streamusercalibrationpath = air2streamusercalibrationpath
        self.air2wateruservalidationpath = air2wateruservalidationpath
        self.air2streamuservalidationpath = air2streamuservalidationpath
        self.log_flag = log_flag
        self.results_file_name = results_file_name
        self.resampling_frequency_days = resampling_frequency_days
        self.resampling_frequency_weeks = resampling_frequency_weeks
        self.sim_id = sim_id
        self.email_send = email_send
        self.email_list = email_list

    def constant_array_interval(self, length, interval):
        # Create an array of 1s
        array = np.ones(length, dtype=int)

        # Place 2s at the specified interval
        array[interval - 1::interval] = 2

        return array

    def random_validation_array(self, length, percentage):
        # Calculate the number of 2s to place in the array
        num_twos = int(length * (percentage / 100))

        # Create an array of 1s
        array = np.ones(length, dtype=int)

        # Randomly select positions to place 2s
        two_positions = np.random.choice(length, num_twos, replace=False)
        array[two_positions] = 2

        return array

    def calculate_monthly_mean(self, group):
        total_count = len(group)
        missing_count = group.isna().sum()
        missing_percentage = missing_count / total_count

        if missing_percentage < self.missing_data_threshold:
            return group.mean()
        else:
            return np.nan

    def check_values(self, df, column, values):
        df = pd.DataFrame(df)
        unique_values = df[column].unique()

        # Print unique values for debugging purposes
        #print("Unique values in the column:", unique_values)

        # Separate check for np.nan
        has_nan = np.nan in unique_values
        check_nan = np.nan in values

        # Remove np.nan from both sets for comparison
        unique_values = set([x for x in unique_values if not pd.isna(x)])
        values = set([x for x in values if not pd.isna(x)])

        # Check subset without np.nan and add the np.nan condition
        is_subset = unique_values.issubset(values) and (not has_nan or check_nan)

        return is_subset

    def run_simulation(self, best_position, dfinput, model, interpolate_use_rmse, results_file_name,
            resampling_frequency_days, resampling_frequency_weeks, error, KGE_button, NS_button, RMSE_button, optimizer,
            owd, mode
    ):
        self.spot_setup.mode2=mode
        self.spot_setup.df=dfinput
        self.spot_setup.Tw_solution=(dfinput[:,4])
        self.spot_setup.Tw_solution[self.spot_setup.Tw_solution == -999] = np.nan
        self.spot_setup.Tw_solution = self.spot_setup.Tw_solution.tolist()

        self.spot_setup.Ta_data=(dfinput[:,3])
        self.spot_setup.Ta_data[self.spot_setup.Ta_data == -999] = np.nan
        self.spot_setup.Ta_data = self.spot_setup.Ta_data.tolist()

        self.spot_setup.Y=dfinput[:,0].tolist()
        self.spot_setup.M = dfinput[:, 1].tolist()
        self.spot_setup.D = dfinput[:, 2].tolist()

        if self.model == "air2stream":
            self.spot_setup.Q=dfinput[:,5]
            self.spot_setup.Q[self.spot_setup.Q == -999] = np.nan
            self.spot_setup.Q=self.spot_setup.Q.tolist()


        best_simulation = self.spot_setup.simulation(best_position)
        best_evaluation = self.spot_setup.evaluation()
        airtempdata = dfinput[:, 3]
        date, _ = self.datetimecalc(dfinput)

        if model == "air2water":
            if not interpolate_use_rmse:
                airtempdata = airtempdata[dfinput[:, 5] == 0]
                date, _ = self.datetimecalc(dfinput[dfinput[:, 5] == 0])
            if dfinput.shape[1] > 6:
                if mode!="validation":
                    airtempdata = airtempdata[dfinput[:, 6] == 1]
                    date, _ = self.datetimecalc(dfinput[dfinput[:, 6] == 1])
                if mode == "validation":
                    airtempdata = airtempdata[dfinput[:, 6] == 2]
                    date, _ = self.datetimecalc(dfinput[dfinput[:, 6] == 2])
        elif model == "air2stream":
            if not interpolate_use_rmse:
                airtempdata = airtempdata[dfinput[:, 6] == 0]
                self.spot_setup.Q = self.spot_setup.Q[dfinput[:, 6] == 0]
                date, _ = self.datetimecalc(dfinput[dfinput[:, 6] == 0])
            if dfinput.shape[1] > 7:
                if mode != "validation":
                    airtempdata = airtempdata[dfinput[:, 7] == 1]
                    self.spot_setup.Q = self.spot_setup.Q[dfinput[:, 7] == 1]
                    date, _ = self.datetimecalc(dfinput[dfinput[:, 7] == 1])
                if mode == "validation":
                    airtempdata = airtempdata[dfinput[:, 7] == 2]
                    self.spot_setup.Q = self.spot_setup.Q[dfinput[:, 7] == 2]
                    date, _ = self.datetimecalc(dfinput[dfinput[:, 7] == 2])
            Q_mean = np.nanmean(self.spot_setup.Q)

        Tmin = np.maximum(4, np.maximum(0, np.min(best_simulation)))

        if model == "air2water":
            DD = np.zeros_like(best_simulation)
            condition = best_simulation >= Tmin

            if condition.all():
                DD = np.exp(-(best_simulation - Tmin) / best_position[3])
            else:
                if self.version == 8 and best_position[6] != 0 and best_position[7] != 0:
                    DD = np.exp((best_simulation - Tmin) / best_position[6]) + np.exp(
                        -(best_simulation / best_position[7]))
                elif self.version in [4, 6] or best_position[6] == 0 or best_position[7] == 0:
                    DD = np.ones_like(best_simulation)

            if self.solver == "cranknicolson":
                DD[DD < 0] = 0.1
            else:
                DD[DD < 0.01] = 0.01

        elif model == "air2stream":
            if self.version == 8 or self.version == 4:
                DD = (self.spot_setup.Q / Q_mean) * best_position[3]
            elif self.version == 5 or self.version == 3:
                DD = np.zeros_like(best_simulation)
            else:
                DD = np.ones_like(best_simulation)
            DD=DD[366:]

        rmse2 = spotpy.objectivefunctions.rmse(best_evaluation, best_simulation)
        print(f'RMSE with optimized parameters {mode}: {rmse2}')

        df_final_means_original = pd.DataFrame({
            'Date': date[366:],
            'Air_temperature_data': airtempdata[366:],
            'Best_simulation': best_simulation,
            'Evaluation_(Water_temperature_data)': best_evaluation,
            'Delta': DD
        })

        df_final_means = df_final_means_original.copy()
        df_final_means.set_index('Date', inplace=True)

        conn = sqlite3.connect(results_file_name)
        df_final_means_original.to_sql(f"{mode}_data", conn, if_exists='replace', index=False)
        conn.close()
        df_final_means_original.to_csv(f"{self.results_file_name[:-3]}_{mode}.csv", index=False)

        #results_file_location = str(owd + os.sep + results_file_name)
        #shutil.copy(results_file_location, datafolder + os.sep + str(f'{run_count}_results_{mode}.db'))

        if resampling_frequency_days is None:
            resampling_frequency_days = 1
        if resampling_frequency_weeks is None:
            resampling_frequency_weeks = 1

        one_day_average = df_final_means.resample('1D').mean()
        one_day_rmse = self.spot_setup.objectivefunction(one_day_average.iloc[:, 2], one_day_average.iloc[:, 1])
        self.rmse = round(one_day_rmse, 3)
        few_days_average = df_final_means.resample(f'{resampling_frequency_days}D')#.mean()
        few_weeks_average = df_final_means.resample(f'{resampling_frequency_weeks}W')#.mean()
        weekly_average = df_final_means.resample('W')#.mean()
        monthly_average = df_final_means.resample('M')#.mean()

        few_days_average= few_days_average.apply(self.calculate_monthly_mean)
        few_weeks_average= few_weeks_average.apply(self.calculate_monthly_mean)
        weekly_average = weekly_average.apply(self.calculate_monthly_mean)
        monthly_average = monthly_average.apply(self.calculate_monthly_mean)

        monthly_rmse = abs(self.spot_setup.objectivefunction(monthly_average.iloc[:, 2], monthly_average.iloc[:, 1]))
        few_days_rmse = abs(self.spot_setup.objectivefunction(few_days_average.iloc[:, 2], few_days_average.iloc[:, 1]))
        few_weeks_rmse = abs(self.spot_setup.objectivefunction(few_weeks_average.iloc[:, 2], few_weeks_average.iloc[:, 1]))

        monthly_ns = monthly_kge = monthly_rms = ''
        few_days_ns = few_days_kge = few_days_rms = ''
        few_weeks_ns = few_weeks_kge = few_weeks_rms = ''

        if error == "RMSE":
            if KGE_button:
                spot_setup.metric = "KGE"
                monthly_kge = abs(self.spot_setup.objectivefunction(monthly_average.iloc[:, 2], monthly_average.iloc[:, 1]))
                few_days_kge = abs(self.spot_setup.objectivefunction(few_days_average.iloc[:, 2], few_days_average.iloc[:, 1]))
                few_weeks_kge = abs(self.spot_setup.objectivefunction(few_weeks_average.iloc[:, 2], few_weeks_average.iloc[:, 1]))
            if NS_button:
                spot_setup.metric = "NS"
                monthly_ns = abs(self.spot_setup.objectivefunction(monthly_average.iloc[:, 2], monthly_average.iloc[:, 1]))
                few_days_ns = abs(self.spot_setup.objectivefunction(few_days_average.iloc[:, 2], few_days_average.iloc[:, 1]))
                few_weeks_ns = abs(self.spot_setup.objectivefunction(few_weeks_average.iloc[:, 2], few_weeks_average.iloc[:, 1]))
        elif error == "NS":
            if RMSE_button:
                spot_setup.metric = "RMSE"
                monthly_rms = abs(self.spot_setup.objectivefunction(monthly_average.iloc[:, 2], monthly_average.iloc[:, 1]))
                few_days_rms = abs(self.spot_setup.objectivefunction(few_days_average.iloc[:, 2], few_days_average.iloc[:, 1]))
                few_weeks_rms = abs(self.spot_setup.objectivefunction(few_weeks_average.iloc[:, 2], few_weeks_average.iloc[:, 1]))
            if KGE_button:
                spot_setup.metric = "KGE"
                monthly_kge = abs(self.spot_setup.objectivefunction(monthly_average.iloc[:, 2], monthly_average.iloc[:, 1]))
                few_days_kge = abs(self.spot_setup.objectivefunction(few_days_average.iloc[:, 2], few_days_average.iloc[:, 1]))
                few_weeks_kge = abs(self.spot_setup.objectivefunction(few_weeks_average.iloc[:, 2], few_weeks_average.iloc[:, 1]))
        elif error == "KGE":
            if NS_button:
                spot_setup.metric = "NS"
                monthly_ns = abs(self.spot_setup.objectivefunction(monthly_average.iloc[:, 2], monthly_average.iloc[:, 1]))
                few_days_ns = abs(self.spot_setup.objectivefunction(few_days_average.iloc[:, 2], few_days_average.iloc[:, 1]))
                few_weeks_ns = abs(self.spot_setup.objectivefunction(few_weeks_average.iloc[:, 2], few_weeks_average.iloc[:, 1]))
            if RMSE_button:
                spot_setup.metric = "RMSE"
                monthly_rms = abs(self.spot_setup.objectivefunction(monthly_average.iloc[:, 2], monthly_average.iloc[:, 1]))
                few_days_rms = abs(self.spot_setup.objectivefunction(few_days_average.iloc[:, 2], few_days_average.iloc[:, 1]))
                few_weeks_rms = abs(self.spot_setup.objectivefunction(few_weeks_average.iloc[:, 2], few_weeks_average.iloc[:, 1]))

        fig = plt.figure(figsize=(9, 6))
        ax = plt.subplot(1, 1, 1)
        default_label = f"{error} (D,W,M)=" + str(f"{round(few_days_rmse, 2)},") + str(
            f" {round(few_weeks_rmse, 2)},") + str(f" {round(monthly_rmse, 2)}")
        if monthly_ns:
            default_label = default_label + f"\n NSE (D,W,M)= {round(few_days_ns, 2)}, {round(few_weeks_ns, 2)}, {round(monthly_ns, 2)}"
        if monthly_kge:
            default_label = default_label + f"\n KGE (D,W,M)= {round(few_days_kge, 2)}, {round(few_weeks_kge, 2)}, {round(monthly_kge, 2)}"
        if monthly_rms:
            default_label = default_label + f"\n RMSE (D,W,M)= {round(few_days_rms, 2)}, {round(few_weeks_rms, 2)}, {round(monthly_rms, 2)}"

        ax.plot(
            df_final_means['Best_simulation'],
            color="black",
            linestyle="solid",
            label=default_label,
        )
        ax.plot(df_final_means['Evaluation_(Water_temperature_data)'], "r.", markersize=3,
                label="Observed water temperature data")
        ax.plot(df_final_means['Air_temperature_data'], color="blue", linewidth=0.2,
                label="Observed air temperature data")
        plt.xlabel("Year")
        plt.ylabel("Temperature")
        plt.legend(loc="upper right")
        fig.savefig(f"{owd}/results/{self.user_id}_{self.group_id}/{mode}_best_modelrun_{self.sim_id}.png", dpi=100)

        results_time_series = BytesIO()
        fig.savefig(results_time_series, format="png", dpi=100)
        results_time_series.seek(0)
        plt.close()

        return results_time_series, one_day_rmse, rmse2

    def run(self):
        owd = settings.MEDIA_ROOT
        if self.mode != "forward":
            air2_water_params = Air2WaterParameters(self.depth, self.method, self.model)
            if self.computeparametersranges == "No":
                _, theoritical_parameters = air2_water_params.calculate_parameters()

            else:

                if self.model == "air2water":

                    parameters, theoretical_parameters = air2_water_params.calculate_parameters()
                    air2_water_params.save_parameters(self.depth, parameters, theoretical_parameters, self.user_id, self.group_id)
                    for root, dirs, files in os.walk(f"{owd}/parameters/{self.user_id}_{self.group_id}/"):
                        for file in files:
                            if fnmatch.fnmatch(file, 'parameters_depth=*m.yaml'):
                                self.parameter_ranges = os.path.join(root, file)

                else:
                    _, theoretical_parameters = air2_water_params.calculate_parameters()
                    for root, dirs, files in os.walk(f"{owd}/parameters/{self.user_id}_{self.group_id}/"):
                        for file in files:
                            if fnmatch.fnmatch(file, 'parameters_air2stream.yaml'):
                                self.parameter_ranges = os.path.join(root, file)
            # else:
            #     do find the optimum parameters file, and ask user if run simulation again

        # if self.mode == "forward":
        #     for file in os.listdir('.' + os.sep + str('config')):
        #         if fnmatch.fnmatch(file, 'parameters_forward.yaml'):
        #             self.parameter_ranges = file
        # else:
        #     if self.model=="air2water":
        #         for file in os.listdir('.' + os.sep + str('config')):
        #             if fnmatch.fnmatch(file, 'parameters_depth=*m.yaml'):
        #                 self.parameter_ranges = file
        #
        #     elif self.model=="air2stream":
        #         for file in os.listdir('.' + os.sep + str('config')):
        #             if fnmatch.fnmatch(file, 'parameters*air2stream.yaml'):
        #                 self.parameter_ranges = file

        if self.mode == "forward":
            all_parameters1 = read_yaml(self.forward_parameters)
        else:
            all_parameters1 = read_yaml(self.parameter_ranges)

        if self.mode != "forward":
            all_parameters = all_parameters1['Optimizer']['parameters']

            all_parameters_names = list(all_parameters.keys())

            a1 = globals()[all_parameters.get(all_parameters_names[0], {}).get('distribution')](
                name=all_parameters_names[0],
                low=all_parameters.get('a1',
                                       {}).get(
                    'low'),
                high=all_parameters.get('a1',
                                        {}).get(
                    'high'))
            if self.model == "air2water":
                if self.log_flag:
                    a2 = globals()[all_parameters.get(all_parameters_names[1], {}).get('distribution')](
                        name=all_parameters_names[1],
                        low=math.log10(
                            all_parameters.get(
                                all_parameters_names[1],
                                {}).get('low')),
                        high=math.log10(
                            all_parameters.get(
                                all_parameters_names[1],
                                {}).get(
                                'high')))  # Search in logarithmic space
                    a3 = globals()[all_parameters.get(all_parameters_names[2], {}).get('distribution')](
                        name=all_parameters_names[2],
                        low=math.log10(
                            all_parameters.get(
                                all_parameters_names[2],
                                {}).get('low')),
                        high=math.log10(
                            all_parameters.get(
                                all_parameters_names[2],
                                {}).get(
                                'high')))  # Search in logarithmic space
                else:
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
            else:
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
            a4 = globals()[all_parameters.get(all_parameters_names[3], {}).get('distribution')](
                name=all_parameters_names[3],
                low=all_parameters.get(
                    all_parameters_names[3],
                    {}).get('low'),
                high=all_parameters.get(
                    all_parameters_names[3],
                    {}).get('high'))
            a5 = globals()[all_parameters.get(all_parameters_names[4], {}).get('distribution')](
                name=all_parameters_names[4],
                low=all_parameters.get(
                    all_parameters_names[4],
                    {}).get('low'),
                high=all_parameters.get(
                    all_parameters_names[4],
                    {}).get('high'))
            a6 = globals()[all_parameters.get(all_parameters_names[5], {}).get('distribution')](
                name=all_parameters_names[5],
                low=all_parameters.get(
                    all_parameters_names[5],
                    {}).get('low'),
                high=all_parameters.get(
                    all_parameters_names[5],
                    {}).get('high'))
            a7 = globals()[all_parameters.get(all_parameters_names[6], {}).get('distribution')](
                name=all_parameters_names[6],
                low=all_parameters.get(
                    all_parameters_names[6],
                    {}).get('low'),
                high=all_parameters.get(
                    all_parameters_names[6],
                    {}).get('high'))
            a8 = globals()[all_parameters.get(all_parameters_names[7], {}).get('distribution')](
                name=all_parameters_names[7],
                low=all_parameters.get(
                    all_parameters_names[7],
                    {}).get('low'),
                high=all_parameters.get(
                    all_parameters_names[7],
                    {}).get('high'))

        else:
            all_parameters = all_parameters1['Optimized']['parameters']
            a1 = all_parameters.get('a1')
            a2 = all_parameters.get('a2')
            a3 = all_parameters.get('a3')
            a4 = all_parameters.get('a4')
            a5 = all_parameters.get('a5')
            a6 = all_parameters.get('a6')
            a7 = all_parameters.get('a7')
            a8 = all_parameters.get('a8')

        parameters = [a1, a2, a3, a4, a5, a6, a7, a8]
        calibration = None
        validation = None

        if self.model == "air2water":
            usercalibrationdatapath = self.air2waterusercalibrationpath
        elif self.model == "air2stream":
            usercalibrationdatapath = self.air2streamusercalibrationpath

        df1 = np.loadtxt(usercalibrationdatapath)
        if self.validation_required and self.validation_required=="Random Percentage":
            array = self.random_validation_array(df1.shape[0],self.percent)
            df1=np.hstack((df1,array.reshape(-1, 1)))
        elif self.validation_required and self.validation_required=="Uniform Number":
            array = self.constant_array_interval(df1.shape[0],self.percent)
            df1 = np.hstack((df1, array.reshape(-1, 1)))
        if self.mode=="forward":
            df1=pd.DataFrame(df1)
            if df1.shape[1] < 5:
                df1.columns = ['year', 'month', 'day', 3]
            else:
                df1.columns = ['year', 'month', 'day', 3, 4] + df1.columns[5:].tolist()

            # Check if column '4' exists and meets any of the specified conditions
            column_exists = 4 in df1.columns
            if (not column_exists or
                    self.check_values(df1, 4, [0, 1, 2]) or
                    self.check_values(df1, 4, [0, 1]) or
                    self.check_values(df1, 4, [0]) or
                    self.check_values(df1, 4, [1]) or
                    self.check_values(df1, 4, [2]) or
                    self.check_values(df1, 4, [0, 2]) or
                    self.check_values(df1, 4, [1, 2])):
                # Shift columns to the right starting from column 4
                df1.insert(4, 4, np.nan)
                df1.iloc[0, 4] = self.Tmin
            df1=df1.to_numpy()

        processor = YearlyDataProcessor(df1, self.n_data_interpolate)
        dfint1, num_missing_col3, missing_col3 = processor.mean_year()
        np.savetxt(f"{owd}/timeseries/{self.user_id}_{self.group_id}/calibration_interpolated.csv", dfint1,
                   delimiter=",", fmt='%s')
        if self.model == "air2water":
            uservalidationdatapath = self.air2wateruservalidationpath
        elif self.model == "air2stream":
            uservalidationdatapath = self.air2streamuservalidationpath
        if self.validation_required == False:
            if self.model == "air2water" and dfint1.shape[1] > 6:
                pass
            elif self.model == "air2stream" and dfint1.shape[1] > 7:
                pass
            else:
                try:
                    df2 = np.loadtxt(uservalidationdatapath)

                    if self.mode == "forward":
                        df2 = pd.DataFrame(df2)
                        if df2.shape[1] < 5:
                            df2.columns = ['year', 'month', 'day', 3]
                        else:
                            df2.columns = ['year', 'month', 'day', 3, 4] + df2.columns[5:].tolist()

                        # Check if column '4' exists and meets any of the specified conditions
                        column_exists = 4 in df2.columns
                        if (not column_exists or
                                self.check_values(df2, 4, [0, 1, 2]) or
                                self.check_values(df2, 4, [0, 1]) or
                                self.check_values(df2, 4, [0]) or
                                self.check_values(df2, 4, [1]) or
                                self.check_values(df2, 4, [2]) or
                                self.check_values(df2, 4, [0, 2]) or
                                self.check_values(df2, 4, [1, 2])):
                            # Shift columns to the right starting from column 4
                            df2.insert(4, 4, np.nan)
                            df2.iloc[0, 4] = self.Tmin
                        df2 = df2.to_numpy()

                except:
                    print(
                        "Validation file or flags not found for \"Validation Required\"= False. Either put \"Validation Required\"=True, or add flag, or add validation file.")
                    num_missing_col3 = None
                    return num_missing_col3

        print(f"There are {num_missing_col3} missing data.")
        if self.interpolate == True and num_missing_col3:
            print(f"Interpolating...")
            if self.validation_required == False:
                if self.model == "air2water" and dfint1.shape[1] > 6:
                    calibration = dfint1
                    validation = dfint1
                elif self.model == "air2stream" and dfint1.shape[1] > 7:
                    calibration = dfint1
                    validation = dfint1
                else:
                    processor2 = YearlyDataProcessor(df2)
                    dfint2, num_missing_col3_2, missing_col3_2 = processor2.mean_year()
                    np.savetxt(f"{owd}/timeseries/{self.user_id}_{self.group_id}/validation_interpolated.csv",
                               dfint2, delimiter=",", fmt='%s')
                    calibration = dfint1
                    validation = dfint2
            elif self.validation_required:
                if self.validation_required=="Uniform Percentage":
                    calibration, validation = train_test_split(dfint1, test_size=self.percent/100, shuffle=False)
                else:
                    calibration = dfint1[dfint1[:,-2]==1]
                    validation = dfint1[dfint1[:,-2]==2]
        elif self.interpolate == False:
            if num_missing_col3 != 0:
                print(f"There are {num_missing_col3} data, and interpolation is false. It might affect results.")
                data = df1
                data = pd.DataFrame(data)
                data['interpolated'] = 0
                data = data.to_numpy()
                if self.validation_required == False:
                    if self.model == "air2water" and data.shape[1] > 6:
                        calibration = data
                        validation = data
                    elif self.model == "air2stream" and data.shape[1] > 7:
                        calibration = data
                        validation = data
                    else:
                        calibration = data
                        validation = df2
                        validation = pd.DataFrame(validation)
                        validation['interpolated'] = 0
                        validation = validation.to_numpy()
                elif self.validation_required:
                    if self.validation_required=="Uniform Percentage":
                        calibration, validation = train_test_split(data, test_size=self.percent/100, shuffle=False)
                    else:
                        calibration = data[data[:,-2]==1]
                        validation = df2[df2[:,-2]==2]

            elif num_missing_col3 == 0:
                data = df1
                data = pd.DataFrame(data)
                data['interpolated'] = 0
                data = data.to_numpy()
                if self.validation_required:
                    if self.validation_required == "Uniform Percentage":
                        calibration, validation = train_test_split(data, test_size=self.percent/100, shuffle=False)
                    else:
                        calibration = data[data[:, -2] == 1]
                        validation = df2[df2[:, -2] == 2]
                elif self.validation_required == False:
                    if self.model == "air2water" and data.shape[1] > 6:
                        calibration = data
                        validation = data
                    elif self.model == "air2stream" and data.shape[1] > 7:
                        calibration = data
                        validation = data
                    else:
                        calibration= data
                        validation = df2
                        validation = pd.DataFrame(validation)
                        validation['interpolated'] = 0
                        validation = validation.to_numpy()

        elif self.interpolate == True and num_missing_col3==0:
            if self.validation_required == False:
                if self.model == "air2water" and dfint1.shape[1] > 6:
                    calibration = dfint1
                    validation = dfint1
                elif self.model == "air2stream" and dfint1.shape[1] > 7:
                    calibration = dfint1
                    validation = dfint1
                else:
                    processor2 = YearlyDataProcessor(df2)
                    dfint2, num_missing_col3_2, missing_col3_2 = processor2.mean_year()
                    np.savetxt(f"{owd}/timeseries/{self.user_id}_{self.group_id}/validation_interpolated.csv",
                               dfint2, delimiter=",", fmt='%s')
                    calibration = dfint1
                    validation = dfint2
            elif self.validation_required:
                if self.validation_required == "Uniform Percentage":
                    calibration, validation = train_test_split(dfint1, test_size=self.percent / 100, shuffle=False)

                else:
                    calibration = dfint1[dfint1[:,-2]==1]
                    validation = dfint1[dfint1[:,-2]==2]


        _, tt = self.datetimecalc(calibration)

        # To replicate the first year of data so that we dont loose data
        if self.warmup_year:
            initial_rows = calibration[:366].copy()
            initial_rows2 = validation[:366].copy()
            calibration = np.concatenate([initial_rows, calibration])
            validation = np.concatenate([initial_rows2, validation])
        if self.model == "air2water":
            if calibration.shape[1] > 6:
                calibration[:, [5, 6]] = calibration[:, [6, 5]]
            if validation.shape[1] > 6:
                validation[:, [5, 6]] = validation[:, [6, 5]]

        if self.model == "air2stream":
            if calibration.shape[1] > 7:
                calibration[:, [6, 7]] = calibration[:, [7, 6]]
            if validation.shape[1] > 7:
                validation[:, [6, 7]] = validation[:, [7, 6]]

        start_time = time.time()
        if self.model == "air2water":
            self.spot_setup.evaluation = evaluation_air2water
            if self.mode == "forward":
                self.spot_setup.simulation = simulation_air2water_no_log
            else:
                if self.log_flag:
                    if self.method == "PYSWARMS_PSO" or self.optimizer == "PSO_A2WS.py":
                        self.spot_setup.simulation = simulation_air2water_log_pyswarms
                    else:
                        self.spot_setup.simulation = simulation_air2water_log
                else:
                    if self.method == "PYSWARMS_PSO" or self.optimizer == "PSO_A2WS.py":
                        self.spot_setup.simulation = simulation_air2water_no_log_pyswarms
                    else:
                        self.spot_setup.simulation = simulation_air2water_no_log

        elif self.model == "air2stream":
            self.spot_setup.evaluation = evaluation_air2stream
            if self.method == "PYSWARMS_PSO":
                self.spot_setup.simulation = simulation_air2stream_pyswarms
            else:
                self.spot_setup.simulation = simulation_air2stream

        if self.mode != "forward":
            self.spot_setup = self.spot_setup(parameters,
                                              model=self.model, metric=self.error, df=calibration, tt=tt,
                                              db_file=self.db_file, optimizer=self.optimizer,
                                              threshold=None, solver=self.solver, CFL=self.CFL, mode2=self.mode,
                                              interpolate=self.interpolate, missing_data=num_missing_col3,
                                              interpolate_use_rmse=self.interpolate_use_rmse, version=self.version)

            if self.method == "PYCUP":
                s = SpotpySetupConverter()
                s.convert(self.spot_setup)

                if self.optimizer == "GLUE":
                    cp.GLUE.run(self.swarmsize, s.dim, lb=s.lb, ub=s.ub, fun=self.objective_function_pycup, args=())

                elif self.optimizer == "SSA":
                    cp.SSA.run(pop=self.swarmsize, dim=s.dim, lb=s.lb, ub=s.ub, MaxIter=self.maxiter,
                               fun=self.objective_function_pycup)

                elif self.optimizer == "GWO":
                    cp.GWO.run(pop=self.swarmsize, dim=s.dim, lb=s.lb, ub=s.ub, MaxIter=self.maxiter,
                               fun=self.objective_function_pycup)

                elif self.optimizer == "MFO":
                    cp.MFO.run(pop=self.swarmsize, dim=s.dim, lb=s.lb, ub=s.ub, MaxIter=self.maxiter,
                               fun=self.objective_function_pycup)

                elif self.optimizer == "PSO":
                    cp.PSO.runMP(self.swarmsize, s.dim, s.lb, s.ub, self.maxiter, self.objective_function_pycup,
                                 args=(), n_jobs=self.core)

                elif self.optimizer == "SCA":
                    cp.SCA.runMP(pop=self.swarmsize, dim=s.dim, lb=s.lb, ub=s.ub, MaxIter=self.maxiter,
                                 fun=self.objective_function_pycup, n_jobs=self.core)

                elif self.optimizer == "SOA":
                    cp.SOA.run(pop=self.swarmsize, dim=s.dim, lb=s.lb, ub=s.ub, MaxIter=self.maxiter,
                               fun=self.objective_function_pycup, fc=2)

                elif self.optimizer == "TSA":
                    cp.TSA.run(pop=self.swarmsize, dim=s.dim, lb=s.lb, ub=s.ub, MaxIter=self.maxiter,
                               fun=self.objective_function_pycup)

                elif self.optimizer == "WOA":
                    cp.WOA.run(pop=self.swarmsize, dim=s.dim, lb=s.lb, ub=s.ub, MaxIter=self.maxiter,
                               fun=self.objective_function_pycup)

                elif self.optimizer == "NSGAII":
                    cp.NSGA2.run(pop=self.swarmsize, dim=s.dim, lb=s.lb, ub=s.ub, MaxIter=self.maxiter,
                                 fun=self.objective_function_pycup)

                saver = cp.save.RawDataSaver.load("RawResult.rst")
                t = SpotpyDbConverter()
                t.RawSaver2csv(f"{owd}/parameters/{self.user_id}_{self.group_id}/RawResult.rst",f"{owd}/parameters/{self.user_id}_{self.group_id}/{self.spot_setup.db_file[:-3]}.csv")
                results = spotpy.analyser.load_csv_results(f"{owd}/results/{self.user_id}_{self.group_id}/{self.spot_setup.db_file[:-3]}.csv")
                df3 = pd.DataFrame(results)
                df3 = df3.iloc[:, :9]
                common_data = results
                best_results = str(spotpy.analyser.get_best_parameterset(results, maximize=False)[0])[1:-1]
                data_list = [float(x) for x in best_results.split(', ')]
                best_position = np.array(data_list)
                conn = sqlite3.connect(self.spot_setup.db_file)
                df3.to_sql(f"{self.spot_setup.db_file[:-3]}", conn, if_exists='replace', index=False)
                conn.close()
                df3.to_csv(f"{self.spot_setup.db_file[:-3]}.csv", index=False)
                print(f"Best Results {self.optimizer}:",
                      best_results)

                bestindex, bestobjf = spotpy.analyser.get_minlikeindex(common_data)
                best_model_run = common_data[bestindex]

            if self.method == "PYSWARMS_PSO":
                s = SpotpySetupConverter()
                s.convert(self.spot_setup)

                if self.optimizer == "PSO_GLOBAL":
                    options = {'c1': self.phi1, 'c2': self.phi2, 'w': self.omega}
                    bounds = (s.lb.T, s.ub.T)
                    sampler = ps.single.GlobalBestPSO(n_particles=self.swarmsize, dimensions=8, options=options,
                                                      bounds=bounds)
                    cost, best_position = sampler.optimize(self.objective_function_pyswarm,
                                                           iters=self.maxiter)  # The objective function used in pyswarms corresponds to the spot_setup.simulation function. But it returns error. Why?

                best_cost = pd.DataFrame(sampler.cost_history)
                best_pos = pd.DataFrame(sampler.swarm.pbest_pos)
                df3 = pd.concat([best_cost, best_pos], axis=1)
                headers = ['like1'] + [f'para{i}' for i in np.arange(1, 1 + len(best_pos.columns))]
                df3.columns = headers
                df3.to_csv(f"{self.spot_setup.db_file[:-3]}.csv", index=False)
                results = spotpy.analyser.load_csv_results(f"{self.spot_setup.db_file[:-3]}")
                common_data = results
                best_results = str(spotpy.analyser.get_best_parameterset(results, maximize=False)[0])[1:-1]
                data_list = [float(x) for x in best_results.split(', ')]
                best_position = np.array(data_list)
                conn = sqlite3.connect(self.spot_setup.db_file)
                df3.to_sql(f"{self.spot_setup.db_file[:-3]}", conn, if_exists='replace', index=False)
                conn.close()
                df3.to_csv(f"{self.spot_setup.db_file[:-3]}.csv", index=False)
                print(f"Best Results {self.optimizer}:",
                      best_results)

                bestindex, bestobjf = spotpy.analyser.get_minlikeindex(common_data)
                best_model_run = common_data[bestindex]

            elif self.method == "SpotPY":
                if self.optimizer == "PSO":

                    s = SpotpySetupConverter()
                    s.convert(self.spot_setup)

                    pso_oop.db_format = self.databaseformat
                    sampler = pso_oop(self.objective_function_pyswarm, self.spot_setup.db_file, pso_oop.db_format,
                                      s.lb, s.ub,
                                      swarm_size=self.swarmsize, phip=self.phi1,
                                      phig=self.phi2, w_max=self.omega1, w_min=self.omega2, maxiter=self.maxiter,
                                      threshold=self.spot_setup.threshold)  # ,model=self.model)
                    if sampler.dbformat == "custom":
                        best_position, _ = sampler.run()
                    elif sampler.dbformat == "ram":
                        best_position, _, df3, spotpyreader = sampler.run()
                elif self.optimizer == "PSO_A2WS":
                    s = SpotpySetupConverter()
                    s.convert(self.spot_setup)

                    pso_oop_new.dbformat = self.databaseformat
                    sampler = pso_oop_new(self.objective_function_pyswarm, self.spot_setup.db_file,
                                          pso_oop_new.dbformat,
                                          s.lb, s.ub,
                                          swarmsize=self.swarmsize, phip=self.phi1,
                                          phig=self.phi2, omega=self.omega, maxiter=self.maxiter, minfunc=1e-8,
                                          processes=self.core,
                                          threshold=self.spot_setup.threshold, model=self.model)
                    if sampler.dbformat == "custom":
                        '''
                        while True:
                            best_position1, _ = sampler.pso()
                            best_position2, _ = sampler.pso()

                            if round(best_position1) != round(best_position2, 2):
                                break

                        best_position=best_position1
                        '''
                        best_position, _ = sampler.pso()

                    elif sampler.dbformat == "ram":
                        '''
                        while True:
                            best_position1, _, df3, spotpyreader = sampler.pso()
                            best_position2, _, df3, spotpyreader = sampler.pso()

                            if round(best_position1) != round(best_position2, 2):
                                break

                        best_position = best_position1
                        '''
                        best_position, _, df3, spotpyreader = sampler.pso()

                    s = SpotpySetupConverter()
                    s.convert(self.spot_setup)

                    if sampler.dbformat == "custom":
                        best_position, _ = sampler.pso()
                    elif sampler.dbformat == "ram":
                        best_position, _, df3, spotpyreader = sampler.pso()
                else:
                    dict = {}
                    dict['spotpy_algo'] = str(self.optimizer.lower())
                    rep = self.numbersim
                    variable = globals()[dict.get('spotpy_algo')]
                    sampler = globals()[dict.get('spotpy_algo')](self.spot_setup, dbformat=self.databaseformat,
                                                                 save_sim=False)  # dbformat="custom"#, save_sim=False)
                    if self.optimizer == "ABC":
                        sampler.optimization_direction = "minimize"
                        sampler.sample(rep, eb=2000, a=0.2, peps=0.00001)
                    elif self.optimizer == "DDS":
                        sampler.optimization_direction = "minimize"
                        sampler.sample(rep, trials=3)
                    elif self.optimizer == "DEMCZ":
                        sampler.optimization_direction = "minimize"
                        sampler.sample(rep, nChains=5, DEpairs=3, eps=0.01)
                    elif self.optimizer == "DREAM":
                        sampler.optimization_direction = "minimize"
                        sampler.sample(rep, nChains=5, nCr=4, delta=0.1, c=0.5, eps=1e-8, convergence_limit=0.001,
                                       runs_after_convergence=2, acceptance_test_option=6)
                    elif self.optimizer == "FAST":
                        sampler.optimization_direction = "minimize"
                        sampler.sample(rep)
                    elif self.optimizer == "FSCABC":
                        sampler.optimization_direction = "minimize"
                        sampler.sample(rep, eb=2000, a=0.2, peps=0.00001, kpow=4)
                    elif self.optimizer == "LHS":
                        sampler.optimization_direction = "minimize"
                        sampler.sample(rep)
                    elif self.optimizer == "LIST_SAMPLER":
                        sampler.optimization_direction = "minimize"
                        sampler.sample(rep)
                    elif self.optimizer == "MC":
                        sampler.optimization_direction = "minimize"
                        sampler.sample(rep)
                    elif self.optimizer == "MCMC":
                        sampler.optimization_direction = "minimize"
                        sampler.sample(rep)
                    elif self.optimizer == "MLE":
                        sampler.optimization_direction = "minimize"
                        sampler.sample(rep)
                    # elif self.optimizer == "NSGAII":
                    #     sampler.optimization_direction = "minimize"
                    #     sampler.sample(generations=100, n_obj=1, n_pop=100)
                    elif self.optimizer == "PADDS":
                        sampler.optimization_direction = "minimize"
                        sampler.sample(rep)
                    elif self.optimizer == "ROPE":
                        sampler.optimization_direction = "minimize"
                        sampler.sample(rep, repetitions_first_run=20, subsets=5, percentage_first_run=0.5,
                                       percentage_following_runs=0.5, NDIR=2000)
                    elif self.optimizer == "SA":
                        sampler.optimization_direction = "minimize"
                        sampler.sample(rep)
                    elif self.optimizer == "SCEUA":
                        sampler.optimization_direction = "minimize"
                        sampler.sample(rep, ngs=7, kstop=3, peps=0.1, pcento=0.1)

                # result_df_raw=pd.DataFrame(result_list)
                # df_expanded = pd.DataFrame(result_df_raw.iloc[:,1].tolist())
                # result_df = pd.concat([result_df_raw.iloc[:,0], df_expanded], axis=1)
                # headers= ['like1'] + [f'para{i}' for i in np.arange(1,len(result_df.columns))]
                # result_df.columns = headers
                #
                # # filename2= cwd + os.sep + str('PSO_TEST.csv')
                # # result_df.to_csv(filename2, index=False)

                if sampler.dbformat == "custom":
                    # Start the sampler, one can specify ngs, kstop, peps and pcento id desired

                    # For custom database.csv
                    # self.spot_setup.database.close()

                    # Connect to the SQLite database
                    conn = sqlite3.connect(self.spot_setup.db_file)

                    # Use pandas to read the query result directly into a DataFrame
                    df = pd.read_sql_query("SELECT * FROM RESULTS", conn)
                    df3 = df
                    # Close the database connection
                    conn.close()

                    # Now you can use the results with Spotpy
                    # Use for sql
                    # Filter rows based on the threshold condition
                    # if threshold != None:
                    #     filtered_df = df[df["like1"] < threshold]
                    #     filtered_df.to_csv("filtered_SCEUA_hymod.csv", index=False)
                    #     results = spotpy.analyser.load_csv_results(
                    #         "filtered_SCEUA_hymod")  # SCEUA_hymod_filtered for filtered database. Run filter_db.py before that
                    # else:
                    df.to_csv(f"{self.spot_setup.db_file[:-3]}.csv", index=False)

                    # Write the filtered DataFrame to a new CSV file
                    results = spotpy.analyser.load_csv_results(
                        self.spot_setup.db_file[
                        :-3])  # SCEUA_hymod_filtered for filtered database. Run filter_db.py before that

                    if self.optimizer != "PSO":
                        best_results = str(spotpy.analyser.get_best_parameterset(results, maximize=False)[0])[1:-1]
                        data_list = [float(x) for x in best_results.split(', ')]
                        best_position = np.array(data_list)
                        print(f"Best Results {self.optimizer}:", best_position)

                    # Load the results gained with the sceua sampler, stored in SCEUA_hymod.csv

                    print(f"Best Results {self.optimizer}:",
                          spotpy.analyser.get_best_parameterset(results, maximize=False))
                    bestindex, bestobjf = spotpy.analyser.get_minlikeindex(results)
                    best_model_run = results[bestindex]


                elif sampler.dbformat == "ram":
                    if self.optimizer == "PSO":
                        results = df3
                        common_data = spotpyreader
                    else:
                        results = sampler.datawriter.data
                        df3 = pd.DataFrame(results)
                        common_data = results
                        best_results = str(spotpy.analyser.get_best_parameterset(results, maximize=False)[0])[1:-1]
                        data_list = [float(x) for x in best_results.split(', ')]
                        best_position = np.array(data_list)
                        print(f"Best Results {self.optimizer}:", best_position)

                    conn = sqlite3.connect(self.spot_setup.db_file)
                    df3.to_sql(f"{self.spot_setup.db_file[:-3]}", conn, if_exists='replace', index=False)
                    conn.close()
                    df3.to_csv(f"{self.spot_setup.db_file[:-3]}.csv", index=False)
                    print(f"Best Results {self.optimizer}:",
                          spotpy.analyser.get_best_parameterset(common_data, maximize=False))

                    bestindex, bestobjf = spotpy.analyser.get_minlikeindex(common_data)
                    best_model_run = common_data[bestindex]

            print("Total Time Taken:", time.time() - start_time)

            # Plot how the objective function was minimized during sampling
            fig = plt.figure(1, figsize=(9, 6))
            plt.plot(results["like1"])
            # plt.show()
            plt.ylabel("RMSE")
            plt.xlabel("Iteration")
            fig.savefig(f"{owd}/results/{self.user_id}_{self.group_id}/objectivefunctiontrace_{self.sim_id}.png", dpi=100)
        else:
            best_position = parameters
            # Plot the best model run
            # Find the run_id with the minimal objective function value

            # Select best model run

            # Filter results for simulation results
            # fields = [word for word in best_model_run.dtype.names if word.startswith("sim")]

            info_dict = {
                'Optimized': {
                    'model': self.model,
                    'parameters': {
                    }

                }
            }
            best_position_array = np.array(best_position)
            for i in range(len(best_position_array)):
                parameter_name = f'a{i + 1}'
                info_dict["Optimized"]["parameters"][parameter_name] = float(best_position_array[i])

            # Save parameters as YAML file
            with open(f'{owd}/parameters/{self.user_id}_{self.group_id}/best_parameters.yaml', 'w') as file:
                yaml.dump(info_dict, file, default_flow_style=False)

            if self.check_values(calibration,4,[np.nan]):
                calibration[0,4]=4.0
                self.spot_setup = self.spot_setup(parameters,
                                                  model=self.model, metric=self.error, df=calibration, tt=tt,
                                                  db_file=self.db_file, optimizer=self.optimizer,
                                                  threshold=None, CFL=self.CFL, mode2=self.mode,
                                                  interpolate=self.interpolate, missing_data=num_missing_col3,
                                                  interpolate_use_rmse=self.interpolate_use_rmse,
                                                  version=self.version)
                best_simulation_init = self.spot_setup.simulation(best_position)
                calibration[:,4]=best_simulation_init[:366]+best_simulation_init
                for i in range(10):
                    initial = max(0, min(calibration[:,4]))
                    initial = max(4, initial)
                    calibration[0,4]=initial
                    self.spot_setup.df=calibration
                    best_simulation_init = self.spot_setup.simulation(best_position)

            else:
                self.spot_setup = self.spot_setup(parameters,
                                                  model=self.model, metric=self.error, df=calibration, tt=tt,
                                                  db_file=self.db_file, optimizer=self.optimizer,
                                                  threshold=None, CFL=self.CFL, mode2=self.mode,
                                                  interpolate=self.interpolate, missing_data=num_missing_col3,
                                                  interpolate_use_rmse=self.interpolate_use_rmse, version=self.version)



        mode="calibration"

        self.results_time_series_calib, one_day_rmse, rmse2= self.run_simulation(best_position, calibration[366:], self.model, self.interpolate_use_rmse, self.results_file_name,
            self.resampling_frequency_days, self.resampling_frequency_weeks, self.error, self.KGE_button, self.NS_button, self.RMSE_button,
            self.optimizer,
            owd, mode
        )

        self.results_time_series_valid= None

        mode="validation"

        self.results_time_series_valid, one_day_rmse2, rmse3 = self.run_simulation(best_position, validation,
                                                                                  self.model,
                                                                                  self.interpolate_use_rmse,
                                                                                  self.results_file_name,
                                                                                  self.resampling_frequency_days,
                                                                                  self.resampling_frequency_weeks,
                                                                                  self.error, self.KGE_button,
                                                                                  self.NS_button, self.RMSE_button,
                                                                                  self.optimizer,
                                                                                  owd, mode
                                                                                  )

        if self.email_send == 1:
            send_email(self.model, self.email_list, self.results_file_name) #Change this function, requires one more argument


        if self.mode != "forward":
            parameters_low = [self.spot_setup.parameters[i].minbound for i in range(len(parameters))]
            parameters_high = [self.spot_setup.parameters[i].maxbound for i in range(len(parameters))]
            #self.Dottyplots = None
            self.Dottyplots = dottyplots(df3, theoretical_parameters, parameters_low, parameters_high, one_day_rmse,
                                         self.error, self.user_id, self.group_id, self.sim_id)
        else:
            self.Dottyplots = None

        if self.mode != "forward" and rmse2.round(2) >= bestobjf.round(2):
            print("Internal Error: Please re-run simulation!")
            num_missing_col3 = None
            return num_missing_col3

        return num_missing_col3



if __name__ == "__main__":
    import time

    start_time = time.time()

    Run = Air2water_OOP(method="SpotPY", optimizer="PSO", swarmsize=100, maxiter=100, computeparameters=False, validation_required=False,compiler="fortran")
    #Run = Air2water_OOP(model="air2water",mode="forward",validation_required=False)
    num_missing_col3 = Run.run()

    total_time = np.array([time.time() - start_time])[0]
    print("Total run time:",total_time)
