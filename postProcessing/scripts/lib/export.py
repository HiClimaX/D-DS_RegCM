"""
Export utilities: RegCM5 projected grid → web-friendly formats.

  make_regridder()  →  fast repeated interpolation via precomputed Delaunay
  to_scalar_png()   →  colorized transparent PNG + bounds JSON (image overlay)
"""
import json
from pathlib import Path

import cmocean
import matplotlib.colors as mcolors
import numpy as np
from PIL import Image
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import Delaunay

# ── Color scale definitions ────────────────────────────────────────────────
# (cmap, vmin, vmax, label, display_units)
COLORDEFS = {
    "tas":       (cmocean.cm.thermal, 15,  40,  "Temperature (2m mean)",  "°C"),
    "tasmax":    (cmocean.cm.thermal, 20,  45,  "Temperature (2m max)",   "°C"),
    "tasmin":    (cmocean.cm.thermal, 10,  35,  "Temperature (2m min)",   "°C"),
    "pr":        (cmocean.cm.rain,    0,   30,  "Precipitation (daily)",  "mm/day"),
    "prmax":     (cmocean.cm.rain,    0,   20,  "Precip max (hourly)",    "mm/hr"),
    "sfcWindmax":(cmocean.cm.speed,   0,   30,  "Wind speed max (10m)",   "m/s"),
    "psavg":     (cmocean.cm.diff,    990, 1025,"Sea-level Pressure",     "hPa"),
}

N_COLORSTOPS = 12


def cmap_to_hex(cmap, n: int = N_COLORSTOPS) -> list[str]:
    return [mcolors.to_hex(cmap(i / (n - 1))) for i in range(n)]


# ── Regridding ─────────────────────────────────────────────────────────────

def make_target_grid(xlat: np.ndarray, xlon: np.ndarray, resolution: float | None = None):
    """Compute a regular lat/lon grid covering the model domain."""
    lat_min, lat_max = float(xlat.min()), float(xlat.max())
    lon_min, lon_max = float(xlon.min()), float(xlon.max())

    if resolution is None:
        dlat = (lat_max - lat_min) / xlat.shape[0]
        dlon = (lon_max - lon_min) / xlon.shape[1]
        resolution = max(round(min(dlat, dlon), 2), 0.05)

    target_lat = np.arange(lat_max, lat_min - resolution / 2, -resolution)
    target_lon = np.arange(lon_min, lon_max + resolution / 2, resolution)
    return target_lat, target_lon


def make_regridder(xlat: np.ndarray, xlon: np.ndarray,
                   target_lat: np.ndarray, target_lon: np.ndarray):
    """
    Return a fast regrid(data_2d) callable.
    Precomputes Delaunay triangulation once; reuses it for every field.
    """
    valid = np.isfinite(xlat) & np.isfinite(xlon)
    pts = np.column_stack([xlon[valid].ravel(), xlat[valid].ravel()])
    tri = Delaunay(pts)

    lon_grid, lat_grid = np.meshgrid(target_lon, target_lat)

    def regrid(data_2d: np.ndarray) -> np.ndarray:
        vals = np.asarray(data_2d, dtype=float)[valid].ravel()
        interp = LinearNDInterpolator(tri, vals)
        return interp(lon_grid, lat_grid)   # shape (ny, nx)

    regrid.target_lat = target_lat
    regrid.target_lon = target_lon
    return regrid


# ── Scalar PNG export ──────────────────────────────────────────────────────

def to_scalar_png(data_2d: np.ndarray, regrid, varname: str, out_png: Path):
    """
    Colorize a scalar field and write a transparent PNG + sidecar bounds JSON.
    Returns the bounds dict.
    """
    cmap, vmin, vmax, _, _ = COLORDEFS.get(varname, (cmocean.cm.thermal, None, None, "", ""))

    grid = regrid(data_2d)

    if vmin is None:
        vmin = float(np.nanpercentile(grid[np.isfinite(grid)], 2))
    if vmax is None:
        vmax = float(np.nanpercentile(grid[np.isfinite(grid)], 98))

    norm = mcolors.Normalize(vmin=vmin, vmax=vmax, clip=True)
    rgba = cmap(norm(grid), bytes=True)          # (ny, nx, 4) uint8

    nan_mask = ~np.isfinite(grid)
    rgba[nan_mask, 3] = 0

    img = Image.fromarray(rgba, mode="RGBA")
    img.save(out_png, "PNG", optimize=True)

    target_lat = regrid.target_lat
    target_lon = regrid.target_lon
    bounds = {
        "sw": [float(target_lat[-1]), float(target_lon[0])],
        "ne": [float(target_lat[0]),  float(target_lon[-1])],
        "vmin": vmin,
        "vmax": vmax,
    }
    bounds_path = out_png.with_suffix(".bounds.json")
    with open(bounds_path, "w") as f:
        json.dump(bounds, f)

    return bounds


# ── Grayscale value PNG (for client-side colorization) ─────────────────────

def to_value_png(data_2d: np.ndarray, regrid, varname: str, out_png: Path):
    """
    Export a scalar field as a grayscale value PNG for client-side colorization.

    Pixel R=G=B = normalized value (0–255 mapping vmin–vmax).
    Alpha = 0 for NaN/out-of-domain, 255 for valid data.
    The sidecar .bounds.json includes vmin/vmax so the browser can reconstruct values.
    """
    cmap, vmin, vmax, _, _ = COLORDEFS.get(varname, (cmocean.cm.thermal, None, None, "", ""))

    grid = regrid(data_2d)

    if vmin is None:
        vmin = float(np.nanpercentile(grid[np.isfinite(grid)], 2))
    if vmax is None:
        vmax = float(np.nanpercentile(grid[np.isfinite(grid)], 98))

    # Normalize to [0, 1], clamp
    norm = np.clip((grid - vmin) / (vmax - vmin), 0, 1)
    gray = (norm * 255).astype(np.uint8)

    # Alpha channel: 0 for NaN, 255 for valid
    alpha = np.where(np.isfinite(grid), 255, 0).astype(np.uint8)

    # RGBA with R=G=B=gray so canvas reads correctly (avoids premultiply issues)
    rgba = np.zeros((*grid.shape, 4), dtype=np.uint8)
    rgba[..., 0] = gray
    rgba[..., 1] = gray
    rgba[..., 2] = gray
    rgba[..., 3] = alpha

    img = Image.fromarray(rgba, mode="RGBA")
    img.save(out_png, "PNG", optimize=True)

    target_lat = regrid.target_lat
    target_lon = regrid.target_lon
    bounds = {
        "sw": [float(target_lat[-1]), float(target_lon[0])],
        "ne": [float(target_lat[0]),  float(target_lon[-1])],
        "vmin": vmin,
        "vmax": vmax,
    }
    bounds_path = out_png.with_suffix(".bounds.json")
    with open(bounds_path, "w") as f:
        json.dump(bounds, f)

    return bounds
