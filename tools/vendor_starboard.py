#!/usr/bin/env python3
"""Refreshes vendor/starboard/ from a Starboard release: python3 tools/vendor_starboard.py v0.29.0

The submission checks run Starboard's own manifest check (starboard/plugins.py, check()). A copy of the few modules it
needs is kept in vendor/starboard/, unchanged, pinned to one release in vendor/starboard/VENDORED.json (the release and
the SHA-256 of each file). Nothing is downloaded when a submission is checked: a person refreshes the copy, in a pull
request, when Starboard's rules or permission names change. A test fails if a vendored file differs from its hash.
"""
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lib"))
import safefetch  # noqa: E402

FILES = ["__init__", "plugins", "app_logs", "plugin_styles", "plugin_update", "plugin_logo", "api_v1", "logs"]
BASE = "https://raw.githubusercontent.com/TheMightyTRex/starboard/"
OUT = HERE.parent / "vendor" / "starboard"


def main(tag):
    if not re.match(r"^v\d+\.\d+\.\d+$", tag):
        sys.exit("Give a release tag such as v0.29.0")
    hashes = {}
    got = {}
    for f in FILES:
        got[f + ".py"] = safefetch.fetch(f"{BASE}{tag}/starboard/{f}.py", max_bytes=512 * 1024)
    got["LICENSE"] = safefetch.fetch(f"{BASE}{tag}/LICENSE", max_bytes=64 * 1024)
    for name, data in got.items():
        (OUT / name).write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    (OUT / "VENDORED.json").write_text(json.dumps({"release": tag, "source": "https://github.com/TheMightyTRex/starboard",
                                                    "sha256": hashes}, indent=1) + "\n")
    print("Vendored Starboard", tag, "into", OUT)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
