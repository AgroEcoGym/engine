# Synthèse Visuelle : 8 Processus Biologiques du Sol

## Diagramme Conceptuel du Flux de Processus

```
MÉTÉOROLOGIE (Weather Entity)
    ↓ rain_amount#mm.day-1
    ↓ ET_0 (évapotranspiration de référence)
    ↓
┌───────────────────────────────────────────────────────────┐
│   MODULE 1: BILAN HYDRIQUE (Water Balance)               │
│   • Input: Pluie                                         │
│   • Output: water_surplus (→ drainage)                   │
│   • État: available_Water#L[x,y]                         │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌───────────────────────────────────────────────────────────┐
│   MODULE 2: CYCLE NUTRIMENTS (Nutrient Cycling)          │
│   • Altération roche-mère (microlife-dépendant)         │
│   • Apports engrais (Fertilizer entity)                  │
│   • État: available_N/P/K/C#g[x,y]                       │
└────────────────────┬────────────────────────────────────┘
                     ↓
        ┌────────────────────────────┐
        ↓                            ↓
    ┌──────────────────┐    ┌──────────────────┐
    │ MODULE 4         │    │ MODULE 5         │
    │ ADVENTICES       │    │ PLANTES          │
    │ (Weed Dynamics)  │    │ (Plant Uptake)   │
    │ • Compétition    │    │ • Prélèvement    │
    │ • Nutriments     │    │ • Stress calc.   │
    │ • Eau            │    │ • Feedback       │
    └──────────────────┘    └──────────────────┘
        ↓ (restitution)          ↓ (litière)
        └────────────────────────┘
                 ↓
┌───────────────────────────────────────────────────────────┐
│   MODULE 3: CONTAMINANTS (Contaminant Tracking)          │
│   • Accumulation cides (Cide entity)                     │
│   • État: amount_cide#g[group][x,y]                      │
│   • Groupes: pollinators, pests, soil, weeds            │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌───────────────────────────────────────────────────────────┐
│   MODULE 6: ÉVAPOTRANSPIRATION (ET)                      │
│   • ET bare soil (1 - ombrage) × humidité × ET_0        │
│   • Percolation basale (microlife-dépendant)            │
│   • État: available_Water#L[x,y] (décréments)           │
└────────────────────┬────────────────────────────────────┘
                     ↓ water_surplus
┌───────────────────────────────────────────────────────────┐
│   MODULE 7: SANTÉ MICROBIOLOGIQUE (Microlife Health)     │
│   • Stresseurs: Toxicité + Engorgement                  │
│   • Survie: fonction sigmoïde (expglm)                   │
│   • Dynamique: croissance vs. déclin                     │
│   • État: microlife_health_index#%[x,y] ∈ [0,100]      │
└────────────────────┬────────────────────────────────────┘
                     ↓ (microlife affecte perméabilité)
┌───────────────────────────────────────────────────────────┐
│   MODULE 8: LESSIVAGE (Leaching)                         │
│   • Si water_surplus > 0:                                │
│   •   Nutrients: perte ∝ (1 - microlife) × flux         │
│   •   Contaminants: dégradation exp(-k × flux)          │
│   • État: available_N/P/K/C#g (décréments)              │
│   •       amount_cide#g[group] (décréments)             │
└───────────────────────────────────────────────────────────┘
                     ↓ (perte vers nappe)
            POLLUTANTS EXPORT
```

---

## Tableau Synthétique des 8 Modules

| # | Nom | Input Clé | Output | État Modifié | Contrôle | Feedback |
|---|-----|-----------|--------|--------------|----------|----------|
| 1 | Water Balance | rain_mm | water_surplus | available_Water#L | Saturation max | → ET, Leaching |
| 2 | Nutrient Cycling | bedrock_rates | nutrient_release | available_N/P/K/C | microlife% | → Plant uptake |
| 3 | Contaminants | cide_release | cide_accumul | amount_cide#g | none (yet) | → Microlife |
| 4 | Weed Dynamics | requirement | net_uptake | N/P/K/C, Water | competition | → Crops (neg) |
| 5 | Plant Uptake | requirement | stress_calc | N/P/K/C, Water | microlife%, wilting | → Crop growth |
| 6 | Evapotranspiration | ET_0 | water_loss | available_Water#L | shadow, wetness | → Water balance |
| 7 | Microlife | stress | health_update | microlife_health% | toxicity, anoxia | → All (modulation) |
| 8 | Leaching | water_surplus | nutrient_export | N/P/K/C, Cides | microlife% | → Pollution |

---

## Dépendances Directionnelles (Graphe)

```
Météo (Weather)
  ├→ [1] Water Balance ─┬→ [6] ET
  │                     ├→ [8] Leaching
  │                     └→ [5] Plant Water
  │
Roches-mère (Bedrock params)
  └→ [2] Nutrient Cycling ─→ [5] Plant N/P/K/C
                           └→ [4] Weed N/P/K/C

Engrais (Fertilizer entity)
  └→ [2] Nutrient Cycling ─→ [5] Plant uptake

Phytosanitaires (Cide entity)
  └→ [3] Contaminants ─→ [7] Microlife stress

Plantes (Plant entity)
  └→ [5] Plant Uptake ←→ [4] Weed Dynamics (compétition)

Adventices (Weed entity)
  └→ [4] Weed Dynamics ─→ [5] Plant stress

                        ┌─────────────────────┐
                        │ [7] MICROLIFE HEALTH│ HUB CENTRAL
                        │ (santé du sol)      │
                        └──────────┬──────────┘
                           ▲  ▲  ▲  ▲
                           │  │  │  └→ [8] Leaching rate
                           │  │  └──→ [2] Nutrient release
                           │  └─────→ [6] Basal percolation
                           └────────→ [5] Nutrient availability
```

---

## État du Sol et Bilan de Masse

### Variables d'État (State Variables)

```
Pools Nutritives (N, P, K, C):
  ├─ Entrée: Altération roche-mère (microlife-dépendant)
  ├─ Entrée: Engrais externes
  ├─ Sortie: Prélèvement cultures + adventices
  ├─ Sortie: Lessivage (lixiviation)
  └─ Restitution: Litière (cultures, adventices, racines)

Pool Hydrique (Water):
  ├─ Entrée: Pluie
  ├─ Entrée: Irrigation (action)
  ├─ Sortie: Prélèvement cultures + adventices
  ├─ Sortie: Évapotranspiration
  ├─ Sortie: Percolation basale
  └─ Sortie: Drainage (lessivage)

Contaminants (Cides par groupe):
  ├─ Entrée: Applications (spray, soil drench, seed treatment)
  ├─ Sortie: Lessivage (lixiviation)
  ├─ Sortie: Dégradation (microbes)
  └─ Accumulation: Sorption sur matière organique

Santé Microbiologique (microlife_health%):
  ├─ Entrée: Récupération (conditions favorables)
  ├─ Sortie: Stress toxique (contaminants sol)
  └─ Sortie: Stress anoxique (engorgement)
```

### Équations de Bilan (Pseudo-code)

```python
# JOUR t → JOUR t+1 (timestep quotidien)

# 1. REMPLISSAGE EAU
W[t+1] = min(W[t] + R_t + I_t, W_max)
        où R_t = pluie, I_t = irrigation, W_max = capacité

# 2. NUTRIMENTS
N[t+1] = N[t] + N_bedrock(microlife[t]) + N_fertilizer
                - N_plant_uptake - N_weed_uptake 
                - N_leaching
                + N_litière

# 3. EAU APRÈS UPTAKE
W_after = W[t+1] - W_plant - W_weed - ET_actual - Perc_basal

# 4. SANTÉ MICROBIOLOGIQUE
microlife[t+1] = microlife[t] × recovery(toxicity, anoxia)

# 5. LESSIVAGE
si water_surplus > 0:
    N_leaching = N × (water_surplus/W_max) × (1 - microlife)
    cide_leaching = cide × (1 - exp(-k × water_surplus/W_max))
```

---

## Cycles Écologiques Implémentés

### Cycle de l'Azote (Nitrogen Cycle)

```
N-Roche-mère (inerte)
    ↓ Altération (microlife-dépendant)
N-Minéral disponible
    ├→ Prélèvement Plantes
    │   ├→ Croissance culture
    │   └→ Litière retour
    ├→ Prélèvement Adventices
    │   ├→ Compétition perte
    │   └→ Litière retour
    ├→ Immobilisation microbes (non-modélisé)
    └→ Lessivage (N-NO3 surtout)
            ↓
        Nappe phréatique (pollution)
```

### Cycle de l'Eau (Hydrologic Cycle)

```
Pluie (R_t)
    ↓
Sol (Infiltration → W_soil)
    ├→ Prélèvement Plantes
    ├→ Prélèvement Adventices
    ├→ Évaporation directe (shade × wetness)
    ├→ Percolation basale (microlife-dépendant)
    └→ Drainage gravitaire (water_surplus)
            ↓
        Nappe phréatique
        
    Atmosphère
    ↑ (Transpiration végétale)
    └─ Évapotranspiration
```

### Cycle des Contaminants (Pesticide Fate)

```
Application (Spray, Seed, Soil drench)
    ↓
Accumulation sol (sorption)
    ├→ Dégradation (photodégradation, microbes)
    │   └→ Métabolites (non-modélisé)
    ├→ Lessivage
    │   └→ Nappe / Eaux de surface
    └→ Volatilisation (non-modélisé)
            ↓
        Résidu disponible pour cultare (bioaccumulation)
```

### Cycle de la Santé Microbienne (Microlife Dynamics)

```
État Optimal (Santé = 100%)
    ↑ Croissance (+2%/jour si conditions bonnes)
    │
État Intermediate (Santé = 50%)
    ┌─ Équilibre (stress faible)
    │
    ↓ Déclin (stress modéré)
    │
État Dégradé (Santé = 10-20%)
    └─ Déclin accéléré (stress fort)
            ↓
        Mort de communauté (Santé → 0)
            ↓
        Perte de services écosystémiques:
        • Altération minérale ralentie
        • Structure sol dégradée
        • Perméabilité accrue (fuites)
        • Dégradation contaminants ↓
```

---

## Paramètres Clés et Plages Réalistes

### Paramètres Hydrodynamiques

| Paramètre | Unité | Sol argileux | Sol limoneux | Sol sableux |
|-----------|-------|--------------|--------------|-------------|
| max_water_capacity | L/m³ | 200 | 250 | 150 |
| wilting_point | L/m³ | 120 | 80 | 40 |
| water_leakage_max | L/m³/day | 3 | 5 | 10 |

### Paramètres Biogéochimiques

| Paramètre | Unité | Valeur faible | Valeur typique | Valeur élevée |
|-----------|-------|---------------|----------------|---------------|
| bedrocks_release_N | mg/day | 10 | 50 | 100 |
| bedrocks_release_K | mg/day | 20 | 100 | 200 |
| bedrocks_release_P | mg/day | 2 | 10 | 20 |
| bedrocks_release_C | mg/day | 200 | 500 | 1000 |

### Constantes Processus

| Processus | Constante | Valeur | Sens |
|-----------|-----------|--------|------|
| Nutrient uptake | microlife_factor | [0, 1] | Disponibilité fonction microlife |
| ET | shadow_fraction | [0, 1] | Réduction par couvert |
| ET | evaporable_depth | 0.15 m | 15 cm couche supérieure |
| Microlife | growth_rate | +2% / jour | Conditions optimales |
| Leaching | decay_rate_k | 1.0 | Exp(-k × flux) pour cides |

---

## Cas d'Usage et Scénarios

### Scénario 1: Année Normale (Beauce typique)

```
Printemps:     600 mm pluie → W = 250 L/m³ (saturé)
Été:           200 mm pluie + 200 mm ET → W = 50 L/m³ (stress)
Automne:       300 mm pluie → W = 200 L/m³ (reconstitution)
Hiver:         100 mm pluie, pas culture → W stable

Nutriments N:  Alimentation complète culture si microlife > 50%
Contaminants:  Lessivage 40-60% si cides appliqués printemps
Microlife:     Reste stable (70-90%) si peu de toxicité
```

### Scénario 2: Sécheresse

```
Printemps:     300 mm pluie (déficit) → W = 150 L/m³
Été:           50 mm pluie + 250 mm ET → W ≈ 0 L/m³ (flétrissement)
Automne:       400 mm pluie (excédent) → W = 250 L/m³
Résultat:      Stress plantes élevé en été
               Récupération automne si pluie arrive à temps
```

### Scénario 3: Pollution Sol (Fongicides sol)

```
Début avril:   Traitement fongicide sol-ciblé
               amount_cide["soil"] = 100 g/m³
Avril-mai:     Microlife baisse (toxicité)
               microlife → 40% (récupération lente)
               Altération minérale ralentie
Juin:          Dégradation microbes + lessivage
               amount_cide → 50 g/m³ (moitié partie)
Sept:          amount_cide → 10 g/m³ (résidu faible)
               Microlife → 70% (récupérée)
```

### Scénario 4: Engorgement (Inondation)

```
Mai:           Pluie intense (100 mm en 2 jours)
               W > W_max → water_surplus élevé
Conséquences:  • Anaérobiose microbes (baisse santé)
               • Lessivage nutriments élevé
               • Lessivage contaminants accéléré
               • Drainage lent si structure dégradée
Récupération:  Si microlife bonne → structure stable → drainage 3-5 jours
               Si microlife mauvaise → drainage 10-15 jours + degradation
```

---

## Améliorations Futures Recommandées

### Phase 1: Cinétiques Manquantes
```python
# Dégradation contaminants
concentration_cide *= exp(-half_life_days / ln(2) × t)

# Minéralisation C organique
C_available = C_litter × (1 - exp(-mineralization_rate × time))

# Immobilisation N microbiénne (C:N feedback)
N_immobilized = C_disponible / C_N_ratio_microbes
```

### Phase 2: États Chimiques Explicites
```python
# Spéciation N (N-NH4 vs N-NO3)
N_NO3 = N_minéral × fraction_nitrification
N_NH4 = N_minéral × (1 - fraction_nitrification)

# Sorption équilibre (K_d)
N_sorbed = N_available × K_d / (1 + K_d)
N_solution = N_available - N_sorbed
```

### Phase 3: Réseau Trophique Microbiologique
```python
# Bactéries hétérotrophes (fonction C)
bacteria = bacteria × (1 + µ_max × C_disponible / (K_s + C_disponible))

# Champignons mycorhiziens (fonction P)
fungi_health = fungi_health × P_disponible / P_critical

# Archées méthanogènes (fonction anoxie)
methanogens = methanogens × (1 + anoxia_factor) × (1 - temperature_stress)
```

---

## Validation et Calibration pour Beauce

### Données Observables
- Stock sol N, P, K (analyses chimie standard)
- Profil humidité (TDR, tensiomètre)
- Biomasse microbienne (fumigation-extraction)
- Activité enzymatique (FDA hydrolysis)
- Rendements cultures (suivi terrain)

### Algorithme Calibration
```python
observations = [
    ("N_available#g", samples_n_spring, samples_n_summer),
    ("available_Water#L", tdr_measurements),
    ("microlife_health#%", microbial_biomass_proxy)
]

parameters_to_tune = [
    "bedrocks_release_N#mg.day-1",
    "max_water_capacity#L.m-3",
    "water_leakage_max#L.m-3.day-1"
]

for param in parameters_to_tune:
    for value in sweep(param_min, param_max):
        run_simulation(param, value)
        error = compare_to_observations()
        save_error(param, value, error)
    best_value = minimize_error()
```
