import numpy as np

from agroecogym_engine.apis.entity_api import Entity_API, Range, fillarray
from agroecogym_engine.utils.python import checkissubclass

class Plant2(Entity_API):
    def __init__(self, field, parameters):
        Entity_API.__init__(self, field, parameters)
        X = self.field.X
        Y = self.field.Y

        self.stages = ["none"] + self.parameters["stages"].keys()

        self.variables = {}
        self.variables["stage"] = fillarray(X, Y, self.stages, "none")
        self.variables["population#nb"] = fillarray(X, Y, (0, 10000), 0.0)
        self.variables["age#day"] = fillarray(X, Y, (0, 10000), 0.0)
        self.variables["effective_stage_duration#day"] = fillarray(X, Y, self.stages,0)

        self.variables["stem_height#cm"] = fillarray(X, Y, (0, 1000), 0.0)
        self.variables["crown_radius#cm"] = fillarray(X, Y, (0, 1000), 0.0)
        self.variables["leaf_area#m2"] = fillarray(X, Y, (0, 1000), 0.0)
        self.variables["root_depth#cm"] = fillarray(X, Y, (0, 1000), 0.0)
        self.variables["root_radius#cm"] = fillarray(X, Y, (0, 1000), 0.0)

        self.variables["dry_weight#g"] = fillarray(X, Y, (0, 1000), 0.0)
        self.variables["water#L"] = fillarray(X, Y, (0, 1000), 0.0)

        self.variables["fruit#kg"] = fillarray(X, Y, (0, 1000), 0.0)
        self.variables["root#kg"] = fillarray(X, Y, (0, 1000), 0.0)

        self.variables["flower#nb"] = fillarray(X, Y, (0, 1000), 0.0)
        self.variables["fruit#nb"] = fillarray(X, Y, (0, 1000), 0.0)


        # Nutrient/water inputs/outputs:
        self.variables["today_C_requested#g"] = fillarray(X, Y, (0, 1000), 0.0)
        self.variables["today_N_requested#g"] = fillarray(X, Y, (0, 1000), 0.0)
        self.variables["today_P_requested#g"] = fillarray(X, Y, (0, 1000), 0.0)
        self.variables["today_H2O_requested#g"] = fillarray(X, Y, (0, 1000), 0.0)

        self.variables["today_C_received_to_be_absorbed#g"] = fillarray(X, Y, (0, 1000), 0.0)
        self.variables["today_N_received_to_be_absorbed#g"] = fillarray(X, Y, (0, 1000), 0.0)
        self.variables["today_P_received_to_be_absorbed#g"] = fillarray(X, Y, (0, 1000), 0.0)
        self.variables["today_H2O_received_to_be_absorbed#g"] = fillarray(X, Y, (0, 1000), 0.0)

        #Total accumulated stress during the lifespan of the plant: (possibly discounted with time).
        self.variables["cumulative_stress_C#g"] = fillarray(X, Y, (0, 1000), 0.0)
        self.variables["cumulative_stress_N#g"] = fillarray(X, Y, (0, 1000), 0.0)
        self.variables["cumulative_stress_P#g"] = fillarray(X, Y, (0, 1000), 0.0)
        self.variables["cumulative_stress_H20#g"] = fillarray(X, Y, (0, 1000), 0.0)


        # Actions
        self.actions = {
            "sow": {
                "plot": field.plots,
                "density#seed.m-2": [1, 5, 10, 20, 50, 100]
            },
            "global_harvest": {},
            "plot_harvest": {"plot": field.plots},
            "remove": {"plot": field.plots},
        }

        # Dependencies
        self.dependencies = {"Weather", "Soil", "Birds", "Pests", "Pollinators"}

        # Methods:
        '''
        The plants works as follows:
        1] The plant observes its local conditions (weather, light, etc).
        2] From this, it determines by how much it wants to grow, that is how much dw and water it requires.
        3] The method self.requested_nutrients(location) outputs this amount converted in nutrients, and can be asked by the soil, other plants, fungi, etc.
        4] There is a buffer of variables for each nutrient and water: this is filled by all external entities giving resources to the plant (mostly soil).
        5] The self.update() method performs the dynamics: the plant looks at the available received  nutrients,
        and grows by the corresponding amount. This amount can be smaller than what was requested (it could be higher, but this is rare since C is usually obtained by air), 
        generating stress.
        
        '''

    def get_parameter_keys(self):
        return [
            "morphology",
            "composition",
            "biotic",
            "fixation",
            "stages"
        ]

    def requirement_nutrients(self, position, entities):
        o_entities = self._get_other_entities(entities)

        photonmol=   o_entities["weather"].variables["daily_photosynthetic_light_integral#mol.m-2.day-1"]*self._leaf_area_noselfshadow(position)

        # This is converted in C by the plant:
        C_efficiency=0.09 # in mol.mol-1, typically 0.07-0.09 but depends on stress of the plant.
        C_gpermol=12 #constant
        Cmax_g = photonmol*C_gpermol*C_efficiency
        #Reduce according to deviation to optimal conditions (stress):
        stage = self.variables["stage"][position].value
        q = self._get_stage_condition_ranges(o_entities, self.parameters["stages"][stage]["optimal_range"])
        day_eff = self._compute_effective_day(q)

        Ceff_g = Cmax_g*day_eff

        #Deduce DW request hence N,P,K request.
        Dweff_g = self.parameters["composition"]["carbon_dryweight_fraction#g.g-1"]*Ceff_g

        n_fraction = sum(self.parameters["composition"]["nitrogen_dryweight_fraction#g.g-1"])
        Neff_g= Dweff_g*n_fraction

        self.variables["today_C_requested#g"].setvalue(Ceff_g)
        self.variables["today_N_requested#g"].setvalue(Neff_g)

        return {"Dw":Dweff_g,"C#g":Ceff_g, "N#g":Neff_g}

    def requirement_water(self, position, weather, field):
        evaw = (
                weather.evaporation(field)  # Evaporation in mL.m-2.day-1
                * self._leaf_area_noselfshadow(position)
        )
        #+w to sustain drymass:

        #+w do sustain drymass increase:

    def _leaf_area_noselfshadow(self,position):
        '''
        :param position:
        :return:  effective leaf_area#m2 that is not covered by the self-shadow of the plant.
        '''
        self_undercanope=0.5 #assumes about half of leaves are not under self-shadow of any other leaves, on average during the day.
        return self.variables["leaf_area#m2"][position].value* (1.-self.parameters["morphology"]["shading_factor#%1"]*self_undercanope)

    def receive_nutrients(self, position, nutrients, stress):
        ()

    def receive_water(self, position, water, stress):
        ()


    def _get_other_entities(self,entities):
        weather = [
            entities[e]
            for e in entities
            if checkissubclass(entities[e].__class__, "Weather")
        ][0]
        soil = [
            entities[e]
            for e in entities
            if checkissubclass(entities[e].__class__, "Soil")
        ][0]
        birds = [
            entities[e]
            for e in entities
            if checkissubclass(entities[e].__class__, "Birds")
        ]
        # nb_birds_eating_seeds = np.sum(
        #     [
        #         b.variables["population#nb"].value
        #         for b in birds
        #         if b.parameters["seed_eater"]
        #     ]
        # )
        pests = [
            entities[e]
            for e in entities
            if checkissubclass(entities[e].__class__, "Pests")
        ]
        pollinators = [
            entities[e]
            for e in entities
            if checkissubclass(entities[e].__class__, "Pollinators")
        ]
        return {"weather":weather,"soil":soil,"birds":birds,"pests":pests,"pollinators":pollinators}


    def _range_response(self,value,vmin,vmax,vopt):
        if (value<vmin) or (value>vmax):
            return 0
        if (vopt==vmax):
            vmax+=1e-10
        if (vopt==vmin):
            vmin-=1e-10
        alpha = (vopt - vmin) / (vmax - vmin)
        beta = (vmax - vopt) / (vmax - vmin)
        r = (((value - vmin) / (vopt - vmin)) ** alpha) * (((vmax - value) / (vmax - vopt)) ** beta)
        return r

    def _compute_effective_day(self,q):
        n_eff=1
        for _val,_range in q:
            m,M,opt=_range
            n_eff = min(n_eff,self._range_response(_val,m,M,opt))
        return n_eff

    def compute_maxdw_growth(self,soil,params_compo):
        '''
        Computes the maximal dryweight that the plant can gain considering soil nutrients limitations.
        TODO: should consider light contribution !
        '''


        max_dw_C= soil.variables["available_C#g"]/ params_compo["carbon_dryweight_fraction#g.g-1"]
        #TODO: However, plant mostly receives C from air !

        max_dw_N_fruit= soil.variables["available_N#g"]/ params_compo["nitrogen_dryweight_fraction#g.g-1"]["fruit"]
        max_dw_N_leaf= soil.variables["available_N#g"]/ params_compo["nitrogen_dryweight_fraction#g.g-1"]["leaf"]
        max_dw_N_root= soil.variables["available_N#g"]/ params_compo["nitrogen_dryweight_fraction#g.g-1"]["root"]
        max_dw_N_stem= soil.variables["available_N#g"]/ params_compo["nitrogen_dryweight_fraction#g.g-1"]["stem"]
        max_dw_N=min(max_dw_N_fruit,max_dw_N_stem,max_dw_N_root,max_dw_N_leaf)
        #TODO: However, plant can receive N from other sources too.

        #x/(x+w)=y hence x=w/(1/y-1)
        max_dw_W_fruit= soil.variables["available_Water#L"]/(1/params_compo["dry_matter_fraction#%"]["fruit"]-1)
        max_dw_W_leaf= soil.variables["available_Water#L"]/(1/params_compo["dry_matter_fraction#%"]["leaf"]-1)
        max_dw_W_root= soil.variables["available_Water#L"]/(1/params_compo["dry_matter_fraction#%"]["root"]-1)
        max_dw_W_stem= soil.variables["available_Water#L"]/(1/params_compo["dry_matter_fraction#%"]["stem"]-1)
        max_dw_W= min(max_dw_W_stem,max_dw_W_root,max_dw_W_fruit,max_dw_W_leaf)

        max_dw=min(max_dw_C,max_dw_N,max_dw_W)
        return max_dw

    def increment_cost(self,delta_dw,organ,params):
        #dw = delta_area_cm2 / params["leaf_area_per_dryweight#cm2.g-1"]  # g DW
        dw=delta_dw
        n = params["nitrogen_dryweight_fraction#g.g-1"][organ] * dw
        c = params["carbon_dryweight_fraction#g.g-1"] * dw
        water = (1 / params["dry_matter_fraction#%"][organ] - 1) * dw
        return {"N#g": n, "C#g": c, "H2O#g": water}

    # def nitrogen_fixation(self,root_dw_g, photosynthetic_dli):
    #     """Simple model: fixation ∝ root DW × DLI, capped by n_fixation_max"""
    #     potential = root_dw_g * params["n_fixation_max"]
    #     return potential * params["n_fixation_efficiency"] * (photosynthetic_dli / (photosynthetic_dli + 10.0))

    def _update_growth(self,x,y,effective_day, entities, stage_params):
        dw_max=self.compute_maxdw_growth(entities["soil"],self.parameters["composition"])

        # plant only grow proportionally to optimal condition:
        dw_max *=effective_day

        # Nutrients consumption for effective growth:
        n=0
        c=0
        w=0
        for organ in ["leaf","stem","root","fruit"]:
            cost = self.increment_cost(dw_max,organ, self.parameters["composition"])
            n+=cost["N#g"]  #from soil+air
            c+=cost["C#g"]  #from air mostly
            w+=cost["H20#g"] #from soil

        # Plant storage: water and drymass
        self.variables["water#L"].set_value(self.variables["water#L"].value+w/1000)
        self.variables["dry_weight#g"].set_value(self.variables["dry_weight#g"]+dw_max)

        #Update other variables deduced from water and dry_weight:
        self._update_morpho_variables_growth(stage_params,dw_max,w)
        return {"N#g": n, "C#g": c, "H2O#g": w} # from different sources (soil, air, etc): How to spearate them?

    def _update_morpho_variables_growth(self,stage_params,delta_dw,delta_w):
        delta_stem=delta_dw*stage_params["dry_growth_allocation#%"]["stem"]*self.parameters["morphology"]["stem_height_per_dryweight#cm.g-1"]
        self.variables["stem_height#cm"].set_value(self.variables["stem_height#cm"].value+delta_stem)
        delta_leaf=delta_dw*stage_params["dry_growth_allocation#%"]["leaf"]*self.parameters["morphology"]["leaf_area_per_dryweight#cm2.g-1"]
        self.variables["leaf_area#m2"].set_value(self.variables["leaf_area#m2"].value+delta_leaf)

        # TODO: Seomthing wrong here:
        delta_root=(delta_dw*stage_params["dry_growth_allocation#%"]["root"]+delta_w)*self.parameters["composition"]["dry_matter_fraction#%"]["root"]/1000
        self.variables["root#kg"].set_value(self.variables["root#kg"].value+delta_root)
        delta_fruit=(delta_dw*stage_params["dry_growth_allocation#%"]["fruit"]+delta_w)*self.parameters["composition"]["dry_matter_fraction#%"]["fruit"]/1000
        self.variables["fruit#kg"].set_value(self.variables["fruit#kg"]+delta_fruit)

    def _update_decay(self,x,y,o_entities,p_decay):
        '''
        Removes drymass from each organ and update their size accordingly. TODO:  This should return on the soil, but not yet in the soil !
        '''
        for organ,org,conv in [("stem#cm","stem",self.parameters["morphology"]["stem_height_per_dryweight#cm.g-1"]),
                           ("leaf#m2","leaf",self.parameters["morphology"]["leaf_area_per_dryweight#cm2.g-1"]),
                           ("root#kg","root",self.parameters["composition"]["dry_matter_fraction#%"]["root"]/1000),
                           ("fruit#kg","fruit",self.parameters["composition"]["dry_matter_fraction#%"]["fruit"]/1000)]:
            dw_organ = self.variables[organ]/conv
            delta_organ = (dw_organ*(1-p_decay[org]/100)) * conv

            self.variables[organ].set_value(self.variables[organ].value - delta_organ)
            #o_entities["soil"].put_on(x,y, bla) ?


    def _get_stage_condition_ranges(self,o_entities,stage_opt_parameters):
        # Retrieve optimal range of variables
        q = []
        for enti, vari in stage_opt_parameters:
            enti_var = o_entities[enti]
            varies = vari.split("|")  # e.g. air_temperature|mean#°C, hence weather["air_temperature"]["mean#°C"]
            for v in varies:
                enti_var = enti_var[v]
            val = enti_var.value
            range_val = stage_opt_parameters[enti, vari]
            q.append((val, range_val))
        return q

    def update_variables(self, field, entities):
        '''
        The update is done after the soil update: the soil already asked the plant how much nutrients it requires, and gave it a possibly different amount.
        Now the plant indeed grows
        :param field:
        :param entities:
        :return: update the dynamics of the plant, transiting from stages to stages.
        '''
        o_entities = self._get_other_entities(entities)
        for x in range(self.field.X):
            for y in range(self.field.Y):
                if self.variables["population#nb"][x, y].value > 0:
                    stage=self.variables["stage"][x, y].value
                    p=self.parameters["stages"][stage]

                    q = self._get_stage_condition_ranges(o_entities,p["optimal_range"])
                    # Retrieve range from nutrients and water request:
                    for nutr in ['C','N','P','H20']:
                        nutr_request= self.variables["today_"+nutr+"_requested#g"][x, y].value # the value requested
                        nutr_val = self.variables["today_"+nutr+"_received_to_be_absorbed#g"][x, y].value # the value actually received
                        range_val = (0,nutr_request,nutr_request)
                        q.append((nutr_val,range_val))

                    effective_day = self._compute_effective_day(q)

                    #update effective day:
                    self.variables["stage_effective_duration#day"][x, y].set_value(
                        self.variables["stage_effective_duration#day"][x, y].value+
                        effective_day
                    )

                    #update age day:
                    self.variables["age#day"][x, y].set_value(
                        self.variables["age#day"][x, y].value + 1
                    )


                    self._update_growth(x,y,effective_day, o_entities, p["dry_growth_allocation#%"])
                    if ("dry_loss#%.day-1" in p):
                        self._update_decay(x,y,o_entities,p["dry_loss#%.day-1"])


                    if (self.variables["stage_effective_duration#day"][x, y].value > p["transition"]["effective_duration#day"]):
                         self.variables["stage"][x, y].set_value(p["transition"]["stage"])
                         self.variables["stage_effective_duration#day"][x, y].set_value(0)


    def compute_shadowsurface(self, position):
        '''
        :param position:
        :return: the total aread, in square meters, of shade collective done by the plants.
        '''
        #
        r = self.variables["radius#cm"][position].value*0.01
        return (np.pi * r * r) * self.variables["population#nb"][position].value * self.parameters['morphology']['shading_factor#%']



    def release_nutrients(self,position,soil):
        r = {"N#g": 0.0, "K#g": 0.0, "P#g": 0.0, "C#g": 0.0}

        return r