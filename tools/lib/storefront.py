"""The storefront text of each plug-in (data/storefront/<id>.json) and its pictures (data/shots.json, assets/shots/<id>/).

The text is written from the plug-in's own README and help pages and never states what they do not. A file that is
broken or breaks the writing rules stops the build, because it is a mistake in this repository. A plug-in with no file
still builds, from its manifest. Standard library only."""
import json
import pathlib
import re

LIMITS = {"summary": 140, "for": 400, "needs": 450, "shows": 600}
BANNED = [(re.compile(r"[–—]"), "a dash used as punctuation"), (re.compile(r"\b\w+n't\b|\bit's\b|\bthat's\b|\bthey're\b|\bwe're\b|\byou're\b|\byou'll\b|\byou've\b", re.I), "a contraction"),
          (re.compile(r"\b(see|look)\b", re.I), "the word See or Look")]


SERVERS = ["jellyfin", "plex", "emby"]


class StorefrontError(ValueError):
    pass


def _words(path, text):
    for rx, what in BANNED:
        m = rx.search(text)
        if m:
            raise StorefrontError(f"{path}: has {what}: {m.group(0)!r}")


def check(pid, d):
    path = f"data/storefront/{pid}.json"
    if not isinstance(d, dict):
        raise StorefrontError(f"{path}: must be an object")
    for k in ("summary", "for", "needs", "shows"):
        if not isinstance(d.get(k), str) or not d[k].strip():
            raise StorefrontError(f"{path}: {k} must be some text")
        if len(d[k]) > LIMITS[k]:
            raise StorefrontError(f"{path}: {k} is {len(d[k])} characters, the most is {LIMITS[k]}")
        _words(path, d[k])
    if not isinstance(d.get("does"), list) or not 1 <= len(d["does"]) <= 3 or not all(isinstance(x, str) and 20 < len(x) <= 600 for x in d["does"]):
        raise StorefrontError(f"{path}: does must be 1 to 3 paragraphs of up to 600 characters")
    for x in d["does"]:
        _words(path, x)
    if not isinstance(d.get("tags"), list) or not all(isinstance(x, str) and re.fullmatch(r"[a-z0-9][a-z0-9 .+-]{0,30}", x) for x in d["tags"]) or len(d["tags"]) > 12:
        raise StorefrontError(f"{path}: tags must be up to 12 short lowercase words")
    ms = d.get("media_servers")
    if not isinstance(ms, list) or not ms or not set(ms) <= set(SERVERS) or len(set(ms)) != len(ms):
        raise StorefrontError(f"{path}: media_servers must be a list of jellyfin, plex and emby (all three when the plug-in is not about a media server)")
    if d.get("media_servers_basis") not in ("api", "text", "none"):
        raise StorefrontError(f"{path}: media_servers_basis must be api, text or none")
    return {"media_servers": [x for x in SERVERS if x in ms], "media_basis": d["media_servers_basis"], "summary": d["summary"].strip(), "does": [x.strip() for x in d["does"]], "for": d["for"].strip(), "needs": d["needs"].strip(),
            "shows": d["shows"].strip(), "tags": d["tags"]}


def load_all(folder):
    out = {}
    for f in sorted(pathlib.Path(folder).glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise StorefrontError(f"{f.name}: cannot be read: {e}")
        out[f.stem] = check(f.stem, d)
    return out


def open_questions(folder):
    """What the owner still has to say, from the 'unclear' lists (used by tools/open_questions.py, never shown on the site)."""
    out = {}
    for f in sorted(pathlib.Path(folder).glob("*.json")):
        q = json.loads(f.read_text(encoding="utf-8")).get("unclear") or []
        if q:
            out[f.stem] = q
    return out


def load_shots(data_file, assets_dir):
    """{plug-in id: [{file, alt, caption}]} for pictures that exist as files."""
    try:
        raw = json.loads(pathlib.Path(data_file).read_text(encoding="utf-8"))
    except OSError:
        return {}
    out = {}
    for pid, items in raw.get("plugins", {}).items():
        keep = []
        for s in items:
            f = pathlib.Path(assets_dir) / pid / s["file"]
            if re.fullmatch(r"[\w.-]+\.(webp|png|jpg)", s["file"]) and f.exists() and len(s.get("alt", "")) >= 20:
                keep.append({"file": f"assets/shots/{pid}/{s['file']}", "alt": s["alt"], "caption": s.get("caption", ""), "w": s.get("w"), "h": s.get("h")})
        if keep:
            out[pid] = keep
    return out
