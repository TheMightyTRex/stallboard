"""A plug-in's manifest as DATA: Starboard's own check, a trimmed copy for the site, and the snapshot that is committed.

Nothing here runs or imports anything a plug-in's maker provides. The manifest is parsed as JSON text; the logo is
cleaned by Starboard's own logo code (vendor/starboard/plugin_logo.py), which rebuilds an SVG from the few drawing
elements it allows and refuses scripts, links, images and styles.
"""
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "vendor"))
sys.path.insert(0, str(HERE))
import safefetch  # noqa: E402
from starboard import plugin_logo, plugins  # noqa: E402

STARBOARD_RELEASE = json.loads((HERE.parent.parent / "vendor" / "starboard" / "VENDORED.json").read_text())["release"]
KINDS = ["Apps you can add", "Jellyfin", "Network", "System", "Accessibility", "Downloads", "Home", "Appearance"]
MAX_MANIFEST = 256 * 1024
MAX_VERSIONS = 40
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
GROUPS = (("added", "Added"), ("changed", "Changed"), ("fixed", "Fixed"), ("deprecated", "Deprecated"),
          ("removed", "Removed"), ("security", "Security"))


def text(value, most):
    """Any value as one clean line of at most `most` characters: no control characters, spaces tidied."""
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        return ""
    s = "".join(c if (c >= " " and c != "\x7f") else " " for c in str(value))
    return " ".join(s.split())[:most]


def whole_words(s, most=600):
    """At most `most` characters, ending at a sentence or a word, never mid-word (as Starboard's catalogue does)."""
    s = " ".join(str(s or "").split())
    if len(s) <= most:
        return s
    cut = s[:most]
    ends = [m.start() for m in re.finditer(r"[.!?](?= )", cut)]
    if ends and ends[-1] + 1 >= most // 2:
        return cut[:ends[-1] + 1]
    return cut.rsplit(" ", 1)[0] + "…"


def number(value, low, high):
    """A real number in a sane range, or None. Never a bool, a string, NaN, infinity or a negative."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value != value or value in (float("inf"), float("-inf")) or not (low <= value <= high):
        return None
    return value


def problems(manifest):
    """Starboard's own check, plus what a storefront adds. Plain sentences; empty when it passes."""
    try:
        out = list(plugins.check(manifest))
        if isinstance(manifest, dict):
            if plugins.builds(manifest):
                out.append("A container built from a zip cannot be installed from an address, so it cannot be listed")
            for i, c in enumerate(manifest.get("containers") or []):
                if isinstance(c, dict) and isinstance(c.get("image"), str) and not re.match(plugins.DIGEST_IMAGE, c["image"]) \
                        and c.get("build") is not True:
                    msg = f"containers[{i}]: the image must be pinned by digest (name@sha256:...), so what was reviewed is what runs"
                    if msg not in out:
                        out.append(msg)
    except RecursionError:
        return ["The manifest is nested too deeply"]
    except Exception:  # a hostile shape must never stop the checks: say it is wrong  # nosec B110
        return ["The manifest could not be checked: its shape is not the one Starboard expects"]
    return out


def kind_for(m):
    """A category when the listing does not name one: styles are Appearance, an app with its own page is Apps you can add."""
    perms = m.get("permissions") or []
    if m.get("styles") or "appearance:styles" in perms:
        return "Appearance"
    if "network:port" in perms:
        return "Apps you can add"
    if any(p.startswith("jellyfin:") for p in perms):
        return "Jellyfin"
    if "downloads:read" in perms:
        return "Downloads"
    if "network:vpn" in perms:
        return "Network"
    return "System"


def trim(m):
    """What the site keeps of a manifest: bounded text and numbers only, never the settings, cards or commands."""
    perms = [p for p in (m.get("permissions") or []) if isinstance(p, str) and p in plugins.PERMISSIONS] if isinstance(m.get("permissions"), list) else []
    containers = []
    for c in (m.get("containers") or [])[:4] if isinstance(m.get("containers"), list) else []:
        if isinstance(c, dict):
            containers.append({"name": text(c.get("name"), 30), "image": text(c.get("image"), 200), "port": number(c.get("port"), 1, 65535),
                               "network": text(c.get("network"), 10) or "default", "start": text(c.get("start"), 20) or "always",
                               "idle_stop_minutes": number(c.get("idle_stop_minutes"), 1, 100000),
                               "publish": number(c.get("publish"), 1, 65535) if not isinstance(c.get("publish"), bool) else None})
    resources = {}
    if isinstance(m.get("resources"), dict):
        for k, r in list(m["resources"].items())[:4]:
            if isinstance(r, dict):
                resources[text(k, 30)] = {"memory": number(r.get("memory"), 1, 65536), "cpus": number(r.get("cpus"), 0.01, 64),
                                          "pids": number(r.get("pids"), 1, 100000)}
    versions = []
    for ch in (m.get("changes") or [])[:MAX_VERSIONS] if isinstance(m.get("changes"), list) else []:
        if not isinstance(ch, dict):
            continue
        groups = []
        for key, label in GROUPS:
            items = ch.get(key)
            if isinstance(items, list):
                clean = [text(i, 500).replace("**", "") for i in items[:12] if isinstance(i, str)]
                clean = [i for i in clean if i]
                if clean:
                    groups.append([label, clean])
        date = text(ch.get("date"), 10)
        versions.append({"version": text(ch.get("version"), 30), "date": date if DATE.match(date) else "", "groups": groups})
    logo = m.get("logo") if isinstance(m.get("logo"), dict) else {}
    return {"id": text(m.get("id"), 40), "name": text(m.get("name"), 40), "version": text(m.get("version"), 30),
            "description": text(m.get("description"), 200), "author": text(m.get("author"), 60), "licence": text(m.get("licence"), 40),
            "homepage": text(m.get("homepage"), 300), "support_url": text(m.get("support_url"), 300),
            "starboard_api": text(m.get("starboard_api"), 40), "permissions": perms,
            "needs": [text(n, 30) for n in (m.get("needs") or [])[:8]] if isinstance(m.get("needs"), list) else [],
            "containers": containers, "resources": resources, "versions": versions,
            "logo": {"file": text(logo.get("file"), 80), "alt": text(logo.get("alt"), 80)} if logo else None}


def changelog_text(version):
    """One plain paragraph for a version, as Starboard's catalogue carries it (at most 600 characters)."""
    parts = []
    for _label, items in version.get("groups", []):
        parts += [i if i[-1:] in ".!?" else i + "." for i in items]
    return whole_words(" ".join(parts), 600)


def https_or_empty(url):
    return url if isinstance(url, str) and re.match(r"^https://[^\s\"'<>]{1,400}$", url) else ""


def make_snapshot(manifest_url, fetch=safefetch.fetch, now=None):
    """Fetch a manifest (and its logo) as data and return the snapshot dict. Raises safefetch.FetchError or ValueError."""
    raw = fetch(manifest_url, max_bytes=MAX_MANIFEST)
    try:
        m = json.loads(raw.decode("utf-8"))
    except (ValueError, RecursionError):
        raise ValueError("The address did not give a Starboard plug-in file: it is not valid JSON text") from None
    if not isinstance(m, dict):
        raise ValueError("The plug-in file must be one JSON object")
    found = problems(m)
    t = trim(m)
    logo_data = ""
    logo_note = ""
    if t["logo"] and not plugin_logo.check_entry(m.get("logo")):
        try:
            url = plugin_logo.address_beside(manifest_url, t["logo"]["file"])
            data, ctype = plugin_logo.clean(fetch(url, max_bytes=plugin_logo.PNG_MAX + 1), t["logo"]["file"])
            logo_data = plugin_logo.as_data(data, ctype)
        except (safefetch.FetchError, ValueError) as e:
            logo_note = str(e)[:200]
    now = now or dt.datetime.now(dt.timezone.utc)
    return {"id": t["id"], "manifest": manifest_url, "fetched_at": now.strftime("%Y-%m-%dT%H:%MZ"),
            "sha256": hashlib.sha256(raw).hexdigest(), "starboard_check": STARBOARD_RELEASE, "problems": found,
            "manifest_data": t, "logo": logo_data, "logo_note": logo_note}


def load_snapshot(path):
    """A committed snapshot, checked for shape. Raises ValueError with what is wrong."""
    s = json.loads(pathlib.Path(path).read_text())
    if not isinstance(s, dict) or not isinstance(s.get("manifest_data"), dict) or not isinstance(s.get("fetched_at"), str):
        raise ValueError(f"{path}: not a snapshot")
    if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z$", s["fetched_at"]):
        raise ValueError(f"{path}: fetched_at must look like 2026-11-23T16:00Z")
    return s


def snapshot_age_days(snap, today):
    d = dt.datetime.strptime(snap["fetched_at"], "%Y-%m-%dT%H:%MZ").date()
    return (today - d).days
