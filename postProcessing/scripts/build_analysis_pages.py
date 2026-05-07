#!/usr/bin/env python
"""
Build static analysis pages for the HiClimaX website.

Run once:
    conda activate hiclimax-analysis
    python scripts/build_analysis_pages.py

Outputs:
    output/site/figures/{topic}/*.png
    output/site/pages/{topic}.html
    output/site/data/manifest.json   (wind entry added)
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cmocean
import colorcet as cc
import matplotlib.pyplot as plt
import numpy as np
from jinja2 import Environment

SCRIPTS_DIR = Path(__file__).parent
ANALYZE_DIR = SCRIPTS_DIR.parent
OUT_FIGURES   = ANALYZE_DIR / "output" / "site" / "figures"
OUT_PAGES     = ANALYZE_DIR / "output" / "site" / "pages"
MANIFEST_PATH = ANALYZE_DIR / "output" / "site" / "data" / "manifest.json"

sys.path.insert(0, str(SCRIPTS_DIR))
from lib.loader import DOMAINS, YEARS, get_coords, load_august

YEAR_COLORS   = {"2011": "#48b0f7", "2014": "#f78b46", "2015": "#38d9a9"}
DOMAIN_COLORS = {"d01": "#e06c75", "d02": "#61afef", "d03": "#98c379"}

URBAN = {"lat": 35.68, "lon": 139.69, "label": "Tokyo (urban)"}
RURAL = {"lat": 35.80, "lon": 139.18, "label": "Central Japan (rural)"}

TOPICS = {
    "temperature": {
        "title": "Temperature",
        "icon": "🌡",
        "desc": "2-m temperature spatial maps, time-series, and domain comparison.",
        "vars": [
            {"name": "tas",    "label": "Mean 2-m Temp (tas)",         "squeeze": ["m2"],
             "convert": lambda x: x - 273.15, "units": "°C",
             "cmap": cc.cm.CET_R4, "vmin": 15, "vmax": 40, "yscale": "linear"},
            {"name": "tasmax", "label": "Daily Max 2-m Temp (tasmax)", "squeeze": ["m2"],
             "convert": lambda x: x - 273.15, "units": "°C",
             "cmap": cc.cm.CET_R4, "vmin": 20, "vmax": 45, "yscale": "linear"},
            {"name": "tasmin", "label": "Daily Min 2-m Temp (tasmin)", "squeeze": ["m2"],
             "convert": lambda x: x - 273.15, "units": "°C",
             "cmap": cc.cm.CET_R4, "vmin": 10, "vmax": 35, "yscale": "linear"},
        ],
    },
    "precipitation": {
        "title": "Precipitation",
        "icon": "🌧",
        "desc": "Total and heavy precipitation statistics across domains.",
        "vars": [
            {"name": "pr",    "label": "Daily Precip (pr)",        "squeeze": [],
             "convert": lambda x: x * 86400, "units": "mm/day",
             "cmap": cmocean.cm.rain, "vmin": 0, "vmax": 30,
             "yscale": "log", "log_floor": 0.1},
            {"name": "prmax", "label": "Hourly Max Precip (prmax)", "squeeze": [],
             "convert": lambda x: x * 3600,  "units": "mm/hr",
             "cmap": cmocean.cm.rain, "vmin": 0, "vmax": 20,
             "yscale": "log", "log_floor": 0.01},
        ],
    },
    "wind": {
        "title": "Wind",
        "icon": "💨",
        "desc": "Surface wind speed and direction analysis.",
        "vars": [
            {"name": "sfcWindmax", "label": "Max 10-m Wind Speed (sfcWindmax)", "squeeze": ["m10"],
             "convert": lambda x: x, "units": "m/s",
             "cmap": cmocean.cm.speed, "vmin": 0, "vmax": 30, "yscale": "linear"},
        ],
    },
    "pressure": {
        "title": "Pressure",
        "icon": "🌊",
        "desc": "Sea-level pressure patterns and synoptic overview.",
        "vars": [
            {"name": "psavg", "label": "Mean Sea-level Pressure (psavg)", "squeeze": [],
             "convert": lambda x: x / 100, "units": "hPa",
             "cmap": cmocean.cm.diff, "vmin": 990, "vmax": 1025, "yscale": "linear"},
        ],
    },
}

# ─── helpers ──────────────────────────────────────────────────────────────────

def _squeeze(da, dims):
    for d in dims:
        if d in da.dims:
            da = da.squeeze(d, drop=True)
    return da


def _load_var(domain, year, varspec):
    ds = load_august(domain, "STS", year)
    da = _squeeze(ds[varspec["name"]], varspec["squeeze"])
    return varspec["convert"](da)


def find_nearest_ij(xlat, xlon, lat, lon):
    dist = np.sqrt((xlat - lat) ** 2 + (xlon - lon) ** 2)
    return np.unravel_index(np.argmin(dist), dist.shape)


def _coast_resolution(domain):
    return "10m" if domain in ("d02", "d03") else "50m"


# ─── Step 1: patch manifest ────────────────────────────────────────────────────

def patch_manifest_wind():
    with open(MANIFEST_PATH) as f:
        m = json.load(f)
    if "wind" in m.get("variables", {}):
        print("manifest: wind entry already present — skip")
        return
    m.setdefault("variables", {})["wind"] = {
        "label": "Wind (10m)",
        "units": "m/s",
        "type": "velocity",
        "vmin": 0,
        "vmax": 25,
        "colorstops": [
            "#3288bd", "#66c2a5", "#abdda4", "#e6f598",
            "#fee08b", "#fdae61", "#f46d43", "#d53e4f",
        ],
    }
    with open(MANIFEST_PATH, "w") as f:
        json.dump(m, f, indent=2)
    print("manifest: wind entry added")


# ─── Step 2a: spatial maps ─────────────────────────────────────────────────────

def make_spatial_maps(varspec, out_dir, coords, data):
    out_path = out_dir / f"spatial_{varspec['name']}.png"
    if out_path.exists():
        print(f"    skip (exists): {out_path.name}")
        return out_path

    proj = ccrs.PlateCarree()
    fig, axes = plt.subplots(
        3, 3, figsize=(15, 12),
        subplot_kw={"projection": proj},
    )
    fig.suptitle(f"August Mean — {varspec['label']}", fontsize=15, fontweight="bold")

    PAD = 3
    domain_meta = {}
    for domain in DOMAINS:
        xlat, xlon = coords[domain]
        interior_xlat = xlat[PAD:-PAD, PAD:-PAD]
        interior_xlon = xlon[PAD:-PAD, PAD:-PAD]
        domain_meta[domain] = {
            "xlat": xlat, "xlon": xlon,
            "extent": [float(interior_xlon.min()), float(interior_xlon.max()),
                       float(interior_xlat.min()), float(interior_xlat.max())],
            "coast": cfeature.NaturalEarthFeature(
                "physical", "coastline", _coast_resolution(domain),
                edgecolor="black", facecolor="none", linewidth=0.6,
            ),
        }

    im = None
    for row, year in enumerate(YEARS):
        for col, domain in enumerate(DOMAINS):
            ax = axes[row, col]
            m = domain_meta[domain]
            da_or_err = data[(domain, year)]
            if isinstance(da_or_err, Exception):
                ax.set_title(f"{year} {domain.upper()}\n(no data)", fontsize=11)
                ax.text(0.5, 0.5, str(da_or_err), transform=ax.transAxes,
                        ha="center", va="center", fontsize=8, wrap=True)
                continue
            data2d = da_or_err.mean(dim="time").values
            im = ax.pcolormesh(
                m["xlon"], m["xlat"], data2d,
                transform=proj,
                cmap=varspec["cmap"],
                vmin=varspec["vmin"],
                vmax=varspec["vmax"],
                shading="nearest",
            )
            ax.set_extent(m["extent"], crs=proj)
            ax.set_aspect("auto")
            ax.add_feature(m["coast"])
            ax.set_title(f"{year} — {domain.upper()}", fontsize=11)

    fig.subplots_adjust(left=0.04, right=0.96, top=0.93, bottom=0.10,
                        hspace=0.30, wspace=0.12)
    if im is not None:
        sm = plt.cm.ScalarMappable(
            cmap=varspec["cmap"],
            norm=plt.Normalize(vmin=varspec["vmin"], vmax=varspec["vmax"]),
        )
        sm.set_array([])
        cbar_ax = fig.add_axes([0.15, 0.03, 0.70, 0.022])
        cbar = fig.colorbar(sm, cax=cbar_ax, orientation="horizontal",
                     label=f"{varspec['label']} ({varspec['units']})")
        cbar.ax.tick_params(labelsize=12)
        cbar.set_label(f"{varspec['label']} ({varspec['units']})", fontsize=13)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"    saved: {out_path.name}")
    return out_path


# ─── Step 2b: time-series ─────────────────────────────────────────────────────

def make_timeseries(varspec, out_dir, coords, data):
    out_path = out_dir / f"timeseries_{varspec['name']}.png"
    if out_path.exists():
        print(f"    skip (exists): {out_path.name}")
        return out_path

    yscale = varspec.get("yscale", "linear")

    fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharey=True)
    fig.suptitle(
        f"Daily Time-Series — {varspec['label']}\n"
        f"(solid = Tokyo urban  ·  dashed = rural 35.80°N 139.18°E)",
        fontsize=13, fontweight="bold",
    )

    # Pre-compute nearest grid-point indices for urban and rural per domain
    domain_pts = {}
    for domain in DOMAINS:
        xlat, xlon = coords[domain]
        i_u, j_u = find_nearest_ij(xlat, xlon, URBAN["lat"], URBAN["lon"])
        i_r, j_r = find_nearest_ij(xlat, xlon, RURAL["lat"], RURAL["lon"])
        domain_pts[domain] = (i_u, j_u, i_r, j_r)

    for col, year in enumerate(YEARS):
        ax = axes[col]
        for domain in DOMAINS:
            color = DOMAIN_COLORS[domain]
            i_u, j_u, i_r, j_r = domain_pts[domain]
            da_or_err = data[(domain, year)]
            if isinstance(da_or_err, Exception):
                continue
            arr = da_or_err.values
            days = np.arange(1, arr.shape[0] + 1)
            if yscale == "log":
                floor = varspec.get("log_floor", 1e-3)
                arr = np.maximum(arr, floor)
            ax.plot(days, arr[:, i_u, j_u], color=color, lw=1.8,
                    label=domain.upper())
            ax.plot(days, arr[:, i_r, j_r], color=color, lw=1.0, ls="--")

        ax.set_title(year, fontsize=13)
        ax.set_xlabel("August day", fontsize=12)
        if col == 0:
            ax.set_ylabel(varspec["units"], fontsize=12)
        ax.set_yscale(yscale)
        ax.legend(fontsize=10, loc="upper right")
        ax.grid(alpha=0.25)
        ax.tick_params(labelsize=11)

    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"    saved: {out_path.name}")
    return out_path


# ─── Step 2c: violin + boxplot ────────────────────────────────────────────────

def make_boxplot(varspec, out_dir, data):
    out_path = out_dir / f"boxplot_{varspec['name']}.png"
    if out_path.exists():
        print(f"    skip (exists): {out_path.name}")
        return out_path

    yscale = varspec.get("yscale", "linear")

    fig, axes = plt.subplots(1, 3, figsize=(13, 5), sharey=True)
    fig.suptitle(
        f"August Distribution — {varspec['label']}",
        fontsize=14, fontweight="bold",
    )

    for col, year in enumerate(YEARS):
        ax = axes[col]
        datasets = []
        positions = []
        colors = []
        for i, domain in enumerate(DOMAINS):
            da_or_err = data[(domain, year)]
            if isinstance(da_or_err, Exception):
                continue
            flat = da_or_err.values.ravel()
            flat = flat[np.isfinite(flat)]
            if yscale == "log":
                floor = varspec.get("log_floor", 1e-3)
                flat = flat[flat >= floor]
            if len(flat) == 0:
                continue
            datasets.append(flat)
            positions.append(i + 1)
            colors.append(DOMAIN_COLORS[domain])

        if not datasets:
            continue

        # Violin (filled — shows density shape)
        parts = ax.violinplot(datasets, positions=positions,
                              showmedians=False, showextrema=False)
        for pc, color in zip(parts["bodies"], colors):
            pc.set_facecolor(color)
            pc.set_alpha(0.55)
            pc.set_edgecolor("none")

        # Boxplot overlay (no fill — shows quartiles)
        bp = ax.boxplot(
            datasets, positions=positions, widths=0.12,
            patch_artist=True, showfliers=False,
            boxprops=dict(facecolor="none", edgecolor="black", linewidth=1.2),
            medianprops=dict(color="black", linewidth=2.0),
            whiskerprops=dict(color="black", linewidth=1.0),
            capprops=dict(color="black", linewidth=1.0),
        )

        ax.set_xticks([1, 2, 3])
        ax.set_xticklabels([d.upper() for d in DOMAINS], fontsize=12)
        ax.set_title(year, fontsize=13)
        ax.set_yscale(yscale)
        if yscale == "log":
            ax.set_ylim(bottom=varspec.get("log_floor", 1e-3))
        ax.grid(axis="y", alpha=0.25)
        ax.tick_params(axis="y", labelsize=11)
        if col == 0:
            ax.set_ylabel(f"{varspec['label']} ({varspec['units']})", fontsize=12)

    handles = [plt.Rectangle((0, 0), 1, 1, color=DOMAIN_COLORS[d], alpha=0.6)
               for d in DOMAINS]
    fig.legend(handles, [d.upper() for d in DOMAINS], loc="lower center", ncol=3,
               fontsize=11, bbox_to_anchor=(0.5, -0.02))

    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"    saved: {out_path.name}")
    return out_path


# ─── Step 2 orchestrator ───────────────────────────────────────────────────────

def build_figures_for_topic(topic_key, topic, coords):
    out_dir = OUT_FIGURES / topic_key
    out_dir.mkdir(parents=True, exist_ok=True)

    fig_paths = {"spatial": [], "timeseries": [], "boxplot": []}
    rel = lambda p: f"../figures/{topic_key}/{p.name}"

    for varspec in topic["vars"]:
        print(f"  {varspec['name']}:")

        data = {}
        for domain in DOMAINS:
            for year in YEARS:
                try:
                    data[(domain, year)] = _load_var(domain, year, varspec)
                except Exception as e:
                    data[(domain, year)] = e

        fig_paths["spatial"].append({
            "path": rel(make_spatial_maps(varspec, out_dir, coords, data)),
            "label": varspec["label"],
        })
        fig_paths["timeseries"].append({
            "path": rel(make_timeseries(varspec, out_dir, coords, data)),
            "label": varspec["label"],
        })
        fig_paths["boxplot"].append({
            "path": rel(make_boxplot(varspec, out_dir, data)),
            "label": varspec["label"],
        })

    return fig_paths


# ─── Step 2 HTML rendering ─────────────────────────────────────────────────────

PAGE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>HiClimaX — {{ title }} Analysis</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
  <style>
    body { max-width: 1100px; margin: 0 auto; padding: 1.5rem 1rem; }
    nav { margin-bottom: 2rem; }
    .fig-section { margin-bottom: 3rem; }
    .fig-section h2 { border-bottom: 2px solid var(--pico-primary); padding-bottom: .4rem; }
    .fig-group { margin-bottom: 2rem; }
    .fig-group h3 { font-size: 1rem; color: var(--pico-muted-color); margin-bottom: .5rem; }
    figure { margin: 0; }
    figure img { width: 100%; border-radius: 6px; box-shadow: 0 2px 8px rgba(0,0,0,.15); }
    figcaption { font-size: .8rem; color: var(--pico-muted-color); margin-top: .4rem; }
    .domains-note { font-size: .85rem; color: var(--pico-muted-color); margin-bottom: 1.5rem; }
  </style>
</head>
<body>
<nav><a href="../index.html">← Back to HiClimaX</a></nav>
<header>
  <h1>{{ icon }} {{ title }} Analysis</h1>
  <p class="domains-note">
    RegCM5 · August only · Three simulations: 2011, 2014, 2015<br>
    Domains: d01 (58×58, coarse) · d02 (98×98, medium) · d03 (118×118, fine — Tokyo metro)
  </p>
</header>
<main>

  <section class="fig-section">
    <h2>Spatial Maps — August Mean</h2>
    <p>Each row shows one simulation year; columns compare d01 (coarse) → d02 (medium) → d03 (fine, Tokyo metro). Note different spatial extents per domain.</p>
    {% for fig in figures.spatial %}
    <div class="fig-group">
      <h3>{{ fig.label }}</h3>
      <figure>
        <img src="{{ fig.path }}" alt="{{ fig.label }} spatial map" loading="lazy">
        <figcaption>August-mean {{ fig.label }}: rows = 2011 / 2014 / 2015, columns = d01 / d02 / d03.</figcaption>
      </figure>
    </div>
    {% endfor %}
  </section>

  <section class="fig-section">
    <h2>Time-Series at Key Locations</h2>
    <p>
      Each panel shows one simulation year; lines compare the three domains.
      Solid lines = Tokyo urban (35.68°N, 139.69°E) · Dashed lines = rural (35.80°N, 139.18°E).
      Colors: <span style="color:#e06c75">■ D01</span>
              <span style="color:#61afef">■ D02</span>
              <span style="color:#98c379">■ D03</span>.
    </p>
    {% for fig in figures.timeseries %}
    <div class="fig-group">
      <h3>{{ fig.label }}</h3>
      <figure>
        <img src="{{ fig.path }}" alt="{{ fig.label }} time-series" loading="lazy">
        <figcaption>Daily {{ fig.label }} — panels left to right: 2011, 2014, 2015.</figcaption>
      </figure>
    </div>
    {% endfor %}
  </section>

  <section class="fig-section">
    <h2>Domain Distribution — Violin + Box Plots</h2>
    <p>Each panel shows one simulation year; violin shapes (filled) show density, boxplot overlay (unfilled) shows quartiles. Data: all grid points × all August days.</p>
    {% for fig in figures.boxplot %}
    <div class="fig-group">
      <h3>{{ fig.label }}</h3>
      <figure>
        <img src="{{ fig.path }}" alt="{{ fig.label }} distribution" loading="lazy">
        <figcaption>August distribution of {{ fig.label }} per domain — panels left to right: 2011, 2014, 2015.</figcaption>
      </figure>
    </div>
    {% endfor %}
  </section>

</main>
<footer><small>HiClimaX · REMOSAT · RegCM5 v5.0.0</small></footer>
</body>
</html>"""


def render_page(topic_key, topic, fig_paths):
    env = Environment(autoescape=False)
    tmpl = env.from_string(PAGE_TEMPLATE)
    html = tmpl.render(title=topic["title"], icon=topic["icon"], figures=fig_paths)
    out_path = OUT_PAGES / f"{topic_key}.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"  page → {out_path.relative_to(ANALYZE_DIR)}")


# ─── main ──────────────────────────────────────────────────────────────────────

def main():
    plt.rcParams.update({"font.size": 14})

    print("=== Step 1: Patch manifest.json (add wind variable) ===")
    patch_manifest_wind()

    print("\n=== Step 2: Generate figures + render analysis pages ===")
    coords = {d: get_coords(d) for d in DOMAINS}
    for topic_key, topic in TOPICS.items():
        print(f"\n--- {topic['title']} ---")
        fig_paths = build_figures_for_topic(topic_key, topic, coords)
        render_page(topic_key, topic, fig_paths)

    print("\nDone. Serve with:  bash scripts/serve.sh")


if __name__ == "__main__":
    main()
