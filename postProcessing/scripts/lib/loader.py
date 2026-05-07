"""Data loading utilities for RegCM5 output.

Data layout (flat, inside analyze/regcm5-out/):
    {domain}_{vartype}.{YYYYMMDD}00.nc
    e.g.  d01_STS.2011080100.nc
"""
import glob
from pathlib import Path

import xarray as xr

_LIB_DIR = Path(__file__).parent
ANALYZE_DIR = _LIB_DIR.parent.parent
DATA_ROOT = ANALYZE_DIR / "regcm5-out"   # flat – no domain subdirs

DOMAINS = ["d01", "d02", "d03"]
YEARS = ["2011", "2014", "2015"]
VARTYPES = ["STS"]   # only STS available; extend when other types are added


def _glob(domain: str, vartype: str, year: str | None = None) -> list[Path]:
    prefix = f"{domain}_{vartype}"
    pattern = f"{prefix}.{year}*.nc" if year else f"{prefix}.*.nc"
    return sorted(DATA_ROOT.glob(pattern))


def load_august(domain: str, vartype: str, year: str) -> xr.Dataset:
    """Load the August file for a domain/vartype/year (selects month==8 only)."""
    files = _glob(domain, vartype, f"{year}0801")
    if not files:
        raise FileNotFoundError(
            f"No August file in {DATA_ROOT}/ for {domain}_{vartype}.{year}0801*.nc"
        )
    # One file per month — open_dataset is sufficient (avoids dask dependency)
    ds = xr.open_dataset(str(files[0]), decode_times=True)
    return ds.sel(time=ds.time.dt.month == 8)


def load_all_august(domain: str, vartype: str) -> xr.Dataset:
    """Load August data for all three years concatenated."""
    parts = []
    for year in YEARS:
        try:
            parts.append(load_august(domain, vartype, year))
        except FileNotFoundError:
            pass
    if not parts:
        raise FileNotFoundError(f"No August data at all for {domain} {vartype}")
    return xr.concat(parts, dim="time", data_vars="minimal", coords="minimal", compat="override")


def get_coords(domain: str, vartype: str = "STS"):
    """Return (xlat, xlon) numpy arrays for the domain grid."""
    # Use any available year's August file for coordinates
    for year in YEARS:
        files = _glob(domain, vartype, f"{year}0801")
        if files:
            with xr.open_dataset(str(files[0])) as ds:
                return ds["xlat"].values.copy(), ds["xlon"].values.copy()
    raise FileNotFoundError(f"No {vartype} file found for {domain} in {DATA_ROOT}/")
