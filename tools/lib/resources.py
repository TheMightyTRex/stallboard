"""What a plug-in uses. Two kinds of number, never mixed: Declared (the limits in its manifest) and Measured (written by
tools/measure_resources.py on a Starboard server, into data/resources/<id>.json). A maker may give figures in a
listing; those are shown as "Maker's figures, not measured by the reviewer". Nothing is ever invented: a figure that is
missing, not a real number or out of range is dropped, and the page says "Not measured yet"."""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import manifest as mf  # noqa: E402

DEFAULT_MEMORY_MB = 128  # Starboard's own default for a container that names no limit (starboard/plugins.py)
FIELDS = {"memory_mib_median": (0, 65536), "memory_mib_max": (0, 65536), "cpu_percent_median": (0, 1000),
          "memory_limit_mib": (1, 65536), "cpus_limit": (0.01, 64), "pids_limit": (1, 100000), "image_size_mb": (0, 100000),
          "data_size_mb": (0, 10000000)}


def clean(d):
    """A measurement file as a clean dict, or None. Unknown or bad figures are dropped, never repaired."""
    if not isinstance(d, dict):
        return None
    at = mf.text(d.get("measured_at"), 25)
    if not re.match(r"^\d{4}-\d{2}-\d{2}(T[\d:+Z.-]{1,20})?$", at):
        return None
    cs = []
    for c in (d.get("containers") or [])[:8] if isinstance(d.get("containers"), list) else []:
        if not isinstance(c, dict):
            continue
        one = {"container": mf.text(c.get("container"), 80)}
        for k, (lo, hi) in FIELDS.items():
            v = mf.number(c.get(k), lo, hi)
            if v is not None:
                one[k] = v
        if "memory_mib_median" in one:
            cs.append(one)
    if not cs:
        return None
    return {"plugin": mf.text(d.get("plugin"), 40), "measured_at": at, "how": mf.text(d.get("how"), 400), "containers": cs}


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
    return round(sum(vals), 2) if len(vals) == len(cs) and vals else None


def measured_totals(m):
    """Totals over a plug-in's containers, or None where a container has no figure (a partial sum would mislead)."""
    if not m:
        return None
    cs = m["containers"]
    return {"memory": _sum(cs, "memory_mib_median"), "memory_max": _sum(cs, "memory_mib_max"), "cpu": _sum(cs, "cpu_percent_median"),
            "image": _sum(cs, "image_size_mb"), "data": _sum(cs, "data_size_mb"), "count": len(cs)}


def declared(manifest):
    """The limits the manifest declares: {memory_mb (sum, with Starboard's default where one is not named), cpus, pids, default_used}."""
    res = manifest.get("resources") or {}
    mem = cpu = 0.0
    pids = None
    used_default = False
    cs = manifest.get("containers") or []
    for c in cs:
        r = res.get(c.get("name")) or {}
        if r.get("memory"):
            mem += r["memory"]
        else:
            mem += DEFAULT_MEMORY_MB
            used_default = True
        cpu += r.get("cpus") or 0.25
        if r.get("pids"):
            pids = (pids or 0) + r["pids"]
    return {"memory_mb": mem if cs else None, "cpus": round(cpu, 2) if cs else None, "pids": pids, "default_used": used_default}


def short_line(measured, maker):
    """The one line for a card or a row."""
    if measured and measured.get("memory") is not None:
        return f"About {fmt(measured['memory'])} MB of memory at rest"
    if maker:
        return f"Maker says about {fmt(maker['memory_mib'])} MB of memory at rest"
    return "Memory use not measured yet"


def fmt(n):
    n = float(n)
    return str(int(round(n))) if n >= 10 else f"{n:.1f}".rstrip("0").rstrip(".")


def rest_memory(measured, maker):
    """(MB, source) for sorting and for the catalogue's rest figure; source is measured, maker or None."""
    if measured and measured.get("memory") is not None:
        return measured["memory"], "measured"
    if maker:
        return maker["memory_mib"], "maker"
    return None, None
