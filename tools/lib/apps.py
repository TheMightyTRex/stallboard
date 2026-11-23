"""Apps Starboard works with, which are not plug-ins: data/apps/<id>.json, one file for each. A page for each is built
from the file (sections of paragraphs and lists, and a links table), so adding an app is adding a file. Everything is
text, every address must be https, and nothing is shown that is not in the file."""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import manifest as mf  # noqa: E402

ID = r"^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$"
KEYS = {"id", "name", "tagline", "summary", "checked_at", "sections", "links"}


class AppError(ValueError):
    pass


def _s(v, most, what, required=True):
    if not isinstance(v, str) or (required and not v.strip()) or len(v) > most or any(ord(c) < 32 for c in v):
        raise AppError(f"{what} must be one line of text of up to {most} characters")
    return v.strip()


def _url(v, what):
    u = mf.https_or_empty(v)
    if not u:
        raise AppError(f"{what} must be an https address")
    return u


def _links(raw, what):
    out = []
    for x in raw or []:
        if not isinstance(x, dict) or set(x) - {"label", "url", "what"}:
            raise AppError(f"{what}: each link has a label, an address and what it is")
        out.append({"label": _s(x.get("label"), 80, "a link's label"), "url": _url(x.get("url"), "a link"),
                    "what": _s(x.get("what", ""), 160, "a link's description", False)})
    return out[:30]


def check(d, filename=None):
    if not isinstance(d, dict) or set(d) - KEYS or not {"id", "name", "tagline", "sections", "links"} <= set(d):
        raise AppError("An app file has id, name, tagline, summary, checked_at, sections and links, and nothing else")
    if not (isinstance(d["id"], str) and re.match(ID, d["id"])) or (filename and filename != d["id"] + ".json"):
        raise AppError("id must be lower case letters, numbers and hyphens, and the file must be called <id>.json")
    out = {"id": d["id"], "name": _s(d["name"], 40, "name"), "tagline": _s(d["tagline"], 120, "tagline"), "summary": _s(d.get("summary", ""), 240, "summary", False)}
    at = str(d.get("checked_at", ""))
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", at):
        raise AppError("checked_at must be a date such as 2026-11-23")
    out["checked_at"] = at
    secs, seen = [], set()
    for s in d["sections"] if isinstance(d["sections"], list) else []:
        if not isinstance(s, dict) or set(s) - {"id", "heading", "paragraphs", "list", "links"}:
            raise AppError("a section has id, heading, paragraphs, list and links")
        sid = _s(s.get("id"), 30, "a section id")
        if not re.match(r"^[a-z][a-z0-9-]*$", sid) or sid in seen:
            raise AppError("section ids are unique lower case words")
        seen.add(sid)
        secs.append({"id": sid, "heading": _s(s.get("heading"), 80, "a heading"), "paragraphs": [_s(p, 900, "a paragraph") for p in (s.get("paragraphs") or [])][:8],
                     "list": [_s(p, 300, "a list item") for p in (s.get("list") or [])][:12], "links": _links(s.get("links"), "a section")})
    if not secs:
        raise AppError("an app page needs at least one section")
    out["sections"] = secs
    out["links"] = _links(d["links"], "links")
    return out


def load_all(folder):
    out = {}
    for p in sorted(pathlib.Path(folder).glob("*.json")):
        try:
            out[p.stem] = check(json.loads(p.read_text()), p.name)
        except (ValueError, RecursionError) as e:
            raise AppError(f"{p.name}: {e}") from None
    return out
