
from agroecogym_engine.core.utils.yaml import yml_tuple_constructor
from gymnasium.spaces import Box, Dict, Discrete, Tuple
from agroecogym_engine.core.utils.gymUnion import MultiUnion, Sequence
import numpy as np

class SpaceBuilder:
    """
    Constructs the observation, action, and state spaces for the Farm environment,
    both in FarmGym and Gym formats.
    """

    def __init__(self, env):
        self.env = env
        self.discretization_nbins = self._get_discretization_bins()

        self.farmgym_observation_actions = self.build_farmgym_observation_actions(
            self.env.rules.actions_allowed["observations"]
        )
        self.farmgym_intervention_actions = self.build_farmgym_intervention_actions(
            self.env.rules.actions_allowed["interventions"]
        )
        self.farmgym_state_space = self.build_gym_state_space()



    # ----------------------------------------------------------------------
    # BASIC SETUP
    # ----------------------------------------------------------------------
    def _get_discretization_bins(self):
        try:
            return self.env.rules.actions_allowed["params"][
                "number_of_bins_to_discretize_continuous_actions"
            ]
        except KeyError:
            return 11



    def build_farmgym_observation_actions(self, action_yaml):
        """
        Generates a list of all possible farmgym observation-actions allowed by the configuration file action_yaml.
        """

        def make(dictio, variables):
            if isinstance(dictio, list):
                actions = {}
                for key in dictio:
                    if key == "*":
                        actions["*"] = ["'"]
                    elif isinstance(key, str) and "(" in key:
                        id = yml_tuple_constructor(key, int)
                        actions[id] = [id]
                    else:
                        actions[key] = [key]
                return actions
            elif dictio is None:
                return ["'"]
            elif isinstance(dictio, dict):
                actions = {}
                for key in dictio:
                    if key == "*":
                        actions["*"] = ["'"]
                    # elif (key=='\'*\''):
                    #    print("KEY2")
                    #    actions[key]=['\'']
                    else:
                        # print("DICTIO", dictio, "key", key, "VAR", variables)
                        p = make(dictio[key], variables[key])
                        actions[key] = p
                return actions

        def unpile(var, paths, prefix):
            actions = []
            if isinstance(paths, dict):
                for key in paths:
                    if key == "*":
                        acts = unpile(var, paths[key], prefix)
                        [actions.append(o) for o in acts]
                    else:
                        acts = unpile(var, paths[key], prefix + [key])
                        [actions.append(o) for o in acts]
            else:
                actions.append((var[0], var[1], var[2], var[3], prefix))
            return actions

        actions = []
        for fa in self.env.farmers:
            if fa in action_yaml.keys():
                for fi in self.env.fields:
                    if fi in action_yaml[fa].keys():
                        for e in self.env.fields[fi].entities:
                            if e in action_yaml[fa][fi].keys():
                                if action_yaml[fa][fi][e] is not None:
                                    for var in self.env.fields[fi].entities[e].variables:
                                        if var in action_yaml[fa][fi][e].keys():
                                            paths = make(
                                                action_yaml[fa][fi][e][var],
                                                self.env.fields[fi]
                                                .entities[e]
                                                .variables[var],
                                            )
                                            acts = unpile((fa, fi, e, var), paths, [])
                                            [actions.append(o) for o in acts]

        free_actions = []
        if "Free" in action_yaml.keys():
            for fi in self.env.fields:
                if fi in action_yaml["Free"].keys():
                    for e in self.env.fields[fi].entities:
                        if e in action_yaml["Free"][fi].keys():
                            if action_yaml["Free"][fi][e] is not None:
                                for var in self.env.fields[fi].entities[e].variables:
                                    if var in action_yaml["Free"][fi][e].keys():
                                        paths = make(
                                            action_yaml["Free"][fi][e][var],
                                            self.env.fields[fi].entities[e].variables[var],
                                        )
                                        acts = unpile(("Free", fi, e, var), paths, [])
                                        [free_actions.append(o) for o in acts]
        self.env.rules.free_observations = free_actions

        if self.env.interaction_mode == "AOMDP":
            return actions
        return []




    def build_farmgym_intervention_actions(self, action_yaml):
        """
        Generates a list of all possible farmgym intervention-actions allowed by the configuration file action_yaml.
        """

        def make(action):
            #            print("ACTION",action, type(action))
            if isinstance(action, str):
                tuple = yml_tuple_constructor(action)
                m, M = tuple
                return Box(low=m, high=M, shape=())
            elif isinstance(action, list):
                ## Need to handle tuples differently.
                # print("KEYY",dictio[key])
                return Discrete(len(action))
            elif action is None:
                return Discrete(1)
            elif isinstance(action, dict):
                actions = {}
                for key in action:
                    actions[key] = make(action[key])
                return Dict(actions)

        def len_discretized_gym_space(gym_space, nbins=10):
            nactiong = 0
            if type(gym_space) == Dict:
                # print(g)
                nactiong = 1
                for key in gym_space:
                    space = gym_space[key]
                    if isinstance(space, Discrete):
                        nactiong *= space.n
                    elif isinstance(space, Box):
                        nactiong *= nbins ** np.prod(space.shape)
            elif type(gym_space) == Discrete:
                nactiong = gym_space.n
            elif type(gym_space) == Box:  # Assumes it is always dimension 1.
                nactiong = nbins  # ** np.prod(gym_space.shape)
            return int(nactiong)

        actions = []
        for fa in self.env.farmers:
            if fa in action_yaml.keys():
                for fi in self.env.fields:
                    if fi in action_yaml[fa].keys():
                        for e in self.env.fields[fi].entities:
                            if e in action_yaml[fa][fi].keys():
                                if action_yaml[fa][fi][e] is not None:
                                    for action in action_yaml[fa][fi][e]:
                                        gym_a = make(action_yaml[fa][fi][e][action])
                                        # print(gym_a)
                                        actions.append(
                                            (
                                                fa,
                                                fi,
                                                e,
                                                action,
                                                action_yaml[fa][fi][e][action],
                                                gym_a,
                                                len_discretized_gym_space(
                                                    gym_a,
                                                    nbins=self.discretization_nbins,
                                                ),
                                            )
                                        )
        return actions




    def build_gym_state_space(self):
        """
        Outputs a state space in gym Tuple format built from all state variables.
        """
        ## TODO: flatten? https://github.com/openai/gym/issues/1830

        def to_gym(range):
            if type(range) == tuple:
                m, M = range
                return Box(m, M, (), float)
            else:
                return Discrete(len(range))

        def make_s(x, indent=""):
            if isinstance(x, dict):
                state = {}
                for k in x:
                    state[k] = make_s(x[k], indent=indent + "  ")
                return Dict(state)
            elif type(x) == np.ndarray:
                it = np.nditer(x, flags=["multi_index", "refs_ok"])
                # s+= str(len(it))+","+str(x.shape) +","+str(len(x.shape))+","+str(len(x))
                if len(x.shape) > 1:
                    state = []
                    state.append(to_gym(x[it.multi_index].range))
                    it.iternext()
                    while not it.finished:
                        state.append(to_gym(x[it.multi_index].range))
                        is_not_finished = it.iternext()
                    return Tuple(state)
                else:
                    state = []
                    for i in range(len(x)):
                        state.append(to_gym(x[i].range))
                    return Tuple(state)
            else:
                return to_gym(x.range)

        state_space = []
        state_space_ = {}
        for fi in self.env.fields:
            state_space_[fi] = {}
            for e in self.env.fields[fi].entities:
                state_space_[fi][e] = {}
                for v in self.env.fields[fi].entities[e].variables:
                    s = make_s(self.env.fields[fi].entities[e].variables[v])
                    # if type(s) == Union:
                    #    [state_space.append(ss) for ss in s.spaces]
                    # else:
                    state_space.append(s)
                    state_space_[fi][e][v] = self.env.fields[fi].entities[e].variables[v]

        return Dict(make_s(state_space_))  # Tuple(state_space)



    def build_gym_observation_space(self, seed):
        """
        Outputs an observation space in gym MultiUnion format from all possible observations.
        """

        # TODO: flatten https://github.com/openai/gym/issues/1830?
        # Number all discrete actions, then discretize continuous ones with param N (nb of elements for each dim). number mutiactions etc.

        def make_space(x):
            if isinstance(x, dict):
                xspace = {}
                for k in x.keys():
                    xspace[k] = make_space(x[k])
                # print("MS",x.keys(),"\n\t",xspace,"\n\t",Dict(xspace))
                # TODO: THe following does not keep the keys from x.keys() in the correct order !! This is a gymnasium (and gym) issue !! It seems to sort them by alphabetic order !!
                return Dict(xspace)
            elif type(x) == np.ndarray:
                xspace = []
                for xx in x:
                    xspace.append(make_space(xx))
                return Tuple(xspace)
            else:
                return x.to_gym_space()

        observation_space = []

        for fo in self.env.rules.free_observations:
            fa_key, fi_key, e_key, variable_key, path = fo
            var = self.env.fields[fi_key].entities[e_key].variables[variable_key]
            x = var
            for p in path:
                x = x[p]
            # print("x",x)
            # observation_space.append(make_space(x))

            o_space = {}
            o_space[fa_key] = {}
            o_space[fa_key][fi_key] = {}
            o_space[fa_key][fi_key][e_key] = {}
            o_space[fa_key][fi_key][e_key][variable_key] = {}
            if path != []:
                # oo ={}
                # for p in path:
                #    oo[p]={}

                o_space[fa_key][fi_key][e_key][variable_key][str(path)] = x
            else:
                o_space[fa_key][fi_key][e_key][variable_key] = x
            # print("MAKE SPACE",make_space(o_space))
            observation_space.append(make_space(o_space))

        for oa in self.farmgym_observation_actions:
            fa_key, fi_key, e_key, variable_key, path = oa
            var = self.env.fields[fi_key].entities[e_key].variables[variable_key]
            x = var
            for p in path:
                x = x[p]

            # observation_space.append(make_space(x))

            o_space = {}
            o_space[fa_key] = {}
            o_space[fa_key][fi_key] = {}
            o_space[fa_key][fi_key][e_key] = {}
            o_space[fa_key][fi_key][e_key][variable_key] = {}
            if path != []:
                o_space[fa_key][fi_key][e_key][variable_key][str(path)] = x
            else:
                o_space[fa_key][fi_key][e_key][variable_key] = x
            observation_space.append(make_space(o_space))

        multi_union = MultiUnion(observation_space)
        multi_union.seed(seed)
        return multi_union



    def build_gym_discretized_action_space(self, seed):
        """Whenever encounters a continuous box, split each dimension into nbins bins"""
        naction = len(self.farmgym_observation_actions)
        for fa, fi, e, a, f_a, g, ng in self.farmgym_intervention_actions:
            naction += ng
        # print("BUILD DISCRETIZED A", naction)
        sequence = Sequence(
            Discrete(naction),
            maxnonzero=self.env.rules.actions_allowed["params"]["max_action_schedule_size"],
        )
        sequence.seed(seed)
        return sequence

    # UNUSED:
    def build_gym_action_space(self, seed):
        multi_union = MultiUnion(
            [Discrete(1) for x in range(len(self.farmgym_observation_actions))]
            + [g for fa, fi, e, a, f_a, g, ng in self.farmgym_intervention_actions],
            maxnonzero=self.env.rules.actions_allowed["params"]["max_action_schedule_size"]
        )
        multi_union.seed(seed)
        return multi_union