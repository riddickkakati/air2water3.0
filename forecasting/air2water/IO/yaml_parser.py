import yaml
import os



def read_yaml(yaml_file):
    try:
        with open(yaml_file, 'r') as stream:
            return yaml.load(stream, Loader=yaml.FullLoader)
    except FileNotFoundError as err:
        print(err, f"-> {yaml_file} not found in {os.getcwd()} folder!")
        return

