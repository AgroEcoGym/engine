import yaml
import os
from pathlib import Path


def yml_tuple_constructor(v, f=float):
    w = v[1:-1]
    tup = tuple(map(lambda x: f(x), w.split(",")))
    return tup


def read_yaml(path):
    """
    Lit un fichier YAML et renvoie le contenu sous forme de dictionnaire.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"YAML file not found: {path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML file '{path}': {e}")


def write_yaml(path, data):
    """
    Écrit un dictionnaire Python dans un fichier YAML.
    """
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True)

#
#
# file_path = Path(os.path.realpath(__file__))
# CURRENT_DIR = file_path.parent.parent
# def load_yaml(spec_file):
#     # spec_file=(class_.__class__.__name__).lower()/entity_instance_name.yaml'
#     string = CURRENT_DIR / 'specifications'/spec_file
#     string = CURRENT_DIR / spec_file
#     with open(string, "r", encoding="utf8") as file:
#         doc_yaml = yaml.safe_load(file)  # Note the safe_load
#         return doc_yaml
