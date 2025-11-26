from agroecogym_engine.rendering.image_renderer import make_rendering_image
from agroecogym_engine.rendering.text_renderer import render_step_text
from agroecogym_engine.apis.entity_api import Range
from agroecogym_engine.rendering.rendering_utils import generate_video
import numpy as np

import json
from pathlib import Path
import os
import time
class FarmRenderer:
    """
    Handles the graphical rendering of the farm environment.
    Supports visualizations for debugging, monitoring and user feedback.
    """

    def __init__(self, env,render_mode="human"):
        self.env = env
        self.render_mode= render_mode


    def init(self):
        if self.render_mode == "image":
            if not os.path.isdir("images"):
                os.mkdir("images")

    def close(self):
        if self.render_mode == "text":
            print("End of rendering")
        if self.render_mode == "image":
            self.render()
            generate_video(image_folder="images/", video_name="images/farm.avi")
        if self.render_mode == "json":
            self.export_history_to_json("./")


    def render(self, mode="human"): # This Renders the current STATE of the farm
        """
        Renders the farm at current time for human display as an image. The image is stored as a png file. Not everything is displayed, depending on display availability of each entity of the farm.
        The method considerably slows down the code execution hence should only be called for visualization purpose.
        """
        if self.render_mode == "text":
            self.render_text()
        elif self.render_mode  == "json":
            self.render_json()
        elif self.render_mode == "image":
            self.render_image()

    def render_text(self):
        snapshot = self.state_to_json()
        print("-"*50)
        print(f"STATE at step {self.env.state_manager.sim_core._get_day()}:")
        print("-"*50)
        print(snapshot)
        print("-"*50)


    def render_json(self):
        snapshot = self.state_to_json()
        if self.env.state_manager.sim_core.is_observation_time:
            day = (self.env.state_manager.sim_core._get_year() - 1) * 365 + (
                    self.env.state_manager.sim_core._get_day())
        else:
            day = (self.env.state_manager.sim_core._get_year() - 1) * 365 + (
                    self.env.state_manager.sim_core._get_day() - 1)

        #self.env.state_manager.history[day] = snapshot
        if day not in self.env.state_manager.history:
            self.env.state_manager.history[day] = {"state": snapshot}
        else:
            self.env.state_manager.history[day]["state"] = snapshot
    def render_image(self):
        image = make_rendering_image(self.env)
        day = (int)(
            self.env.fields["Field-0"]
            .entities["Weather-0"]
            .variables["day#int365"]
            .value
        )
        if self.env.interaction_mode == "AOMDP":
            if self.env.state_manager.sim_core.is_observation_time:  # Assumes it just switch from False to True
                image.save("images/farm-day-" + "{:03d}".format(day) + "-2.png")
            else:
                image.save("images/farm-day-" + "{:03d}".format(day) + "-1.png")
        else:
            image.save("farm-day-" + "{:03d}".format(day) + ".png")




    def render_step(self, action, observation, reward, terminated, truncated, info): #This renders an INTERACTION step between agent and environment
        if self.render_mode == "text":
            render_step_text(self.env,action, observation, reward, terminated, truncated, info)
        elif self.render_mode == "json":
            self.render_step_json(self.env,action, observation, reward, terminated, truncated, info)
        elif self.render_mode == "image":
            self.render_step_image(self.env,action, observation, reward, terminated, truncated, info)




    def render_step_json(self,farm,action, observation, reward, terminated, truncated, info):
        snapshot = self.step_to_json(action, observation, reward, terminated, truncated, info)
        #print(f'STEP {day} SNAPSHOT: {snapshot}')
        if self.env.state_manager.sim_core.is_observation_time:
            step = "intervention-step"
            day = (self.env.state_manager.sim_core._get_year()-1)*365+(self.env.state_manager.sim_core._get_day()-1)
        else:
            step = "observation-step"
            day = (self.env.state_manager.sim_core._get_year()-1)*365+(self.env.state_manager.sim_core._get_day())
        if day not in self.env.state_manager.history:
            self.env.state_manager.history[day] = {step: snapshot}
        else:
            self.env.state_manager.history[day][step] = snapshot

    def step_to_json(self,action, observation, reward, terminated, truncated, info):
        snapshot = {}
        snapshot["action"]= {}
        for i in range (len(action)):
            snapshot["action"][int(i)] = int(action[i])
        # snapshot["observation"]={}
        # for i in range (len(observation)):
        #     snapshot["observation"][str(i)] = observation[i]
        snapshot["reward"]=reward
        if ("observation cost") in info.keys():
            snapshot["observation cost"]=info["observation cost"]
        if ("intervention cost") in info.keys():
            snapshot["intervention cost"]=info["intervention cost"]
        return snapshot


    def render_step_image(self,farm,action, observation, reward, terminated, truncated, info):
         ()

    def state_to_json(self):
        """
        Capture a lightweight version of the environment state.
        Only variable values are stored.
        """
        def make_json(x, indent=""):
            s = {}
            if type(x) in [Range]:
                return x.value
            elif isinstance(x, dict):
                for k in x:
                    s[k]=make_json(x[k])
            elif type(x) == np.ndarray:
                it = np.nditer(x, flags=["multi_index", "refs_ok"])
                # s+= str(len(it))+","+str(x.shape) +","+str(len(x.shape))+","+str(len(x))
                s= {}
                if len(x.shape) > 1:
                    while not it.finished:
                        s[str(it.multi_index)] = make_json(it[0])
                        it.iternext()
                elif x.size>1:
                    #print("::",x)
                    for i in range(x.size - 1):
                        s[i] = make_json(x[i])
                else:
                    s=make_json(x.item())
            return s

        snapshot = {}

        for fi in self.env.fields:
            snapshot[fi] = {}
            for e in self.env.fields[fi].entities:
                snapshot[fi][e] = {}
                for v in self.env.fields[fi].entities[e].variables:
                    vari = self.env.fields[fi].entities[e].variables[v]
                    snapshot[fi][e][v] = make_json(vari)

        return snapshot

    def export_history_to_json(self,output_dir):

        out = Path(output_dir)
        (out / "data").mkdir(parents=True, exist_ok=True)

        with open(out / "data" / "state_history.json", "w", encoding="utf-8") as f:
            json.dump(self.env.state_manager.history, f,
            ensure_ascii=False,   # permet d’écrire "°" directement
            indent=2              # optionnel mais plus lisible)
                      )

    def actions_to_string(self):
        nb_actions = self.env.action_space.space.n
        nb_observations = len(self.env.space_builder.farmgym_observation_actions)

        def variable_to_string(var):
            sva = var.split("#")
            ssva = sva[0].split("_")
            tva = ""
            for s in ssva:
                tva += s[0].upper() + s[1:] + " "
            if len(sva) > 1:
                tva += "(" + sva[1] + ")"
            else:
                tva = tva[:-1]
            return tva

        a = self.env.action_converter.gymaction_to_discretized_farmgymaction([])
        s = "-] Do nothing (empty).\n"
        if self.env.interaction_mode == "AOMDP":
            s += "Observation-actions:\n"
            for i in range(nb_observations):
                a = self.env.action_converter.gymaction_to_discretized_farmgymaction([i])
                fa, fi, e, a, p = a[0]
                sp = " with parameters " + str(p) if p != [] else ""
                s += (
                        str(i)
                        + "] Farmer "
                        + str(fa)
                        + " observes"
                        + " variable '"
                        + variable_to_string(str(a))
                        + "'"
                        + sp
                        + " on "
                        + str(e)
                        + " in "
                        + str(fi)
                        + ".\n"
                )

            s += "Intervention-actions:\n"
        for i in range(nb_observations, nb_actions):
            a = self.env.action_converter.gymaction_to_discretized_farmgymaction([i])
            fa, fi, e, a, p = a[0]
            sp = " with parameters " + str(p) if p != {} else ""
            s += (
                    str(i)
                    + "] Farmer "
                    + str(fa)
                    + " performs"
                    + " intervention "
                    + str(a)
                    + sp
                    + " on "
                    + str(e)
                    + " in "
                    + str(fi)
                    + ".\n"
            )

        return s

    #
    # def export_html_viewer(self, output_dir, viewer_template_path="viewer_template.html"):
    #     """
    #     Export an interactive HTML viewer for a Farm-Gym environment.
    #
    #     Parameters
    #     ----------
    #     env : the farm gym environment *after running a full episode*
    #           must expose env.fields, each having entities and variables.
    #     output_dir : str or Path where to generate the viewer directory.
    #     viewer_template_path : file path to the HTML template.
    #     """
    #
    #     out = Path(output_dir)
    #     (out / "data").mkdir(parents=True, exist_ok=True)
    #     (out / "frames").mkdir(parents=True, exist_ok=True)
    #
    #     self.export_history_to_json(output_dir)
    #
    #
    #     # ------------------------------
    #     # 2. Export images for each field/entity
    #     # ------------------------------
    #     # We will create ONE rendering per day by stacking field/entity images.
    #     image_names = []
    #
    #     for day, snapshot in enumerate(self.env.history):
    #         # Compose a render for this day:
    #         # each entity renders its own PIL image,
    #         # you can composite them if needed.
    #         first_field = snapshot.fields[0]
    #
    #         # Create canvas from first entity as base
    #         base = None
    #         for entity in first_field.entities.values():
    #             img = entity.to_fieldimage()
    #
    #             if base is None:
    #                 base = img.copy()
    #             else:
    #                 base.alpha_composite(img)
    #
    #         name = f"render_day_{day:03d}.png"
    #         base.save(out / "frames" / name)
    #         image_names.append(name)
    #
    #     # ------------------------------
    #     # 3. Save meta info
    #     # ------------------------------
    #     meta = {
    #         "images": image_names
    #     }
    #
    #     with open(out / "data" / "fields.json", "w") as f:
    #         json.dump(meta, f)
    #
    #     # ------------------------------
    #     # 4. Copy viewer template → index.html
    #     # ------------------------------
    #     html = Path(viewer_template_path).read_text()
    #     (out / "index.html").write_text(html)
    #
    #     print(f"Interactive viewer exported to: {out / 'index.html'}")