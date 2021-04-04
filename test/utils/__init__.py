import yaml


def read_yaml(path: str):
    with open(path, "r") as stream:
        return yaml.safe_load(stream)


class log:
    _GREEN = '\033[92m'
    _RED = '\033[91m'
    _DARK_GREY = '\033[90m'
    _END = '\033[0m'
    _BOLD = '\033[01m'

    def __init__(self, *args, **kwargs):
        print(*args, **kwargs)

    @staticmethod
    def error(*args, **kwargs):
        message = log.get_message(*args)
        print(log._RED + message + log._END, **kwargs)

    @staticmethod
    def info(*args, **kwargs):
        message = log.get_message(*args)
        print(log._DARK_GREY + message + log._END, **kwargs)

    @staticmethod
    def success(*args, **kwargs):
        message = log.get_message(*args)
        print(log._GREEN + message + log._END, **kwargs)

    @staticmethod
    def get_message(*args):
        return ' '.join(map(str, args))
