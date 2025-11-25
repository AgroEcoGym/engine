import math

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
