
def render_step(farm, action, observation, reward, terminated, truncated, info):
    # Called after a step.
    s = "Farm:\t" + farm.shortname + "\t"
    if farm.is_new_day:  # Assumes it just switch from False to True
        s += "\tAfternoon phase (interventions)\n"
    else:
        s += "\tMorning phase (observations)\n"
    s += "Actions planned: " + str(action) + "\n"
    for a in farm.gymaction_to_discretized_farmgymaction(action):
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
    return s