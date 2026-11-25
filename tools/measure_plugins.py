#!/usr/bin/env python3
"""Measures what each plug-in uses on a TEST Starboard that holds made-up data, and writes data/resources-test/<id>.json and
docs/PLUGIN-MEMORY.md. It never touches the owner's live server: it refuses the default Docker daemon unless that is allowed in
words (--allow-default-docker), because the default daemon on this computer is the live server's.

One repeatable command (the plug-ins' containers are the ones the test Starboard started, named plugin-<id>-<container>):

    python3 tools/measure_plugins.py --docker-host ssh://test-box --phase both --use-command "tools/plugin-shots.sh ../starboard"

  --phase start      memory (docker stats MiB, and the cgroup's memory.current when this computer can read it) once the plug-in has
                     been idle for --settle seconds after it started, and the processor averaged over --cpu-seconds (default 60)
  --phase used       memory again, after the screenshots have used it (run --use-command in between with --phase both)
  --phase both       start, then --use-command, then used
  --manifests-only   no Docker: a plug-in whose manifest names no container is written as "no container" (for example Styles)
  --table            only rewrite docs/PLUGIN-MEMORY.md from the files

Processor is the container's own CPU time (cgroup cpu.stat, else the average of docker stats readings) over the window, as a percent
of one core. Image size is the unpacked local size. Read-only commands only: docker ps, stats, inspect, image inspect."""
import argparse
import datetime as dt
import json
import os
import pathlib
import platform
import re
import statistics
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "lib"))
import testbench  # noqa: E402

OUT = ROOT / "data" / "resources-test"
DOC = ROOT / "docs" / "PLUGIN-MEMORY.md"
UNITS = {"b": 1 / 1048576, "kib": 1 / 1024, "mib": 1, "gib": 1024, "kb": 0.000953674, "mb": 0.953674, "gb": 953.674}


def mib(s):
    """'24.5MiB / 1GiB' -> 24.5 (the first figure of docker's used / limit)."""
    m = re.match(r"^\s*([\d.]+)\s*([A-Za-z]+)", str(s).split("/")[0])
    return round(float(m.group(1)) * UNITS[m.group(2).lower()], 2) if m and m.group(2).lower() in UNITS else None


class Docker:
    """The read-only docker calls, on one chosen daemon. Tests replace run()."""

    def __init__(self, host=None):
        self.env = dict(os.environ)
        if host:
            self.env["DOCKER_HOST"] = host

    def run(self, *cmd):
        return subprocess.run(("docker",) + cmd, capture_output=True, text=True, timeout=120, check=True, env=self.env).stdout

    def names(self):
        return [n for n in self.run("ps", "--format", "{{.Names}}").split() if n.startswith("plugin-")]

    def stats(self, names):
        out = {}
        for line in self.run("stats", "--no-stream", "--format", "{{json .}}", *names).splitlines():
            d = json.loads(line)
            out[d["Name"]] = (mib(d["MemUsage"]), float(d["CPUPerc"].rstrip("%") or 0))
        return out

    def inspect(self, name):
        return json.loads(self.run("inspect", name))[0]

    def image_mb(self, image_id):
        return round(json.loads(self.run("image", "inspect", image_id))[0]["Size"] / 1048576, 1)


def cgroup_dir(cid):
    for base in ("/sys/fs/cgroup/system.slice", "/sys/fs/cgroup/docker", "/sys/fs/cgroup"):
        p = pathlib.Path(base) / f"docker-{cid}.scope"
        if p.exists():
            return p
        p = pathlib.Path(base) / cid
        if p.exists():
            return p
    return None


def cgroup_mib(cid):
    d = cgroup_dir(cid)
    try:
        return round(int((d / "memory.current").read_text()) / 1048576, 1) if d else None
    except (OSError, ValueError):
        return None


def cgroup_cpu_usec(cid):
    d = cgroup_dir(cid)
    try:
        m = re.search(r"^usage_usec (\d+)", (d / "cpu.stat").read_text(), re.M) if d else None
        return int(m.group(1)) if m else None
    except OSError:
        return None


def plugin_of(container, ids):
    best = ""
    for i in ids:
        if container.startswith(f"plugin-{i}-") and len(i) > len(best):
            best = i
    return best


def machine():
    cores = os.cpu_count() or 0
    mem = ""
    try:
        kb = int(re.search(r"MemTotal:\s+(\d+)", pathlib.Path("/proc/meminfo").read_text()).group(1))
        mem = f", {round(kb / 1048576)} GB memory"
    except (OSError, AttributeError):
        pass
    return f"{platform.system()} {platform.machine()}, {cores} cores{mem}"


def merge_phase(existing, phase, container, values):
    """Puts one container's figures for a phase into the plug-in's record (start: memory_*_start; used: memory_*_used)."""
    cs = existing.setdefault("containers", [])
    row = next((c for c in cs if c["container"] == container), None)
    if row is None:
        row = {"container": container}
        cs.append(row)
    suffix = "start" if phase == "start" else "used"
    if values.get("memory") is not None:
        row[f"memory_mib_{suffix}"] = values["memory"]
    if values.get("cgroup") is not None:
        row[f"cgroup_mib_{suffix}"] = values["cgroup"]
    for k in ("cpu", "image"):
        if values.get(k) is not None and phase == "start":
            row["cpu_percent_60s" if k == "cpu" else "image_size_mb"] = values[k]
    return existing


def measure(docker, ids, phase, settle, cpu_seconds, sleep=time.sleep, clock=time.monotonic, folder=OUT, version="", now=None):
    names = [n for n in docker.names() if plugin_of(n, ids)]
    if not names:
        raise SystemExit("No running plug-in containers found on that daemon. Start the test Starboard and add the plug-ins first.")
    sleep(settle)
    infos = {n: docker.inspect(n) for n in names}
    cids = {n: infos[n]["Id"] for n in names}
    before = {n: cgroup_cpu_usec(cids[n]) for n in names}
    t0 = clock()
    samples = {n: [] for n in names}
    mem = {}
    step = max(1.0, cpu_seconds / 12) if phase == "start" else 0
    reads = 12 if phase == "start" else 1
    for i in range(reads):
        got = docker.stats(names)
        for n, (m, c) in got.items():
            samples[n].append((m, c))
            mem[n] = m
        if i + 1 < reads:
            sleep(step)
    elapsed = max(0.001, clock() - t0)
    out = {}
    for n in names:
        s = [x for x in samples[n] if x[0] is not None]
        if not s:
            continue
        cpu = None
        if phase == "start":
            after = cgroup_cpu_usec(cids[n])
            cpu = round(max(0.0, (after - before[n]) / 1e6 / elapsed * 100), 2) if after is not None and before[n] is not None else round(statistics.mean(x[1] for x in s), 2)
        values = {"memory": round(statistics.median(x[0] for x in s), 1), "cgroup": cgroup_mib(cids[n]), "cpu": cpu,
                  "image": docker.image_mb(infos[n]["Image"]) if phase == "start" else None}
        pid = plugin_of(n, ids)
        path = pathlib.Path(folder) / f"{pid}.json"
        rec = json.loads(path.read_text()) if path.exists() else {"plugin": pid}
        rec.update({"measured_at": (now or dt.datetime.now(dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M+00:00"), "no_container": False,
                    "environment": {"kind": "test server, made-up data", "starboard_version": version, "machine": machine()},
                    "how": f"docker stats and cgroup memory.current, idle {settle:g} s after start and again after the screenshots used it; "
                           f"processor over {cpu_seconds:g} s; image size is the unpacked local size"})
        out[pid] = merge_phase(rec, phase, n, values)
    pathlib.Path(folder).mkdir(parents=True, exist_ok=True)
    for pid, rec in out.items():
        if testbench.clean(rec):
            (pathlib.Path(folder) / f"{pid}.json").write_text(json.dumps(rec, indent=1) + "\n")
            print("wrote", pid, len(rec["containers"]), "container(s)")
    return out


def manifests_only(folder=OUT, root=ROOT, version="", now=None):
    """Plug-ins whose manifest names no container run nothing, so there is nothing to measure: say so, from the manifest."""
    n = 0
    for f in sorted((root / "data" / "snapshots").glob("*.json")):
        m = json.loads(f.read_text())["manifest_data"]
        if m.get("containers"):
            continue
        pathlib.Path(folder).mkdir(parents=True, exist_ok=True)
        rec = {"plugin": m["id"], "measured_at": (now or dt.datetime.now(dt.timezone.utc)).strftime("%Y-%m-%d"), "no_container": True,
               "environment": {"kind": "read from the manifest", "starboard_version": version, "machine": ""},
               "how": "its manifest names no container, so it runs nothing of its own"}
        (pathlib.Path(folder) / f"{m['id']}.json").write_text(json.dumps(rec, indent=1) + "\n")
        n += 1
    return n


def table(root=ROOT, folder=OUT):
    """docs/PLUGIN-MEMORY.md: one row for each plug-in, read from the files (nothing is invented)."""
    rows = []
    t = testbench.load_all(folder)
    ids = sorted(p.stem for p in (root / "listings").glob("*.json"))
    for pid in ids:
        r = t.get(pid)
        if r is None:
            rows.append(f"| {pid} | not measured yet | | | | | |")
        elif r["no_container"]:
            rows.append(f"| {pid} | no container | | | | | |")
        else:
            x = testbench.totals(r)
            f = lambda v: "" if v is None else f"{v:g}"  # noqa: E731
            rows.append(f"| {pid} | {x['count']} | {f(x['memory_start'])} | {f(x['memory_used'])} | {f(x['cgroup_start'])} / {f(x['cgroup_used'])} | {f(x['cpu'])} | {f(x['image'])} |")
    body = ("# Plug-in memory, processor and image size on a test Starboard\n\n"
            "Written by `python3 tools/measure_plugins.py`. Measured on a test Starboard that holds made-up data, never on a real server. "
            "Memory is docker stats in MiB, idle after start and again after the screenshots used the plug-in; the cgroup column is memory.current "
            "for the same two moments. Processor is a percent of one core averaged over 60 seconds idle. Image size is the unpacked size in MB. "
            "Figures are summed over a plug-in's containers; a blank is a figure that could not be read.\n\n"
            "| Plug-in | Containers | Memory at start (MiB) | Memory after use (MiB) | cgroup start / after use (MiB) | Processor (% of a core) | Image (MB) |\n"
            "|---|---|---|---|---|---|---|\n" + "\n".join(rows) + "\n")
    return body


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--docker-host", default="")
    ap.add_argument("--allow-default-docker", action="store_true")
    ap.add_argument("--phase", choices=["start", "used", "both"], default="both")
    ap.add_argument("--use-command", default="")
    ap.add_argument("--settle", type=float, default=60)
    ap.add_argument("--cpu-seconds", type=float, default=60)
    ap.add_argument("--starboard-version", default="")
    ap.add_argument("--manifests-only", action="store_true")
    ap.add_argument("--table", action="store_true")
    a = ap.parse_args()
    if a.table or a.manifests_only:
        if a.manifests_only:
            print(manifests_only(version=a.starboard_version), "plug-ins with no container")
        DOC.write_text(table())
        return
    if not a.docker_host and not a.allow_default_docker and "DOCKER_HOST" not in os.environ:
        sys.exit("Refusing to use this computer's own Docker: that is the live server. Give --docker-host of the test Starboard's daemon.")
    ids = [p.stem for p in (ROOT / "listings").glob("*.json")]
    d = Docker(a.docker_host or None)
    if a.phase in ("start", "both"):
        measure(d, ids, "start", a.settle, a.cpu_seconds, version=a.starboard_version)
    if a.phase == "both" and a.use_command:
        subprocess.run(a.use_command, shell=True, check=True)  # the screenshot step, which is what uses the plug-ins
    if a.phase in ("used", "both"):
        measure(d, ids, "used", 0, 0, version=a.starboard_version)
    DOC.write_text(table())


if __name__ == "__main__":
    main()
