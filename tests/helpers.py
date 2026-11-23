import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
for p in (ROOT / "tools" / "lib", ROOT / "tools", ROOT / "vendor"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
