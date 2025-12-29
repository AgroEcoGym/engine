"""
Soil Entity Module for Agroecology Simulator

This module implements a comprehensive soil dynamics simulator within the AgroEcoGym
ecosystem. It models water balance, nutrient cycling, microbial health, contaminant
fate, and interactions with plants, weeds, and management inputs.

Architecture:
    The Soil class uses a modular approach where update_variables() orchestrates
    calls to specialized sub-modules for each biogeochemical process:

    1. _update_water_balance()      - Hydrological processes (infiltration, percolation)
    2. _update_nutrient_cycling()   - Natural and external nutrient inputs
    3. _update_contaminants()       - Pesticide/herbicide/biocide tracking
    4. _update_plant_interactions() - Nutrient/water uptake and stress
    5. _update_weed_dynamics()      - Competition for resources
    6. _update_evapotranspiration() - Water loss to atmosphere and soil
    7. _update_microlife_health()   - Soil biological community dynamics
    8. _update_leaching()           - Nutrient and contaminant transport

Design Principles:
    - Spatial resolution: grid-based (X, Y coordinates for each plot)
    - Temporal discretization: daily timestep
    - Units consistency: kg↔g conversions explicitly managed
    - Feedback loops: nutrient cycling, stress propagation
    - Modularity: each process is independently testable and tuneable
"""

import numpy as np
from PIL import Image

from agroecogym_engine.apis.entity_api import Entity_API, Range, fillarray
from agroecogym_engine.core.utils.python import checkissubclass
from agroecogym_engine.core.utils.transitions import expglm


class Soil(Entity_API):
    """
    Comprehensive soil entity modeling water, nutrients, contaminants, and microlife.

    This class simulates soil state variables and their daily dynamics across a
    spatially-discretized field. It manages interactions with coupled entities
    (plants, weather, weeds, fertilizers, contaminants) and responds to management
    actions (irrigation).
    """

    def __init__(self, field, parameters):
        """
        Initialize soil variables and action space.

        Args:
            field: Field object containing spatial discretization (X, Y) and plot properties
            parameters: Dict of soil parameters (capacities, release rates, leakage, etc.)

        Variables initialized:
            - Nutrient pools: N, P, K, C (g) for plant availability
            - Water: available water (L) in root zone
            - Physical: depth (m), microlife health index (%)
            - Contaminants: cide amounts for 4 functional groups (g)
            - Cumulative trackers: total added water, total added cides
        """
        Entity_API.__init__(self, field, parameters)
        X = self.field.X
        Y = self.field.Y

        self.variables = {}

        # Nutrient pools (available to plants, not bound to soil matrix)
        self.variables["available_N#g"] = fillarray(
            X, Y, (0, 10000), 100 * self.field.plotsurface
        )  # 100 g/m³
        self.variables["available_P#g"] = fillarray(
            X, Y, (0, 10000), 100 * self.field.plotsurface
        )
        self.variables["available_K#g"] = fillarray(
            X, Y, (0, 100000), 100 * self.field.plotsurface
        )
        self.variables["available_C#g"] = fillarray(
            X, Y, (0, 100000), 100 * self.field.plotsurface
        )

        # Water balance
        self.variables["available_Water#L"] = fillarray(
            X, Y, (0, 10000), 1 * self.field.plotsurface
        )  # 1 L/m³

        # Soil physical properties
        self.variables["depth#m"] = fillarray(X, Y, (0, 10), 1.0)

        # Soil biological health (controls nutrient mobilization and contaminant fate)
        self.variables["microlife_health_index#%"] = fillarray(X, Y, (0, 100), 75)

        # Contaminant fate tracking (by target functional group)
        self.variables["amount_cide#g"] = {
            "pollinators": fillarray(X, Y, (0, 10000), 0.0),
            "pests": fillarray(X, Y, (0, 10000), 0.0),
            "soil": fillarray(X, Y, (0, 10000), 0.0),
            "weeds": fillarray(X, Y, (0, 10000), 0.0),
        }

        # Cumulative input trackers (for environmental accounting)
        self.variables["total_cumulated_added_water#L"] = Range((0, 100000), 0.0)
        self.variables["total_cumulated_added_cide#g"] = {
            "pollinators": Range((0, 100000), 0.0),
            "pests": Range((0, 100000), 0.0),
            "soil": Range((0, 100000), 0.0),
            "weeds": Range((0, 100000), 0.0),
        }

        # Action definitions for agent control
        self.actions = {
            "water_discrete": {
                "plot": field.plots,
                "amount#L": list(np.linspace(0, 15, 16)),  # 0, 1, 2, ..., 15 L
            },
            "water_continuous": {
                "plot": field.plots,
                "amount#L": (0.0, 20.0),  # 0-20 L continuous
            },
        }

        # Dependencies for ordered updates
        self.dependencies = {"Plant", "Weather"}

    def get_parameter_keys(self):
        """
        Return required soil parameters for initialization and dynamics.

        Returns:
            List[str]: Parameter keys for validator/config system
        """
        return [
            "max_water_capacity#L.m-3",  # Soil water holding capacity
            "depth#m",  # Root zone depth
            "wilting_point#L.m-3",  # Water availability threshold
            "water_surface_absorption_speed#m2.day-1",  # Infiltration rate
            "bedrocks_release_N#mg.day-1",  # N remobilization from bedrock
            "bedrocks_release_K#mg.day-1",  # K remobilization from bedrock
            "bedrocks_release_P#mg.day-1",  # P remobilization from bedrock
            "bedrocks_release_C#mg.day-1",  # C remobilization from bedrock
            "water_leakage_max#L.m-3.day-1",  # Maximum basal percolation rate
        ]

    def reset(self):
        """
        Initialize soil to a realistic baseline state.

        Sets spatial heterogeneity in:
        - Nutrient pools (based on typical soil compositions)
        - Water content (based on field capacity)
        - Microlife health (initially 100%, optimal)
        - Contaminants (initially 0)
        """
        for x in range(self.field.X):
            for y in range(self.field.Y):
                # Physical properties
                self.variables["depth#m"][x, y].set_value(self.parameters["depth#m"])

                # Nutrient pools (uniform based on depth and soil type)
                # Assumes moderate-fertility soil
                self.variables["available_N#g"][x, y].set_value(
                    self.variables["depth#m"][x, y].value
                    * self.field.plotsurface
                    * (5000 + 200) / 2  # ~2600 g/m³
                )
                self.variables["available_P#g"][x, y].set_value(
                    self.variables["depth#m"][x, y].value
                    * self.field.plotsurface
                    * (5000 + 100) / 2  # ~2550 g/m³
                )
                self.variables["available_K#g"][x, y].set_value(
                    self.variables["depth#m"][x, y].value
                    * self.field.plotsurface
                    * (50000 + 5000) / 2  # ~27,500 g/m³
                )
                self.variables["available_C#g"][x, y].set_value(
                    self.variables["depth#m"][x, y].value
                    * self.field.plotsurface
                    * (50000 + 10000) / 2  # ~30,000 g/m³
                )

                # Water content at field capacity
                self.variables["available_Water#L"][x, y].set_value(
                    self.variables["depth#m"][x, y].value
                    * self.field.plotsurface
                    * min(
                        self.parameters["max_water_capacity#L.m-3"],
                        (200 + 300) / 2,  # ~250 L/m³
                    )
                )

                # Biological community state
                self.variables["microlife_health_index#%"][x, y].set_value(100)

                # Contaminants (clean initialization)
                for cide_type in ["pollinators", "pests", "soil", "weeds"]:
                    self.variables["amount_cide#g"][cide_type][x, y].set_value(0)

        # Reset cumulative trackers
        self.variables["total_cumulated_added_water#L"].set_value(0.0)
        for cide_type in ["pollinators", "pests", "soil", "weeds"]:
            self.variables["total_cumulated_added_cide#g"][cide_type].set_value(0.0)

        # Apply any scenario-specific initial conditions
        self.initialize_variables(self.initial_conditions)

    def update_variables(self, field, entities):
        """
        Orchestrate daily soil dynamics across all spatial locations.

        Calls sub-modules in dependency order:
        1. Extract coupled entities (Plant, Weather, etc.)
        2. For each spatial location (x, y):
           a. Water balance (infiltration → saturation control)
           b. Nutrient inputs (bedrock, fertilizers)
           c. Contaminant additions (cides)
           d. Weed dynamics (competition)
           e. Plant interactions (uptake, stress feedback)
           f. Evapotranspiration (water loss)
           g. Microlife health (stress response)
           h. Leaching (contaminant and nutrient fate)

        Args:
            field: Field object (for spatial context)
            entities (dict): Dict of all coupled entities by name
        """
        # Pre-compute field-scale hydrological parameters
        max_water_plot_capacity = (
                self.parameters["max_water_capacity#L.m-3"]
                * self.field.plotsurface
                * self.parameters["depth#m"]
        )

        # Extract dependent entities for efficient lookup
        plants = [
            entities[e]
            for e in entities
            if checkissubclass(entities[e].__class__, "Plant")
        ]
        weather = [
            entities[e]
            for e in entities
            if checkissubclass(entities[e].__class__, "Weather")
        ][0]
        fertilizers = [
            entities[e]
            for e in entities
            if checkissubclass(entities[e].__class__, "Fertilizer")
        ]
        weeds = [
            entities[e]
            for e in entities
            if checkissubclass(entities[e].__class__, "Weeds")
        ]
        cides = [
            entities[e]
            for e in entities
            if checkissubclass(entities[e].__class__, "Cide")
        ]

        # Spatial iteration: process each soil cell
        for x in range(self.field.X):
            for y in range(self.field.Y):
                # Call sub-modules in sequence
                water_surplus = self._update_water_balance(
                    x, y, weather, max_water_plot_capacity
                )
                self._update_nutrient_cycling(x, y, fertilizers)
                self._update_contaminants(x, y, cides)
                self._update_weed_dynamics(x, y, weeds)
                self._update_plant_interactions(x, y, plants, weather, field)
                self._update_evapotranspiration(x, y, weather, plants, weeds, field)
                self._update_microlife_health(x, y, water_surplus)
                self._update_leaching(
                    x, y, water_surplus, max_water_plot_capacity
                )

    # =========================================================================
    # SUB-MODULE 1: Water Balance
    # =========================================================================

    def _update_water_balance(self, x, y, weather, max_water_plot_capacity):
        """
        Update soil water content after precipitation and drainage.

        Process:
            1. Add rainfall (converted from mm/day to L)
            2. Limit to field capacity (max_water_plot_capacity)
            3. Track surplus for leaching calculations

        Args:
            x, y (int): Spatial location
            weather: Weather entity (provides rain_amount#mm.day-1)
            max_water_plot_capacity (float): Saturation limit (L)

        Returns:
            float: Water surplus (L) above field capacity (fed to leaching module)

        State Updated:
            - available_Water#L[x, y]

        Physics:
            - Rainfall (mm) → surface area × mm/1000 m/m³ × 1000 L/m³ = L
            - Drainage: implicit via leaching (module 8)
            - Capillary rise: not yet implemented
        """
        # Convert rain (mm/day) to volume (L)
        # Formula: rain_mm * plotsurface_m² / 1000 m/mm * 1000 L/m³ = rain_L
        rain_L = (
                weather.variables["rain_amount#mm.day-1"].value
                * self.field.plotsurface
                / 1000
                * 1000
        )

        # Calculate new water content after rainfall
        water_after_input = self.variables["available_Water#L"][x, y].value + rain_L

        # Prevent oversaturation: cap at field capacity
        new_water = min(max_water_plot_capacity, water_after_input)
        self.variables["available_Water#L"][x, y].set_value(new_water)

        # Compute drainage/runoff surplus for leaching module
        water_surplus = max(0, water_after_input - new_water)

        return water_surplus

    # =========================================================================
    # SUB-MODULE 2: Nutrient Cycling
    # =========================================================================

    def _update_nutrient_cycling(self, x, y, fertilizers):
        """
        Update nutrient pools from natural weathering and external inputs.

        Processes:
            1. Bedrock weathering: slow release of N, P, K, C (controlled by microlife)
            2. Fertilizer application: addition from external entities

        Args:
            x, y (int): Spatial location
            fertilizers (list): List of Fertilizer entities active on field

        State Updated:
            - available_N#g[x, y]
            - available_P#g[x, y]
            - available_K#g[x, y]
            - available_C#g[x, y]

        Biogeochemistry:
            - Bedrock release rates (mg/day) are controlled by soil microlife activity
            - Hypothesis: high microlife health ↔ high mineral weathering
            - Fertilizers emit nutrients via release_nutrients((x,y), soil) method

        Units:
            - Bedrock rates: mg/day → g/day (÷1000)
            - Fertilizer releases: kg → g (×1000)
        """
        # 1. Natural weathering from bedrock (conditioned on microlife health)
        microlife_fraction = (
                self.variables["microlife_health_index#%"][x, y].value / 100.0
        )

        for nutrient in ["N", "K", "P", "C"]:
            bedrock_release_rate = self.parameters[
                f"bedrocks_release_{nutrient}#mg.day-1"
            ]
            # Effective release = weathering_rate × microlife_activity
            nutrient_release = (
                    microlife_fraction * bedrock_release_rate / 1000.0
            )  # mg → g
            self.variables[f"available_{nutrient}#g"][x, y].set_value(
                self.variables[f"available_{nutrient}#g"][x, y].value
                + nutrient_release
            )

        # 2. External fertilizer inputs
        for fertilizer in fertilizers:
            # Query fertilizer entity for nutrients it releases at (x, y)
            # Returns: dict {"N": kg, "K": kg, "P": kg, "C": kg}
            release_dict = fertilizer.release_nutrients((x, y), self)

            for nutrient in ["N", "K", "P", "C"]:
                if nutrient in release_dict:
                    # Convert kg → g
                    nutrient_added_g = release_dict[nutrient] * 1000.0
                    self.variables[f"available_{nutrient}#g"][x, y].set_value(
                        self.variables[f"available_{nutrient}#g"][x, y].value
                        + nutrient_added_g
                    )

    # =========================================================================
    # SUB-MODULE 3: Contaminant Fate Tracking
    # =========================================================================

    def _update_contaminants(self, x, y, cides):
        """
        Accumulate contaminant residues from external applications.

        Process:
            - Each Cide entity releases a fraction targeted to specific groups
            - Soil tracks amount for each group (pollinators, pests, soil, weeds)
            - Not modeled: contaminant degradation (can be added in future)

        Args:
            x, y (int): Spatial location
            cides (list): List of Cide entities on field

        State Updated:
            - amount_cide#g[group][x, y] for group in {pollinators, pests, soil, weeds}

        Note:
            - Cide residues are tracked by functional group (target organism)
            - Contaminant transport (leaching, spray drift) handled in separate modules
            - Degradation kinetics not yet implemented (could be added as exp(-λt))

        Units:
            - Cide.release(): returns kg
            - Conversion: kg → g (×1000)
            - Cide.parameters[group]: fraction of active ingredient for this group
        """
        for cide in cides:
            # Get total cide released at this location (kg)
            total_release_kg = cide.release((x, y))

            # Distribute to target groups
            for group in ["pollinators", "pests", "soil", "weeds"]:
                if group in cide.parameters:
                    # Amount targeting this group (kg) → g
                    group_share = total_release_kg * cide.parameters[group]
                    self.variables["amount_cide#g"][group][x, y].set_value(
                        self.variables["amount_cide#g"][group][x, y].value
                        + group_share * 1000.0  # kg → g
                    )

    # =========================================================================
    # SUB-MODULE 4: Weed Dynamics
    # =========================================================================

    def _update_weed_dynamics(self, x, y, weeds):
        """
        Account for weed biomass competing with crops for soil resources.

        Process:
            1. Compute weed nutrient requirements (N, P, K, C)
            2. Compute weed biomass and water loss
            3. Nutrient redistribution: weeds extract then partially return (litter)

        Args:
            x, y (int): Spatial location
            weeds (list): List of Weed entities

        State Updated:
            - available_N#g, available_P#g, available_K#g, available_C#g [x, y]
            - available_Water#L[x, y]

        Ecological Dynamics:
            - Weeds consume resources (requirement → uptake)
            - Weeds release residues (litter return, N fixation by some species)
            - Net effect usually negative for crop (competition)

        Implementation:
            - requirement_dict: {"N#g", "K#g", "P#g", "C#g", "Water#L"}
            - release_dict: nutrient return from dead biomass
        """
        for weed in weeds:
            # Get weed resource demands at this location
            requirement_dict = weed.requirement((x, y))  # Returns {nutrient: amount}
            release_dict = weed.release_nutrients((x, y), self)  # Litter

            # Nutrient dynamics (competition + recycling)
            for nutrient in ["N", "K", "P", "C"]:
                req_key = f"{nutrient}#g"
                available = self.variables[f"available_{nutrient}#g"][x, y].value
                if req_key in requirement_dict:
                    uptake = requirement_dict[req_key]
                else:
                    uptake = 0

                if req_key in release_dict:
                    return_nutrient = release_dict[req_key]
                else:
                    return_nutrient = 0

                # Net nutrient change: loss to weeds, gain from weed residues
                new_value = max(0.0, available - uptake + return_nutrient)
                self.variables[f"available_{nutrient}#g"][x, y].set_value(new_value)

            # Water dynamics (simplified: instantaneous loss)
            if "Water#L" in requirement_dict:
                water_uptake = requirement_dict["Water#L"]
                current_water = self.variables["available_Water#L"][x, y].value
                new_water = max(0.0, current_water - water_uptake)
                self.variables["available_Water#L"][x, y].set_value(new_water)

    # =========================================================================
    # SUB-MODULE 5: Plant Nutrient & Water Interactions
    # =========================================================================

    def _update_plant_interactions(self, x, y, plants, weather, field):
        """
        Process plant resource uptake and compute stress indices.

        Processes:
            1. Nutrient uptake: limited by soil availability AND microlife activity
            2. Stress calculation: measure of nutrient limitation
            3. Water uptake: above wilting point, below field capacity
            4. Plant feedback: communicate actual uptake + stress to plant entity

        Args:
            x, y (int): Spatial location
            plants (list): List of Plant entities
            weather: Weather entity (for ET_0, evaporation reference)
            field: Field object

        State Updated:
            - available_N#g, P#g, K#g, C#g [x, y] (decrement via uptake)
            - available_Water#L[x, y] (decrement via uptake)

        Methods Called (plant entity):
            - p.requirement_nutrients((x, y)): returns dict {nutrient: demand}
            - p.release_nutrients((x, y), soil): litter, dead roots
            - p.receive_nutrients((x, y), uptake_dict, stress_dict): feedback
            - p.requirement_water((x, y), weather, field): water demand
            - p.receive_water((x, y), uptake, stress): feedback

        Stress Calculation:
            - stress[n] = max(0, requirement[n] - uptake[n])
            - High stress → reduced photosynthesis, growth penalties

        Microlife Modulation:
            - Microlife health modulates nutrient availability
            - Hypothesis: sick soil reduces mycorrhizal symbiosis, mineral uptake
            - Uptake = min(soil_available, microlife_fraction × requirement)

        Wilting Point:
            - Plants cannot extract water below wilting_point
            - Available water for uptake = max(total_available - wilting_point, 0)
        """
        # Pre-compute wilting point threshold (constant for this (x,y))
        wilting_point_L = (
                self.parameters["wilting_point#L.m-3"]
                * self.parameters["depth#m"]
                * self.field.plotsurface
        )

        # Microlife modulation factor (range: 0-1)
        microlife_fraction = (
                self.variables["microlife_health_index#%"][x, y].value / 100.0
        )

        # Process each plant in the field
        for plant in plants:
            # ---- NUTRIENT DYNAMICS ----
            nutrient_requirement = plant.requirement_nutrients((x, y))
            nutrient_release = plant.release_nutrients((x, y), self)  # Litter, roots

            uptake_dict = {}
            stress_dict = {}

            for nutrient in ["N", "K", "P", "C"]:
                req_key = f"{nutrient}"
                var_name = f"available_{nutrient}#g"

                if req_key in nutrient_requirement:
                    requirement = nutrient_requirement[req_key]
                else:
                    requirement = 0

                # Available: min of soil pool and microlife-limited uptake capacity
                soil_available = self.variables[var_name][x, y].value
                uptake_capacity = microlife_fraction * requirement
                uptake = min(soil_available, uptake_capacity)

                # Compute stress (unmet demand)
                stress = max(0, requirement - uptake)

                uptake_dict[f"{nutrient}#g"] = uptake
                stress_dict[f"{nutrient}#g"] = stress

                # Update soil nutrient pool
                new_nutrient = (
                        soil_available
                        - uptake
                        + nutrient_release.get(f"{nutrient}#g", 0)
                )
                self.variables[var_name][x, y].set_value(max(0.0, new_nutrient))

            # Communicate actual uptake and stress to plant entity
            plant.receive_nutrients((x, y), uptake_dict, stress_dict)

            # ---- WATER DYNAMICS ----
            requirement_water = plant.requirement_water((x, y), weather, field)

            # Water available for uptake: above wilting point
            water_available = max(
                0,
                self.variables["available_Water#L"][x, y].value - wilting_point_L,
            )

            # Uptake: limited by availability and demand
            uptake_water = min(requirement_water, water_available)
            stress_water = max(0, requirement_water - uptake_water)

            # Update soil water pool
            self.variables["available_Water#L"][x, y].set_value(
                self.variables["available_Water#L"][x, y].value - uptake_water
            )

            # Communicate actual water uptake and stress to plant entity
            plant.receive_water((x, y), uptake_water, stress_water)

    # =========================================================================
    # SUB-MODULE 6: Evapotranspiration
    # =========================================================================

    def _update_evapotranspiration(self, x, y, weather, plants, weeds, field):
        """
        Calculate and apply daily soil water loss to atmosphere.

        Processes:
            1. Reference ET (ET_0): climate-driven potential evaporation
            2. Soil shadowing: reduce ET by plant/weed cover
            3. Soil wetness: reduce ET as soil dries
            4. Basal percolation: constant seepage (not purely evaporative)

        Args:
            x, y (int): Spatial location
            weather: Weather entity (provides evaporation/ET_0)
            plants (list): Plant entities (for shadow computation)
            weeds (list): Weed entities (for shadow computation)
            field: Field object

        Returns:
            float: Total soil evaporation (mL)

        State Updated:
            - available_Water#L[x, y]

        Evapotranspiration Model:
            ET_actual = ET_0 × (1 - shadow) × wetness_factor + basal_percolation

            Where:
            - ET_0 (mL/m²/day): reference evapotranspiration from climate
            - shadow (0-1): fractional canopy cover (plants + weeds)
            - wetness_factor (0-1): reduction at drier soil (normalized by wilting point)
            - basal_percolation (mL): constant drainage loss (depends on microlife)

        Physics:
            - Only top 15 cm of soil contributes to evaporation (typically)
            - Basal percolation increases with microbial stress (poor structure, cracking)
        """
        # 1. Reference ET from climate (mL/m²/day)
        ET_0 = weather.evaporation(field)

        # 2. Shadow fraction (plants + weeds reduce bare soil exposure)
        plant_shadow = np.sum(
            [p.compute_shadowsurface((x, y)) for p in plants]
        )
        weed_shadow = np.sum([w.compute_shadowsurface((x, y)) for w in weeds])
        total_shadow_L = plant_shadow + weed_shadow
        shadow_fraction = min(total_shadow_L / self.field.plotsurface, 1.0)

        # 3. Soil wetness factor (0 at wilting point, 1 at saturation)
        wilting_point_L = (
                self.parameters["wilting_point#L.m-3"]
                * self.parameters["depth#m"]
                * self.field.plotsurface
        )
        max_water_L = (
                self.parameters["max_water_capacity#L.m-3"]
                * self.parameters["depth#m"]
                * self.field.plotsurface
        )
        current_water = self.variables["available_Water#L"][(x, y)].value
        wetness_range = max_water_L - wilting_point_L
        wetness_factor = max(
            0, (current_water - wilting_point_L) / wetness_range
        )

        # 4. Effective evaporative depth (only top layer evaporates)
        evaporable_depth_m = min(0.15, self.parameters["depth#m"])
        evaporable_volume_L = (
                self.field.plotsurface * evaporable_depth_m * 1000
        )  # m² × m × 1000 L/m³

        # 5. ET calculation (mL)
        bare_soil_ET = (
                ET_0
                * (1.0 - shadow_fraction)
                * wetness_factor
                * evaporable_volume_L
        )

        # 6. Basal percolation (structural water loss, increases with microlife stress)
        microlife_health = (
                self.variables["microlife_health_index#%"][(x, y)].value / 100.0
        )
        basal_percolation = (
                (1.1 - microlife_health)
                * self.field.plotsurface
                * self.parameters["depth#m"]
                * self.parameters["water_leakage_max#L.m-3.day-1"]
                * 1000  # L → mL
        )

        # 7. Total evaporation
        total_evaporation_mL = bare_soil_ET + basal_percolation

        # 8. Update water pool
        evaporation_L = total_evaporation_mL / 1000
        self.variables["available_Water#L"][(x, y)].set_value(
            max(0, self.variables["available_Water#L"][(x, y)].value - evaporation_L)
        )

    # =========================================================================
    # SUB-MODULE 7: Soil Microlife Health Dynamics
    # =========================================================================

    def _update_microlife_health(self, x, y, water_surplus):
        """
        Update soil microbial community health based on stress factors.

        Processes:
            1. Toxicity stress: from soil-targeted contaminants
            2. Waterlogging stress: from excess water (anaerobic conditions)
            3. Survival probability: sigmoidal dose-response (expglm model)
            4. Health update: differential equation (growth vs. decay)

        Args:
            x, y (int): Spatial location
            water_surplus (float): Excess water above field capacity (L)

        State Updated:
            - microlife_health_index#%[x, y]

        Stress Model (Dose-Response):
            Uses expglm() function: sigmoidal response to toxic doses

            Stressors:
            - Toxicity: cide amount targeting soil processes
            - Waterlogging: water_surplus / field_capacity (anaerobic threshold)

            p_stayalive = expglm(0.0, [(effect_1, dose_1, ...), (effect_2, dose_2, ...)])

            Returns: probability of survival (range 0-1)

        Health Update Dynamics:
            If p_stayalive is high (healthy conditions):
                - Microbes thrive: health_new = health × (1 + 0.02 × p_stayalive)
                - +2% per day at optimal conditions
            If p_stayalive is low (stressed):
                - Microbes decline: health_new = health × (p_stayalive)²
                - Faster decline under toxic or waterlogged conditions
        """
        max_water_capacity_L = (
                self.parameters["max_water_capacity#L.m-3"]
                * self.field.plotsurface
                * self.parameters["depth#m"]
        )

        # Construct dose-response curves for stress factors
        stresses = []

        # Stress 1: Soil toxicity (targeting soil microorganisms)
        soil_cide_amount = self.variables["amount_cide#g"]["soil"][x, y].value
        stresses.append(
            (2.0, soil_cide_amount / 100.0, 0, 0)  # Threshold, slope parameters
        )

        # Stress 2: Waterlogging (excess water → anaerobiosis)
        waterlogging_factor = water_surplus / max_water_capacity_L
        stresses.append(
            (5.0, waterlogging_factor, 0, 0)  # Stronger effect of waterlogging
        )

        # Compute survival probability from combined stresses
        p_stayalive = expglm(0.0, stresses)

        # Update microlife health (coupled dynamics)
        # Healthy populations grow; stressed populations decline
        recovery_factor = (
                p_stayalive * (1 + 0.02 * p_stayalive)
                + (1 - p_stayalive) * p_stayalive
        )
        new_health = (
                recovery_factor
                * self.variables["microlife_health_index#%"][x, y].value
        )

        # Clamp to valid range
        self.variables["microlife_health_index#%"][x, y].set_value(
            max(0, min(100, new_health))
        )

    # =========================================================================
    # SUB-MODULE 8: Nutrient & Contaminant Leaching
    # =========================================================================

    def _update_leaching(self, x, y, water_surplus, max_water_plot_capacity):
        """
        Model transport of nutrients and contaminants during drainage events.

        Process:
            - Excess water carries dissolved nutrients and contaminants out of
              the root zone
            - Transport efficiency depends on microlife (affects soil structure)
            - High microlife = better soil stability = lower losses
            - Low microlife = poor structure = higher leaching losses

        Args:
            x, y (int): Spatial location
            water_surplus (float): Water above field capacity (L)
            max_water_plot_capacity (float): Field capacity (L)

        State Updated:
            - available_N#g, P#g, K#g, C#g [x, y]
            - amount_cide#g[group][x, y] for all groups

        Leaching Model:
            Fraction lost = water_surplus / field_capacity × (1 - microlife_health)

            For nutrients:
            - Loss ~ (1 - microlife), assuming high microlife binds nutrients
            - Example: if 25% water surplus and 50% microlife, ~12.5% N loss

            For contaminants:
            - Loss ~ water_surplus / field_capacity (exponential decay)
            - Microlife controls degradation, not just binding

        Environmental Context:
            - Leaching is major source of non-point pollution (N → eutrophication)
            - Pesticide leaching → groundwater contamination
            - Microbial structure critical for pollutant retention
        """
        if water_surplus <= 0:
            # No drainage, no leaching
            return

        # Microlife-dependent retention efficiency
        microlife_fraction = (
                self.variables["microlife_health_index#%"][x, y].value / 100.0
        )

        # Leaching intensity (normalized water flux)
        leaching_intensity = water_surplus / max_water_plot_capacity

        # 1. Nutrient leaching (reduced by soil microlife/structure)
        nutrient_loss_fraction = (
                leaching_intensity * (1.0 - microlife_fraction)
        )

        for nutrient in ["N", "K", "P", "C"]:
            var_name = f"available_{nutrient}#g"
            current = self.variables[var_name][x, y].value
            loss = current * nutrient_loss_fraction
            self.variables[var_name][x, y].set_value(max(0.0, current - loss))

        # 2. Contaminant leaching (exponential decay with discharge)
        # Hypothesis: microbes degrade leached contaminants
        # Loss fraction = 1 - exp(-k × water_surplus)
        leaching_decay_rate = 1.0  # Tunable parameter
        contaminant_loss_fraction = 1.0 - np.exp(
            -leaching_decay_rate * leaching_intensity
        )

        for cide_group in ["pollinators", "pests", "soil", "weeds"]:
            current_cide = self.variables["amount_cide#g"][cide_group][x, y].value
            loss = current_cide * contaminant_loss_fraction
            self.variables["amount_cide#g"][cide_group][x, y].set_value(
                max(0.0, current_cide - loss)
            )

    # =========================================================================
    # Management Action: Irrigation
    # =========================================================================

    def act_on_variables(self, action_name, action_params):
        """
        Apply management action to soil state variables.

        Supported Actions:
            - "water_discrete": Add discrete water volume (0-15 L in 1 L steps)
            - "water_continuous": Add continuous water volume (0-20 L)

        Parameters (for both water actions):
            - "plot" (tuple): (x, y) coordinates of target plot
            - "amount#L" (float): Volume of water to add (liters)

        Effects:
            - Updates water content (capped at field capacity)
            - Triggers contaminant flushing (similar to rainfall)
            - Updates microlife health (waterlogging stress)
            - Tracks cumulative irrigation input

        Implementation:
            - Reuses same dynamics as rainfall (saturation control)
            - Surplus water induces leaching (module 8)
            - Microlife may decline if waterlogged

        Args:
            action_name (str): Name of action ("water_discrete", "water_continuous")
            action_params (dict): {"plot": (x, y), "amount#L": float}

        Raises:
            AssertionError: If action or parameters are invalid
        """
        self.assert_action(action_name, action_params)

        if action_name in ["water_discrete", "water_continuous"]:
            x, y = action_params["plot"]
            water_to_add = action_params["amount#L"]

            # Field capacity limit
            max_water_plot_capacity = (
                    self.parameters["max_water_capacity#L.m-3"]
                    * self.field.plotsurface
                    * self.parameters["depth#m"]
            )

            # Calculate new water content
            water_after_input = (
                    self.variables["available_Water#L"][x, y].value
                    + water_to_add
            )
            new_water = min(max_water_plot_capacity, water_after_input)
            water_surplus = max(0, water_after_input - new_water)

            # Update water pool and cumulative tracker
            water_added_actual = new_water - self.variables["available_Water#L"][x, y].value
            self.variables["total_cumulated_added_water#L"].set_value(
                self.variables["total_cumulated_added_water#L"].value
                + water_added_actual
            )
            self.variables["available_Water#L"][x, y].set_value(new_water)

            # Process surplus (leaching, microlife stress)
            if water_surplus > 0:
                # Microlife modulation (same as rainfall surplus)
                microlife_fraction = (
                        self.variables["microlife_health_index#%"][x, y].value / 100.0
                )

                # Nutrient leaching
                for nutrient in ["N", "K", "P", "C"]:
                    var_name = f"available_{nutrient}#g"
                    loss = (
                            self.variables[var_name][x, y].value
                            * water_surplus
                            * (1.0 - microlife_fraction)
                            / max_water_plot_capacity
                    )
                    self.variables[var_name][x, y].set_value(
                        max(0.0, self.variables[var_name][x, y].value - loss)
                    )

                # Contaminant flushing
                for cide_group in ["pollinators", "pests", "soil", "weeds"]:
                    self.variables["amount_cide#g"][cide_group][x, y].set_value(
                        max(
                            0.0,
                            self.variables["amount_cide#g"][cide_group][x, y].value
                            * np.exp(
                                -water_surplus / max_water_plot_capacity
                            ),
                        )
                    )

                # Microlife stress from waterlogging
                stresses = []
                soil_cide = self.variables["amount_cide#g"]["soil"][x, y].value
                stresses.append((5.0, soil_cide, 0, 0))
                stresses.append(
                    (2.0, water_surplus / max_water_plot_capacity, 0, 0)
                )
                p_stayalive = expglm(0.0, stresses)

                recovery = (
                        p_stayalive * (1 + 0.02 * p_stayalive)
                        + (1 - p_stayalive) * p_stayalive
                )
                new_health = recovery * self.variables["microlife_health_index#%"][x, y].value
                self.variables["microlife_health_index#%"][x, y].set_value(
                    max(0, min(100, new_health))
                )

    # =========================================================================
    # Visualization
    # =========================================================================

    def to_fieldimage(self):
        """
        Generate a visual representation of soil water status.

        Returns:
            PIL.Image: RGBA image showing soil wetness at each grid cell
                - Wet soil (>75% capacity): green
                - Dry soil (<75% capacity): brown/beige
        """
        im_width, im_height = 64, 64
        image = Image.new(
            "RGBA",
            (im_width * self.field.X, im_height * self.field.Y),
            (255, 255, 255, 0),
        )

        for x in range(self.field.X):
            for y in range(self.field.Y):
                max_capacity = (
                        self.field.plotsurface
                        * self.variables["depth#m"][x, y].value
                        * self.parameters["max_water_capacity#L.m-3"]
                )
                current_water = self.variables["available_Water#L"][x, y].value

                if current_water > 0.75 * max_capacity:
                    # Wet soil visualization
                    image.paste(self.images["wet"], (im_width * x, im_height * y))
                else:
                    # Dry soil visualization
                    image.paste(self.images["dry"], (im_width * x, im_height * y))

        return image
