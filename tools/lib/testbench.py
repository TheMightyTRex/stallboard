"""Figures measured on a TEST Starboard that holds made-up data (tools/measure_plugins.py writes data/resources-test/<id>.json).
Kept apart from the figures measured on a real server (resources.py): the pages label each one. A figure that is missing, not a
real number or out of range is dropped, never repaired, and a plug-in with no figures is shown as "Not measured yet"."""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import manifest as mf  # noqa: E402

FIELDS = {"memory_mib_start": (0, 65536), "memory_mib_used": (0, 65536), "cgroup_mib_start": (0, 65536), "cgroup_mib_used": (0, 65536),
          "cpu_percent_60s": (0, 1000), "image_size_mb": (0, 100000)}


def clean(d):
    """A test measurement as a clean dict, or None. {"no_container": True} when the plug-in runs nothing of its own."""
    if not isinstance(d, dict):
        return None
    at = mf.text(d.get("measured_at"), 25)
    if not re.match(r"^\d{4}-\d{2}-\d{2}(T[\d:+Z.-]{1,20})?$", at):
        return None
    env = d.get("environment") if isinstance(d.get("environment"), dict) else {}
    out = {"plugin": mf.text(d.get("plugin"), 40), "measured_at": at, "how": mf.text(d.get("how"), 400),
           "starboard_version": mf.text(env.get("starboard_version"), 20), "machine": mf.text(env.get("machine"), 120), "containers": [], "no_container": False}
    if d.get("no_container") is True:
        out["no_container"] = True
        return out
    cs = d.get("containers")
    for c in (cs[:8] if isinstance(cs, list) else []):
        if not isinstance(c, dict):
            continue
        one = {"container": mf.text(c.get("container"), 80)}
        for k, (lo, hi) in FIELDS.items():
            v = mf.number(c.get(k), lo, hi)
            if v is not None:
                one[k] = v
        if "memory_mib_start" in one or "memory_mib_used" in one:
            out["containers"].append(one)
    return out if out["containers"] else None


def load_all(folder):
    out = {}
    for p in sorted(pathlib.Path(folder).glob("*.json")):
        try:
            c = clean(json.loads(p.read_text()))
        except (ValueError, RecursionError):
            c = None
        if c:
            out[p.stem] = c
    return out


def _sum(cs, key):
    vals = [c[key] for c in cs if key in c]
    return round(sum(vals), 1) if len(vals) == len(cs) and vals else None


def totals(t):
    """Sums over the containers, None where one has no figure (a partial sum would mislead); None for no figures at all."""
    if not t or t["no_container"]:
        return None
    cs = t["containers"]
    return {"memory_start": _sum(cs, "memory_mib_start"), "memory_used": _sum(cs, "memory_mib_used"), "cgroup_start": _sum(cs, "cgroup_mib_start"),
            "cgroup_used": _sum(cs, "cgroup_mib_used"), "cpu": _sum(cs, "cpu_percent_60s"), "image": _sum(cs, "image_size_mb"), "count": len(cs)}


def sort_memory(t):
    """The figure the listings sort by: memory after use, else at start (MiB), or None."""
    tt = totals(t)
    if not tt:
        return 0.0 if t and t["no_container"] else None
    return tt["memory_used"] if tt["memory_used"] is not None else tt["memory_start"]
