"""A listing: listings/<id>.json, one file for each listed plug-in. The file says who reviewed it and when; the
manifest (as a committed snapshot) says everything else."""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import manifest as mf  # noqa: E402
import safefetch  # noqa: E402

ID = r"^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$"
SEMVER = r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$"
DATE = r"^\d{4}-\d{2}-\d{2}$"
KEYS = {"id", "name", "manifest", "maker", "listed_at", "reviewed", "notes", "kind", "help", "recommended", "older_versions",
        "maker_figures", "pitch"}
REQUIRED = {"id", "name", "manifest", "maker", "listed_at", "reviewed"}
OWN_MAKERS = ("TheMightyTRexUK",)  # the owner's own plug-ins carry the mark "Starboard's own"


class ListingError(ValueError):
    pass


def _text(d, key, most, required=True):
    v = d.get(key)
    if v is None and not required:
        return ""
    if not isinstance(v, str) or not (1 if required else 0) <= len(v.strip()) <= most or any(ord(c) < 32 for c in v):
        raise ListingError(f"{key} must be one line of text of up to {most} characters")
    return v.strip()


def check(d, filename=None):
    """The listing as a clean dict, or ListingError saying what is wrong."""
    if not isinstance(d, dict):
        raise ListingError("A listing must be a JSON object")
    extra, missing = sorted(set(d) - KEYS), sorted(REQUIRED - set(d))
    if extra:
        raise ListingError("Unknown field " + ", ".join(extra))
    if missing:
        raise ListingError("Missing field " + ", ".join(missing))
    out = {}
    if not (isinstance(d["id"], str) and re.match(ID, d["id"])):
        raise ListingError("id must be 3 to 40 lower case letters, numbers and hyphens")
    if filename is not None and filename != d["id"] + ".json":
        raise ListingError(f"The file must be called {d['id']}.json")
    out["id"] = d["id"]
    out["name"] = _text(d, "name", 40)
    try:
        safefetch.check_address(d["manifest"])
    except safefetch.FetchError as e:
        raise ListingError("manifest: " + str(e)) from None
    out["manifest"] = d["manifest"]
    out["maker"] = _text(d, "maker", 60)
    for k in ("listed_at",):
        if not (isinstance(d[k], str) and re.match(DATE, d[k])):
            raise ListingError(f"{k} must be a date such as 2026-11-23")
        out[k] = d[k]
    r = d["reviewed"]
    if not isinstance(r, dict) or set(r) != {"by", "at", "version"}:
        raise ListingError("reviewed must have by, at and version")
    if not (isinstance(r["at"], str) and re.match(DATE, r["at"])) or not (isinstance(r["version"], str) and re.match(SEMVER, r["version"])):
        raise ListingError("reviewed.at must be a date and reviewed.version a version such as 1.2.0")
    out["reviewed"] = {"by": _text(r, "by", 60), "at": r["at"], "version": r["version"]}
    out["notes"] = _text(d, "notes", 500, False)
    out["pitch"] = _text(d, "pitch", 110, False)
    if "kind" in d:
        if d["kind"] not in mf.KINDS:
            raise ListingError("kind must be one of: " + ", ".join(mf.KINDS))
        out["kind"] = d["kind"]
    if "help" in d:
        out["help"] = d["help"] if isinstance(d["help"], str) and re.match(r"^https://[^\s\"'<>]{1,400}$", d["help"]) else ""
        if not out["help"]:
            raise ListingError("help must be an https address")
    out["recommended"] = d.get("recommended") is True
    if "recommended" in d and not isinstance(d["recommended"], bool):
        raise ListingError("recommended must be true or false")
    older = []
    for v in d.get("older_versions") or []:
        if not isinstance(v, dict) or not (isinstance(v.get("version"), str) and re.match(SEMVER, v["version"])) \
                or not mf.https_or_empty(v.get("manifest")):
            raise ListingError("each older version needs a version and an https manifest address")
        sha = str(v.get("manifest_sha256") or "").lower()
        older.append({"version": v["version"], "starboard_api": mf.text(v.get("starboard_api"), 40), "manifest": v["manifest"],
                      "manifest_sha256": sha if re.match(r"^[0-9a-f]{64}$", sha) else ""})
    out["older_versions"] = older[:20]
    mfig = d.get("maker_figures")
    if mfig is not None:
        if not isinstance(mfig, dict) or set(mfig) - {"memory_mib", "cpu_percent"}:
            raise ListingError("maker_figures may hold memory_mib and cpu_percent only")
        mem, cpu = mf.number(mfig.get("memory_mib"), 0.1, 65536), mf.number(mfig.get("cpu_percent", 0), 0, 1000)
        if mem is None or cpu is None:
            raise ListingError("maker_figures must be real numbers in a sensible range (memory 0.1 to 65536 MiB, processor 0 to 1000 %)")
        out["maker_figures"] = {"memory_mib": mem, "cpu_percent": cpu}
    return out


def load_all(folder):
    """{id: listing} for every listings/*.json; raises ListingError naming the file."""
    out = {}
    for p in sorted(pathlib.Path(folder).glob("*.json")):
        try:
            out[p.stem] = check(json.loads(p.read_text()), p.name)
        except (ValueError, RecursionError) as e:
            raise ListingError(f"{p.name}: {e}") from None
    return out


def is_own(listing):
    return listing["maker"] in OWN_MAKERS
