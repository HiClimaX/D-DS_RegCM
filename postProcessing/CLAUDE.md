# HiClimaX Analysis — CLAUDE.md

## Project Purpose
Analyze RegCM5 regional climate model output and produce results as a static website.
The analysis compares variables across all three nested domains (d01, d02, d03).

---

## Golden Rules
- **Never remove, rename, or edit** any file outside the `urban-map/` working directory.
- All outputs (plots, HTML, data) go inside `urban-map/output/`.
- All scripts go inside `urban-map/scripts/`.
- Use `urban-map/regcm5-out/` (symlink) to access model output — treat it as read-only.

---

## Data Inventory

### Location
```
urban-map/regcm5-out/
├── d01/    # coarse domain  (58 × 58 grid)
├── d02/    # medium domain  (98 × 98 grid)
└── d03/    # fine domain    (118 × 118 grid)
```

### File naming convention
```
{domain}_{vartype}.{YYYYMMDD}00.nc      # e.g. d01_SRF.2011060100.nc
```

### Simulation periods
Three summer seasons, each starting June 1 and running through September:
- **2011**: 2011-06-01 to 2011-09-01
- **2014**: 2014-06-01 to 2014-09-01
- **2015**: 2015-06-01 to 2015-09-01

### Analyze period
Only August of each simulated case.

### Grid dimensions
| Domain | jx × iy | σ-levels | Description |
|--------|---------|----------|-------------|
| d01 | 58 × 58 | 18 | Coarse (parent) |
| d02 | 98 × 98 | 23 | Medium (nested) |
| d03 | 118 × 118 | 41 | Fine (innermost) |

### Variable type files
| Type | Key variables | Notes |
|------|--------------|-------|
| `SRF` | `pr`, `tas`, `hurs`, `sfcWind`, `psl`, `clt`, `evspsbl`, `hfss`, `hfls`, `rsds`, `rlds`, `uas`, `vas`, `zmla` | 2-D surface, daily mean from 6-hourly |
| `STS` | `tasmax`, `tasmin`, `prmax`, `sfcWindmax`, `pr`, `psmin`, `psavg` | Daily statistics |


### Coordinate system
- Spatial coordinates: `xlat`, `xlon` (2-D lat/lon arrays on model projection grid)
- Time axis: CF-convention double, decode with `xr.open_dataset(..., decode_times=True)`

---

## Analysis Goals
The user will specify variables to compare. The general pattern is:
1. Load the same variable from d01, d02, and d03 for a chosen period.
2. Compute statistics (mean, max, percentiles) over the time axis.
3. Produce side-by-side spatial maps, time-series plots, box-&violin-plots, for each domain.
4. Extract data of some locations to compare the time-series plots and box-&violin-plots.
5. Write results to the static website under `output/site/`.

---

## Environment

### Conda environment
Environment name: **`hiclimax-analysis`**

Create once:
```bash
conda create -n hiclimax-analysis -c conda-forge \
    python=3.11 \
    xarray netcdf4 scipy numpy pandas \
    matplotlib cartopy cmocean colorcet \
    jupyterlab notebook \
    jinja2 \
    Pillow \
    tqdm \
    -y
conda activate hiclimax-analysis
```

Activate before any analysis work:
```bash
conda activate hiclimax-analysis
```

Do **not** use the existing `r-env` environment for new scripts.

---

## Repository Layout (inside `urban-map/`)

```
urban-map/
├── CLAUDE.md                    # this file
├── SKILL-ANALYSIS.md            # analysis page tuning reference
├── SKILL-WEBPAGE.md             # website architecture reference
├── regcm5-out/                  # input data symlink (READ-ONLY)
├── scripts/
│   ├── lib/
│   │   └── loader.py            # load_august(), get_coords(), DOMAINS, YEARS
│   ├── preprocess_wind.py       # SRF uas/vas → wind_{ts}.json (leaflet-velocity)
│   ├── preprocess.py            # SRF/STS → grayscale PNGs + bounds JSON + manifest
│   ├── build_analysis_pages.py  # STS → figures + analysis HTML pages
│   └── serve.sh                 # python -m http.server 8080
└── output/
    └── site/                    # static website root
        ├── index.html           # landing page
        ├── map.html             # interactive Windy-style map
        ├── assets/
        │   ├── css/site.css     # dual-theme styles (709 lines)
        │   └── js/map.js        # map controller (477 lines)
        ├── data/
        │   ├── manifest.json    # domains + variables + timesteps
        │   ├── d01/             # wind JSON + scalar PNGs + bounds JSON
        │   ├── d02/
        │   └── d03/
        ├── figures/             # analysis PNGs (spatial/timeseries/boxplot)
        │   ├── temperature/
        │   ├── precipitation/
        │   ├── wind/
        │   └── pressure/
        └── pages/               # static analysis pages
            ├── temperature.html
            ├── precipitation.html
            ├── wind.html
            └── pressure.html
```

---

## Website Format
- Static HTML — no server required (open `output/site/index.html` in a browser).
- One page per analysis topic (e.g., `precipitation.html`, `temperature.html`).
- Figures embedded as PNG or inline SVG.
- A top-level `index.html` with links to all topic pages.
- Style: minimal, clean — use a simple CSS framework (e.g., Pico CSS via CDN).
- **Interactive map** (Windy-style): Leaflet.js + leaflet-velocity plugin (see below).

---

## Interactive Map — Windy-Style Visualization

### Concept
The main interactive page replicates Windy.com's look:
- Leaflet.js base map (OpenStreetMap tiles)
- Animated wind particles via **leaflet-velocity** (canvas-based particle advection)
- Color scalar overlays (temperature, precipitation, etc.) as PNG images draped on the map
- Time slider to browse 6-hourly timesteps within August
- Domain switcher (d01 / d02 / d03)
- Variable switcher (wind, temperature, precipitation, ...)

### Data pipeline (Python → web)
All pre-processing runs once; outputs land in `output/site/data/`.

```
scripts/
├── lib/
│   └── loader.py            # load_august(), get_coords(), DOMAINS, YEARS
├── preprocess_wind.py       # exports wind_{ts}.json for leaflet-velocity
├── preprocess.py            # exports grayscale PNGs + bounds JSON + manifest
└── build_analysis_pages.py  # generates figures + analysis HTML pages
```

#### 1. Wind → velocity JSON (leaflet-velocity format)
leaflet-velocity expects a JSON array with two objects (U component, V component):
```json
[
  { "header": { "parameterCategory": 2, "parameterNumber": 2,
                "lo1": lon_min, "la1": lat_max,
                "dx": delta_lon, "dy": delta_lat,
                "nx": ncols, "ny": nrows,
                "refTime": "2011-08-01T00:00:00Z" },
    "data": [ ...u_values_row_major... ] },
  { "header": { "parameterCategory": 2, "parameterNumber": 3, ... },
    "data": [ ...v_values_row_major... ] }
]
```
One JSON file per domain per 6-hourly timestep → `output/site/data/{domain}/wind_{timestamp}.json`

#### 2. Scalar fields → PNG overlay
For each variable (tas, pr, psl, …) and each timestep:
- Apply colormap (e.g. `cmocean.cm.thermal` for temperature, `cmocean.cm.rain` for precipitation)
- Save transparent PNG sized to grid (jx × iy pixels, no axes)
- Save a sidecar `{var}_{timestamp}.json` with `{ "bounds": [[lat_sw, lon_sw], [lat_ne, lon_ne]] }`
→ `output/site/data/{domain}/{var}_{timestamp}.png` + `.json`

### Frontend stack (all via CDN, no build step)
| Library | Purpose |
|---------|---------|
| Leaflet 1.9 | Interactive map base |
| leaflet-velocity | Animated wind particles |
| chroma.js | Color scale for legends |
| noUiSlider | Time slider UI |
| Pico CSS | Minimal base styles |

### File layout additions
```
output/site/
├── index.html              # landing page with links
├── map.html                # main interactive Windy-style map
├── assets/
│   ├── css/site.css
│   └── js/map.js           # domain/variable/time controls
├── data/
│   ├── manifest.json       # list of available domains, variables, timesteps
│   ├── d01/
│   │   ├── wind_2011080100.json
│   │   ├── tas_2011080100.png
│   │   ├── tas_2011080100.json   # bounds
│   │   └── ...
│   ├── d02/
│   └── d03/
└── pages/                  # static analysis pages (maps, time-series, etc.)
```

### manifest.json structure
```json
{
  "domains": {
    "d01": { "sw": [lat_sw, lon_sw], "ne": [lat_ne, lon_ne], "center": [lat, lon] },
    "d02": { ... },
    "d03": { ... }
  },
  "variables": {
    "wind":       { "label": "Wind (10m)", "units": "m/s", "type": "velocity", "vmin": 0, "vmax": 25, "colorstops": [...] },
    "tas":        { "label": "Temperature 2m (mean)", "units": "°C", "type": "scalar", "vmin": ..., "vmax": ... },
    "sfcWindmax": { ... },
    "psavg":      { ... }
  },
  "timesteps": ["2011080100", "2011080200", ..., "2015083100"]
}
```

> **Note:** `domains` is a **dict** (not a list) — each entry carries `sw`, `ne`, `center` used by `map.js` for `fitBounds`. Timesteps are daily (one per August day × 3 years = 93 total).

---

## Workflow for a New Analysis

1. **Add a topic entry** to `TOPICS` in `scripts/build_analysis_pages.py` (see `SKILL-ANALYSIS.md`).
2. **Add a card** in `output/site/index.html` linking to `pages/{topic}.html`.
3. **Run** `conda activate hiclimax-analysis && python scripts/build_analysis_pages.py`.
4. For a **new interactive-map variable**: preprocess with `preprocess.py`, add an `<option>` in `map.html`.

### Standard data-loading pattern
```python
from scripts.lib.loader import load_august, get_coords, DOMAINS, YEARS

# Load August-only DataArray for a variable across all domains/years
for domain in DOMAINS:
    for year in YEARS:
        ds = load_august(domain, "STS", year)   # or "SRF"
        da = ds["tasmax"].squeeze("m2", drop=True) - 273.15   # → °C
        xlat, xlon = get_coords(domain)          # 2-D lat/lon arrays
```

---

## Variable Reference (most commonly used)

| CF name | Long name | Units | File |
|---------|-----------|-------|------|
| `pr` | Precipitation | mm/hr or kg m-2 s-1 | SRF, STS, SHF |
| `tas` | 2-m Air Temperature | K | SRF, STS |
| `tasmax` / `tasmin` | Daily max/min 2-m Temp | K | STS |
| `psl` | Sea-level Pressure | Pa | SRF |
| `sfcWind` | Surface Wind Speed | m s-1 | SRF |
| `clt` | Total Cloud Fraction | % | SRF |
| `hurs` | 2-m Relative Humidity | % | SRF |
| `ua` / `va` | Horizontal wind components | m s-1 | ATM |
| `ta` | Air Temperature (3-D) | K | ATM |
| `rh` | Relative Humidity (3-D) | % | ATM |
| `rlut` | TOA Outgoing LW | W m-2 | RAD |
| `rsds` | Surface Downwelling SW | W m-2 | SRF |
