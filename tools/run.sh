#!/usr/bin/env bash
# Runs the accessibility and behaviour checks, the screenshots or the social images in the Playwright image.
#   tools/run.sh check | shots | social       (build the site first: python3 tools/build.py)
# The same image runs in GitHub Actions. Locally, set PLAYWRIGHT_NPM_CACHE to mount an npm cache, as Starboard's tools/screenshots.sh does.
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
cache="${PLAYWRIGHT_NPM_CACHE:-}"   # a folder holding node_modules/playwright 1.63, to run offline; empty installs it
out="${OUT_DIR:-$here/reports}"
mkdir -p "$out"
if [ -n "$cache" ] && [ -d "$cache/node_modules/playwright" ]; then
  setup="ln -s /cache/node_modules node_modules"; mount=(-v "$cache:/cache:ro")
else
  setup="npm init -y >/dev/null && npm i --silent playwright@1.63.0 >/dev/null"; mount=()
fi
docker run --rm --memory 3g --memory-swap 3g --cpus 2 --network host -u "$(id -u):$(id -g)" -e HOME=/tmp \
  -e MODE="${1:-check}" -e SITE=/site/site -e AXE=/axe/axe.min.js -e OUT=/out \
  -v "$here:/site:ro" -v "$here/tools/axe:/axe:ro" -v "$out:/out" "${mount[@]}" mcr.microsoft.com/playwright:v1.63.0-noble \
  sh -c "mkdir -p /tmp/s && cp /site/tools/check.mjs /tmp/s/ && cd /tmp/s && $setup && node check.mjs"
