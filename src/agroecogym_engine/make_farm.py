import inspect
import sys

import yaml

import farmgym
from agroecogym_engine.entities.Birds import Birds
from agroecogym_engine.entities.Cide import Cide
from agroecogym_engine.entities.Facilities import Facility
from agroecogym_engine.entities.Fertilizer import Fertilizer
from agroecogym_engine.entities.Pests import Pests
from agroecogym_engine.entities.Plant import Plant
from agroecogym_engine.entities.Pollinators import Pollinators
from agroecogym_engine.entities.Soil import Soil

## The following import lines are import for the make_farm function that uses inspection module!
from agroecogym_engine.entities.Weather import Weather
from agroecogym_engine.entities.Weeds import Weeds
from agroecogym_engine.farm import Farm
from agroecogym_engine.actors.farmers.BasicFarmer import BasicFarmer
from agroecogym_engine.field import Field
from agroecogym_engine.actors.actionrules.BasicRule import BasicRule
from agroecogym_engine.scores.BasicScore import BasicScore


def make_farm(yamlfile):
    with open(yamlfile, "r", encoding="utf8") as file:
        farm_yaml = yaml.safe_load(file)

    farm = farm_yaml["Farm"]

    fields = []
    farmers = []
    for fi in farm:
        if "Field" in fi:
            entities = farm[fi]["entities"]
            ent = []
            for e in entities:
                k = (list(e.keys()))[0]
                c = getattr(sys.modules[__name__], k)
                # print("E",e, list(e.keys()), k,c)
                ent.append((c, str(e[k])))
            fields.append(
                Field(
                    localization=farm[fi]["localization"],
                    shape=farm[fi]["shape"],
                    entities_specifications=ent,
                )
            )
        if "Farmer" in fi:
            if farm[fi]["type"] == "basic":
                farmers.append(
                    BasicFarmer(
                        max_daily_interventions=farm[fi]["parameters"][
                            "max_daily_interventions"
                        ],
                        max_daily_observations=farm[fi]["parameters"][
                            "max_daily_observations"
                        ],
                    )
                )

    interaction_mode = farm_yaml["interaction_mode"]
    name = yamlfile[:-5]
    # TODO: Perhaps these names could be defined automatically? or actually remove the initailization file entirely,
    #  and proceed with init_values only.
    name_score = name + "_" + farm_yaml["score"]
    name_init = name + "_" + farm_yaml["initialization"]
    name_actions = name + "_" + farm_yaml["actions"]

    scoring = BasicScore(score_configuration=name_score)

    rules = BasicRule(init_configuration=name_init, actions_configuration=name_actions)

    farm = Farm(
        fields=fields,
        farmers=farmers,
        scoring=scoring,
        rules=rules,
        policies=[],
        interaction_mode=interaction_mode,
    )
    return farm
