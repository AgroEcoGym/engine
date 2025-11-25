


from  agroecogym_engine.core.config.build_yamls import (  # noqa: E402
    build_actionsyaml,
    build_inityaml,
    build_scoreyaml,
)


class SetupManager:
    """Handles creation and validation of YAML configuration files (score, init, actions)."""

    def __init__(self, env):
        self.env = env

    def ensure_configurations(self, base_path):
        self._setup_score_configuration(base_path)
        self._setup_initial_configuration(base_path)
        self._setup_action_configuration(base_path)
        self.env.scoring.setup(self.env)
        self.env.rules.setup(self.env)

    def _setup_score_configuration(self, farmpath):
        scoring = self.env.scoring
        if scoring.score_configuration is None:
            path = f"{farmpath}_score_vanilla.yaml"
            print("[Farmgym Warning] Missing score configuration file.")
            build_scoreyaml(path, self.env)
            scoring.score_configuration = path
            print(
                "[Solution]"
                + " Vanilla score configuration file automatically generated in "
                + str(path)
                + " and used instead. Please, open and modify as wanted."
            )
        else:
            try:
                open(scoring.score_configuration, "r", encoding="utf8")
            except FileNotFoundError as err:
                print("[Farmgym Warning] Missing score configuration file.")
                build_scoreyaml(scoring.score_configuration, self.env)
                print(
                    "[Solution]"
                    + " Vanilla score configuration file automatically generated in "
                    + str(scoring.score_configuration)
                    + " and used instead. Please, open and modify as wanted."
                )

    def _setup_initial_configuration(self,farmpath):
        rules = self.env.rules
        # TODO : Double check the behavior when empty init file, or nor empty with or without init_values as parameter.
        if rules.init_configuration is None:
            print("[Farmgym Warning] Missing initial conditions configuration file.")
            path = f"{farmpath}_init_vanilla.yaml"
            build_inityaml(
                path,
                self,
                mode="default",
                init_values=rules.initial_conditions_values,
            )
            rules.init_configuration = path
            print(
                "[Solution]"
                + " Vanilla initial conditions configuration file automatically generated in "
                + str(path)
                + " and used instead. Please, open and modify as wanted. Deleting a line corresponding to a state variable makes it initialized at default value."
            )
        else:
            try:
                open(rules.init_configuration, "r", encoding="utf8")
            except FileNotFoundError as err:
                print(
                    "[Farmgym Warning] Missing initial conditions configuration file."
                )
                build_inityaml(
                    rules.init_configuration,
                    self.env,
                    mode="default",
                    init_values=None,  # self.rules.initial_conditions_values,
                )
                # print('INIT VALUE', self.rules.initial_conditions_values)
                print(
                    "[Solution]"
                    + "  Vanilla initial conditions configuration file automatically generated in "
                    + str(rules.init_configuration)
                    + " and used instead. Please, open and modify as wanted. Deleting a line corresponding to a state variable makes it initialized at default value."
                )


    def _setup_action_configuration(self,farmpath):
        rules = self.env.rules
        if rules.actions_configuration is None:
            path = f"{farmpath}_actions_vanilla.yaml"
            print("[Farmgym Warning] Missing actions configuration file.")
            build_actionsyaml(path, self.env)
            rules.actions_configuration = path
            print(
                "[Solution]"
                + " Vanilla action configuration file automatically generated in "
                + str(path)
                + " and used instead. Please, open and remove any line corresponding to an unwanted action."
            )
        else:
            try:
                open(rules.actions_configuration, "r", encoding="utf8")
            except FileNotFoundError as err:
                print("[Farmgym Warning] Missing actions configuration file.")
                build_actionsyaml(rules.actions_configuration, self.env)
                print(
                    "[Solution]"
                    + " Vanilla action configuration file automatically generated in "
                    + str(rules.actions_configuration)
                    + " and used instead. Please, open and remove any line corresponding to an unwanted action."
                )
