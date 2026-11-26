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
    """The docker calls, on one chosen daemon. Tests replace run(). With via="<container>" every call runs inside that
    Docker-in-Docker container (docker exec), so no socket is shared with this computer's Docker."""

    def __init__(self, host=None, via=None):
        self.env = dict(os.environ)
        self.via = via
        if host:
            self.env["DOCKER_HOST"] = host

    def run(self, *cmd, timeout=120):
        pre = ("exec", self.via) if self.via else ()
        return subprocess.run(("docker",) + pre + (() if not self.via else ("docker",)) + cmd, capture_output=True, text=True, timeout=timeout, check=True, env=self.env).stdout

    def outer(self, *cmd, timeout=120):
        """A call on the daemon this computer uses (the one that runs the Docker-in-Docker container), for `exec` only."""
        return subprocess.run(("docker",) + cmd, capture_output=True, text=True, timeout=timeout, check=True, env=dict(os.environ)).stdout

    def _cgroup_file(self, cid, name):
        cands = [f"/sys/fs/cgroup/docker/{cid}/{name}", f"/sys/fs/cgroup/{cid}/{name}", f"/sys/fs/cgroup/system.slice/docker-{cid}.scope/{name}"]
        for p in cands:
            try:
                if self.via:
                    return self.outer("exec", self.via, "cat", p)
                return pathlib.Path(p).read_text()
            except (OSError, subprocess.CalledProcessError):
                continue
        return None

    def cgroup_mib(self, cid):
        t = self._cgroup_file(cid, "memory.current")
        try:
            return round(int(t) / 1048576, 1) if t else None
        except ValueError:
            return None

    def cgroup_cpu_usec(self, cid):
        m = re.search(r"^usage_usec (\d+)", self._cgroup_file(cid, "cpu.stat") or "", re.M)
        return int(m.group(1)) if m else None

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


def measure(docker, ids, phase, settle, cpu_seconds, sleep=time.sleep, clock=time.monotonic, folder=OUT, version="", now=None, only=None):
    names = [n for n in docker.names() if plugin_of(n, ids) and (not only or plugin_of(n, ids) in only)]
    if not names:
        raise SystemExit("No running plug-in containers found on that daemon. Start the test Starboard and add the plug-ins first.")
    sleep(settle)
    infos = {n: docker.inspect(n) for n in names}
    cids = {n: infos[n]["Id"] for n in names}
    cpu_read = getattr(docker, "cgroup_cpu_usec", cgroup_cpu_usec)
    mem_read = getattr(docker, "cgroup_mib", cgroup_mib)
    before = {n: cpu_read(cids[n]) for n in names}
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
            after = cpu_read(cids[n])
            cpu = round(max(0.0, (after - before[n]) / 1e6 / elapsed * 100), 2) if after is not None and before[n] is not None else round(statistics.mean(x[1] for x in s), 2)
        values = {"memory": round(statistics.median(x[0] for x in s), 1), "cgroup": mem_read(cids[n]), "cpu": cpu,
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


PLUGINS_REPO = os.environ.get("PLUGINS_REPO") or str(ROOT.parent / "starboard-plugins")


def raw_manifest(pid, root=ROOT):
    """The whole reviewed manifest (the snapshots keep a trimmed one), from the plug-ins repository at the listed commit, only if its
    SHA-256 is the reviewed one."""
    import hashlib
    snap = json.loads((root / "data" / "snapshots" / f"{pid}.json").read_text())
    m = re.match(r"https://raw\.githubusercontent\.com/[^/]+/[^/]+/([0-9a-f]{40})/(.+)$", snap["manifest"])
    got = subprocess.run(["git", "-C", PLUGINS_REPO, "show", f"{m.group(1)}:{m.group(2)}"], capture_output=True) if m else None
    if got is None or got.returncode or hashlib.sha256(got.stdout).hexdigest() != snap["sha256"]:
        raise RuntimeError("the reviewed manifest could not be read from PLUGINS_REPO")
    return json.loads(got.stdout)


def run_args(pid, manifest, c):
    """`docker run` arguments that start one manifest container in the test daemon as Starboard would, with its declared limits:
    its volumes as empty named volumes, its env (a {secret:...} or {...} value becomes a made-up word), user, command and tmpfs.
    Files Starboard would write into it are not written, so a plug-in that needs one may not start: that is recorded."""
    lim = (manifest.get("resources") or {}).get(c["name"]) or {}
    name = f"plugin-{pid}-{c['name']}"
    a = ["run", "-d", "--name", name, "--label", "stallbench=1", "--network", f"stallbench-{pid}", "--network-alias", c["name"],
         "--memory", f"{lim.get('memory') or 128}m", "--cpus", str(lim.get("cpus") or 0.25), "--pids-limit", str(lim.get("pids") or 256),
         "--security-opt", "no-new-privileges", "--cap-drop", "ALL"]
    for v in c.get("volumes") or []:
        path, _, mode = str(v).partition(":")
        target = "/" + path.lstrip("/")
        a += ["-v", f"stallbench-{pid}-{path.replace('/', '-')}:{target}" + (":ro" if mode == "ro" else "")]
    for k, v in (c.get("env") or {}).items():
        a += ["-e", f"{k}={re.sub(r'[{][^}]*[}]', 'example', str(v))}"]
    for t in c.get("tmpfs") or []:
        a += ["--tmpfs", t]
    if c.get("user") and str(c["user"]) not in ("media",):
        a += ["--user", str(c["user"])]
    if c.get("entrypoint"):
        a += ["--entrypoint", c["entrypoint"][0]]
    a.append(c["image"])
    a += (c["entrypoint"][1:] if c.get("entrypoint") else []) + list(c.get("command") or [])
    return a


def start_plugin(docker, pid, manifest):
    """Starts every container of the plug-in (databases first as listed) on its own network. Returns the container names."""
    docker.run("network", "create", f"stallbench-{pid}")
    names = []
    for c in manifest.get("containers", []):
        docker.run(*run_args(pid, manifest, c), timeout=1800)  # the pull is the long part
        names.append(f"plugin-{pid}-{c['name']}")
    return names


def use_plugin(docker, pid, manifest, requests=20):
    """The 'use' between the two readings: HTTP requests to each container's home page and health address from inside the test
    daemon's own network (a real Starboard and browser are not run here), so the plug-in has answered work before the second reading."""
    for c in manifest.get("containers", []):
        if not c.get("port"):
            continue
        for path in ("/", "/health"):
            for _ in range(requests // 2):
                try:
                    docker.run("run", "--rm", "--network", f"stallbench-{pid}", "busybox", "wget", "-q", "-T", "3", "-O", "/dev/null",
                               f"http://{c['name']}:{c['port']}{path}", timeout=30)
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    pass  # an error page still counts as use; a plug-in with no answer is seen in the memory figure


def stop_plugin(docker, pid, manifest):
    """Removes its containers, network, volumes and then its images, so disk use stays bounded."""
    for c in manifest.get("containers", []):
        for cmd in (("rm", "-f", f"plugin-{pid}-{c['name']}"),):
            try:
                docker.run(*cmd)
            except subprocess.CalledProcessError:
                pass
    for cmd in (("network", "rm", f"stallbench-{pid}"),):
        try:
            docker.run(*cmd)
        except subprocess.CalledProcessError:
            pass
    try:
        vols = docker.run("volume", "ls", "-q", "--filter", f"name=stallbench-{pid}-").split()
        if vols:
            docker.run("volume", "rm", "-f", *vols)
    except subprocess.CalledProcessError:
        pass
    for c in manifest.get("containers", []):
        try:
            docker.run("rmi", "-f", c["image"])
        except subprocess.CalledProcessError:
            pass


def record_problem(pid, text, folder=OUT, version="", now=None):
    pathlib.Path(folder).mkdir(parents=True, exist_ok=True)
    rec = {"plugin": pid, "measured_at": (now or dt.datetime.now(dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M+00:00"), "no_container": False, "problem": text[:300],
           "environment": {"kind": "test server, made-up data", "starboard_version": version, "machine": machine()}, "containers": []}
    (pathlib.Path(folder) / f"{pid}.json").write_text(json.dumps(rec, indent=1) + "\n")


def one_by_one(docker, ids, a, sleep=time.sleep):
    """For each plug-in in turn: start, let it settle, measure, use, measure, remove. A plug-in that does not start, or is stopped by
    its memory limit, is recorded with the reason, and the next one begins."""
    for pid in ids:
        manifest = raw_manifest(pid)
        if not manifest.get("containers"):
            continue
        print("==", pid, flush=True)
        try:
            names = start_plugin(docker, pid, manifest)
            sleep(a.settle)
            running = [n for n in docker.names() if n in names]
            if len(running) < len(names):
                gone = [n for n in names if n not in running]
                why = ""
                try:
                    why = docker.run("inspect", "-f", "exit {{.State.ExitCode}}, killed by memory limit: {{.State.OOMKilled}}", gone[0]).strip()
                except subprocess.CalledProcessError:
                    pass
                record_problem(pid, f"Did not stay running on the test server ({', '.join(gone)} stopped; {why})", version=a.starboard_version)
                continue
            measure(docker, ids, "start", 0, a.cpu_seconds, version=a.starboard_version, only={pid})
            use_plugin(docker, pid, manifest)
            measure(docker, ids, "used", 0, 0, version=a.starboard_version, only={pid})
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, RuntimeError, SystemExit) as e:
            err = getattr(e, "stderr", "") or str(e)
            record_problem(pid, f"Did not start on the test server: {' '.join(str(err).split())[:200]}", version=a.starboard_version)
        finally:
            stop_plugin(docker, pid, manifest)


def table(root=ROOT, folder=OUT):
    """docs/PLUGIN-MEMORY.md: one row for each plug-in, read from the files (nothing is invented)."""
    rows = []
    t = testbench.load_all(folder)
    ids = sorted(p.stem for p in (root / "listings").glob("*.json"))
    for pid in ids:
        r = t.get(pid)
        if r is None:
            rows.append(f"| {pid} | not measured yet | | | | | |")
        elif r.get("problem") and not r["containers"]:
            rows.append(f"| {pid} | did not run: {r['problem'].replace('|', '/')} | | | | | |")
        elif r["no_container"]:
            rows.append(f"| {pid} | no container | | | | | |")
        else:
            x = testbench.totals(r)
            f = lambda v: "" if v is None else f"{v:g}"  # noqa: E731
            rows.append(f"| {pid} | {x['count']} | {f(x['memory_start'])} | {f(x['memory_used'])} | {f(x['cgroup_start'])} / {f(x['cgroup_used'])} | {f(x['cpu'])} | {f(x['image'])} |")
    body = ("# Plug-in memory, processor and image size on a test Starboard\n\n"
            "Written by `python3 tools/measure_plugins.py`. Measured on a test Starboard that holds made-up data, never on a real server. "
            "Memory is docker stats in MiB, idle after start and again after the screenshots used the plug-in. The cgroup column is memory.current "
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
    ap.add_argument("--ids", nargs="*", default=[], help="only these plug-ins")
    ap.add_argument("--via", default="", help="the name of a Docker-in-Docker container: every call runs inside it (docker exec)")
    ap.add_argument("--start", action="store_true", help="start each plug-in from its manifest in the test daemon, one at a time")
    a = ap.parse_args()
    if a.table or a.manifests_only:
        if a.manifests_only:
            print(manifests_only(version=a.starboard_version), "plug-ins with no container")
        DOC.write_text(table())
        return
    if not a.docker_host and not a.via and not a.allow_default_docker and "DOCKER_HOST" not in os.environ:
        sys.exit("Refusing to use this computer's own Docker: that is the live server. Give --docker-host of the test Starboard's daemon.")
    ids = [p.stem for p in (ROOT / "listings").glob("*.json")]
    d = Docker(a.docker_host or None, a.via or None)
    if a.start:
        one_by_one(d, a.ids or ids, a)
        DOC.write_text(table())
        return
    if a.phase in ("start", "both"):
        measure(d, ids, "start", a.settle, a.cpu_seconds, version=a.starboard_version)
    if a.phase == "both" and a.use_command:
        subprocess.run(a.use_command, shell=True, check=True)  # the screenshot step, which is what uses the plug-ins
    if a.phase in ("used", "both"):
        measure(d, ids, "used", 0, 0, version=a.starboard_version)
    DOC.write_text(table())


if __name__ == "__main__":
    main()
