########################################
# make_farm.py
########################################

import yaml
import importlib
from pathlib import Path

# Import du nouvel environnement refactorisé
from agroecogym_engine.farm import Farm
#from agroecogym_engine.farm import Farm
from agroecogym_engine.actors.farmers.BasicFarmer import BasicFarmer
from agroecogym_engine.core.structure.field import Field
from agroecogym_engine.actors.actionrules.BasicRule import BasicRule
from agroecogym_engine.scores.BasicScore import BasicScore
import agroecogym_engine.entities as entities_


def make_farm(yamlfile):
    """
    Construct a complete Farm environment from a YAML configuration file.

    Parameters
    ----------
    yamlfile : str | Path
        Path to the YAML configuration file describing fields, farmers, and entities.

    Returns
    -------
    FarmEnv
        Fully configured farm environment instance.
    """

    yamlfile = Path(yamlfile)
    with open(yamlfile, "r", encoding="utf8") as file:
        farm_yaml = yaml.safe_load(file)

    farm_config = farm_yaml["Farm"]

    # ----------------------------------------------------------------------
    # Build FIELDS
    # ----------------------------------------------------------------------
    fields = []
    for fi in farm_config:
        if "Field" in fi:
            entities = farm_config[fi]["entities"]
            ent = []
            for e in entities:
                entity_name = list(e.keys())[0]
                module = importlib.import_module(
                    f"{entities_.__name__}.{entity_name.lower()}.{entity_name.lower()}"
                )
                entity_class = getattr(module, entity_name)
                ent.append((entity_class, str(e[entity_name])))
            fields.append(
                Field(
                    localization=farm_config[fi]["localization"],
                    shape=farm_config[fi]["shape"],
                    entities_specifications=ent,
                )
            )

    # ----------------------------------------------------------------------
    # Build FARMERS
    # ----------------------------------------------------------------------
    farmers = []
    for fi in farm_config:
        if "Farmer" in fi:
            if farm_config[fi]["type"] == "basic":
                params = farm_config[fi]["parameters"]
                farmers.append(
                    BasicFarmer(
                        max_daily_interventions=params["max_daily_interventions"],
                        max_daily_observations=params["max_daily_observations"],
                    )
                )

    # ----------------------------------------------------------------------
    # RULES AND SCORING
    # ----------------------------------------------------------------------
    interaction_mode = farm_yaml["interaction_mode"]
    name_base = str(yamlfile).replace(".yaml", "")
    name_score = name_base + "_" + farm_yaml["score"]
    name_init = name_base + "_" + farm_yaml["initialization"]
    name_actions = name_base + "_" + farm_yaml["actions"]

    scoring = BasicScore(score_configuration=name_score)
    rules = BasicRule(
        init_configuration=name_init, actions_configuration=name_actions
    )

    # ----------------------------------------------------------------------
    # CREATE FARM ENVIRONMENT
    # ----------------------------------------------------------------------
    farm_env = Farm(
        fields=fields,
        farmers=farmers,
        scoring=scoring,
        rules=rules,
        policies=[],
        interaction_mode=interaction_mode,
    )

    return farm_env


# ----------------------------------------------------------------------
# Optional CLI usage
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python make_farm.py <path_to_yaml>")
        sys.exit(1)

    farm_path = sys.argv[1]
    env = make_farm(farm_path)
    print(env)
    obs, info = env.reset()
    print("Initial observation:", obs)
