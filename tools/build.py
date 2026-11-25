#!/usr/bin/env python3
"""Builds the whole site into site/ from listings/, data/snapshots/, data/resources/ and data/starboard-releases.json.
Standard library only. It never touches the network: a build works offline from the committed snapshots.

    python3 tools/build.py [--out site] [--today 2026-11-23] [--max-age 14]

A listing is left out of the site, with a warning that is printed and put in the run's summary, when its snapshot is
missing, is older than --max-age days, does not pass Starboard's check, or is for another plug-in. A build does not fail
because a maker's server was down: the old snapshot is used until it is too old (see docs in README, How it is built).
Exit code 1 only when a listing file or a data file is broken, which is a mistake in this repository."""
import argparse
import base64
import datetime as dt
import json
import os
import pathlib
import re
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "lib"))
import apps as appdata  # noqa: E402
import listing as lst  # noqa: E402
import manifest as mf  # noqa: E402
import pages  # noqa: E402
import releases as rl  # noqa: E402
import render as R  # noqa: E402
import resources as rs  # noqa: E402
import storefront as sfm  # noqa: E402

MAX_AGE_DAYS = 14
PINNED = re.compile(r"/[0-9a-f]{40}/")


def read_json(path, default):
    try:
        return json.loads(pathlib.Path(path).read_text())
    except OSError:
        return default


def merge(listings, snaps_dir, measures, releases, today, max_age, warnings, text=None, shots=None):
    text, shots = text or {}, shots or {}
    out = []
    for lid, l in listings.items():
        sp = snaps_dir / f"{lid}.json"
        if not sp.exists():
            warnings.append(f"{lid}: left out, because it has no snapshot (run tools/refresh_snapshots.py)")
            continue
        try:
            s = mf.load_snapshot(sp)
        except (ValueError, KeyError, OSError, RecursionError) as e:
            warnings.append(f"{lid}: LEFT OUT, because its snapshot is broken ({safe_line(e)})")
            continue
        age = mf.snapshot_age_days(s, today)
        if age > max_age:
            warnings.append(f"{lid}: LEFT OUT, because its snapshot is {age} days old (the limit is {max_age}). It is listed again when the snapshot is refreshed.")
            continue
        m = s["manifest_data"]
        if m.get("id") != lid or s.get("manifest") != l["manifest"]:
            warnings.append(f"{lid}: left out, because its snapshot is for another plug-in or address")
            continue
        if s.get("problems"):
            warnings.append(f"{lid}: left out, because its manifest fails Starboard's check: " + "; ".join(s["problems"][:3]))
            continue
        m = dict(m)
        m["name"] = m["name"] or l["name"]
        meas = measures.get(lid)
        tot = rs.measured_totals(meas)
        maker = l.get("maker_figures")
        mem, src = rs.rest_memory(tot, maker)
        need = rl.needs(m["starboard_api"], releases)
        dates = [v["date"] for v in m["versions"] if v["date"]]
        cur = [v["date"] for v in m["versions"] if v["version"] == m["version"] and v["date"]]
        logo_alt = (m["logo"] or {}).get("alt") or ""
        # Defence in depth: the logo is cleaned again here, from the snapshot, before it becomes a file.
        logo = mf.reclean_data_address(s["logo"]) if s["logo"] else None
        if s["logo"] and not logo:
            warnings.append(f"{lid}: its logo failed the logo check again, so a plain one is shown")
        ext = logo[1] if logo else "svg"
        out.append({
            "id": lid, "name": m["name"], "kind": l.get("kind") or mf.kind_for(m), "manifest": m, "manifest_url": l["manifest"],
            "description": m["description"], "pitch": l.get("pitch", ""), "maker": l["maker"], "notes": l.get("notes", ""), "help": l.get("help", ""),
            "reviewed": l["reviewed"], "listed_at": l["listed_at"], "recommended": l.get("recommended", False),
            "older_versions": l.get("older_versions", []), "maker_figures": maker, "own": lst.is_own(l), "measured": meas,
            "measured_totals": tot, "mem_value": mem, "mem_source": src, "mem_line": rs.short_line(tot, maker),
            "needs_sb": need, "latest_date": (cur or sorted(dates, reverse=True) or [""])[0], "snapshot_date": s["fetched_at"][:10],
            "logo_data": mf.plugin_logo.as_data(logo[0], "image/svg+xml" if logo[1] == "svg" else "image/png") if logo else "", "logo_bytes": logo[0] if logo else b"", "logo_file": f"assets/logos/{lid}.{ext}" if logo else "assets/logo/no-logo.svg",
            "logo_alt": logo_alt if len(logo_alt) >= 3 else f"{m['name']} logo", "sha256": s["sha256"],
            "sf": text.get(lid), "shots": shots.get(lid, []), "media": (text.get(lid) or {}).get("media_servers", ["jellyfin", "plex", "emby"]),
        })
    return out


def catalogue(plugins, sb, today, apps=()):
    """catalogue.json in the schema Starboard's catalogue sources read (the same as starboard-plugins' catalogue.json)."""
    entries = []
    for p in sorted(plugins, key=lambda p: p["id"]):
        m = p["manifest"]
        cur = next((v for v in m["versions"] if v["version"] == m["version"]), None)
        latest = {"version": m["version"], "starboard_api": m["starboard_api"], "manifest": p["manifest_url"],
                  "changelog": mf.changelog_text(cur) if cur else "", "released": (cur or {}).get("date", "")}
        latest["manifest_sha256"] = p["sha256"]  # always: Starboard refuses a file that differs from the one that was reviewed
        latest = {k: v for k, v in latest.items() if v != ""}
        versions = [latest] + [{k: v for k, v in o.items() if v != ""} for o in p["older_versions"] if o["version"] != m["version"]]
        e = {"id": p["id"], "name": m["name"], "description": m["description"], "kind": p["kind"], "author": p["maker"],
             "permissions": m["permissions"], "version": m["version"], "starboard_api": m["starboard_api"], "manifest": p["manifest_url"],
             "published": True, "recommended": p["recommended"], "versions": versions}
        if p["logo_data"]:
            e["logo"], e["logo_alt"] = p["logo_data"], p["logo_alt"]
        if p["mem_value"] is not None:
            cpu = (p["measured_totals"] or {}).get("cpu") if p["mem_source"] == "measured" else (p["maker_figures"] or {}).get("cpu_percent")
            e["rest"] = {"memory_mb": round(p["mem_value"]), "cpu_percent": round(cpu or 0, 2)}
        entries.append(e)
    top = {"catalogue_version": 1, "name": "Stallboard", "site": R.SITE_URL, "generated": today.isoformat(), "plugins": entries}
    # Apps Starboard works with that are not plug-ins. Starboard's reader ignores keys it does not know, so this cannot be installed as a plug-in.
    top["apps"] = [{"id": a["id"], "name": a["name"], "kind": "app", "description": a["tagline"], "page": R.SITE_URL + a["id"] + ".html",
                    "links": [{"label": l["label"], "url": l["url"]} for l in a["links"]]} for a in apps]
    # Which media servers each plug-in works with (all three when it is not about one). Stallboard's own top-level key, beside "apps":
    # Starboard's reader ignores it, and each entry keeps exactly the schema of the starboard-plugins catalogue. DASH-567 can read it.
    top["media_servers"] = {p["id"]: p["media"] for p in sorted(plugins, key=lambda p: p["id"])}
    if sb["latest"]:
        top["starboard"] = {"latest": sb["latest"]["version"], "plugin_api": sb["latest"]["api"], "releases": sb["latest"]["url"]}
    return top


def safe_line(s):
    """One printable line, so text from a manifest can never start a workflow command (::...) in a log."""
    s = "".join(c if " " <= c < "\x7f" or c > "\xa0" else " " for c in str(s))
    return " ".join(s.replace("::", ": :").split())[:300]


def sitemap(urls, today):
    rows = "".join(f"<url><loc>{R.esc(R.SITE_URL + u)}</loc><lastmod>{today.isoformat()}</lastmod></url>" for u in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{rows}</urlset>\n'


def build(out, today, max_age=MAX_AGE_DAYS, root=ROOT):
    root = pathlib.Path(root)
    warnings = []
    listings = lst.load_all(root / "listings")
    releases = rl.load(root / "data" / "starboard-releases.json")
    measures = rs.load_all(root / "data" / "resources")
    for k in measures:
        if k not in listings:
            warnings.append(f"data/resources/{k}.json is for a plug-in that is not listed, so it is not used yet")
    apps = appdata.load_all(root / "data" / "apps")
    R.APP_NAV[:] = [(a["id"], a["name"]) for a in apps.values()]
    text = sfm.load_all(root / "data" / "storefront")
    for k in text:
        if k not in listings:
            warnings.append(f"data/storefront/{k}.json is for a plug-in that is not listed, so it is not used yet")
    shots = sfm.load_shots(root / "data" / "shots.json", root / "assets" / "shots")
    plugins = merge(listings, root / "data" / "snapshots", measures, releases, today, max_age, warnings, text, shots)
    for p in plugins:
        if not p["sf"]:
            warnings.append(f"{p['id']}: has no storefront text (data/storefront/{p['id']}.json), so its page uses the manifest's description")
    shots = read_json(root / "data" / "starboard-screenshots.json", {}).get("screenshots", [])
    sb = {"releases": releases, "latest": releases[-1] if releases else None, "shots": [s for s in shots if re.match(r"^[\w.-]+\.(png|jpg)$", s.get("file", ""))]}
    out = pathlib.Path(out)
    if out.exists():
        shutil.rmtree(out)
    (out / "plugins").mkdir(parents=True)
    (out / "category").mkdir()
    shutil.copytree(root / "assets", out / "assets")
    (out / "assets" / "logos").mkdir(exist_ok=True)
    for p in plugins:
        if p["logo_bytes"]:
            (out / p["logo_file"]).write_bytes(p["logo_bytes"])
    check_label = "release " + mf.STARBOARD_RELEASE
    files = {}
    files["index.html"] = R.page("Stallboard: plug-ins for Starboard", "Find plug-ins for Starboard. Each one is checked and read by a person before it is listed.", 0, "index.html", "home", "home",
                                 R.home(plugins, releases, sb, list(apps.values())))
    files["starboard.html"] = pages.starboard_page(sb, plugins)
    for a in apps.values():
        files[f"{a['id']}.html"] = pages.app_page(a)
    files["submit.html"] = pages.submit_page(check_label)
    files["what-reviewed-means.html"] = pages.reviewed_page(check_label)
    files["accessibility.html"] = pages.accessibility_page("4.14", today)
    files["privacy.html"] = pages.privacy_page(today)
    files["404.html"] = pages.not_found_page()
    files["category/index.html"] = R.page("Categories: plug-ins for Starboard | Stallboard", "Every category of plug-in for Starboard, each with a page and a search of its own.", 1, "category/index.html", "categories", "categories", R.category_index(plugins))
    for k in R.KINDS:
        if any(p["kind"] == k for p in plugins):
            files[f"category/{R.KINDS[k][0]}.html"] = R.page(f"{k}: plug-ins for Starboard | Stallboard", f"{R.KINDS[k][2]} Plug-ins for Starboard in the {k} category.", 1,
                                                              f"category/{R.KINDS[k][0]}.html", "category", "", R.category_page(k, plugins))
    for p in plugins:
        files[f"plugins/{p['id']}.html"] = R.page(f"{p['name']}: a plug-in for Starboard | Stallboard", f"{p['name']}: {R.pitch_of(p)} Reviewed by {p['reviewed']['by']}.", 1,
                                                  f"plugins/{p['id']}.html", "plugin", "", R.plugin_page(p, sb))
    for name, html in files.items():
        (out / name).write_text(html, encoding="utf-8")
    (out / "catalogue.json").write_text(json.dumps(catalogue(plugins, sb, today, list(apps.values())), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    urls = [n for n in files if n != "404.html"] + ["catalogue.json"]
    (out / "sitemap.xml").write_text(sitemap(sorted(urls), today), encoding="utf-8")
    (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {R.SITE_URL}sitemap.xml\n", encoding="utf-8")
    (out / ".nojekyll").write_text("")
    return plugins, warnings, files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "site"))
    ap.add_argument("--today", default=os.environ.get("BUILD_DATE") or dt.date.today().isoformat())
    ap.add_argument("--max-age", type=int, default=MAX_AGE_DAYS)
    a = ap.parse_args()
    try:
        plugins, warnings, files = build(a.out, dt.date.fromisoformat(a.today), a.max_age)
    except (lst.ListingError, appdata.AppError, sfm.StorefrontError) as e:
        sys.exit(f"A listing is broken: {e}")
    print(f"Built {len(files)} pages for {len(plugins)} plug-ins into {a.out}")
    if warnings:
        print("\nWARNINGS")
        warnings = [safe_line(w) for w in warnings]
        for w in warnings:
            print(" -", w)
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a", encoding="utf-8") as f:
                f.write("### Stallboard build warnings\n\n" + "\n".join(f"- {w}" for w in warnings) + "\n")
            for w in warnings:
                print(f"::warning title=Stallboard build::{w}")


if __name__ == "__main__":
    main()
