#!/usr/bin/env bash
# Serve the static site locally.
# Run from the analyze/ directory:
#   bash scripts/serve.sh

PORT=${1:-8080}
SITE_DIR="$(dirname "$0")/../output/site"

echo "Serving HiClimaX site at http://localhost:${PORT}"
echo "Open: http://localhost:${PORT}/index.html"
echo "Press Ctrl+C to stop."
echo ""

cd "${SITE_DIR}"
python -m http.server "${PORT}"
