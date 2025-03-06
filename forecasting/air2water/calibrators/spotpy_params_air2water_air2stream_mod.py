
import sqlite3

import numpy as np
import spotpy
import os
import numpy.ma as ma


class spot_setup(object):

    def __init__(self,parameters, db_file, df, tt, model, metric="RMSE", optimizer="ABC",threshold=1000,version=8,solver="cranknicolson",compiler="fortran",CFL=0.9,mode2="calibration"):
        # Load Observation data from file
        self.Tw_solution, self.Ta_data, self.Q, self.Y, self.M, self.D = [], [], [], [], [], []
        # Find Path to Hymod on users system
        self.mode2=mode2
        self.parameters = parameters
        self.owd = "/home/dicam01/DEV/Work/air2water"#os.getcwd()#Activate this for PyCharm
        self.metric = metric
        self.optimizer = optimizer
        self.threshold = threshold
        self.db_file = db_file
        self.tt = tt
        if os.path.exists(self.db_file):
            os.remove(self.db_file)




        #Custom writing database .csv
        #self.db_headers = ['like1'] + [f'para{i}' for i in np.arange(1,9)]
        #self.database = open("MyOwnDatabase.csv", "w")
        #self.database.write(",".join(self.db_headers) + "\n")

        #self.version = 3
        #self.hymod_path = str("/home/riddick/git/air2water/src/air2water")
        '''
        #Non pandas version
        climatefile = open(self.owd + os.sep + "data" + os.sep + "stndrck_sat_cc.txt", "r")
        headerline = climatefile.readline()[:-1]

        # Read model forcing in working storage (this is done only ones)
        if ";" in headerline:
            self.delimiter = ";"
        else:
            self.delimiter = "\t"
        self.header = headerline.split(self.delimiter)
        for line in climatefile:
            values = line.strip().split(self.delimiter)
            self.Y.append(int(values[0]))
            self.M.append(int(values[1]))
            self.D.append(int(values[2]))
            self.Ta_data.append(float(values[3]))
            self.Tw_solution.append(float(values[4]))
        climatefile.close()
    '''
        self.df=df
        self.version=version
        self.solver=solver
        self.compiler=compiler
        self.CFL=CFL
        self.model=model
        self.Y=self.df[:,0].tolist()
        self.M=self.df[:,1].tolist()
        self.D=self.df[:,2].tolist()
        self.Ta_data=self.df[:,3]
        self.Ta_data[self.Ta_data == -999] = np.nan
        self.Ta_data=self.Ta_data.tolist()
        self.Tw_solution=self.df[:,4]
        self.Tw_solution[self.Tw_solution == -999] = np.nan
        self.Tw_solution=self.Tw_solution.tolist()
        if self.model == "air2stream":
            self.Q=self.df[:,5]
            self.Q[self.Q == -999] = np.nan
            self.Q=self.Q.tolist()


    # a1 = logNormal(mean=1.0, sigma=50)
    # a2 = Normal(mean=1.0, stddev=50)
    # a3 = Normal(mean=1.0, stddev=50)
    # a4 = Normal(mean=1.0, stddev=50)
    # a5 = Normal(mean=1.0, stddev=50)
    # a6 = logNormal(mean=1.0, sigma=50)
    # a7 = Normal(mean=1.0, stddev=50)
    # a8 = Normal(mean=1.0, stddev=50)

    def simulation(self, x):
        pass

    def evaluation(self):
        return self.Tw_solution[366:]


    def objectivefunction(self, simulation, evaluation, params=None):
        # SPOTPY expects to get one or multiple values back,
        # that define the performance of the model run
        maximize= ["ABC","DEMCZ","DREAM","FSCABC","MCMC","MLE","ROPE","SA"]
        if self.metric.upper() == 'MAE':
            if self.optimizer.upper() in maximize:
                like = -spotpy.objectivefunctions.mae(evaluation,
                                                      simulation)  # Use negative for PSO, ABC, and remove negative (-) for SCEUA
            else:
                like = spotpy.objectivefunctions.mae(evaluation,
                                                      simulation)  # Use negative for PSO, ABC, and remove negative (-) for SCEUA
        elif self.metric.upper() == 'RMSE':
            if self.optimizer.upper() in maximize:
                like = -spotpy.objectivefunctions.rmse(evaluation,
                                                      simulation)  # Use negative for PSO, ABC, and remove negative (-) for SCEUA
            else:
                like = spotpy.objectivefunctions.rmse(evaluation,
                                                      simulation)  # Use negative for PSO, ABC, and remove negative (-) for SCEUA
        elif self.metric.upper() == 'R2':
            like = spotpy.objectivefunctions.rsquared(evaluation,
                                                  simulation)  # Use negative for PSO, ABC, and remove negative (-) for SCEUA
        elif self.metric.upper() == 'NS':
            like = spotpy.objectivefunctions.nashsutcliffe(evaluation,
                                                      simulation)  # Use negative for PSO, ABC, and remove negative (-) for SCEUA
        elif self.metric.upper() == 'KGE':
            r = ma.corrcoef(ma.masked_invalid(evaluation), ma.masked_invalid(simulation))[0, 1]
            beta = np.nanmean(simulation) / np.nanmean(evaluation)
            gamma = np.nanstd(simulation) / np.nanstd(evaluation)
            like = 1 - np.sqrt((r - 1) ** 2 + (beta - 1) ** 2 + (gamma - 1) ** 2)
            #like = spotpy.objectivefunctions.kge(evaluation,
                                                           #simulation)  # Use negative for PSO, ABC, and remove negative (-) for SCEUA

        return like

    #Custom saving database csv

    def save(self, objectivefunctions, parameter, simulations, *args, **kwargs):
        conn = sqlite3.connect(self.db_file)
        if self.threshold is None:
            self.threshold = 10000
        if objectivefunctions < float(self.threshold):
            cursor = conn.cursor()

            # Dynamically create the table schema
            param_columns = ", ".join([f"par{i + 1} REAL" for i in range(len(parameter))])
            sim_columns = ", ".join([f"sim{i + 1} REAL" for i in range(len(simulations))])
            create_table_query = f'''CREATE TABLE IF NOT EXISTS RESULTS (
                                        like1 REAL,
                                        {param_columns},
                                        {sim_columns}
                                    )'''
            cursor.execute(create_table_query)

            # Convert parameters and simulations to floats
            param_values = [float(p) for p in parameter]
            sim_values = [float(s) for s in simulations]

            # Dynamically create the INSERT statement
            placeholders = ", ".join(["?"] * (1 + len(param_values) + len(sim_values)))
            insert_query = f'''INSERT INTO RESULTS (like1, {", ".join([f"par{i + 1}" for i in range(len(param_values))])}, {", ".join([f"sim{i + 1}" for i in range(len(sim_values))])})
                               VALUES ({placeholders})'''

            # Execute the INSERT statement
            cursor.execute(insert_query, (objectivefunctions, *param_values, *sim_values))

            conn.commit()
            cursor.close()
            conn.close()

    #Save for csv
    # def save(self, objectivefunctions, parameter, *args, **kwargs):
    #     if objectivefunctions<float(self.threshold):
    #         param_str = ",".join((str(p) for p in parameter))
    #         line = ",".join([str(objectivefunctions), param_str]) + "\n"
    #         self.database.write(line)