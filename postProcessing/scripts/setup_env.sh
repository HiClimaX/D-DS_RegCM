#!/usr/bin/env bash
# Create the hiclimax-analysis conda environment.
# Run once from the analyze/ directory:
#   bash scripts/setup_env.sh

set -e

ENV_NAME="hiclimax-analysis"

if conda env list | grep -q "^${ENV_NAME}"; then
  echo "Environment '${ENV_NAME}' already exists — skipping creation."
  echo "To update packages: conda activate ${ENV_NAME} && conda install -c conda-forge <pkg>"
else
  echo "Creating conda environment '${ENV_NAME}' …"
  conda create -n "${ENV_NAME}" -c conda-forge \
    python=3.11 \
    xarray netcdf4 scipy numpy pandas \
    matplotlib cartopy cmocean \
    jupyterlab notebook \
    jinja2 \
    Pillow \
    tqdm \
    -y
  echo ""
  echo "Done. Activate with:"
  echo "  conda activate ${ENV_NAME}"
fi

echo ""
echo "Next steps:"
echo "  conda activate ${ENV_NAME}"
echo "  python scripts/preprocess.py       # export web data (~5-15 min)"
echo "  bash scripts/serve.sh              # start local HTTP server"
