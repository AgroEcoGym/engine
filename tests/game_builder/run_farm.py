import os
import time

import numpy as np
from agroecogym_engine.rendering.rendering_utils import generate_video  # generate_gif


def run_gym_xp(farm: object, agent: object, max_steps: object = np.infty, render: object = True, monitoring: object = False) -> object:
    agent.reset(farm)
    observation, information = farm.reset()
    if "text" in render:
        farm.renderer.render_step([], observation, 0, False, False, information)
    if "json" in render:
        farm.renderer.render_json()
    if "image" in render:
        time_tag = time.time()
        os.mkdir("run-" + str(time_tag))
        os.chdir("run-" + str(time_tag))
        farm.render()
    agent.init(observation)

    terminated = False
    i = 0
    while (not terminated) and i <= max_steps:
        action = agent.choose_action()
        obs, reward, terminated, truncated, info = farm.step(action)
        if "text" in render:
            farm.renderer.render_step(action, obs, reward, terminated, truncated, info)
        if "json" in render:
            farm.renderer.render_json()
        if "image" in render:
            farm.render()
        agent.update(obs, reward, terminated, truncated, info)
        i += 1

    if farm.monitor is not None:
        farm.monitor.close()

    if "image" in render:
        farm.render()
        generate_video(image_folder=".", video_name="farm.avi")
        os.chdir("../")
    if "json" in render:
        farm.renderer.export_history_to_json("./")


def run_policy_xp(farm, policy, max_steps=np.infty):
    if farm.monitor is not None:
        farm.monitor = None
    cumreward = 0.0
    cumcost = 0.0
    policy.reset()
    observation = farm.reset()
    terminated = False
    i = 0
    while (not terminated) and i <= max_steps:
        i += 1
        observations = farm.state_manager.sim_core.get_free_observations()
        observation_schedule = policy.observation_schedule(observations)
        observation, _, _, _, info = farm.state_manager.sim_core.farmgym_step(observation_schedule)
        obs_cost = info["observation cost"]
        intervention_schedule = policy.intervention_schedule(observation)
        obs, reward, terminated, truncated, info = farm.state_manager.sim_core.farmgym_step(intervention_schedule)
        int_cost = info["intervention cost"]
        cumreward += reward
        cumcost += obs_cost + int_cost
    return cumreward, cumcost
