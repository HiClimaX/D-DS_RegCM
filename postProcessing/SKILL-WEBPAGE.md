# HiClimaX — Website Architecture

Complete reference for `output/site/`. All files are static — no server required (`open index.html`), though a local HTTP server is needed for the interactive map (due to `fetch()` calls).

```bash
bash scripts/serve.sh          # Python http.server on port 8080
# open http://localhost:8080
```

---

## 1. Page Inventory

| File | Theme | Purpose |
|------|-------|---------|
| `index.html` | Light blue | Landing page — mini wind map + 4 analysis card links |
| `map.html` | Dark navy | Interactive Windy-style map with full controls |
| `pages/temperature.html` | Light (Pico CSS) | Temperature analysis figures |
| `pages/precipitation.html` | Light (Pico CSS) | Precipitation analysis figures |
| `pages/wind.html` | Light (Pico CSS) | Wind analysis figures |
| `pages/pressure.html` | Light (Pico CSS) | Pressure analysis figures |

---

## 2. Asset Files

| File | Lines | Purpose |
|------|-------|---------|
| `assets/css/site.css` | 709 | All styles — dual-theme CSS custom properties |
| `assets/js/map.js` | 477 | Interactive map controller |

### 2.1 CSS Architecture — Dual Theme

All colors are defined as CSS custom properties on `:root` (dark navy palette). Both themes share the same component classes; only the variable values differ.

```css
:root {
  --bg: #1b2838;  --panel-bg: #243447;  --accent: #48b0f7;  ...
}
body.map-page {          /* light blue overrides for map panel */
  --bg: #d6e9f5;  --panel-bg: #ffffff;  --accent: #1a5fa8;  ...
}
body.index-page {        /* light blue index page (block layout) */
  background: #d6e9f5;  ...
}
```

Any base rule using `color: var(--accent)` automatically adapts to the active theme — no per-element overrides needed.

### 2.2 Color Palette Constants

```python
YEAR_COLORS   = {"2011": "#48b0f7", "2014": "#f78b46", "2015": "#38d9a9"}
DOMAIN_COLORS = {"d01": "#e06c75", "d02": "#61afef", "d03": "#98c379"}
```

---

## 3. Index Page (`index.html`)

### Layout

- Full-page light-blue `index-page` body
- `<main class="index-main">` max-width 980px, centered
- Decorative: compass SVG (top-right), two ☀️ deco elements

### Top grid (2 columns)

| Left | Right |
|------|-------|
| **Mini wind map** — embedded Leaflet + leaflet-velocity | **Interactive Climate Map** card → `map.html` |

### Mini wind map

- **Library**: Leaflet 1.9 + leaflet-velocity 2.1 (loaded via CDN in `index.html` only)
- **Tiles**: CartoDB Dark Matter (`dark_all`)
- **Center**: 33°N, 140°E — zoom 4
- **All controls disabled** (no zoom, drag, scroll, attribution)
- **Data**: d01 wind, August 2014, daily timesteps (`data/d01/wind_2014080100.json` … `wind_2014083100.json`)
- **Cycling**: `setInterval` every 2 s — advances one day, prefetches the next
- **Overlap swap**: new velocity layer is added first; old layer removed after 500 ms — prevents blank gap while particles initialise
- **`particleAge: 120`** — particles live 6 s at 20 fps; keeps field dense across transitions
- **Cache**: plain object, all 31 JSONs retained after first cycle (~1.4 MB total)
- **"Open Map →" pill**: `position: absolute; bottom: 14px; right: 14px`

### Analysis card grid (4 cards)

Links to `pages/{topic}.html` for Temperature, Precipitation, Wind, Pressure.

---

## 4. Interactive Map (`map.html` + `assets/js/map.js`)

### Frontend libraries (CDN)

| Library | Version | Purpose |
|---------|---------|---------|
| Leaflet | 1.9.4 | Base map |
| leaflet-velocity | 2.1.4 | Animated wind particles |
| noUiSlider | 15.8.1 | Time-step slider |
| chroma.js | 2.4.2 | Client-side colorization + legend |

### Map tiles

- **Base** (no labels): CartoDB `light_nolabels`
- **Labels overlay** (top pane): CartoDB `light_only_labels` — placed above wind layer so city names remain readable

### Controls (side panel)

| Control | Behaviour |
|---------|-----------|
| **Domain** (D01/D02/D03) | Calls `map.fitBounds()` for that domain's extent — always re-zooms (no locked zoom) |
| **Variable** selector | Switches between wind (velocity) and 7 scalar variables |
| **Overlay opacity** | Slider 10–100 %; applied live to the scalar image layer |
| **Year** (2011/2014/2015) | Filters `manifest.timesteps` to that year's 31 daily steps |
| **Date slider** | noUiSlider; each step = one August day |
| **Prev / Next buttons** | Step ±1 day |
| **Color Scale** | 10 presets via chroma.js (`CMAP_PRESETS`) |
| **Min / Max / Ticks** | Override `vmin`/`vmax` from manifest; `Apply` re-renders |
| **Reset** | Restores manifest defaults |

### Domain switching — `fitToDomain(domain)`

Reads SW/NE bounds from `manifest.domains[domain]`, calls `map.fitBounds()` with 8 % padding and `animate: true`. Every switch re-zooms — d01 shows all of Japan; d03 zooms to Tokyo metro.

### Variable types

**Wind** (`type: "velocity"`)
- Fetches `data/{domain}/wind_{ts}.json` (leaflet-velocity JSON format — two-element array with U/V headers + row-major data)
- Rendered by leaflet-velocity canvas layer
- `velocityScale: 0.008`, `particleAge: 40`, `lineWidth: 1.2`, `frameRate: 16`

**Scalar** (`type: "scalar"`)
- Fetches `data/{domain}/{var}_{ts}.png` — a **grayscale value PNG** where pixel intensity encodes the physical value (0 = vmin, 255 = vmax)
- JavaScript reads pixel values via `<canvas>`, maps to color via chroma.js at the selected colormap/range
- Fetches `data/{domain}/{var}_{ts}.bounds.json` for the `L.imageOverlay` bounds
- Colorized image drawn to canvas; rendered as `L.imageOverlay`

### LRU cache

`Map` object, max 80 entries. Evicts oldest on overflow. Caches both JSON (wind) and colorized `Blob` URLs (scalar).

### Legend

Horizontal `<canvas>` colorbar (260 × 14 px) rendered via chroma.js. Tick labels computed from `vmin`, `vmax`, and `customTicks` (default 5).

---

## 5. Data Files (`output/site/data/`)

### `manifest.json`

```jsonc
{
  "domains": {
    "d01": { "sw": [22.53, 121.22], "ne": [48.75, 158.48], "center": [35.64, 139.85] },
    "d02": { "sw": [31.40, 133.96], "ne": [40.22, 145.39], "center": [35.81, 139.67] },
    "d03": { "sw": [34.76, 138.29], "ne": [36.86, 140.94], "center": [35.81, 139.62] }
  },
  "variables": {
    "tas":       { "label": "Temperature 2m (mean)", "units": "°C",   "type": "scalar", "vmin": ..., "vmax": ... },
    "tasmax":    { ... },
    "tasmin":    { ... },
    "pr":        { "label": "Precipitation (daily)", "units": "mm/day","type": "scalar", ... },
    "prmax":     { ... },
    "sfcWindmax":{ ... },
    "psavg":     { ... },
    "wind":      { "label": "Wind (10m)", "units": "m/s", "type": "velocity", "colorstops": [...] }
  },
  "timesteps": ["2011080100", "2011080200", ..., "2015083100"]  // 93 daily steps
}
```

### Per-domain data (`d01/`, `d02/`, `d03/`)

| Pattern | Count | Description |
|---------|-------|-------------|
| `wind_{ts}.json` | 93 / domain | leaflet-velocity U+V JSON (daily, ~44 KB each) |
| `{var}_{ts}.png` | 93 × 7 / domain | Grayscale value PNG (pixel = physical value) |
| `{var}_{ts}.bounds.json` | 93 × 7 / domain | `{"bounds": [[lat_sw, lon_sw], [lat_ne, lon_ne]]}` |

**Total data files**: ≈ 93 × (1 + 7 + 7) × 3 domains = ~4 200 files

---

## 6. Analysis Pages (`pages/`)

Generated by `scripts/build_analysis_pages.py`. Each page uses **Pico CSS** (CDN, max-width 1100px) and contains three sections:

1. **Spatial Maps** — 3×3 grid PNG (rows = years, cols = domains)
2. **Time-Series** — 1×3 PNG (cols = years; solid = urban, dashed = rural)
3. **Violin + Box Plots** — 1×3 PNG (cols = years; violin shape + boxplot overlay)

Figures live in `figures/{topic}/` and are referenced with relative paths (`../figures/…`).
See `SKILL-ANALYSIS.md` for all tuning parameters.

---

## 7. Preprocessing Scripts

| Script | Inputs | Outputs | Notes |
|--------|--------|---------|-------|
| `preprocess_wind.py` | SRF NetCDF (uas, vas) | `data/{domain}/wind_{ts}.json` | Bilinear interpolation to regular lat/lon grid; Delaunay rebuild is slow — run once |
| `preprocess.py` | STS/SRF NetCDF | `data/{domain}/{var}_{ts}.png` + `.bounds.json` | Grayscale value encoding; also writes `manifest.json` with domains/variables/timesteps |
| `build_analysis_pages.py` | STS NetCDF | `figures/{topic}/*.png` + `pages/{topic}.html` + manifest wind entry | Idempotent — skips existing PNGs; delete to regenerate |

---

## 8. Adding a New Variable to the Interactive Map

1. **Preprocess**: add the variable to `preprocess.py` and re-run to generate PNG + bounds + manifest entry.
2. **HTML** (`map.html`): add `<option value="{varname}">Label</option>` to `#var-select`.
3. **No JS changes needed** — `map.js` reads variable metadata from `manifest.json` at runtime.

## 9. Adding a New Analysis Topic

1. Add a new entry to `TOPICS` dict in `build_analysis_pages.py` (see `SKILL-ANALYSIS.md` for schema).
2. Add a card in `index.html` pointing to `pages/{topic_key}.html`.
3. Run `build_analysis_pages.py`.
