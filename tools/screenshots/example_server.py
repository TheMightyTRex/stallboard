#!/usr/bin/env python3
"""Starboard's example server (made-up data, nothing real is read, nothing leaves this computer) with Stallboard's own
catalogue and the reviewed manifests, for the plug-in pictures (tools/plugin-shots.sh).

    python3 tools/screenshots/example_server.py <starboard checkout> <data folder> <port>

Starboard's example server starts with made-up apps and some plug-ins already added. This wrapper makes both of
Starboard's catalogue addresses answer with site/catalogue.json (build the site first) and each manifest address answer
with the manifest in data/snapshots, so the Catalogue lists every plug-in in this store and Install shows what it asks for.
No network request is made and no container is started."""
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent.parent
starboard, data, port = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, str(pathlib.Path(starboard) / "tools" / "screenshots"))
sys.argv = ["example_server.py", data, port]
import example_server as ex  # noqa: E402  (Starboard's example server: its set-up runs on import, main() below)
from starboard import plugins_admin  # noqa: E402

CATALOGUE = json.loads((HERE / "site" / "catalogue.json").read_text())
# Starboard's install check reads a plug-in's whole manifest, which the snapshots do not keep (they hold the trimmed one the site
# shows). The whole file is read from the plug-ins repository at the same commit as the listing, and used only if its SHA-256 is the
# one that was reviewed (PLUGINS_REPO, a checkout of TheMightyTRex/starboard-plugins; only read).
PLUGINS_REPO = os.environ.get("PLUGINS_REPO") or str(HERE.parent / "starboard-plugins")
MANIFESTS = {}
for f in (HERE / "data" / "snapshots").glob("*.json"):
    s = json.loads(f.read_text())
    m = re.match(r"https://raw\.githubusercontent\.com/[^/]+/[^/]+/([0-9a-f]{40})/(.+)$", s["manifest"])
    got = subprocess.run(["git", "-C", PLUGINS_REPO, "show", f"{m.group(1)}:{m.group(2)}"], capture_output=True) if m else None
    if got is not None and got.returncode == 0 and hashlib.sha256(got.stdout).hexdigest() == s["sha256"]:
        MANIFESTS[s["manifest"]] = json.loads(got.stdout)
    else:
        sys.exit(f"{f.stem}: the reviewed manifest could not be read from PLUGINS_REPO ({PLUGINS_REPO}) at that commit")
_real_catalogue, _real_manifest = plugins_admin.fetch_catalogue, plugins_admin.fetch_manifest


def catalogue(address, opener=None):
    if address in (plugins_admin.CATALOGUE_URL, plugins_admin.BUILTIN_SOURCES[0]["url"]):
        return {"name": "Stallboard", "items": [x for x in map(plugins_admin._clean_entry, CATALOGUE["plugins"]) if x]}
    return _real_catalogue(address, opener)


def manifest(address, opener=None, sha256=""):
    if address in MANIFESTS:
        return json.loads(json.dumps(MANIFESTS[address]))
    return _real_manifest(address, opener) if not sha256 else _real_manifest(address, opener, sha256)


plugins_admin.fetch_catalogue = catalogue
plugins_admin.fetch_manifest = manifest
ex.main()
