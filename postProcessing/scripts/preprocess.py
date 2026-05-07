#!/usr/bin/env python
"""
Preprocess RegCM5 STS output → web data for the HiClimaX interactive map.

Data layout (flat, inside analyze/regcm5-out/):
    {domain}_STS.{YYYYMMDD}00.nc

Run once:
    conda activate hiclimax-analysis
    python scripts/preprocess.py

Outputs (under output/site/data/):
    {domain}/{var}_{YYYYMMDDHH}.png          -- colorized scalar overlay
    {domain}/{var}_{YYYYMMDDHH}.bounds.json  -- lat/lon bounds + value range
    manifest.json                            -- index consumed by map.js
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from lib.loader import DOMAINS, YEARS, get_coords, load_august
from lib.export import (
    COLORDEFS,
    cmap_to_hex,
    make_regridder,
    make_target_grid,
    to_value_png,
)

ANALYZE_DIR = SCRIPTS_DIR.parent
OUT_ROOT = ANALYZE_DIR / "output/site/data"
OUT_ROOT.mkdir(parents=True, exist_ok=True)

# ── STS variable specs ──────────────────────────────────────────────────────
# varname → (squeeze_dims, unit_convert_fn)
SCALAR_SPECS = {
    "tas":        (["m2"],  lambda x: x - 273.15),   # K → °C
    "tasmax":     (["m2"],  lambda x: x - 273.15),
    "tasmin":     (["m2"],  lambda x: x - 273.15),
    "pr":         ([],      lambda x: x * 86400),     # kg m-2 s-1 → mm/day
    "prmax":      ([],      lambda x: x * 3600),      # kg m-2 s-1 → mm/hr
    "sfcWindmax": (["m10"], lambda x: x),             # m/s, no conversion
    "psavg":      ([],      lambda x: x / 100),       # Pa → hPa
}


def squeeze_dims(da, dim_names):
    for d in dim_names:
        if d in da.dims:
            da = da.squeeze(d, drop=True)
    return da


def ts_key(ts: pd.Timestamp) -> str:
    return ts.strftime("%Y%m%d%H")


# ── Per-domain processing ───────────────────────────────────────────────────

def process_domain(domain: str) -> dict:
    print(f"\n{'='*60}\nDomain: {domain}\n{'='*60}")

    out_dir = OUT_ROOT / domain
    out_dir.mkdir(exist_ok=True)

    xlat, xlon = get_coords(domain, "STS")
    target_lat, target_lon = make_target_grid(xlat, xlon)
    print(
        f"  Grid {xlat.shape} → target {len(target_lat)}×{len(target_lon)}"
        f"  lat [{target_lat[-1]:.2f}, {target_lat[0]:.2f}]"
        f"  lon [{target_lon[0]:.2f}, {target_lon[-1]:.2f}]"
    )
    print("  Building Delaunay triangulation …", end=" ", flush=True)
    regrid = make_regridder(xlat, xlon, target_lat, target_lon)
    print("done")

    domain_bounds = {
        "sw":     [float(target_lat[-1]), float(target_lon[0])],
        "ne":     [float(target_lat[0]),  float(target_lon[-1])],
        "center": [
            float((target_lat[0] + target_lat[-1]) / 2),
            float((target_lon[0] + target_lon[-1]) / 2),
        ],
    }

    exported_ts = []

    for year in YEARS:
        try:
            ds = load_august(domain, "STS", year)
        except FileNotFoundError as e:
            print(f"  SKIP {year}: {e}")
            continue

        times = pd.DatetimeIndex(ds.time.values)
        print(f"\n  {year}: {len(times)} timesteps")

        for i, ts in enumerate(tqdm(times, desc=f"  {domain}/{year}")):
            key = ts_key(ts)

            for varname, (squeeze, convert) in SCALAR_SPECS.items():
                out_png = out_dir / f"{varname}_{key}.png"
                if out_png.exists():
                    continue
                da = ds[varname].isel(time=i)
                da = squeeze_dims(da, squeeze)
                data = convert(da.values.astype(np.float32))
                to_value_png(data, regrid, varname, out_png)

            exported_ts.append(key)

        ds.close()

    return {"bounds": domain_bounds, "timesteps": sorted(set(exported_ts))}


# ── Manifest ────────────────────────────────────────────────────────────────

def build_manifest(domain_meta: dict):
    variables = {}
    for varname in SCALAR_SPECS:
        cmap, vmin, vmax, label, units = COLORDEFS[varname]
        variables[varname] = {
            "label":      label,
            "units":      units,
            "type":       "scalar",
            "vmin":       vmin,
            "vmax":       vmax,
            "colorstops": cmap_to_hex(cmap),
        }

    # Collect all unique timesteps across domains
    all_ts = sorted({ts for m in domain_meta.values() for ts in m["timesteps"]})

    manifest = {
        "domains":   {d: m["bounds"] for d, m in domain_meta.items()},
        "variables": variables,
        "timesteps": all_ts,
        "years":     YEARS,
    }

    path = OUT_ROOT / "manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nManifest → {path}")
    print(f"  Domains:   {list(manifest['domains'])}")
    print(f"  Variables: {list(manifest['variables'])}")
    print(f"  Timesteps: {len(manifest['timesteps'])}")


# ── Entry point ─────────────────────────────────────────────────────────────

def main():
    domain_meta = {}
    for domain in DOMAINS:
        domain_meta[domain] = process_domain(domain)
    build_manifest(domain_meta)
    print("\nPreprocessing complete.")


if __name__ == "__main__":
    main()
