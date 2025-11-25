

def run_AOMDP(farm,agent):

    observation, info = farm.reset() # Receives free observations
    agent.reset(observation)

    episode_over = False
    total_reward = 0

    while not episode_over:
        # Observation time:
        observation_action = agent.choose_observation()
        observation, reward, terminated, truncated, info = farm.step(observation_action) # Receives requested observations
        agent.update(observation_action,reward,observation)

        #Intervention time:
        intervention_action = agent.choose_intervention()
        observation, reward, terminated, truncated, info = farm.step(intervention_action) # Receives next free observations
        agent.update(intervention_action,reward,observation)

        total_reward += reward
        episode_over = terminated or truncated

    print(f"Episode finished! Total reward: {total_reward}")
    farm.close()


def run_POMDP(farm,agent):

    observation, info = farm.reset()
    agent.reset(observation)

    episode_over = False
    total_reward = 0

    while not episode_over:
        #Intervention time:
        intervention_action = agent.choose_intervention()
        observation, reward, terminated, truncated, info = farm.step(intervention_action)
        agent.update(intervention_action,reward,observation)

        total_reward += reward
        episode_over = terminated or truncated

    print(f"Episode finished! Total reward: {total_reward}")
    farm.close()


def run_policy_xp(farm, triggeredpolicy, max_steps=10000, show_actions=False):
    #    if farm.monitor is not None:
    #        farm.monitor = None
    cumreward = 0.0
    cumcost = 0.0
    triggeredpolicy.reset()
    observation = farm.reset()
    terminated = False
    i = 0
    while (not terminated) and i <= max_steps:
        i += 1
        observations = farm.state_manager.sim_core.get_free_observations()
        observation_schedule,_ = triggeredpolicy.action_schedule(observations)
        if show_actions:
            print(f"Day = {i}, Observation-actions : {observation_schedule}")
        observation, _, _, _, info = farm.state_manager.sim_core.farmgym_step(observation_schedule)
        obs_cost = info["observation cost"]
        _,intervention_schedule = triggeredpolicy.action_schedule(observation)
        if show_actions:
            print(f"Day = {i}, Intervention-actions : {intervention_schedule}")
        obs, reward, terminated, truncated, info = farm.state_manager.sim_core.farmgym_step(intervention_schedule)
        #SO: Here obs is never used? Is this what we want???
        triggeredpolicy.update()
        int_cost = info["intervention cost"]
        cumreward += reward
        cumcost += obs_cost + int_cost
    return cumreward, cumcost
