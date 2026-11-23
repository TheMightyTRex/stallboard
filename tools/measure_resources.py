#!/usr/bin/env python3
"""Measures what running plug-ins use, on a Starboard server, and writes data/resources/<id>.json.

Run it on the server (it needs the docker command, and only READS: docker ps, docker stats, docker inspect):
    python3 tools/measure_resources.py [--samples 6] [--gap 4] [--out data/resources] [--ids extra-id ...]
Then open a pull request with the files. Each file says when it was measured and how. Only containers named
plugin-<id>-<container> for a plug-in id in listings/ (or given with --ids) are written.
Memory at rest is the MEDIAN of the samples; the most seen is the largest. Run it when the plug-ins are quiet, so
"at rest" means rest; a plug-in that was not running is not written, so it stays "Not measured yet"."""
import argparse
import datetime as dt
import json
import pathlib
import re
import statistics
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "lib"))
import resources  # noqa: E402

UNITS = {"b": 1 / 1048576, "kib": 1 / 1024, "kb": 1 / 1000 * 0.953674, "mib": 1, "mb": 0.953674, "gib": 1024, "gb": 953.674}


def mib(s):
    """'24.5MiB' -> 24.5, '1.2GiB' -> 1228.8 (the first figure of docker's 'used / limit')."""
    m = re.match(r"^\s*([\d.]+)\s*([A-Za-z]+)", str(s).split("/")[0])
    return round(float(m.group(1)) * UNITS[m.group(2).lower()], 2) if m and m.group(2).lower() in UNITS else None


def run(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True).stdout


def plugin_of(container, ids):
    best = ""
    for i in ids:
        if container.startswith(f"plugin-{i}-") and len(i) > len(best):
            best = i
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=6)
    ap.add_argument("--gap", type=float, default=4)
    ap.add_argument("--out", default=str(ROOT / "data" / "resources"))
    ap.add_argument("--ids", nargs="*", default=[])
    a = ap.parse_args()
    ids = [p.stem for p in (ROOT / "listings").glob("*.json")] + a.ids
    names = [n for n in run("docker", "ps", "--format", "{{.Names}}").split() if n.startswith("plugin-")]
    names = [n for n in names if plugin_of(n, ids)]
    if not names:
        sys.exit("No running plug-in containers found.")
    samples = {n: [] for n in names}
    for i in range(a.samples):
        for line in run("docker", "stats", "--no-stream", "--format", "{{json .}}", *names).splitlines():
            d = json.loads(line)
            samples[d["Name"]].append((mib(d["MemUsage"]), float(d["CPUPerc"].rstrip("%"))))
        if i + 1 < a.samples:
            time.sleep(a.gap)
    out = {}
    for n in names:
        s = [x for x in samples[n] if x[0] is not None]
        if not s:
            continue
        insp = json.loads(run("docker", "inspect", n))[0]
        host = insp.get("HostConfig", {})
        img = json.loads(run("docker", "image", "inspect", insp["Image"]))[0]
        one = {"container": n, "memory_mib_median": round(statistics.median(x[0] for x in s), 1), "memory_mib_max": max(x[0] for x in s),
               "cpu_percent_median": round(statistics.median(x[1] for x in s), 2), "image_size_mb": round(img["Size"] / 1048576, 1)}
        if host.get("Memory"):
            one["memory_limit_mib"] = round(host["Memory"] / 1048576)
        if host.get("NanoCpus"):
            one["cpus_limit"] = round(host["NanoCpus"] / 1e9, 2)
        if host.get("PidsLimit"):
            one["pids_limit"] = host["PidsLimit"]
        out.setdefault(plugin_of(n, ids), []).append(one)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M+00:00")
    how = (f"docker stats, {a.samples} samples {a.gap:g} seconds apart, containers as they were running; "
           "image size is the unpacked local size")
    folder = pathlib.Path(a.out)
    folder.mkdir(parents=True, exist_ok=True)
    for pid, cs in out.items():
        data = {"plugin": pid, "measured_at": now, "how": how, "containers": cs}
        if not resources.clean(data):
            print("skipped", pid, "(figures not usable)")
            continue
        (folder / f"{pid}.json").write_text(json.dumps(data, indent=1) + "\n")
        print("wrote", pid, len(cs), "container(s)")


if __name__ == "__main__":
    main()
