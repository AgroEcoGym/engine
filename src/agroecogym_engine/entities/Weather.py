import math

import numpy as np
from PIL import Image

import agroecogym_engine.specifications.specification_manager as sm
from agroecogym_engine.apis.entity_api import Entity_API, Range


class Weather(Entity_API):
    def __init__(self, field, parameters):
        Entity_API.__init__(self, field, parameters)
        self.localization = self.field.localization

        self.variables = {}

        # Global weather
        self.variables["year#int100"] = Range(list(range(100)), 0)
        self.variables["day#int365"] = Range(list(range(365)), 0)
        self.variables["air_temperature"] = {
            "max#°C": Range((-100, 100), 22.0),
            "mean#°C": Range((-100, 100), 20.0),
            "min#°C": Range((-100, 100), 18.0),
        }
        self.variables["humidity#%"] = Range((0.0, 100.0), 50.0)
        self.variables["wind"] = {
            "speed#km.h-1": Range((0.0, 500), 0.0),
            "direction": Range(list(range(360)), 0),
        }
        self.variables["clouds#%"] = Range((0.0, 100.0), 0)
        self.variables["rain_amount#mm.day-1"] = Range((0, 1000), 0)

        # TODO: put this in a sperate entity "light" ?
        self.variables["daily_photosynthetic_light_integral#mol.m-2.day-1"] = Range((0.0, 100.0), 0)

        self.variables["consecutive_frost#day"] = Range((0, 10000), 0.0)
        self.variables["consecutive_dry#day"] = Range((0, 10000), 0.0)

        self.variables["forecast"] = {
            "air_temperature": {
                "mean#°C": np.full(
                    self.parameters["forecast_lookahead"],
                    fill_value=Range((-100, 100), 20.0),
                ),
                "min#°C": np.full(
                    self.parameters["forecast_lookahead"],
                    fill_value=Range((-100, 100), 18.0),
                ),
                "max#°C": np.full(
                    self.parameters["forecast_lookahead"],
                    fill_value=Range((-100, 100), 22.0),
                ),
            },
            "humidity#%": np.full(
                self.parameters["forecast_lookahead"],
                fill_value=Range((0.0, 100.0), 50.0),
            ),
            "clouds#%": np.full(
                self.parameters["forecast_lookahead"],
                fill_value=Range((0.0, 100.0), 0.0),
            ),
            "rain_amount#mm.day-1": np.full(
                self.parameters["forecast_lookahead"],
                fill_value=Range((0.0, 100.00), 0.0),
            ),
            "wind": {
                "speed#km.h-1": np.full(
                    self.parameters["forecast_lookahead"],
                    fill_value=Range((0.0, 500), 0.0),
                ),
                "direction": np.full(
                    self.parameters["forecast_lookahead"],
                    fill_value=Range(list(range(360)), 0),
                ),
            },
        }

        # required fields in CSV data file:
        self.datakeys = {
            "T": "Temperature",
            "Tmin": "TemperatureMin",
            "Tmax": "TemperatureMax",
            "H": "Humidity",
            "R": "Rain",
            "C": "Clouds",
            "WS": "WindSpeed",
            "WD": "WindDirection",
        }

        # self.year_weather = sm.load_weather_table(self.parameters["one_year_data_filename"])
        self.year_weathers, self.weather_alphas = sm.load_weather_table(
            self.parameters["one_year_data_filename"]
        )
        # Local weather

        # Actions
        self.actions = {}

        self.dependencies = {}

    def get_parameter_keys(self):
        return [
            "one_year_data_filename",
            "air_temperature_noise",
            "humidity_noise",
            "clouds_noise",
            "rain_amount_noise",
            "wind_speed_noise",
            "wind_direction_noise",
            "forecast_lookahead",
            "forecast_noise",
        ]

    def reset(self):
        # print("WEATHER INIT", self.initial_conditions)
        self.initialize_variables(self.initial_conditions)
        # Init variables:

        if "year#int100" not in self.initial_conditions:
            self.variables["year#int100"].set_value((0))
        if "day#int365" not in self.initial_conditions:
            self.variables["day#int365"].set_value(((-1) % 365))
        else:
            self.variables["day#int365"].set_value(
                ((self.initial_conditions["day#int365"] - 1) % 365)
            )
        if "consecutive_frost#day" not in self.initial_conditions:
            self.variables["consecutive_frost#day"].set_value(0.0)
        if "cconsecutive_dry#day" not in self.initial_conditions:
            self.variables["consecutive_dry#day"].set_value(0.0)

        # if ('day#int365' in self.initial_conditions):
        #     day= self.initial_conditions['day#int365']
        # if ('consecutive_frost#day' in self.initial_conditions):
        #     self.variables["consecutive_frost#day"].set_value(self.initial_conditions['consecutive_frost#day'])
        # if ('cconsecutive_dry#day' in self.initial_conditions):
        #     self.variables["consecutive_dry#day"].set_value(self.initial_conditions['consecutive_dry#day'])

        self.update_variables(self.field, entities={})

    def update_variables(self, field, entities):
        day = (self.variables["day#int365"].value + 1) % 365
        if day == 0:
            self.variables["year#int100"].set_value(
                self.variables["year#int100"].value + 1
            )
        self.variables["day#int365"].set_value(((day) % 365))

        eps = self.np_random.normal(0, self.parameters["air_temperature_noise"], 1)[0]
        self.variables["air_temperature"]["mean#°C"].set_value(
            self.read_weathercsv(self.datakeys["T"], day % 365) + eps
        )
        self.variables["air_temperature"]["min#°C"].set_value(
            self.read_weathercsv(self.datakeys["Tmin"], day % 365) + eps
        )
        self.variables["air_temperature"]["max#°C"].set_value(
            self.read_weathercsv(self.datakeys["Tmax"], day % 365) + eps
        )
        eps = self.np_random.normal(0, self.parameters["humidity_noise"], 1)[0]
        self.variables["humidity#%"].set_value(
            self.read_weathercsv(self.datakeys["H"], day % 365) + eps
        )
        eps = self.np_random.normal(0, self.parameters["clouds_noise"], 1)[0]
        self.variables["clouds#%"].set_value(
            self.read_weathercsv(self.datakeys["C"], day % 365) + eps
        )
        eps = self.np_random.normal(0, self.parameters["rain_amount_noise"], 1)[0]
        self.variables["rain_amount#mm.day-1"].set_value(
            self.read_weathercsv(self.datakeys["R"], day % 365) + eps
        )
        eps = self.np_random.normal(0, self.parameters["wind_speed_noise"], 1)[0]
        self.variables["wind"]["speed#km.h-1"].set_value(
            self.read_weathercsv(self.datakeys["WS"], day % 365) + eps
        )
        eps = self.np_random.normal(0, self.parameters["wind_direction_noise"], 1)[0]
        self.variables["wind"]["direction"].set_value(
            int(self.read_weathercsv(self.datakeys["WD"], day % 365) + eps) % 360
        )

        if self.variables["air_temperature"]["min#°C"].value < 0:
            self.variables["consecutive_frost#day"].set_value(
                self.variables["consecutive_frost#day"].value + 1
            )
        else:
            self.variables["consecutive_frost#day"].set_value(0)
        if self.variables["rain_amount#mm.day-1"].value < 1:
            self.variables["consecutive_dry#day"].set_value(
                self.variables["consecutive_dry#day"].value + 1
            )
        else:
            self.variables["consecutive_dry#day"].set_value(0)


        # TODO: put this in a seperate entity "light" ? Only requires weather.variables["clouds#%"] and current day.
        self.variables["daily_photosynthetic_light_integral#mol.m-2.day-1"].set_value(
            daily_photosynthetic_light(self.localization["latitude#°"],self.variables["day#int365"].value,self.variables["clouds#%"].value)
        )

        for i in range(self.parameters["forecast_lookahead"]):
            eps = self.np_random.normal(
                0,
                self.parameters["air_temperature_noise"]
                + self.parameters["forecast_noise"] * i,
                1,
            )[0]
            self.variables["forecast"]["air_temperature"]["mean#°C"][i].set_value(
                self.read_weathercsv(self.datakeys["T"], (day + i) % 365) + eps
            )
            self.variables["forecast"]["air_temperature"]["min#°C"][i].set_value(
                self.read_weathercsv(self.datakeys["Tmin"], day % 365) + eps
            )
            self.variables["forecast"]["air_temperature"]["max#°C"][i].set_value(
                self.read_weathercsv(self.datakeys["Tmax"], day % 365) + eps
            )
            eps = self.np_random.normal(
                0,
                self.parameters["humidity_noise"]
                + self.parameters["forecast_noise"] * i,
                1,
            )[0]
            self.variables["forecast"]["humidity#%"][i].set_value(
                self.read_weathercsv(self.datakeys["H"], day % 365) + eps
            )
            eps = self.np_random.normal(
                0,
                self.parameters["wind_speed_noise"]
                + self.parameters["forecast_noise"] * i,
                1,
            )[0]
            self.variables["forecast"]["wind"]["speed#km.h-1"][i].set_value(
                self.read_weathercsv(self.datakeys["WS"], day % 365) + eps
            )
            eps = self.np_random.normal(
                0,
                self.parameters["wind_direction_noise"]
                + self.parameters["forecast_noise"] * i,
                1,
            )[0]
            self.variables["forecast"]["wind"]["direction"][i].set_value(
                int(self.read_weathercsv(self.datakeys["WD"], day % 365) + eps) % 360
            )
            eps = self.np_random.normal(
                0,
                self.parameters["clouds_noise"] + self.parameters["forecast_noise"] * i,
                1,
            )[0]
            self.variables["forecast"]["clouds#%"][i].set_value(
                self.read_weathercsv(self.datakeys["C"], day % 365) + eps
            )
            eps = self.np_random.normal(
                0,
                self.parameters["rain_amount_noise"]
                + self.parameters["forecast_noise"] * i,
                1,
            )[0]
            self.variables["forecast"]["rain_amount#mm.day-1"][i].set_value(
                self.read_weathercsv(self.datakeys["R"], day % 365) + eps
            )

    def read_weathercsv(self, variable, day):
        value = 0
        # In case there are many weather files, this enables to interpolate between the values of each file:
        for i in range(len(self.weather_alphas)):
            # print("VAR",variable,"DAY",day,i,self.year_weathers[i][variable][day],self.weather_alphas[i])
            value += self.year_weathers[i][variable][day] * self.weather_alphas[i]
        return value

    def act_on_variables(self, action_name, action_params):
        pass

    def evaporation(
        self, field
    ):  # in mm.m-2.day-1 for a surface in plain sunlight for the whole day.
        """
        Evaporation in mL.m-2.day-1 for a water surface in plain sunlight for the whole (possibly cloudy) day.
        """
        cl = self.variables["clouds#%"].value / 100
        RA = daily_ground_irradiance(field.localization["longitude#°"], self.variables["day#int365"].value,cloud_fraction=cl)
        #RA = irradiance_perday(
        #    field.localization["longitude#°"], self.variables["day#int365"].value
        #)#  # in kWh/m2 per day

        rh = self.variables["humidity#%"].value / 100
        t_av = self.variables["air_temperature"]["mean#°C"].value / 100
        w = self.variables["wind"]["speed#km.h-1"].value * (
            24 * 1000 * 1000
        )  # in mm.day-1
        w_max = 9  # 90 km.h-1 # #90*1000*1000*1e-7
        alt = field.localization["altitude#m"]

        # chaleur latente de vaporisatoin de l'eau: 0.626kWh/kg = 626kWh/m3
        evapo = (
            (RA / 0.626)
            * ((1 - rh) ** 0.8)
            * (max(t_av, 0) ** 1.1)
            * ((w * 1e-7 / w_max) ** 1.2)
            * (1 + alt * 1e-5) ** 0.8
        )  # mm/m2

        # Base evaporation in mm per day at any point.
        return evapo

    def to_thumbnailimage(self):
        im_width, im_height = 64, 64
        image = Image.new("RGBA", (im_width, im_height), (255, 255, 255, 0))
        if self.variables["clouds#%"].value <= 50:
            image.paste(self.images["sunny"], (0, 0))
        if self.variables["clouds#%"].value >= 50:
            image.paste(self.images["cloudy"], (0, 0))
        if self.variables["rain_amount#mm.day-1"].value >= 0.5:
            image.paste(self.images["rainy"], (0, 0))
        if self.variables["wind"]["speed#km.h-1"].value >= 40:
            image.paste(self.images["windy"], (0, 0))
        if self.variables["air_temperature"]["mean#°C"].value >= 30:
            image.paste(self.images["hot"], (0, 0))
        if self.variables["air_temperature"]["mean#°C"].value <= 0:
            image.paste(self.images["freeze"], (0, 0))
        return image


def daily_extraterrestrial_irradiance(latitude, jour):  # in kWh/m2/day
    H0 = 1367  # Constante solaire en W/m^2
    L = math.radians(latitude)  # Convertir la latitude en radians
    J = jour

    # Calcul de la déclinaison solaire #0 lors des equinoxes, +0.41/-0.41 aux solstices.
    delta = math.radians(23.45) * math.sin(math.radians(360 * (284 + J) / 365))

    # TODO-WU :
    # print(delta,L,math.sin(L) * math.sin(delta) / (math.cos(delta)*math.cos(L)))

    # Calcul de l'angle horaire du coucher du soleil
    valeur = math.tan(L) * math.tan(delta)
    if -1 < valeur < 1:
        h_s = math.acos(-math.tan(L) * math.tan(delta))
    else:
        h_s = 0

    # Eccentricity correction
    E0 = 1 + 0.033 * math.cos(2 * math.pi * J / 365)

    # Calcul de la puissance solaire
    H = (24 * 3600 / math.pi) * (
        H0
        * E0
        * (math.cos(L)   * math.cos(delta)  * math.sin(h_s)
           +h_s * math.sin(L) * math.sin(delta))
        )
    return H/ 3.6e6 # in kWh/m2/day
def estimate_clearness_index_from_cloud(cloud_fraction):
    # Clear 0.75 → Overcast 0.15
    cloud_fraction = max(0.0, min(1.0, cloud_fraction))
    return 0.75 - 0.60 * cloud_fraction

def daily_ground_irradiance(latitude_deg, day_of_year, cloud_fraction=None):
    H0 = daily_extraterrestrial_irradiance(latitude_deg, day_of_year)  # kWh/m²/day
    if cloud_fraction is None:
        k_t = 0.65  # reasonable clear-to-scattered default
    else:
        k_t = estimate_clearness_index_from_cloud(cloud_fraction)
    return k_t * H0  # kWh/m²/day at ground (GHI)

# 3) Convert GHI (kWh/m²/day) to DLI (mol/m²/day)
# GHI=(Ground-level) Global horizontal irradiance
# DLI = (photosynthetic) Daily Light Integral
#    Assumptions:
#    - ~45% of sunlight energy is PAR (photosynthetically active radiation): 400–700 nm;
#    - 1 mol PAR ≈ 0.060 kWh/m²
#    ⇒ DLI ≈ 0.45/0.060 * GHI ≈ 7.5 * GHI
def ghi_to_dli(ghi_kwh_m2_day):
    return 7.45 * ghi_kwh_m2_day  # mol/m²/day (approx)
def daily_photosynthetic_light(latitude_deg, day_of_year, cloud_fraction=None):
    # That is "DLI" in horticulture
    return ghi_to_dli(daily_ground_irradiance(latitude_deg, day_of_year, cloud_fraction))


if __name__ == "__main__":
    # Exemple d'utilisation
    latitude = 48.8566  # Latitude de Paris
    jour = 200  # Jour de l'année
    for jour in [81, 81 + 365 // 4, 81 + 365 // 2, 81 + 3 * 365 // 4]:
        for latitude in [
            -70,
            #-66,
            #-60,
            #-50,
            #-40,
            #-30,
            #-5,
            0,
            #5,
            #30,
            #40,
            #50,
            #60,
            #66,
            70,
            #80,
        ]:
            puissance = daily_extraterrestrial_irradiance(latitude, jour)
            print(
                f"La puissance solaire reçue à la latitude {latitude} le jour {jour} est de {puissance} J/m²."
            )

            irradiance = daily_ground_irradiance(latitude, jour)
            print(
                f"L'irradiance solaire à la latitude {latitude} le jour {jour} est de {irradiance} kWh/m2 par jour soit {irradiance/0.626} mm/m2 potentiellement evapore par jour"
            )
