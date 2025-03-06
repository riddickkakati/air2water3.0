import uuid
import os
import yaml

cwd=os.getcwd()

def generate_uuids(num_uuids):
    uuid_dict = {}
    for i in range(1, num_uuids+1):
        uuid_dict[i] = str(uuid.uuid4())

    with open(f'{cwd[:-12]}air2water/UUIDs.yaml', 'w') as file:
        yaml.dump(uuid_dict, file, default_flow_style=False)

    return uuid_dict

if __name__ == "__main__":
    num_uuids = 10000
    uuid_dict = generate_uuids(num_uuids)
    print("Generated UUIDs:")
    for key, value in uuid_dict.items():
        print(f"{key}: {value}")
