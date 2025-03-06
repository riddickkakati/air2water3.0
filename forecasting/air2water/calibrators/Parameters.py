import numpy as np
from scipy.io import loadmat
from scipy.interpolate import interp1d
import os
import yaml
from django.conf import settings

class Air2WaterParameters:
    def __init__(self, depth, method, model):
        self.owd = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        self.params_all_depths = str(self.owd + os.sep + "fullparameterset.mat")
        self.data = loadmat(self.params_all_depths)
        self.par = self.data['par']
        self.depth = depth
        self.method = method
        self.model = model

    def calculate_parameters(self):
        meanD = self.depth
        
        if self.depth:
            par_8 = np.zeros((8, 1))
            par_4 = np.zeros((8, 1))

            par_8[0, :] = 0.487944 - 0.096334 * np.log(meanD)
            par_4[0, :] = -0.042417 + 0.01745 * np.log(meanD)
            par_8[1, :] = 0.207095 * meanD ** (-0.67172)
            par_4[1, :] = 0.222683 * meanD ** (-0.635202)
            par_8[2, :] = 0.262359 * meanD ** (-0.658578)
            par_4[2, :] = 0.1753 * meanD ** (-0.540387)
            par_8[3, :] = 31.331137 * meanD ** (-0.329713)
            par_4[3, :] = 35.382662 * meanD ** (-0.360257)
            par_8[4, :] = 0.843294 * meanD ** (-0.731699)
            par_8[5, :] = 0.627705 - 0.030032 * np.log(meanD)
            par_theo = np.array([par_8, par_4]).squeeze()
            depthint = int((abs(meanD) * 10) % 10)
            if not depthint:
                meanD= int(meanD)
                par_range = np.squeeze(self.par[:, meanD, :])
                P = np.vstack((par_range[:, 0], par_range[:, 1]))
            else:
                meanD = int(meanD)
                meanDplus1 = int(meanD + 1)
                par_rangeDlow = np.squeeze(self.par[:, meanD, :])[:, 0]
                par_rangeDplus1low = np.squeeze(self.par[:, meanDplus1, :])[:, 0]
                par_rangeDhigh = np.squeeze(self.par[:, meanD, :])[:, 1]
                par_rangeDplus1high = np.squeeze(self.par[:, meanDplus1, :])[:, 1]
                linfit1 = interp1d([1, 10], np.vstack([par_rangeDlow, par_rangeDplus1low]), axis=0)
                linfit2 = interp1d([1, 10], np.vstack([par_rangeDhigh, par_rangeDplus1high]), axis=0)
                par1 = linfit1(depthint)
                par2 = linfit2(depthint)
                P = np.vstack((par1, par2))
        else:
            par_min= np.min(self.par,axis=1)[:,0]
            par_max= np.max(self.par,axis=1)[:,1]
            P = np.vstack((par_min,par_max))
            par_theo=np.zeros([2,8])

        return P, par_theo

    def save_parameters(self, depth, parameters, theoretical_parameters, user_id, group_id):
        # Save parameters as text file
        wd = settings.MEDIA_ROOT
        with open(f'{wd}/parameters/{user_id}_{group_id}/parameters_depth={depth}m.txt', 'w') as file:
            np.savetxt(file, parameters, fmt='%15.6e')

        # Save theoretical parameters as text file
        with open(f'{wd}/parameters/{user_id}_{group_id}/theoretical_parameters={depth}m.txt', 'w') as file:
            np.savetxt(file, theoretical_parameters, fmt='%15.6e')

        # Convert parameters to dictionary with appropriate structure
        info_dict = {
            'Optimizer': {
                'Method': self.method,
                'model': self.model,
                'parameters': {
                }

            }
        }

        for i in range(parameters.shape[1]):
            parameter_name = f'a{i + 1}'
            info_dict["Optimizer"]["parameters"][parameter_name] = {'low': float(parameters[0, i]), 'high': float(parameters[1, i]), 'distribution':'Uniform'}

        # Save parameters as YAML file
        with open(f'{wd}/parameters/{user_id}_{group_id}/parameters_depth={depth}m.yaml', 'w') as file:
            yaml.dump(info_dict, file, default_flow_style=False)

        # Convert theoretical parameters to dictionary with appropriate structure
        for i in range(theoretical_parameters.shape[1]):
            parameter_name = f'a{i + 1}'
            info_dict["Optimizer"]["parameters"][parameter_name] = {'low': float(theoretical_parameters[0, i]),
                                                          'high': float(theoretical_parameters[1, i])}

        # Save theoretical parameters as YAML file
        with open(f'{wd}/parameters/{user_id}_{group_id}/theoretical_parameters={depth}m.yaml', 'w') as file:
            yaml.dump(info_dict, file, default_flow_style=False)


if __name__ == "__main__":
    depth=14
    method='SpotPY'
    model='Air2water'
    air2_water_params = Air2WaterParameters(depth,method,model)
    parameters, theoretical_parameters = air2_water_params.calculate_parameters()
    air2_water_params.save_parameters(depth, parameters, theoretical_parameters)