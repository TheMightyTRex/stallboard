#!/usr/bin/env bash
# Takes each plug-in's Catalogue row and "what it asks for" panel from a TEST copy of Starboard that holds made-up data only
# (never a real server), then makes the small pictures:   tools/plugin-shots.sh [path to a Starboard checkout]
# Build the site first (python3 tools/build.py): the test Starboard reads site/catalogue.json and data/snapshots. Nothing is
# fetched, no container starts. PLUGINS_REPO (default ../starboard-plugins) is a checkout of the plug-ins repository, read for each reviewed manifest. Needs Docker. The Starboard checkout is only read. Output goes to a temporary folder, then
# tools/make_shots.py writes assets/shots/<id>/*.webp and data/shots.json. Check every picture before committing.
set -euo pipefail
cd "$(dirname "$0")/.."
export PLUGINS_REPO="${PLUGINS_REPO:-$(cd ../starboard-plugins 2>/dev/null && pwd || true)}"
sb="$(cd "${1:-${STARBOARD_DIR:-../starboard}}" && pwd)"
PORT="${SHOTS_PORT:-18830}"
cache="${PLAYWRIGHT_NPM_CACHE:-}"   # a folder holding node_modules/playwright 1.63, to run offline
[ -d "$cache/node_modules/playwright" ] || cache=""
work="$(mktemp -d)"
trap 'kill "$server" 2>/dev/null || true; rm -rf "$work"' EXIT
python3 -c "import json; c=json.load(open('site/catalogue.json')); json.dump([{'id':p['id'],'name':p['name']} for p in c['plugins']], open('$work/plugins.json','w'))"
EXAMPLE_CONTAINERS=1 python3 tools/screenshots/example_server.py "$sb" "$work/data" "$PORT" > "$work/server.log" 2>&1 &
server=$!
for _ in $(seq 1 40); do grep -q READY "$work/server.log" 2>/dev/null && break; sleep 1; done
grep -q READY "$work/server.log" || { cat "$work/server.log"; echo "The test Starboard did not start" >&2; exit 1; }
mkdir -p "$work/out"
docker run --rm --memory 3g --memory-swap 3g --cpus 2 --network host -u "$(id -u):$(id -g)" -e HOME=/tmp \
  -e BASE="http://127.0.0.1:$PORT" -e PASSWORD_FILE=/work/data/password -e PLUGINS=/work/plugins.json -e OUT=/work/out -e ONLY="${ONLY:-}" \
  -v "$work:/work" -v "$PWD/tools/screenshots/plugin_shots.mjs:/shots/plugin_shots.mjs:ro" ${cache:+-v "$cache:/cache:ro"} \
  mcr.microsoft.com/playwright:v1.63.0-noble \
  sh -c "mkdir -p /tmp/s && cp /shots/plugin_shots.mjs /tmp/s/ && cd /tmp/s && if [ -d /cache/node_modules/playwright ]; then ln -s /cache/node_modules node_modules; else npm init -y >/dev/null && npm i --silent playwright@1.63.0 >/dev/null; fi && node plugin_shots.mjs" || true
python3 tools/make_shots.py "$work/out"
