from agroecogym_engine.core.dynamics.simulation_core import SimulationCore

class StateManager:
    """
    Controls the main simulation loop of the farm environment:
    - Initialization (reset)
    - Step evolution
    - Switching between AOMDP and POMDP interaction modes
    """

    def __init__(self, env):
        self.env = env
        self.sim_core = SimulationCore(env)
        self.history = {}



    def reset(self, seed=None, options=None):
        """
        Resets the environment.
        """
        farmgym_observations, farmgym_information = self.sim_core.farmgym_reset(seed, options)

        observations = self.env.action_converter.farmgym_to_gym_observations(farmgym_observations)
        information = farmgym_information
        information["farmgym observations"] = farmgym_observations


        self.history = {}

        # print("RESET",observations,information)
        return (observations, information)

    def step(self, action):
        """
        Performs a step evolution of the system, from current stage to next state given the input action.
        """
        if self.env.interaction_mode == "POMDP":
            # print("POMDP step")
            return self.gym_step_POMDP(action)
        else:  # Assumes it is AOMDP
            return self.gym_step_AOMDP(action)



    def gym_step_POMDP(self, gym_action):
        # Observation step
        _, _, _, _, _ = self.sim_core.farmgym_step([])
        # Intervention step
        farmgym_obs, reward, terminated, truncated, info = self.sim_core.farmgym_step(
            self.env.action_converter.gymaction_to_discretized_farmgymaction(gym_action)
        )

        # Updated state of the farm
        #obs = self.env.state_manager.sim_core.get_free_observations()
        return self.env.action_converter.farmgym_to_gym_observations(farmgym_obs), reward, terminated, truncated, info



    def gym_step_AOMDP(self, gym_action):
        """
        Performs a step evolution of the system, from current stage to next state given the input action.
        It follows the gym signature, and outputs observations, reward, is_done, information.
        Farmgym observations are added in information["farmgym observations"].
        """
        (
            farmgym_observations,
            reward,
            terminated,
            truncated,
            information,
        ) = self.sim_core.farmgym_step(
            # self.gymaction_to_farmgymaction(gym_action)
            self.env.action_converter.gymaction_to_discretized_farmgymaction(gym_action)
        )

        observations = self.env.action_converter.farmgym_to_gym_observations(farmgym_observations)
        #information = farmgym_information
        #information["farmgym observations"] = farmgym_observations

        return observations, reward, terminated, truncated, information