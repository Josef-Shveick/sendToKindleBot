import json
import os

from helpers.path import PATH

SECRETS = 'secrets.json'


def read_envs_from_json(json_file):
    with open(os.path.join(PATH.ENV, json_file)) as f:
        return json.load(f)


secrets = read_envs_from_json(SECRETS)

if __name__ == "__main__":
    print(secrets)
