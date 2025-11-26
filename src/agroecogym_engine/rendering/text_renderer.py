
def render_step_text(farm, action, observation, reward, terminated, truncated, info):
    # Called after a step.
    s = "Farm:\t" + farm.shortname + "\t"
    if farm.state_manager.sim_core.is_observation_time:  # Assumes it just switch from False to True
    #if farm.state_manager.sim_core.is_new_day:  # Assumes it just switch from False to True
        s += "\nPhase II: Intervention\n"
    else:
        s += "\nPhase I: Observation\n"
    s += "Actions planned: " + str(action) + "\n"
    #for a in farm.action_converter.gymaction_to_discretized_farmgymaction(action):
    for a in farm.action_converter.gymaction_to_discretized_farmgymaction(action):
        s += "\t- " + str(a) + "\n"
    s += "Observations received:\n"
    for o in observation:
        s += "\t- " + str(o) + "\n"
    s += "Reward received: " + str(reward) + "\n"
    s += "Information:\n"
    for i in info:
        s += "\t- " + str(i) + ": " + str(info[i]) + "\n"
    if terminated:
        s += "Terminated.\n"
    if truncated:
        s += "Truncated.\n"
    print(s)


