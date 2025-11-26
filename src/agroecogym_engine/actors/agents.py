class AgroEcoGym_Agent:
    def __init__(self):
        self.farm = None

    def init(self, farm):
        self.farm = farm

    def reset(self, observation):
        pass

    def update(self, action,reward,observation,information):
        pass

    def choose_observation(self):
        raise NotImplementedError


    def choose_intervention(self):
        raise NotImplementedError