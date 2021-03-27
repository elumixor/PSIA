import yaml


def read_yaml(path: str, dot_dict=True):
    with open(path, "r") as stream:
        return yaml.safe_load(stream)
