import os

from tests.game_agents.basic_agents import Farmgym_RandomAgent
from tests.game_builder.make_farm import make_farm
from tests.game_builder.run_farm import run_gym_xp

from agroecogym_engine.rendering.monitoring import make_variables_to_be_monitored

def env():
    yaml_path = os.path.join(os.path.dirname(__file__), "farm2.yaml")
    farm = make_farm(yaml_path)
    variables = ["f0>soil>available_Water#L",
                 "f0>weather>rain_amount#mm.day-1",
                 "f0>weather>forecast>air_temperature>min#°C"]
    varlist=make_variables_to_be_monitored(variables)
    farm.add_monitoring(varlist)
    return farm


if __name__ == "__main__":
    agent = Farmgym_RandomAgent()
    run_gym_xp(env(), agent, max_steps=15, render="image")
