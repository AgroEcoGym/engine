######################################
# ruff: noqa: F841, F821
import inspect
import os
from pathlib import Path
from textwrap import indent
import gymnasium as gym
from gymnasium.utils import seeding


file_path = Path(os.path.realpath(__file__))
CURRENT_DIR = file_path.parent

from agroecogym_engine.core.config.naming import NameAssigner
from agroecogym_engine.core.config.setup_manager import SetupManager
from agroecogym_engine.core.dynamics.state_manager import StateManager
from agroecogym_engine.core.spaces.space_builder import SpaceBuilder
from agroecogym_engine.core.spaces.action_conversion import ActionConverter
from agroecogym_engine.rendering.monitoring_utils import MonitoringManager
from agroecogym_engine.rendering.farm_renderer import FarmRenderer

## Here is the reason why you should use dictionaries instead of lists as much as possible: https://towardsdatascience.com/faster-lookups-in-python-1d7503e9cd38




class Farm(gym.Env):
    """
    Instantiates a Farm environment.
    Constructed from one or several fields (:class:`~farmgym.v2.field.Field`), farmers (:class:`~farmgym.v2.farmer_api.Farmer_API`), a score (:class:`~farmgym.v2.scoring_api.Scoring_API`) and  a set of rules (:class:`~farmgym.v2.rules_api.Rules_API`). The farm can then be constructed through ``farm=Farm(fields,farmers,scoring,rules)``.

    Parameters
    ----------
    fields : a list of fields, that is instances of the class :class:`~farmgym.v2.field.Field`
        Field used to define the farm.

    farmers: a list of farmers, that is instances of a class implementing the :class:`~farmgym.v2.farmer_api.Farmer_API`
        Farmers used to define the farm.

    scoring: an instance of the :class:`~farmgym.v2.scoring_api.Scoring_API`
        Scoring function used to generate the reward of the farm.

    rules: an instance of the   :class:`~farmgym.v2.rules_api.Rules_API`
        Rules used to define the farm (i.e. allowed actions, how to filter actions...)

    policies: a list of policies, that is instances of a class implementing the :class:`~farmgym.v2.policy_api.Policy_API`
        Expert policies defined in the farm

    seed: an integer,
        seed used by the random-number generator.

    Notes
    -----
    At creation, automatically generates yaml configuration files to help customize the farm. One file to specify the list of allowed actions, one file to initialize state variables, and one file to specify the score.


    """

    def __init__(
        self,
        fields,
        farmers,
        scoring,
        rules,
        policies=None,
        interaction_mode="AOMDP",
        seed=None,
        render_mode="human"
    ):
        # --- Naming and structure
        self.name_assigner = NameAssigner()
        self.fields = self.name_assigner.assign_fields(fields)
        self.farmers = self.name_assigner.assign_farmers(farmers,fields)
        self.name = self.name_assigner.build_full_name(self.fields, self.farmers)
        self.shortname = self.name_assigner.build_short_name(self.fields)

        # --- Base components
        self.scoring = scoring
        self.rules = rules
        self.policies=policies
        self.interaction_mode = interaction_mode
        self.monitor = None


        # --- Build YAML configuration files if missing
        farm_call = " ".join(inspect.stack()[1].code_context[0].split("=")[0].split())
        filep = "/".join(inspect.stack()[1].filename.split("/")[0:-1])
        farmpath= filep + "/" + farm_call

        self.config_manager = SetupManager(self)
        self.config_manager.ensure_configurations(farmpath)

        self.seed(seed)

        self.space_builder = SpaceBuilder(self)
        self.observation_space = self.space_builder.build_gym_observation_space(seed)
        self.action_space = self.space_builder.build_gym_discretized_action_space(seed)

        #Initialize
        self.state_manager = StateManager(self)
        self.state_manager.sim_core.initialize_state()

        self.action_converter = ActionConverter(self)
        self.monitoring = MonitoringManager(self)
        self.renderer = FarmRenderer(self,render_mode)


    def seed(self, seed=None):
        """
         Modifies the seed of the random generators used in the environment.
         """
        self.np_random, seed = seeding.np_random(seed)
        for fi in self.fields:
            for e in self.fields[fi].entities:
                self.fields[fi].entities[e].set_random(self.np_random)
        return [seed]

    # QUESTION:  Do we add shared entities outside fields ?? (but need to be updated only once /day ). Or do let an entity in a field to be used by a farmer in other field (e.g. water tank).

    def set_render_mode(self,render_mode):
        if (render_mode=="human"):
            self.renderer.render_mode= "text"
        else:
            self.renderer.render_mode= render_mode
        self.renderer.init()

    def reset(self, seed=None, options=None):
        """
        Resets the environment.
        """
        super().reset(seed=seed, options=options)
        return self.state_manager.reset(seed, options)


    def step(self, action):
        """
        Performs a step evolution of the system, from current stage to next state given the input action.
        """
        """Perform a simulation step (Gym standard API)."""
        return self.state_manager.step(action)

    def render(self, mode="human"):
        """Render the current state of the farm."""
        self.renderer.render(mode)

    def add_monitoring(
        self, list_of_variables, tensorboard=True, matview=True, launch=True
    ):
        """Attach monitoring to visualize variables."""
        self.monitoring.attach(list_of_variables, tensorboard, matview, launch)


    def close(self):
        super().close()
        if self.monitor:
            self.monitor.close()
        self.renderer.close()

    def __str__(self):
        """
        Outputs a string showing a snapshot of the farm at the given time. All state variables of each entity, farmers information as well ws all free observations, available observations and available interventions.
        """
        s = "Full name: " + self.name + "\nShort name: " + self.shortname + "\n"
        s += "Fields: " + str(len(self.fields))+"\n"

        for f in self.fields:
            s += indent(str(self.fields[f]), "\t", lambda line: True) + "\n"

        s += "Farmers:" + "\n"
        for f in self.farmers:
            s += indent(str(self.farmers[f]), "\t", lambda line: True) + "\n"

        s += f"Interaction mode: {self.interaction_mode}\n"

        s += "Free farmgym observations:" + "\n"
        for o in self.rules.free_observations:
            s += "\t" + str(o) + "\n"

        if self.interaction_mode == "AOMDP":
            s += "Available farmgym observations:" + "\n"
            for o in self.space_builder.farmgym_observation_actions:
                s += "\t" + str(o) + "\n"

        s += "Available farmgym interventions:" + "\n"
        for i in self.space_builder.farmgym_intervention_actions:
            fa, fi, e, a, f_a, g, ng = i
            s += "\t" + str((fa, fi, e, a, f_a)) + "\n"

        s += (
            "Available gym actions: (as list [n1 n2 n3] where ni is one of the following)"
            + "\n"
        )
        s += self.renderer.actions_to_string()
        return s
    #
    # def print_state(self):
    #     """Print a concise view of the current observable state."""
    #     for fi, field in self.fields.items():
    #         print(f"Field: {fi}")
    #         for e, ent in field.entities.items():
    #             vals = {v: getattr(val, 'value', None) for v, val in ent.variables.items()}
    #             print(f"  {e}: {vals}")

    def understand_the_farm(self):
        farm = self
        print(farm)
        # PLAY WITH ENVIRONMENT:
        print("#############INTERVENTIONS###############")
        actions = farm.space_builder.farmgym_intervention_actions
        for ac in actions:
            fa, fi, e, a, f_a, g, ng = ac
            print(ac, ":\t", (fa, fi, e, a, g.sample(), ng))
        print("#############OBSERVATIONS###############")
        actions = farm.space_builder.farmgym_observation_actions
        for ac in actions:
            # fa,fi,e,a,g = ac
            print(ac)
        print("###########GYM SPACES#################")
        from agroecogym_engine.core.utils.gymUnion import str_pretty

        print("Gym states:\n", str_pretty(farm.space_builder.farmgym_state_space))
        s = farm.space_builder.farmgym_state_space.sample()
        print("Random state:", s)
        print("Gym observations:\n", farm.observation_space)
        o = farm.observation_space.sample()
        print("Random observation:", o)
        # print("?", farm.farmgym_state_space.contains(s), farm.observation_space.contains(o))

        print("############RANDOM ACTIONS################")
        print(
            "Random intervention allowed by rules:\t",
            farm.action_converter.random_allowed_intervention(),
        )
        print(
            "Random observation allowed by rules:\t", farm.action_converter.random_allowed_observation()
        )
        print("############RANDOM GYM ACTIONS################")
        print("Gym (discretized) actions:", farm.action_space)
        # disc_space= farm.build_gym_discretized_action_space()
        # print("Gym discretized  actions:", disc_space)
        print("Do nothing gym action schedule:", "[]")
        print(
            " corresponding farmgym action schedule:",
            farm.action_converter.gymaction_to_farmgymaction([]),
        )
        print("Now sampling 25 actions uniformly randomly:")
        for i in range(25):
            a = farm.action_space.sample()
            print(
                "Random gym action schedule:\t\t",
                a,
                "\n corresponding discretized farmgym action schedule:",
                farm.action_converter.gymaction_to_discretized_farmgymaction(a),
            )

        print("###############################")
        # print(farm.actions_to_string())



