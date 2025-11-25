

from agroecogym_engine.rendering.monitoring import MonitorPlt, MonitorTensorBoard

class MonitoringManager:
    """
    Unified manager for farm monitoring utilities.
    Can attach Matplotlib and TensorBoard visualizers.
    """

    def __init__(self, env):
        self.env = env
        self.tensorboard_monitor = None
        self.plt_monitor = None

    # ----------------------------------------------------------------------
    def attach(self, variables, tensorboard=True, matview=True, launch=True):
        """
               Adds a Monitor to the farm, allowing to observe evolution of some state variables with time.
               list_of_variables: the list of variables to be monitored.
               The format for one variable is (field,entity,variable,function,name,option).
               For instance:
               ("Field-0","Plant-0","fruits_per_plant#nb",lambda x: sum_value(x),"Fruits (nb)","range_auto")
               """
        if tensorboard:
            self.monitor = MonitorTensorBoard(
                self, variables, matview=matview, launch=launch
            )
        else:
            self.monitor = MonitorPlt(self, variables)