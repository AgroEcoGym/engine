
from agroecogym_engine.core.utils.yaml import yml_tuple_constructor

from gymnasium.spaces import Box, Dict, Discrete


class ActionConverter:
    """
    Converts between Gym actions and FarmGym actions.
    Also handles random action generation and observation formatting.
    """

    def __init__(self, env):
        self.env = env
        self.rules = env.rules
        #self.fields = env.fields
        self.farmers = env.farmers


    def farmgym_to_gym_observations(self, farmgym_observations):
        gym_observations = []
        for fo in farmgym_observations:
            fa_key, fi_key, e_key, variable_key, path, value = fo
            gym_value = (
                self.env.fields[fi_key]
                .entities[e_key]
                .gym_observe_variable(variable_key, path)
            )
            g = {}
            g[fa_key] = {}
            g[fa_key][fi_key] = {}
            g[fa_key][fi_key][e_key] = {}
            g[fa_key][fi_key][e_key][variable_key] = {}
            if path != []:
                # print("PATH",str(path))
                # TODO UPDATE for path=['min#°C',2]?
                g[fa_key][fi_key][e_key][variable_key][str(path)] = gym_value
            else:
                g[fa_key][fi_key][e_key][variable_key] = gym_value
            # gym_observations[str(fa_key)+"."+str(fi_key)+"."+str(e_key)+"."+str(variable_key)+"."+str(path)]=gym_value
            gym_observations.append(g)
        return gym_observations



    def gymaction_to_farmgymaction(self, actions):
        # TODO: Check it on all cases. Is it still working?
        """
        Converts actions given in gym format to actions in farmgym format.
        By construction, this only generates actions in the subset of available actions specified by the configuration file.
        """

        # def convert(value, ranges):
        #     if ranges is None:
        #         return {}
        #     if isinstance(ranges, list):
        #         if isinstance(ranges[value], str) and "(" in ranges[value]:  # Plots.
        #             return yml_tuple_constructor(ranges[value], int)
        #         return ranges[value]
        #     elif (
        #         isinstance(ranges, str) and "(" in ranges
        #     ):  # Range of continuous values
        #         # print("?",value, ranges)
        #         return (float)(value)
        #     elif isinstance(ranges, dict):
        #         c_v = {}
        #         for k in ranges:
        #             c_v[k] = convert(value[k], ranges[k])
        #         return c_v

        ll = len(self.env.space_builder.farmgym_observation_actions)
        fg_actions = []
        for action in actions:
            index, act = action
            # print("I,A",index,act,len(self.farmgym_observation_actions))
            # if index == 0:
            #    fg_actions.append(self.farmgym_observation_actions[act])
            if index < ll:
                if act == 0:
                    fg_actions.append(self.env.space_builder.farmgym_observation_actions[index])
            else:
                fa, fi, e, a, f_a, g, ng = self.env.space_builder.farmgym_intervention_actions[index - ll]
                # fa, fi, e, a, f_a, g, ng = self.farmgym_intervention_actions[index - 1]
                farmgym_act = self._convert_param(act, f_a)
                # TODO: proper mapping from OrderedDict to Dict when dict parameters, + case of None parameter.
                fg_actions.append((fa, fi, e, a, farmgym_act))
        return fg_actions




    def gymaction_to_discretized_farmgymaction(self, actions):
        """
        Input:
            actions = [4, 8 ...]
        Output:
            fg_actions = [('BasicFarmer-0', 'Field-0', 'Plant-0', 'stage', [(0, 0)]), ...]
        """

        # def convert(value, ranges):
        #     if ranges is None:
        #         return {}
        #     if isinstance(ranges, list):
        #         if isinstance(ranges[value], str) and "(" in ranges[value]:  # Plots.
        #             return yml_tuple_constructor(ranges[value], int)
        #         return ranges[value]
        #     elif (
        #         isinstance(ranges, str) and "(" in ranges
        #     ):  # Range of continuous values
        #         # r = ranges.split(",")
        #         # m=float(r[0][1:])
        #         # M=float(r[1][:-1])
        #         # print("?",value, ranges,m,M)
        #         return (float)(value)
        #     elif isinstance(ranges, dict):
        #         c_v = {}
        #         for k in ranges:
        #             c_v[k] = convert(value[k], ranges[k])
        #         return c_v

        fg_actions = []
        for action in actions:
            if action < len(self.env.space_builder.farmgym_observation_actions):
                fg_actions.append(self.env.space_builder.farmgym_observation_actions[action])
            else:
                theindex = action - len(self.env.space_builder.farmgym_observation_actions)
                theaction = None
                # print("A", action)
                # print("gymtodiscre", theindex, self.farmgym_intervention_actions,actions)
                for fa, fi, e, a, f_a, g, ng in self.env.space_builder.farmgym_intervention_actions:
                    if ng > theindex:
                        theaction = (fa, fi, e, a, f_a, g, ng)
                        break
                    else:
                        theindex -= ng
                # print("gymtodiscre", theindex, theaction)
                fa, fi, e, a, f_a, g, ng = theaction

                # print("B1",g,type(g), theindex, ng)

                if type(g) == Discrete:
                    act = theindex
                elif type(g) == Box:
                    i = theindex
                    m = g.low
                    M = g.high
                    factor = ng // self.env.space_builder.discretization_nbins
                    # factor = nbins
                    j = i // factor
                    i = i - j * factor
                    act = m + j / (self.env.space_builder.discretization_nbins + 1) * (M - m)

                elif type(g) == Dict:
                    i = theindex
                    factor = ng
                    act = {}
                    for key in g:
                        if type(g[key]) == Discrete:
                            factor = factor // g[key].n
                            # factor = g[key].n
                            j = i // factor
                            i = i - j * factor
                            act[key] = j
                            # print(g[key], i,j, act[key],factor)
                        elif type(g[key]) == Box:
                            # print("B2", g[key], g[key].shape, i, ng)
                            # print(g[key].low, g[key].high)
                            m = g[key].low
                            M = g[key].high
                            factor = factor // self.env.space_builder.discretization_nbins
                            # factor = nbins
                            j = i // factor
                            i = i - j * factor
                            act[key] = m + j / (self.env.space_builder.discretization_nbins + 1) * (M - m)
                            # print(g[key], i,j, act[key],factor)
                else:
                    act = {}
                    # print("C",act,i,f_a)
                farmgym_act = self._convert_param(act, f_a)
                fg_actions.append((fa, fi, e, a, farmgym_act))
        return fg_actions


    def discretized_farmgymaction_to_gymaction(self, actions):
        """
        Input:
            actions = [('BasicFarmer-0', 'Field-0', 'Plant-0', 'stage', [(0, 0)]), ...]
        Output:
            ii = [4,5, etc]
        """
        ii = []
        nb_tot_actions = self.env.action_space.space.n + len(
            self.env.space_builder.farmgym_observation_actions
        )
        for action in actions:
            for i in range(nb_tot_actions):
                a = self.env.action_converter.gymaction_to_discretized_farmgymaction([i])
                fa, fi, e, a, p = a[0]
                if action == a[0]:
                    ii.append(i)
        return ii



    def random_allowed_observation(self):
        """Randomly sample a valid observation action if available, as allowed by the yaml file, in farmgym format."""
        obs_actions = self.env.space_builder.farmgym_observation_actions
        if len(obs_actions) == 0:
            return None
        n = self.env.np_random.integers(len(obs_actions))
        return obs_actions[n]



    def random_allowed_intervention(self):
        """
        Outputs a randomly generated intervention, as allowed by the yaml file, in farmgym format.
        """
        n = self.env.np_random.integers(len(self.env.space_builder.farmgym_intervention_actions))
        # intervention = self.np_random.choice(list(self.farmgym_intervention_actions))
        (
            fa,
            fi,
            e,
            inter,
            params,
            gym_space,
            len_gym_space,
        ) = self.env.space_builder.farmgym_intervention_actions[n]
        o = gym_space.sample()

        # def convert(value, ranges):
        #     if isinstance(ranges, list):
        #         if isinstance(ranges[value], str) and "(" in ranges[value]:  # Plots.
        #             return yml_tuple_constructor(ranges[value], int)
        #         return ranges[value]
        #     elif (
        #         isinstance(ranges, str) and "(" in ranges
        #     ):  # Range of continuous values
        #         # print("?",value, ranges)
        #         return (float)(value)
        #     elif isinstance(ranges, dict):
        #         c_v = {}
        #         for k in ranges:
        #             c_v[k] = convert(value[k], ranges[k])
        #         return c_v



        farmgym_act = {}
        if isinstance(params, dict):
            # print("DICT:",f_a,act)
            farmgym_act = {}
            for k in params:
                farmgym_act[k] = self._convert_param(o[k], params[k])

        return (fa, fi, e, inter, farmgym_act)


    # ----------------------------------------------------------------------
    # UTILITIES
    # ----------------------------------------------------------------------
    def _convert_param(self, value, ranges):
        """Helper for decoding parameter spaces (nested or continuous)."""
        if ranges is None:
            return {}
        if isinstance(ranges, list):
            if isinstance(ranges[value], str) and "(" in ranges[value]:
                return yml_tuple_constructor(ranges[value], int)
            return ranges[value]
        elif isinstance(ranges, str) and "(" in ranges:
            return float(value)
        elif isinstance(ranges, dict):
            return {k: self._convert_param(value[k], ranges[k]) for k in ranges}
        return value
