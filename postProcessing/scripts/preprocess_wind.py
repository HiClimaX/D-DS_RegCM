#!/usr/bin/env python
"""
Preprocess RegCM5 SRF wind output → leaflet-velocity JSON for the HiClimaX map.

RegCM5 stores uas/vas as *grid-relative* wind on a Lambert Conformal Conic
projection.  We must:
  1. Rotate (uas, vas) from grid-relative to true (east, north) components
  2. Regrid from the projected 2-D grid to a regular lat/lon grid
  3. Write the leaflet-velocity JSON format (U + V header/data arrays)

Run once:
    conda activate hiclimax-analysis
    python scripts/preprocess_wind.py

Outputs (under output/site/data/):
    {domain}/wind_{YYYYMMDDHH}.json   -- leaflet-velocity JSON
    manifest.json                     -- updated with wind variable
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import Delaunay
from tqdm import tqdm

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from lib.loader import ANALYZE_DIR, DATA_ROOT, DOMAINS, YEARS

OUT_ROOT = ANALYZE_DIR / "output/site/data"
OUT_ROOT.mkdir(parents=True, exist_ok=True)


# ── Wind rotation: grid-relative → true East/North ─────────────────────────
def rotation_angle_lcc(xlon: np.ndarray, lon0: float) -> np.ndarray:
    """
    Compute the rotation angle (radians) for Lambert Conformal Conic.

    For LCC the grid-north direction differs from true north by an angle
    proportional to (lon - lon0) × sin(lat0).  RegCM5 uses standard_parallel
    but for the rotation we need the cone constant n.

    For a 2-SP LCC:  n = ln(cos φ1 / cos φ2) / ln(tan(π/4 + φ2/2) / tan(π/4 + φ1/2))
    But a simpler (and adequate) approach: the rotation angle α at each point
    is:  α = n × (lon - lon0)   where n = sin(lat0) for a tangent cone,
    or computed from the two standard parallels.

    RegCM5's d01/d02/d03 all share:
      standard_parallel: [30, 40]
      longitude_of_central_meridian: 139.6
    """
    # Compute cone constant n for 2-SP LCC
    phi1 = np.radians(30.0)
    phi2 = np.radians(40.0)
    n = (np.log(np.cos(phi1)) - np.log(np.cos(phi2))) / \
        (np.log(np.tan(np.pi / 4 + phi2 / 2)) - np.log(np.tan(np.pi / 4 + phi1 / 2)))

    alpha = n * np.radians(xlon - lon0)
    return alpha


def rotate_wind(uas: np.ndarray, vas: np.ndarray,
                xlon: np.ndarray, lon0: float = 139.6):
    """
    Rotate grid-relative (uas, vas) to true (u_east, v_north).

    uas = grid-eastward, vas = grid-northward
    u_east =  uas × cos(α) + vas × sin(α)
    v_north = -uas × sin(α) + vas × cos(α)
    """
    alpha = rotation_angle_lcc(xlon, lon0)
    cos_a = np.cos(alpha)
    sin_a = np.sin(alpha)

    u_east  =  uas * cos_a + vas * sin_a
    v_north = -uas * sin_a + vas * cos_a
    return u_east, v_north


# ── Regular grid + regridding ──────────────────────────────────────────────
def make_regular_grid(xlat, xlon, resolution=None, inset_cells=2):
    """Build a regular lat/lon target grid covering the model domain.
    
    inset_cells: shrink the domain by this many grid cells on each side
    to avoid Delaunay edge artifacts (long triangles at boundaries).
    """
    lat_min, lat_max = float(xlat.min()), float(xlat.max())
    lon_min, lon_max = float(xlon.min()), float(xlon.max())

    if resolution is None:
        dlat = (lat_max - lat_min) / xlat.shape[0]
        dlon = (lon_max - lon_min) / xlon.shape[1]
        resolution = max(round(min(dlat, dlon), 2), 0.05)

    # Inset the domain to avoid edge interpolation artifacts
    margin = resolution * inset_cells
    lat_min += margin
    lat_max -= margin
    lon_min += margin
    lon_max -= margin

    target_lat = np.arange(lat_max, lat_min - resolution / 2, -resolution)
    target_lon = np.arange(lon_min, lon_max + resolution / 2, resolution)
    return target_lat, target_lon, resolution


def build_regridder(xlat, xlon, target_lat, target_lon):
    """Build Delaunay-based regridder (precompute triangulation once)."""
    valid = np.isfinite(xlat) & np.isfinite(xlon)
    pts = np.column_stack([xlon[valid].ravel(), xlat[valid].ravel()])
    tri = Delaunay(pts)

    lon_grid, lat_grid = np.meshgrid(target_lon, target_lat)

    def regrid(data_2d: np.ndarray) -> np.ndarray:
        vals = np.asarray(data_2d, dtype=float)[valid].ravel()
        interp = LinearNDInterpolator(tri, vals)
        result = interp(lon_grid, lat_grid)
        return result

    return regrid


# ── leaflet-velocity JSON export ───────────────────────────────────────────
def wind_to_velocity_json(u_grid: np.ndarray, v_grid: np.ndarray,
                          target_lat: np.ndarray, target_lon: np.ndarray,
                          dx: float, dy: float,
                          ref_time: str) -> list:
    """
    Build the leaflet-velocity JSON structure.

    Format: array of two objects (U, V), each with header + data.
    Data is row-major, starting from lat_max (north), going south.
    NaN values are replaced with JSON null (leaflet-velocity skips them).
    """
    ny, nx = u_grid.shape

    # Convert to Python lists with None for NaN (serializes as JSON null)
    def to_list_with_null(arr):
        flat = np.round(arr, 2).ravel()
        return [None if not np.isfinite(v) else float(v) for v in flat]

    u_list = to_list_with_null(u_grid)
    v_list = to_list_with_null(v_grid)

    header_common = {
        "lo1": round(float(target_lon[0]), 4),
        "la1": round(float(target_lat[0]), 4),   # north-most latitude
        "dx":  round(dx, 4),
        "dy":  round(dy, 4),
        "nx":  nx,
        "ny":  ny,
        "refTime": ref_time,
    }

    return [
        {
            "header": {
                **header_common,
                "parameterCategory": 2,
                "parameterNumber": 2,
                "parameterUnit": "m.s-1",
                "parameterNumberName": "eastward_wind",
            },
            "data": u_list,
        },
        {
            "header": {
                **header_common,
                "parameterCategory": 2,
                "parameterNumber": 3,
                "parameterUnit": "m.s-1",
                "parameterNumberName": "northward_wind",
            },
            "data": v_list,
        },
    ]


# ── Per-domain processing ──────────────────────────────────────────────────
def ts_key(ts: pd.Timestamp) -> str:
    """Normalize to daily key YYYYMMDD00 to match STS scalar convention."""
    return ts.strftime("%Y%m%d") + "00"


def process_domain(domain: str) -> dict:
    print(f"\n{'='*60}\nWind: {domain}\n{'='*60}")

    out_dir = OUT_ROOT / domain
    out_dir.mkdir(exist_ok=True)

    # Open any SRF file to get coordinates + CRS
    sample_file = None
    for year in YEARS:
        candidates = sorted(DATA_ROOT.glob(f"{domain}_SRF.{year}0801*.nc"))
        if candidates:
            sample_file = candidates[0]
            break
    if sample_file is None:
        print(f"  No SRF files for {domain} — skipping")
        return {"timesteps": []}

    with xr.open_dataset(str(sample_file)) as ds0:
        xlat = ds0["xlat"].values.copy()
        xlon = ds0["xlon"].values.copy()

    target_lat, target_lon, res = make_regular_grid(xlat, xlon)
    print(f"  Grid {xlat.shape} → regular {len(target_lat)}×{len(target_lon)} (res={res}°)")
    print(f"  lat [{target_lat[-1]:.2f}, {target_lat[0]:.2f}]")
    print(f"  lon [{target_lon[0]:.2f}, {target_lon[-1]:.2f}]")

    print("  Building Delaunay triangulation …", end=" ", flush=True)
    regrid = build_regridder(xlat, xlon, target_lat, target_lon)
    print("done")

    exported_ts = []

    for year in YEARS:
        srf_files = sorted(DATA_ROOT.glob(f"{domain}_SRF.{year}0801*.nc"))
        if not srf_files:
            print(f"  SKIP {year}: no SRF August file")
            continue

        ds = xr.open_dataset(str(srf_files[0]), decode_times=True)
        ds_aug = ds.sel(time=ds.time.dt.month == 8)
        times = pd.DatetimeIndex(ds_aug.time.values)
        print(f"\n  {year}: {len(times)} timesteps")

        for i, ts in enumerate(tqdm(times, desc=f"  {domain}/{year}")):
            key = ts_key(ts)
            out_json = out_dir / f"wind_{key}.json"

            if out_json.exists():
                exported_ts.append(key)
                continue

            # Extract uas/vas, squeeze m10 dimension
            uas_raw = ds_aug["uas"].isel(time=i)
            vas_raw = ds_aug["vas"].isel(time=i)
            if "m10" in uas_raw.dims:
                uas_raw = uas_raw.squeeze("m10", drop=True)
                vas_raw = vas_raw.squeeze("m10", drop=True)

            uas_data = uas_raw.values.astype(np.float32)
            vas_data = vas_raw.values.astype(np.float32)

            # Rotate from grid-relative to true East/North
            u_east, v_north = rotate_wind(uas_data, vas_data, xlon)

            # Regrid to regular lat/lon
            u_reg = regrid(u_east)
            v_reg = regrid(v_north)

            # Build velocity JSON
            ref_time = pd.Timestamp(ts).strftime("%Y-%m-%dT%H:%M:%SZ")
            velocity = wind_to_velocity_json(
                u_reg, v_reg, target_lat, target_lon,
                dx=res, dy=res, ref_time=ref_time,
            )

            with open(out_json, "w") as f:
                json.dump(velocity, f, separators=(",", ":"))

            exported_ts.append(key)

        ds.close()

    return {"timesteps": sorted(set(exported_ts))}


# ── Manifest update ────────────────────────────────────────────────────────
def update_manifest(wind_meta: dict):
    """Add wind variable to the existing manifest (preserves scalar data)."""
    manifest_path = OUT_ROOT / "manifest.json"

    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
    else:
        manifest = {"domains": {}, "variables": {}, "timesteps": [], "years": YEARS}

    # Add wind variable definition
    manifest["variables"]["wind"] = {
        "label": "Wind (10m)",
        "units": "m/s",
        "type": "velocity",
        "vmin": 0,
        "vmax": 25,
        "colorstops": [
            "#3288bd", "#66c2a5", "#abdda4", "#e6f598",
            "#fee08b", "#fdae61", "#f46d43", "#d53e4f",
            "#9e0142", "#67001f", "#40000c", "#1a0005",
        ],
    }

    # Merge wind timesteps into existing timesteps
    wind_ts = set()
    for m in wind_meta.values():
        wind_ts.update(m["timesteps"])

    existing_ts = set(manifest.get("timesteps", []))
    merged_ts = sorted(existing_ts | wind_ts)
    manifest["timesteps"] = merged_ts

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nManifest updated → {manifest_path}")
    print(f"  Wind timesteps added: {len(wind_ts)}")
    print(f"  Total timesteps: {len(merged_ts)}")


# ── Entry point ────────────────────────────────────────────────────────────
def main():
    wind_meta = {}
    for domain in DOMAINS:
        wind_meta[domain] = process_domain(domain)
    update_manifest(wind_meta)
    print("\nWind preprocessing complete.")


if __name__ == "__main__":
    main()
