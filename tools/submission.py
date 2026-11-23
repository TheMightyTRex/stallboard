#!/usr/bin/env python3
"""The submission checks, and the step that turns an approved submission into a pull request.

    python3 tools/submission.py check         reads the issue from the event file, writes reports/submission/
    python3 tools/submission.py approve       the same checks again, then writes the listing and snapshot to reports/approval/
    python3 tools/submission.py open-pr       reads reports/approval/ (checked again), makes a branch and a pull request

SECURITY. The issue is written by a stranger, so every part of it is text and nothing else:
  * It is read from the event file ($GITHUB_EVENT_PATH) with json, never put in a command line, a script or an
    expression. Each field is checked against a strict pattern before it is used, and shown in comments only inside
    a code span with its markdown and mentions removed.
  * The address in it is fetched as DATA ONLY by tools/lib/safefetch.py: https only, public addresses only (resolved
    once, then connected to), no redirects off github.com's own hosts, 256 KB and 10 seconds at most. Nothing fetched
    is run, imported or unpacked. The logo is rebuilt by Starboard's own logo code.
  * Who may approve is decided by GitHub's own record of the person's permission on this repository (the API), never
    by a name in the text. Labels that matter are read from the event, never from the body.
  * No secret is used: the token is the job's own, with only the permissions the workflow gives that job.
"""
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "lib"))
import listing as lst  # noqa: E402
import manifest as mf  # noqa: E402
import safefetch  # noqa: E402
from starboard import plugins  # noqa: E402

LABELS = {"Address of the plug-in file": "manifest", "Your name or GitHub name": "maker", "How to reach you, if not through this issue (optional)": "contact",
          "What it does, in one sentence": "summary", "What it asks to read or change, and why": "asks", "Licence": "licence", "Confirmation": "confirm"}
MAKER = re.compile(r"^[\w .'’+-]{1,60}$")
LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})(?:\[bot\])?$")
MARKER = re.compile(r"<!-- stallboard-checks sha256=([0-9a-f]{64}) id=([a-z0-9-]{3,40}) -->")
MAY_APPROVE = ("admin", "maintain", "write")
CHECKLIST = ["What it asks for matches what it says it does (each permission is needed, none is extra)",
             "The licence is real and lets Stallboard list it",
             "Its image is pinned by digest and comes from the maker's own repository or registry",
             "The maker's repository exists and the code matches the plug-in",
             "No secrets, keys or private addresses are in the file or the image",
             "Its help exists, and it says where to report a problem",
             "The listing and the snapshot in this pull request are what I read"]


def md(s, most=300):
    """Text from a stranger as one safe line for markdown: no markup, no mentions, no links, no references."""
    s = " ".join(str(s or "").split())[:most]
    s = re.sub(r"[`<>\[\]()*_~|#!\\]", " ", s).replace("&", "and")
    return s.replace("@", " at ").replace("://", " : ").strip()


def code(s, most=200):
    return "`" + md(s, most).replace("`", "") + "`"


def parse_body(body):
    """{field: text} from an issue form's body. Unknown headings are ignored; a repeated heading keeps its first text."""
    fields = {}
    cur = None
    for line in str(body or "").replace("\r\n", "\n").split("\n"):
        m = re.match(r"^### (.{1,200})$", line)
        if m:
            cur = LABELS.get(m.group(1).strip())
            if cur and cur not in fields:
                fields[cur] = []
            else:
                cur = None
            continue
        if cur is not None:
            fields[cur].append(line)
    out = {}
    for k, lines in fields.items():
        t = "\n".join(lines).strip()
        out[k] = "" if t == "_No response_" else t
    return out


def risk_table(manifest):
    rows = []
    for p in manifest.get("permissions") or []:
        if p in plugins.PERMISSIONS:
            words, risk, _ = plugins.PERMISSIONS[p]
            rows.append(f"| `{p}` | {md(words, 120)} | {md(risk)} |")
    return rows


def run_checks(fields, listings_dir=None, fetch=safefetch.fetch, now=None):
    """The checks. Returns {passed, ok:[...], fix:[...], note:[...], snapshot, id, sha256, manifest_url, maker}."""
    ok, fix, note = [], [], []
    res = {"ok": ok, "fix": fix, "note": note, "snapshot": None, "id": "", "sha256": "", "manifest_url": "", "maker": "", "passed": False}
    url = (fields.get("manifest") or "").strip()
    try:
        safefetch.check_address(url)
        ok.append("The address is a public https address.")
    except safefetch.FetchError as e:
        fix.append(f"The address: {md(e)}.")
        url = ""
    maker = (fields.get("maker") or "").strip()
    if MAKER.match(maker):
        res["maker"] = maker
        ok.append("The maker's name is given.")
    else:
        fix.append("Your name or GitHub name must be 1 to 60 letters, numbers, spaces or . - _ ' characters.")
    if re.search(r"^- \[[xX]\] ", fields.get("confirm", ""), re.M):
        ok.append("You said you wrote it or have the right to submit it.")
    else:
        fix.append("Tick the box to say you wrote it or have the right to submit it.")
    summary = " ".join((fields.get("summary") or "").split())
    if 3 <= len(summary) <= 200:
        ok.append("It has a one sentence description.")
    else:
        fix.append("Say in one sentence, up to 200 characters, what it does.")
    if 3 <= len((fields.get("asks") or "").strip()) <= 1000:
        ok.append("It says what it asks to read or change, and why.")
    else:
        fix.append("Say what it asks to read or change, and why (up to 1000 characters).")
    lic = (fields.get("licence") or "").strip()
    if not re.match(plugins.SPDX, lic):
        fix.append("Give its licence as a short licence name such as MIT or Apache-2.0.")
    if not url:
        return res
    try:
        snap = mf.make_snapshot(url, fetch=fetch, now=now)
    except (safefetch.FetchError, ValueError) as e:
        fix.append(f"Reading the plug-in file: {md(e)}.")
        return res
    ok.append("The plug-in file was read as plain text (nothing was run).")
    res["sha256"], res["id"] = snap["sha256"], snap["id"]
    md_data = snap["manifest_data"]
    if snap["problems"]:
        fix += [f"Starboard's own check: {md(p)}." for p in snap["problems"][:25]]
        if len(snap["problems"]) > 25:
            fix.append(f"And {len(snap['problems']) - 25} more problems. Fix these first.")
    else:
        ok.append(f"Starboard's own manifest check passes (rules from Starboard {mf.STARBOARD_RELEASE}).")
    if lic and md_data["licence"] and lic.lower() != md_data["licence"].lower():
        fix.append(f"The licence you gave ({code(lic, 40)}) is not the one in the file ({code(md_data['licence'], 40)}). Make them the same.")
    if listings_dir is not None and md_data["id"] and (pathlib.Path(listings_dir) / f"{md_data['id']}.json").exists():
        fix.append(f"A plug-in with the id {code(md_data['id'], 40)} is already listed. To change a listing, open a pull request.")
    if md_data["logo"] and snap["logo"]:
        ok.append("Its logo is a clean image with a description.")
    elif md_data["logo"]:
        note.append("Its logo could not be used (" + md(snap["logo_note"] or "it failed the logo check") + "), so a plain one is shown.")
    else:
        note.append("It has no logo, so a plain one is shown. A logo with a description makes it easier to find.")
    if md_data["support_url"].startswith("https://") and md_data["homepage"].startswith("https://"):
        ok.append("It gives a home page and a place to report problems.")
    if snap["logo"]:
        res["logo_ok"] = True
    res["snapshot"] = snap
    res["passed"] = not fix
    res["table"] = risk_table(md_data)
    res["name"] = md_data["name"]
    res["version"] = md_data["version"]
    return res


def comment(res):
    lines = ["## Checks on your plug-in", "",
             "These checks read your plug-in file as plain text. Nothing in it was run. They are the same checks Starboard runs, so a plug-in that passes here installs there.", ""]
    if res["passed"]:
        lines += ["**All the checks passed.** A person will now read it, using the [review checklist](https://github.com/TheMightyTRex/stallboard/blob/main/REVIEWING.md). You may hear from them here.", ""]
    else:
        lines += ["**Some checks did not pass.** Fix what is below, then edit your issue (change the text, or save it again). The checks run again by themselves.", ""]
    if res["fix"]:
        lines += ["### To fix", ""] + [f"- {f}" for f in res["fix"]] + [""]
    if res["ok"]:
        lines += ["### Passed", ""] + [f"- {f}" for f in res["ok"]] + [""]
    if res["note"]:
        lines += ["### Worth knowing", ""] + [f"- {f}" for f in res["note"]] + [""]
    if res.get("table"):
        lines += ["### What it asks for", "", "| Permission | In words | Risk |", "|---|---|---|"] + res["table"] + [""]
    if res["sha256"] and res["id"] and re.match(plugins.ID, res["id"]):
        lines.append(f"<!-- stallboard-checks sha256={res['sha256']} id={res['id']} -->")
    return "\n".join(lines) + "\n"


def event():
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as f:
        return json.load(f)


def write(path, text):
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def cmd_check():
    ev = event()
    body = (ev.get("issue") or {}).get("body") or ""
    res = run_checks(parse_body(body), ROOT / "listings")
    out = ROOT / "reports" / "submission"
    write(out / "comment.md", comment(res))
    write(out / "result.json", json.dumps({"passed": res["passed"]}))
    print("passed" if res["passed"] else "to fix:", *res["fix"], sep="\n")


def permission_of(login, repo, runner=None):
    """GitHub's own record of this person's role on this repository: admin, maintain, write, triage, read or none."""
    if not LOGIN.match(login or "") or not re.match(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", repo or ""):
        return "none"
    run = runner or (lambda args: subprocess.run(args, capture_output=True, text=True, timeout=30, check=False))
    r = run(["gh", "api", f"repos/{repo}/collaborators/{login}/permission", "--jq", ".role_name"])
    return (r.stdout or "").strip() if r.returncode == 0 else "none"


def flatten(pages):
    """`gh api --paginate --slurp` gives a list of pages; a plain list of comments also works."""
    out = []
    for x in pages if isinstance(pages, list) else []:
        out += x if isinstance(x, list) else [x]
    return [c for c in out if isinstance(c, dict)]


def latest_marker(comments):
    """(sha256, id) from the newest comment the Actions bot wrote with a checks marker, or None. Anyone else's comment
    is ignored, so a stranger cannot supply a marker."""
    for c in reversed(comments or []):
        user = c.get("user") or {}
        if user.get("login") == "github-actions[bot]" and user.get("type") == "Bot":
            m = MARKER.search(c.get("body") or "")
            if m:
                return m.group(1), m.group(2)
    return None


def cmd_approve(today=None):
    ev = event()
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    sender = (ev.get("sender") or {}).get("login", "")
    issue = ev.get("issue") or {}
    labeled = (ev.get("label") or {}).get("name")
    if labeled != "approved":
        sys.exit("Not the approved label.")
    role = permission_of(sender, repo)
    if role not in MAY_APPROVE:
        write(ROOT / "reports" / "approval" / "refused.md", "The `approved` label was added by someone who is not a maintainer of this repository, so nothing was done. "
              "Only a maintainer's approval counts. The label has been removed.\n")
        sys.exit("The label was added by someone without maintainer permission: " + md(sender, 40) + " (" + md(role, 20) + ")")
    comments = flatten(json.loads(pathlib.Path(os.environ.get("COMMENTS_FILE", ROOT / "reports" / "comments.json")).read_text() or "[]"))
    marker = latest_marker(comments)
    res = run_checks(parse_body(issue.get("body") or ""), ROOT / "listings")
    out = ROOT / "reports" / "approval"
    if not res["passed"]:
        write(out / "refused.md", "The checks do not pass now, so no pull request was opened. Fix what the checks say, then add `approved` again.\n")
        sys.exit("The checks do not pass.")
    if not marker or marker != (res["sha256"], res["id"]):
        write(out / "refused.md", "The plug-in file is not the one the checks passed, or the checks have not run on this version of the issue. "
              "Edit the issue (save it again) so the checks run, read the result, then add `approved` again.\n")
        sys.exit("The plug-in file changed since it was checked.")
    day = (today or dt.date.today()).isoformat()
    snap = res["snapshot"]
    m = snap["manifest_data"]
    n = issue.get("number")
    if not isinstance(n, int) or n < 1:
        sys.exit("No issue number.")
    listing = {"id": res["id"], "name": m["name"], "manifest": res["manifest_url"] or snap["manifest"], "maker": res["maker"], "listed_at": day,
               "reviewed": {"by": sender, "at": day, "version": m["version"]}, "kind": mf.kind_for(m)}
    lst.check(listing, f"{res['id']}.json")
    body = ["Adds a plug-in listing, approved by a maintainer on the issue.", "", f"Closes #{n}", "",
            f"- Plug-in: {code(m['name'], 40)} {code(m['version'], 30)}", f"- Maker: {code(res['maker'], 60)}", f"- Reviewed by: {code(sender, 40)} on {day}",
            f"- Category: {code(listing['kind'], 30)} (change `kind` in the listing if it is wrong)",
            f"- Manifest SHA-256 at the time of the checks: `{res['sha256']}`", "",
            "### What it asks for", "", "| Permission | In words | Risk |", "|---|---|---|"] + (res.get("table") or []) + ["",
            "### Before you merge", "",
            "Read `listings/" + res["id"] + ".json` and `data/snapshots/" + res["id"] + ".json` in this pull request. Merging lists the plug-in and deploys the site.", ""] + [f"- [ ] {c}" for c in CHECKLIST]
    write(out / "listing.json", json.dumps(listing, indent=1, ensure_ascii=False) + "\n")
    write(out / "snapshot.json", json.dumps(snap, indent=1, ensure_ascii=False) + "\n")
    write(out / "pr-body.md", "\n".join(body) + "\n")
    write(out / "meta.json", json.dumps({"id": res["id"], "issue": n, "branch": f"listing/{res['id']}-{n}", "title": f"List {m['name']} {m['version']}"[:100]}))
    print("approved:", res["id"])


def cmd_open_pr():
    """Takes what `approve` wrote (an artifact that is checked again here) and opens the pull request. Every command is a
    list of arguments, never a shell line, and every name in them was checked."""
    src = ROOT / "reports" / "approval"
    meta = json.loads((src / "meta.json").read_text())
    if not (re.match(plugins.ID, meta["id"]) and isinstance(meta["issue"], int) and meta["branch"] == f"listing/{meta['id']}-{meta['issue']}"):
        sys.exit("The approval is not in the form this step expects.")
    listing = lst.check(json.loads((src / "listing.json").read_text()), f"{meta['id']}.json")
    snap = json.loads((src / "snapshot.json").read_text())
    if snap.get("id") != meta["id"] or not isinstance(snap.get("manifest_data"), dict) or snap.get("problems"):
        sys.exit("The snapshot is not for this plug-in or does not pass.")
    lp, sp = ROOT / "listings" / f"{meta['id']}.json", ROOT / "data" / "snapshots" / f"{meta['id']}.json"
    if lp.exists():
        sys.exit("That plug-in is already listed.")
    write(lp, json.dumps(listing, indent=1, ensure_ascii=False) + "\n")
    write(sp, json.dumps(snap, indent=1, ensure_ascii=False) + "\n")
    # The site must build with it, offline, before anyone is asked to merge.
    subprocess.run([sys.executable, str(HERE / "build.py"), "--out", str(ROOT / "reports" / "site-test")], check=True, cwd=ROOT)
    g = ["git", "-c", "user.name=github-actions[bot]", "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com"]
    subprocess.run(g + ["checkout", "-b", meta["branch"]], check=True, cwd=ROOT)
    subprocess.run(g + ["add", "--", f"listings/{meta['id']}.json", f"data/snapshots/{meta['id']}.json"], check=True, cwd=ROOT)
    subprocess.run(g + ["commit", "-m", meta["title"] + "\n\nApproved on issue #" + str(meta["issue"]) + "."], check=True, cwd=ROOT)
    subprocess.run(["git", "push", "origin", meta["branch"]], check=True, cwd=ROOT)
    subprocess.run(["gh", "pr", "create", "--base", "main", "--head", meta["branch"], "--title", meta["title"], "--body-file", str(src / "pr-body.md")], check=True, cwd=ROOT)


if __name__ == "__main__":
    {"check": cmd_check, "approve": cmd_approve, "open-pr": cmd_open_pr}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
