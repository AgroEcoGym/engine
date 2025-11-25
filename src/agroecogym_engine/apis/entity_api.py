
import numpy as np
from gymnasium.spaces import Box, Discrete
from PIL import Image

from agroecogym_engine.specifications.specification_manager import load_yaml
import numbers

class Range:
    def __init__(self, range, value):
        self.default_value = value
        self.range = range
        if type(range) == tuple:
            self.min, self.max = range
            self.value = max(self.min, min(self.max, value))
        else:
            if value in self.range:
                self.value = value
            else:
                if len(self.range) > 0:
                    self.value = self.range[0]
                else:
                    self.value = None

    def set_value(self, value):
        if (type(self.range) == tuple):
            if (isinstance(value, numbers.Real)):
                self.value = max(self.min, min(self.max, value))
            else: self.value = self.default_value
        elif value in self.range:
            self.value = value

    def get_default_value(self):
        return self.default_value

    def random_value(self, np_random=np.random):
        if type(self.range) == tuple:
            m, M = self.range
            return m + np_random.random() * (M - m)
        else:
            if len(self.range) > 0:
                return np_random.choice(list(self.range))
            return None

    def to_gym_space(self):
        if type(self.range) == tuple:
            m, M = self.range
            return Box(
                low=np.array([np.float32(m)]),
                high=np.array([np.float32(M)]),
                dtype=np.float32,
            )
        else:
            return Discrete(len(self.range))

    def gym_value(self):
        if type(self.range) == tuple:
            # TODO: should be [self.value] for observation to be part of observation space, but creates spurious [][] elsewhere !
            return [self.value]
        else:
            return self.range.index(self.value)

    def __str__(self):
        s = "(range: "
        if type(self.range) == tuple:
            m, M = self.range
            s += str(m) + ", " + str(M)
        else:
            s += str(list(self.range))
        s += "; value: "
        s += str(self.value) + ")"
        return s

    def __repr__(self):
        s = "(range: "
        if type(self.range) == tuple:
            m, M = self.range
            s += str(m) + ", " + str(M)
        else:
            s += str(list(self.range))
        s += "; value: "
        s += str(self.value) + ")"
        return s


def fillarray(x, y, myrange, value):
    ar = np.empty((x, y), dtype=Range)
    for xx in range(x):
        for yy in range(y):
            ar[xx, yy] = Range(myrange, value)
    return ar


class Entity_API:
    """
    class for entity defini
    tion

    Naming conventions:
    For variables and parameter names, please use "name_of_the_variable#name_of_the_unit" or "name_of_the_parameter#name_of_the_unit" in case there is a unit.
    """

    def __init__(self, field, parameters):
        self.name = "Entity"
        self.field = field

        if isinstance(parameters, str):
            # self.parameters = load_yaml(
            #     (self.__class__.__name__).lower() + "_specifications.yaml", parameters
            # )
            self.parameters = load_yaml(
                (self.__class__.__name__) + "/"+parameters+".yaml"
            )
        else:
            self.parameters = parameters
            for k in self.get_parameter_keys():
                assert k in self.parameters.keys(), "Parameter " + k + " not specified."

        self.variables = {}  # key:   this  {'range': range, 'value': value } or array of this or dict of variables.

        self.actions = {}  # key:  params, where params is Dict of "key: range", where range is either (m,M), or list (e.g. integer).

        self.dependencies = {}  # List of other entities on which the entity depends.

        self.load_images()

        self.set_random()

        self.initial_conditions = {}

    def set_random(self, np_random=np.random):
        self.np_random = np_random

    def reset(self):
        pass


    def initialize_variables(self, values):
        def set_var(var, value):
            if isinstance(var, dict):
                for k in var:
                    if (type(var[k]) in [dict, np.ndarray]) and k in value.keys():
                        set_var(var[k], value[k])
                    else:
                        if k in value.keys():
                            if type(value[k]) == tuple:
                                m, M = value[k]
                                var[k].set_value(m + self.np_random.random() * (M - m))
                            elif isinstance(value[k], list):
                                var[k].set_value(self.np_random.choice(list(value[k])))
                            else:
                                var[k].set_value(value[k])
            elif type(var) == np.ndarray:
                if type(value) == tuple:
                    m, M = value
                    it = np.nditer(var, flags=["multi_index", "refs_ok"])
                    for x in it:
                        var[it.multi_index].set_value(
                            m + self.np_random.random() * (M - m)
                        )
                elif isinstance(value, list):
                    it = np.nditer(var, flags=["multi_index", "refs_ok"])
                    for x in it:
                        var[it.multi_index].set_value(
                            self.np_random.choice(list(value))
                        )
                else:
                    it = np.nditer(var, flags=["multi_index", "refs_ok"])
                    for x in it:
                        var[it.multi_index].set_value(value)

        # print("SET_VAR:",self.variables,values)
        set_var(self.variables, values)

    def get_parameter_keys(self):
        return []

    def update_variables(self, field, entities: dict):
        # Choice: When an entity update is linked to another entity update, one may ask which of the recevier or emitter should triger the action. Choice: Receiver always triggers action, Emitter never triggers it.

        pass

    def assert_action(self, action_name, action_params):
        assert action_name in self.actions
        for p in action_params:
            #print("is action",p,"in",self.actions[action_name].keys())
            assert p in self.actions[action_name].keys()
            if type(self.actions[action_name][p]) is tuple:
                # print("ASSERT",action_name, self.actions[action_name], self.actions[action_name][p][0])
                assert (
                    self.actions[action_name][p][0]
                    <= action_params[p]
                    <= self.actions[action_name][p][1]
                ), (
                    "Action value "
                    + str(action_params[p])
                    + " for key "
                    + p
                    + " not in range ["
                    + str(self.actions[action_name][p][0])
                    + ", "
                    + str(self.actions[action_name][p][1])
                    + "]!"
                )
            else:
                # print("ASSERT", action_name, self.actions[action_name], action_params, action_params[p], self.actions[action_name][p])
                if p == "plot":
                    assert str(action_params[p]) in self.actions[action_name][p], (
                        "PLOT"
                        + str(action_params[p])
                        + " not in "
                        + str(self.actions[action_name][p])
                    )
                else:
                    assert action_params[p] in self.actions[action_name][p], (
                        str(action_params[p])
                        + " not in "
                        + str(self.actions[action_name][p])
                    )

    def observe_variable(self, variable_key, path):
        # print("OBSERVE_VARIABLE:",variable_key,path)
        def make_obs(x):
            if type(x) == Range:
                return x.value  # x.gym_value()
            elif isinstance(x, dict):
                ob = {}
                for k in x.keys():
                    ob[k] = make_obs(x[k])
                return ob
            elif type(x) == np.ndarray:
                ob = []
                for xx in x:
                    ob.append(make_obs(xx))
                return ob
            else:
                return x

        obs = self.variables[variable_key]
        for p in path:
            obs = obs[p]
        return make_obs(obs)

    def gym_observe_variable(self, variable_key, path):
        # print("OBSERVE_VARIABLE:",variable_key,path)
        def make_obs(x):
            # print("OBSERVE_VARIABLE:", x)
            if type(x) == Range:
                # TODO : change to [...] ?
                return x.gym_value()
            elif isinstance(x, dict):
                ob = {}
                for k in x.keys():
                    ob[k] = make_obs(x[k])
                return ob
            elif type(x) == np.ndarray:
                # print("OBS VARIABLE", x, " is array")
                ob = []
                for xx in x:
                    ob.append(make_obs(xx))
                return ob
            else:
                # print("OBS VARIABLE", x)
                return x

        obs = self.variables[variable_key]
        for p in path:
            obs = obs[p]
        return make_obs(obs)

    def act_on_variables(self, action_name, action_params) -> None:
        return None

    def load_images(self):
        import os
        from pathlib import Path

        file_path = Path(os.path.realpath(__file__))
        CURRENT_DIR = file_path.parent.parent
        self.images = {}
        if "sprites" in self.parameters:
            for key in self.parameters["sprites"]:
                self.images[key] = Image.open(
                    CURRENT_DIR
                    / ("rendering/sprites/" + self.parameters["sprites"][key])
                )

    def to_fieldimage(self):
        im_width, im_height = 64, 64
        image = Image.new(
            "RGBA",
            (im_width * self.field.X, im_height * self.field.Y),
            (255, 255, 255, 0),
        )
        return image

    def to_thumbnailimage(self):
        im_width, im_height = 64, 64
        image = Image.new("RGBA", (im_width, im_height), (255, 255, 255, 0))  # noqa: F841
        return None

    def __str__(self):
        def make(x, indent=""):
            s = ""
            if isinstance(x, dict):
                s += "\n"
                for k in x:
                    s += indent + ("  " + k + ": ")
                    s += make(x[k], indent=indent + "  ")
            elif type(x) == np.ndarray:
                it = np.nditer(x, flags=["multi_index", "refs_ok"])
                s += "["
                for xx in it:
                    s += str(x[it.multi_index]) + ","
                s = s[:-1]
                s += "]\n"
            elif type(x) in [Range]:
                s += str(x) + "\n"
            else: # This is not an array, not a Range, so it must be Null.
                s += "???\n"
            return s

        s = self.name + ":"
        s += make(self.variables, "")
        return s






if __name__ == "__main__":
    ()