import numpy as np

class Farmgym_Agent:
    def __init__(self):
        self.farm = None

    def reset(self, observation):
        ()

    def init(self, farm):
        self.farm = farm

    def update(self, action,reward,observation,info):
        pass

    def choose_observation(self):
        raise NotImplementedError


    def choose_intervention(self):
        raise NotImplementedError


class Farmgym_RandomAgent(Farmgym_Agent):
    def __init__(self, mode="POMDP"):
        super(Farmgym_RandomAgent, self).__init__()
        self.x = 1
        self.mode = mode

    def get_harvest_index(self, n_obs, n_act):
        for i in range(n_obs, n_act):
            a = self.farm.action_converter.gymaction_to_discretized_farmgymaction([i])
            fa, fi, e, a, p = a[0]
            if a == "harvest":
                return [i]
        return []

    def choose_action(self):
        # if self.mode == "POMDP":
        self.x += 0.25
        threshold = 10 / self.x
        if np.random.rand() > threshold:
            obs_actions_len = len(self.farm.space_builder.farmgym_observation_actions)
            action = self.get_harvest_index(
                obs_actions_len, self.farm.action_space.space.n
            )
            return action
        return self.farm.action_space.sample()


    def choose_intervention(self):
        return self.choose_action()

    def choose_observation(self):
        return self.choose_action()


class Farmgym_PolicyAgent(Farmgym_Agent):
    def __init__(self, policy):
        super(Farmgym_PolicyAgent, self).__init__()
        self.policy = policy
        self.observation = []

    def update(self, obs, reward, terminated, truncated, info):
        self.observation = obs
    def choose_action(self):
        if (self.farm.is_observation_time):
            schedule= self.policy.observation_schedule(self.observation)
        else:
            schedule= self.policy.intervention_schedule(self.observation)
        print("AGENT:", schedule) #TODO: Convert from FarmGym [('BasicFarmer-0', 'Field-0', 'Plant-0', 'stage', [(0, 0)]),..]  to Gym [4,...]
        return schedule


class Farmgym_TriggeredPolicyAgent(Farmgym_Agent):
    def __init__(self, triggeredpolicy):
        super(Farmgym_PolicyAgent, self).__init__()
        self.policy = triggeredpolicy
        self.observation = []

    def update(self, obs, reward, terminated, truncated, info):
        self.policy.update()
        self.observation = obs
    def choose_action(self):
        obs_schedule,int_schedule= self.policy.action(self.observation)
        if (self.farm.is_observation_time):
            schedule= obs_schedule
        else:
            schedule= int_schedule
        print("AGENT:", schedule) #TODO: Convert from FarmGym [('BasicFarmer-0', 'Field-0', 'Plant-0', 'stage', [(0, 0)]),..]  to Gym [4,...]
        return schedule