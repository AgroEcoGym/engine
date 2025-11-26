
from gymnasium.utils import seeding

class SimulationCore:
    """
    Implements the detailed simulation logic of the farm:
    - initialization of state variables
    - alternating observation and intervention steps
    - reward computation and termination
    """

    def __init__(self, env):
        self.env = env
        self.is_observation_time = True
        self.last_farmgym_action = None

        # ----------------------------------------------------------------------
        # INITIALIZATION
        # ----------------------------------------------------------------------
    def initialize_state(self):
        self.last_farmgym_action = None
        for fi in self.env.rules.initial_conditions:
            for e in self.env.rules.initial_conditions[fi]:
                self.env.fields[fi].entities[
                    e
                ].initial_conditions = self.env.rules.initial_conditions[fi][e]

        self.day_path = {
            "field": "Field-0",
            "entity": "Weather-0",
            "variable": "day#int365",
        }
        self.year_path = {
            "field": "Field-0",
            "entity": "Weather-0",
            "variable": "year#int100",
        }
        self.is_observation_time = True


    def _get_day(self):
        return (int)(
            self.env.fields[self.day_path["field"]]
            .entities[self.day_path["entity"]]
            .variables[self.day_path["variable"]]
            .value
        )


    def _get_year(self):
        return (int)(
            self.env.fields[self.year_path["field"]]
            .entities[self.year_path["entity"]]
            .variables[self.year_path["variable"]]
            .value
        )

    def _set_day_path(self, path):
        self.day_path = path

    def farmgym_reset(self, seed=None, options=None):
        """
        Resets the environment.
        """

        self.last_farmgym_action = None
        self.np_random, seed = seeding.np_random(seed)
        self.is_observation_time = True
        for f in self.env.fields.values():
            f.np_random = self.np_random
            f.reset()

        observations = []
        # Add free observations if any
        obs_vec = self.get_free_observations()
        [observations.append(o) for o in obs_vec]

        # observations, _, _, info = self.farmgym_step([])
        # _, _, _, _ = self.farmgym_step([])

        info = {"intervention cost": 0}
        return observations, info


    def farmgym_step(self, action_schedule):
        """
        Performs a step evolution of the system, from current stage to next state given the input action.
        A farm gym step alternates between observation step and action step before moving to next day.
        """
        # print("AS",action_schedule)
        filtered_action_schedule = self.env.rules.filter_actions(
            self.env, action_schedule, self.is_observation_time
        )
        self.env.rules.assert_actions(filtered_action_schedule)

        if self.is_observation_time:
            self.last_farmgym_action = (filtered_action_schedule, None)
            output = self._observation_step(filtered_action_schedule)
            self.is_observation_time = False
            return output
        else:
            self.last_farmgym_action = (
                self.last_farmgym_action[0],
                filtered_action_schedule,
            )
            output = self._intervention_step(filtered_action_schedule)
            self.is_observation_time = True
            return output




    def get_free_observations(self):
        """
        :param field:
        :return:  list of (field-key,position, entity-key, variable, value)
        """
        # Give all information
        # entities_list = field.entities.values()
        observations = []

        for fo in self.env.rules.free_observations:
            fa_key, fi_key, e_key, variable_key, path = fo
            value = (
                self.env.fields[fi_key].entities[e_key].observe_variable(variable_key, path)
            )
            observations.append((fa_key, fi_key, e_key, variable_key, path, value))

        return observations

    def _observation_step(self, observation_schedule):
        """
        Performs an observation step, one of the two types of farmgym steps.
        """
        observations = []

        # # Add free observations if any
        # obs_vec = self.get_free_observations()
        # [observations.append(o) for o in obs_vec]

        # Perform action
        observation_schedule_cost = 0
        # self.rules.assert_actions(action_schedule)
        for observation_item in observation_schedule:
            fa_key, fi_key, entity, variable_key, path = observation_item
            # assert(action_type=='observe')
            # We can change this to policies using:
            # fa_key,fi_key,pos,action = policy_item.action(observations)
            cost = self.env.scoring.observation_cost(
                self.env.farmers[fa_key],
                self.env.fields[fi_key],
                fi_key,
                entity,
                variable_key,
                path,
            )
            day = self._get_day()
            obs_vec = self.env.farmers[fa_key].perform_observation(
                fi_key, entity, variable_key, path, day
            )
            observation_schedule_cost +=cost
            [observations.append(o) for o in obs_vec]
            # print("OV",obs_vec)
            # print("O",observations)

        return observations, 0, False, False, {
            "observation cost": observation_schedule_cost
        }
        # return (observation, reward, terminated, truncated, info) or  (observation, reward, done, info)



    def _intervention_step(self, action_schedule):
        """
        Performs an intervention step, one of the two types of farmgym steps.
        """
        observations = []

        # Perform action
        intervention_schedule_cost = 0
        for intervention_item in action_schedule:
            fa_key, fi_key, entity_key, action_name, params = intervention_item
            # We can change this to policies using:
            # fa_key,fi_key,pos,action = policy_item.action(observations)
            cost = self.env.scoring.intervention_cost(
                fa_key, fi_key, entity_key, action_name, params
            )
            day = self._get_day()
            obs_vec = self.env.farmers[fa_key].perform_intervention(
                fi_key, entity_key, action_name, params, day
            )
            # print("OBSVEC", obs_vec)
            [observations.append(o) for o in obs_vec]
            intervention_schedule_cost += cost

        # Update dynamics
        for f in self.env.fields.values():
            f.update_to_next_day()
        for fa in self.env.farmers:
            self.env.farmers[fa].update_to_next_day()

        # Compute reward
        reward = 0
        for f in self.env.fields:
            entities_list = self.env.fields[f].entities.values()
            reward += self.env.scoring.reward(entities_list)

        # Check if terminal
        terminated = self.env.rules.is_terminal(self.env.fields)

        if self.env.monitor is not None:
            self.env.monitor.update_fig()

        # Compute final reward
        if terminated:
            for f in self.env.fields.values():
                reward += self.env.scoring.final_reward(f.entities.values())
            if self.env.monitor is not None:
                self.env.monitor.close()

        # Add free observations if any
        obs_vec = self.get_free_observations()
        [observations.append(o) for o in obs_vec]

        return (
            observations,
            reward,
            terminated,
            False,
            {"intervention cost": intervention_schedule_cost},
        )