# HiClimaX — Analysis Pages Specification

This file describes every tunable aspect of `scripts/build_analysis_pages.py`.
Edit here, then re-run the script (delete existing PNGs first to regenerate figures).

```
conda activate hiclimax-analysis
rm -rf output/site/figures/          # force full regeneration
python scripts/build_analysis_pages.py
```

---

## 1. Analysis Period & Domains

| Setting | Value |
|---------|-------|
| Month | August only |
| Years | 2011, 2014, 2015 |
| File type | STS (daily statistics) |
| d01 | 58×58 grid, coarse — Japan + surrounding seas |
| d02 | 98×98 grid, medium — Honshu |
| d03 | 118×118 grid, fine — Tokyo metro |

---

## 2. Reference Locations (time-series)

| Label | Lat | Lon | Used in |
|-------|-----|-----|---------|
| Tokyo (urban) | 35.68°N | 139.69°E | all domains |
| Central Japan (rural) | 35.80°N | 139.18°E | all domains |

---

## 3. Topics & Variables

### 3.1 Temperature

File: `output/site/figures/temperature/`

| Variable | Label | Source dim squeeze | Conversion | Units | Colormap | vmin | vmax |
|----------|-------|--------------------|------------|-------|----------|------|------|
| `tas`    | Mean 2-m Temp | `m2` | K − 273.15 | °C | colorcet.cet_r4 | 15 | 40 |
| `tasmax` | Daily Max 2-m Temp | `m2` | K − 273.15 | °C | colorcet.cet_r4 | 20 | 45 |
| `tasmin` | Daily Min 2-m Temp | `m2` | K − 273.15 | °C | colorcet.cet_r4 | 10 | 35 |

### 3.2 Precipitation

File: `output/site/figures/precipitation/`

| Variable | Label | Source dim squeeze | Conversion | Units | Colormap | vmin | vmax |
|----------|-------|--------------------|------------|-------|----------|------|------|
| `pr`     | Daily Precip | _(none)_ | × 86400 | mm/day | cmocean.rain | 0 | 30 |
| `prmax`  | Hourly Max Precip | _(none)_ | × 3600 | mm/hr | cmocean.rain | 0 | 20 |

### 3.3 Wind

File: `output/site/figures/wind/`

| Variable | Label | Source dim squeeze | Conversion | Units | Colormap | vmin | vmax |
|----------|-------|--------------------|------------|-------|----------|------|------|
| `sfcWindmax` | Max 10-m Wind Speed | `m10` | identity | m/s | cmocean.speed | 0 | 30 |

### 3.4 Pressure

File: `output/site/figures/pressure/`

| Variable | Label | Source dim squeeze | Conversion | Units | Colormap | vmin | vmax |
|----------|-------|--------------------|------------|-------|----------|------|------|
| `psavg`  | Mean Sea-level Pressure | _(none)_ | ÷ 100 | hPa | cmocean.diff | 990 | 1025 |

---

## 4. Figure Types (per variable)

Three PNGs are produced per variable:

### 4.1 Spatial Maps (`spatial_{var}.png`)

- Layout: **3 rows × 3 cols** (rows = years 2011/2014/2015, cols = d01/d02/d03)
- Projection: PlateCarree (`pcolormesh` with 2D xlat/xlon)
- Extent: trimmed by `PAD=3` cells to avoid LCC boundary wedge artifact
- Coastlines: 50m for d01, 10m for d02/d03
- Colorbar: shared horizontal bar below the grid
- Text size: 14pt
- Figure size: 15×12 inches, dpi 150

### 4.2 Time-Series (`timeseries_{var}.png`)

- Layout: **1 row × 3 cols** (cols = years 2011/2014/2015)
- Each panel:
    - one solid line per domain (d01/d02/d03) at the nearest grid point to **Tokyo urban**
    - one thin dashed line per domain (d01/d02/d03) at the nearest grid point to **Central Japan rural**
- X-axis: August day (1–31)
- Colors:
    - solid lines: d01 = `#e06c75` (red), d02 = `#61afef` (blue), d03 = `#98c379` (green)
    - dashed lines: d01 = `#e06c75` (red), d02 = `#61afef` (blue), d03 = `#98c379` (green)
- Y-axis shared across panels (`sharey=True`)
    - precipitation in log-scale
    - temperature in linear scale
    - wind in linear scale
    - pressure in linear scale
- **Log-scale floor** — for log-scale variables, values below `log_floor` are clipped to `log_floor` before plotting (prevents near-zero floating-point noise from spiking the axis):
    - `pr`: `log_floor = 0.1` mm/day
    - `prmax`: `log_floor = 0.01` mm/hr
- Text size: 14pt
- Figure size: 15×4 inches, dpi 150

### 4.3 Violin Plots (`boxplot_{var}.png`)

- Layout: **1 row × 3 cols** (cols = years 2011/2014/2015)
- Each panel:
    - one boxplot per domain, no fill color, using **all grid points × all 31 August days** (full spatial distribution)
    - one violin plot per domain, filled with same color, showing density distribution using **all grid points × all 31 August days** (full spatial distribution)
- Colors match domain colors above
- Y-axis shared across panels
    - temperature in linear scale
    - precipitation in log-scale
    - wind in linear scale
    - pressure in linear scale
- **Log-scale floor** — for log-scale variables, values below `log_floor` are excluded from the distribution entirely (not clipped — excluded) and the y-axis lower bound is set to `log_floor`. Same thresholds as time-series above.
- Text size: 14pt
- Figure size: 13×5 inches, dpi 150

---

## 5. Color Palette

```python
YEAR_COLORS   = {"2011": "#48b0f7", "2014": "#f78b46", "2015": "#38d9a9"}
DOMAIN_COLORS = {"d01": "#e06c75", "d02": "#61afef", "d03": "#98c379"}
```

---

## 6. HTML Page Structure (per topic)

Each page (`output/site/pages/{topic}.html`) has three sections:

1. **Spatial Maps — August Mean** — one figure group per variable
2. **Time-Series at Tokyo Urban** — one figure group per variable
3. **Domain Distribution — Violin Plots** — one figure group per variable

Style: Pico CSS (CDN), max-width 1100px, lazy-loaded `<img>` tags.

---