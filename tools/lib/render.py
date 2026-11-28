"""The pages of the site, as plain HTML text. Every value that came from a manifest, a listing or a snapshot goes
through esc(); addresses go through addr(), which keeps only https addresses. Nothing here needs JavaScript to read."""
import html
import pathlib
import re
import sys
import urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import manifest as mf  # noqa: E402
import releases as rl  # noqa: E402
import resources as rs  # noqa: E402
import testbench as tb  # noqa: E402

SITE_URL = "https://themightytrex.github.io/stallboard/"
SITE_PATH = "/stallboard/"
REPO = "TheMightyTRex/stallboard"
REPO_URL = "https://github.com/" + REPO
STARBOARD_REPO = "https://github.com/TheMightyTRex/starboard"
HELP_CENTRE = "https://themightytrex.github.io/starboard-plugins/help/index.html"
CATALOGUE_URL = SITE_URL + "catalogue.json"
CSP = "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; base-uri 'self'; object-src 'none'; form-action https://github.com"
SPRITE = (HERE / "sprite.html").read_text()
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

KINDS = {
    "Apps you can add": ("apps", "app-window", "Whole apps, added to your server in a few steps."),
    "Jellyfin": ("jellyfin", "film", "Make your films and series work harder."),
    "Network": ("network", "network", "Speed, safety and reaching home from outside."),
    "System": ("system", "server", "Disks, backups and the news from your server."),
    "Accessibility": ("accessibility", "headphones", "Made for blind and partially sighted people."),
    "Downloads": ("downloads", "download", "What is coming in, and how safely."),
    "Home": ("home", "house", "Your house, on your dashboard."),
    "Appearance": ("appearance", "sparkles", "Change how Starboard looks."),
    "AI assistants": ("ai-assistants", "bot", "Ask an assistant about your server, or let an AI tool manage Starboard, with your own model or key."),
}
PERM = {
    "jellyfin:key": ("Use your Jellyfin key", "Signs in to Jellyfin as a helper, so it can find, tag or play titles.", "both"),
    "reelix:key": ("Use your Reelix key", "Talks to Reelix to find, prefer or manage releases.", "both"),
    "usenet:servers": ("Use your news server sign-in", "Reads the address and sign-in of your news server, from NZBGet or SABnzbd.", "read"),
    "media:read": ("Read the names of your media", "Reads the titles and details of your films, series and books. It does not read the files.", "read"),
    "network:lan": ("Talk to things on your home network", "Connects to apps and devices at home, and to the internet.", "both"),
    "network:port": ("Open its own web page", "Gives the app a page on your server, which you open in a browser.", "change"),
    "alerts:send": ("Send alerts", "Adds alerts to Starboard when something needs you.", "change"),
    "system:read": ("Read disk, memory and processor use", "Reads figures about your server and changes nothing.", "read"),
    "downloads:read": ("Read your downloads", "Reads the download queue and what has finished.", "read"),
    "apps:read": ("Read which apps are running", "Reads the list of apps on Starboard and whether each one is up.", "read"),
    "library:holding": ("Move titles to the holding folder", "Moves titles out of your library into a holding folder. It never deletes, and each can be put back.", "change"),
    "jellyfin:metadata": ("Change pictures and details in Jellyfin", "Replaces posters and photos Jellyfin keeps.", "change"),
    "jellyfin:libraries": ("Add its own libraries to Jellyfin", "Starboard adds libraries to Jellyfin for folders the plug-in fills.", "change"),
    "appearance:styles": ("Change how Starboard looks", "Changes colours, shapes and text styles across Starboard.", "change"),
    "network:vpn": ("Use your VPN connection", "Runs inside your VPN, so what it sends goes out through it.", "both"),
}
LEVEL = {"read": ("Reads", "eye"), "change": ("Changes", "pencil"), "both": ("Reads and changes", "arrow-up-down")}
APPS = ["Jellyfin", "Reelix", "Home Assistant", "Pi-hole or AdGuard Home", "Philips Hue"]
EXTRA_WORKS = {"wizarr": ["Jellyfin"], "jellystat": ["Jellyfin"], "maintainerr": ["Jellyfin"], "seerr": ["Jellyfin"], "themearr": ["Jellyfin", "Reelix"],
               "home-assistant": ["Home Assistant"], "dns-blocking": ["Pi-hole or AdGuard Home"], "philips-hue": ["Philips Hue", "Home Assistant"]}


def esc(s):
    return html.escape(str(s), quote=True)


def addr(url):
    """An https address safe to put in an attribute, or ''."""
    u = mf.https_or_empty(url)
    return esc(u) if u else ""


def icon(n, cls="i"):
    return f'<svg class="{cls}" aria-hidden="true" focusable="false"><use href="#i-{n}"/></svg>'


def nice_date(iso):
    iso = str(iso)
    try:
        y, m, d = (int(x) for x in iso.split("-"))
        return f"{d} {MONTHS[m - 1]} {y}"
    except (ValueError, IndexError):
        return iso


def join_words(a):
    a = list(a)
    return a[0] if len(a) == 1 else (", ".join(a[:-1]) + " and " + a[-1] if a else "")


def api_words(s):
    m = re.match(r"^>=([\d.]+)\s*<([\d.]+)$", s or "")
    return f"plug-in API {m.group(1)} or later, up to but not including {m.group(2)}" if m else (esc(s) if s else "not stated")


def pitch_of(p):
    return p["pitch"] or (p.get("sf") or {}).get("summary") or mf.whole_words(re.split(r"(?<=\.)\s", p["description"])[0], 110)


# ------------------------------------------------------------------ the frame


def rel(depth):
    return "../" * depth


def head(title, desc, depth, page_path, page_id, extra=""):
    p = rel(depth)
    url = SITE_URL + page_path
    return f'''<!doctype html>
<html lang="en-GB" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(url)}">
<meta property="og:type" content="website"><meta property="og:site_name" content="Stallboard"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{esc(url)}"><meta property="og:image" content="{SITE_URL}assets/social.png"><meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{p}assets/logo/stallboard-mark-light.svg" type="image/svg+xml"><link rel="icon" href="{p}assets/logo/favicon-32.png" sizes="32x32" type="image/png"><link rel="apple-touch-icon" href="{p}assets/logo/apple-touch-icon.png">
<link rel="stylesheet" href="{p}assets/ds/tokens.css">
<link rel="stylesheet" href="{p}assets/ds/components.css">
<link rel="stylesheet" href="{p}assets/store.css">
<script src="{p}assets/theme.js"></script>{extra}
</head>
<body data-page="{page_id}">
{SPRITE}
<a class="skip-link" href="#main">Skip to the main content</a>
'''


MARK = ('<svg viewBox="0 0 64 64" aria-hidden="true" focusable="false"><rect class="lg-tile" width="64" height="64" rx="16"/>'
        + "".join('<path class="%s" d="M%d 12h8v12a4 4 0 0 1-8 0z"/>' % ("lg-cream" if i % 2 == 0 else "lg-plum", 8 + 8 * i) for i in range(6))
        + '<rect class="lg-post" x="17" y="34" width="6" height="18" rx="3"/><rect class="lg-post" x="41" y="34" width="6" height="18" rx="3"/></svg>')


APP_NAV = []  # (id, name) of the apps Starboard works with, set by the build


def header(depth, current):
    p = rel(depth)

    def item(href, text, key):
        c = ' aria-current="page"' if current == key else ""
        return f'<li><a href="{p}{href}"{c}>{text}</a></li>'
    return f'''<header class="top"><div class="wrap top__bar">
  <a class="brand" href="{p}index.html">{MARK}<span>Stallboard<span class="visually-hidden"> home</span></span></a>
  <nav class="nav" aria-label="Main"><ul>
    {item("starboard.html", "Start here: Starboard", "starboard")}
    {"".join(item(f"{i}.html", esc(n), i) for i, n in APP_NAV)}
    {item("category/index.html", "Categories", "categories")}
    {item("index.html#all-plug-ins", "Browse", "home")}
    {item("submit.html", "Submit a plug-in", "submit")}
    <li><a href="{HELP_CENTRE}" target="_blank" rel="noopener">Help centre {icon("help-new-tab")}<span class="visually-hidden"> (opens in a new tab)</span></a></li>
    <li><button class="btn js-only" type="button" id="display-open" data-opens="display-panel" aria-haspopup="dialog" aria-expanded="false" hidden>{icon("sun")}Display and accessibility</button></li>
  </ul></nav>
</div></header>
'''


def footer(depth):
    p = rel(depth)
    return f'''<footer class="foot"><div class="wrap foot__grid">
  <div><h2>What Reviewed means</h2><p>Automatic checks, a safety check of what a plug-in asks for, then a person reads it. Only then does a plug-in get the Reviewed mark, with the date and who reviewed it.</p><p><a href="{p}what-reviewed-means.html">What Reviewed means</a></p></div>
  <div><h2>Feedback</h2><p>The Send feedback button is Snaglist. You choose what to send, check the whole report first, and it keeps no personal information.</p><p><a href="{p}privacy.html">What a report holds</a></p></div>
  <div><h2>Stallboard</h2><ul><li><a href="{p}starboard.html">Start here: Starboard</a></li><li><a href="{p}index.html#all-plug-ins">Browse plug-ins</a></li><li><a href="{p}submit.html">Submit a plug-in</a></li><li><a href="{p}accessibility.html">Accessibility statement</a></li><li><a href="{p}privacy.html">Privacy</a></li><li><a href="{HELP_CENTRE}" target="_blank" rel="noopener">Plug-in help centre<span class="visually-hidden"> (opens in a new tab)</span></a></li><li><a href="{REPO_URL}" target="_blank" rel="noopener">Source on GitHub<span class="visually-hidden"> (opens in a new tab)</span></a></li></ul></div>
</div></footer>
'''


def seg(name, label, options, default):
    items = "".join(f'<label><input type="radio" name="{name}" value="{v}" data-display="{name}"{" checked" if v == default else ""}><span>{esc(t)}</span></label>' for v, t in options)
    return f'<fieldset><legend>{esc(label)}</legend><div class="segmented">{items}</div></fieldset>'


def display_panel():
    """Display and accessibility: the design system's own panel (docs/ACCESSIBILITY.md section 1) in its own words and order.
    components.js applies the choices at once from the data-display inputs and keeps them in this browser (data-display-save)."""
    return f'''
<div class="side-panel-layer" id="display-panel" hidden>
  <div class="side-panel-backdrop"></div>
  <div class="side-panel" role="dialog" aria-modal="true" aria-labelledby="display-h">
    <div class="panel-header"><h2 class="panel-header__title" id="display-h">Display and accessibility</h2><button class="icon-btn" type="button" data-closes aria-label="Close display and accessibility">{icon("x")}</button></div>
    <form class="side-panel__body" id="display-form" data-display-save="stallboard-display">
      {seg("theme", "Theme", [("system", "Match device"), ("light", "Light"), ("dark", "Dark")], "light")}
      {seg("text", "Text size", [("100", "100%"), ("125", "125%"), ("150", "150%"), ("175", "175%")], "100")}
      {seg("motion", "Reduce motion", [("device", "Match device"), ("on", "Active"), ("off", "Inactive")], "device")}
      <label class="switch"><span>High contrast</span><input type="checkbox" role="switch" data-display="contrast"></label>
      <label class="switch"><span>Underline links</span><input type="checkbox" role="switch" data-display="underline"></label>
      <label class="switch"><span>Wider text spacing</span><input type="checkbox" role="switch" data-display="spacing"></label>
      <label class="switch"><span>Remove drop shadows</span><input type="checkbox" role="switch" data-display="shadows" aria-describedby="display-shadows-note"></label>
      <p class="small muted" id="display-shadows-note">Drop shadows cost a little processor on every scroll; turning them off helps small and older computers.</p>
      <p class="small muted">Choices apply at once and are kept in this browser only. Stallboard sets no cookie and sends nothing.</p>
      <p class="visually-hidden" id="display-status" role="status"></p>
    </form>
    <div class="side-panel__foot"><button class="btn btn--primary" type="button" data-closes>Close</button><button class="btn" type="button" data-display-reset="stallboard-display">Reset to defaults</button></div>
  </div>
</div>
'''


def tail(depth, scripts=True):
    p = rel(depth)
    return f'''
<script src="{p}assets/ds/components.js" defer></script>
<script src="{p}assets/store.js" defer></script>
<script src="{p}assets/snaglist.js" data-start data-app="Stallboard" defer></script>
<script src="{p}assets/snaglist-start.js" defer></script>
</body>
</html>
'''


def page(title, desc, depth, path, pid, current, body, extra_head=""):
    return head(title, desc, depth, path, pid, extra_head) + header(depth, current) + body + footer(depth) + display_panel() + tail(depth)


# ------------------------------------------------------------------ pieces


def reviewed_chip():
    return f'<span class="chip" data-tone="success">{icon("shield-check")}<span class="visually-hidden">Mark: </span>Reviewed</span>'


def own_chip():
    return f'<span class="chip">{icon("star")}<span class="visually-hidden">Mark: </span>Starboard\'s own</span>'


def logo_img(p, depth, size=72, alt=""):
    return f'<img src="{rel(depth)}{p["logo_file"]}" alt="{esc(alt)}" width="{size}" height="{size}" loading="lazy">'


def needs_apps(p):
    m = p["manifest"]
    a = []
    if any(x.startswith("jellyfin:") for x in m["permissions"]):
        a.append("Jellyfin")
    if "reelix:key" in m["permissions"]:
        a.append("Reelix")
    return a


def works_with(p):
    s = set(EXTRA_WORKS.get(p["id"], []))
    if p["kind"] in ("Jellyfin", "Accessibility") or any(x.startswith("jellyfin:") for x in p["manifest"]["permissions"]):
        s.add("Jellyfin")
    if "reelix:key" in p["manifest"]["permissions"]:
        s.add("Reelix")
    return [a for a in APPS if a in s]


def sb_need_text(p):
    """'Needs Starboard 0.26 or later' (plain words, with the newest known to work when the range stops early)."""
    n = p["needs_sb"]
    if not n["first"]:
        return "Needs a Starboard that is not out yet", ""
    text = f"Needs Starboard {n['first']} or later"
    upto = f"Known to work up to Starboard {n['newest']}" if n["limited"] else ""
    return text, upto


MEDIA = {"jellyfin": "Jellyfin", "plex": "Plex", "emby": "Emby"}


def media_label(p):
    """'Works with Jellyfin, Plex and Emby' (not related to a media server), or 'Works with Jellyfin only', or two of them."""
    m = [MEDIA[x] for x in p["media"]]
    return "Works with " + (join_words(m) + (" only" if len(m) == 1 else "" if len(m) == 3 else " only"))


def media_chips(p, tag="ul", icons=True):
    """One chip for each media server the plug-in supports. The words carry the meaning; the group has one spoken name."""
    m = p["media"]
    label = media_label(p)
    ic = icon("tv") if icons else ""
    chips = "".join(f'<li><span class="chip chip--media" data-server="{x}">{ic}{MEDIA[x]}{"<span class=visually-hidden> only</span>" if len(m) == 1 else ""}</span></li>' for x in m)
    return f'<ul class="chiprow media-chips" aria-label="{esc(label)}">{chips}</ul>'


def search_text(p):
    """What the search reads: name, one line, category and tags (lower case, from this page's own data)."""
    sf = p.get("sf") or {}
    bits = [p["name"], pitch_of(p), sf.get("summary", ""), p["kind"], " ".join(sf.get("tags", [])), " ".join(works_with(p)), " ".join(p["manifest"].get("needs") or [])]
    return " ".join(" ".join(bits).lower().split())


def plate(p, depth, size=88):
    """The picture on a card and on a plug-in page. Every plug-in gets the same treatment: its logo on a white tile, over a tint of its
    category's colour. A plug-in with no logo gets its first letter on its category's colour, so no card is ever blank, stretched or cropped."""
    if p["logo_bytes"]:
        return f'<span class="plate plate--{size}"><img src="{rel(depth)}{p["logo_file"]}" alt="" width="{size}" height="{size}" loading="lazy" decoding="async"></span>'
    return f'<span class="plate plate--{size} plate--mono" aria-hidden="true">{esc(p["name"][:1].upper())}</span>'


def tile(p, depth, data=True):
    """A poster card: the same parts in the same places on every card, so every card is the same height. At most three chips
    (the media servers). The name is the one link and covers the card, so a card is one tab stop and one big target."""
    sb, _ = sb_need_text(p)
    mem = p["mem_value"]
    attrs = ""
    if data:
        attrs = (f' data-id="{esc(p["id"])}" data-kind="{esc(p["kind"])}" data-name="{esc(p["name"].lower())}" data-mem="{"" if mem is None else mem}" data-sb="{esc(p["needs_sb"].get("first_full") or "")}"'
                 f' data-works="{esc("|".join(works_with(p)))}" data-search="{esc(search_text(p))}" data-media="{" ".join(p["media"])}" data-testmem="{"" if p.get("test_mem") is None else p["test_mem"]}" data-date="{esc(p["latest_date"])}"')
    return f'''<li class="tile kind-{KINDS[p["kind"]][0]}"{attrs}>
      <div class="tile__art">{plate(p, depth)}</div>
      <div class="tile__body">
        <h3 class="tile__name"><a href="{rel(depth)}plugins/{esc(p["id"])}.html">{esc(p["name"])}</a></h3>
        <p class="tile__kind">{esc(p["kind"])}</p>
        <p class="tile__pitch">{esc(pitch_of(p))}</p>
        {media_chips(p, icons=False)}
        <p class="tile__need"><span class="sb-need">{esc(sb)}</span></p>
        <p class="tile__use">{esc(p["mem_line"])}</p>
      </div></li>'''


# ------------------------------------------------------------------ the shelf: home and category pages


KIND_ABOUT = {
    "Apps you can add": "Each one adds a whole app to your server, with its own page, and Starboard keeps it up to date. Most of them need only a few steps and nothing else set up first.",
    "Jellyfin": "These work with the films and series in Jellyfin. They tidy the library, make files play directly, show what people watch and make your own channels.",
    "Network": "These look after speed, safety and reaching your home from outside. They cover ad blocking, line speed, remote access and checks on the services you rely on.",
    "System": "These watch the server itself: when disks will be full, whether backups ran, and how Starboard's alerts reach you.",
    "Accessibility": "Made for blind and partially sighted people: descriptions of what happens on screen, and the tracks that carry them.",
    "Downloads": "These show what is coming in, and check that downloads go out through your VPN.",
    "Home": "These put your house on the Starboard dashboard, with lights and home automation beside your media.",
    "Appearance": "These change how Starboard looks, with colours, shapes and text styles across every screen.",
    "AI assistants": "These let you ask an assistant about your server, or let an AI tool manage Starboard, with your own model or key.",
}


def plural(n):
    return f"{n} plug-in{'' if n == 1 else 's'}"


def rail(plugins, releases, current, depth, with_test_sort):
    """The rail: categories (links, they work without a script), then the filters (script only). On a phone the filters are a sheet
    that a Filters button opens, with Works with first, and the categories fold up."""
    p = rel(depth)
    here = "" if depth == 0 else "../"
    counts = {k: sum(1 for x in plugins if x["kind"] == k) for k in KINDS}
    all_href = "#all-plug-ins" if depth == 0 else f"{here}index.html#all-plug-ins"
    cat_href = (lambda k: f"category/{KINDS[k][0]}.html") if depth == 0 else (lambda k: f"{KINDS[k][0]}.html")
    items = [f'<li><a href="{all_href}"{" aria-current=\"page\"" if current == "all" else ""}>All plug-ins <span class="n">{len(plugins)}</span></a></li>']
    for k in KINDS:
        if counts[k]:
            items.append(f'<li><a href="{cat_href(k)}"{" aria-current=\"page\"" if current == k else ""}>{esc(k)} <span class="n">{counts[k]}</span></a></li>')
    media = "".join(f'<label class="seg__o"><input type="radio" name="media" value="{v}"{" checked" if v == "" else ""}><span>{t}</span></label>' for v, t in [("", "Any"), ("jellyfin", "Jellyfin"), ("plex", "Plex"), ("emby", "Emby")])
    sbs = "".join(f'<option value="{esc(r["version"])}">Starboard {esc(r["version"])}</option>' for r in sorted(releases, key=lambda r: rl.ver(r["version"]), reverse=True)[:12])
    sorts = '<option value="name">Name, A to Z</option><option value="mem">Memory at rest, lowest first</option>' + ('<option value="testmem">Memory on the test server, lowest first</option>' if with_test_sort else "") + '<option value="new">Newest first</option>'
    return f'''<div class="store-layout__rail">
    <nav class="catnav" aria-label="Categories"><details id="cat-fold" open><summary>Categories</summary><ul>{"".join(items)}</ul></details></nav>
    <section class="filters js-only" id="filters" aria-labelledby="filters-h" hidden>
      <div class="filters__head"><h2 id="filters-h" tabindex="-1">Filters</h2><button class="btn btn--quiet filters__done" type="button" id="filters-close">Show results</button></div>
      <fieldset class="seg"><legend>Works with</legend><div class="seg__row">{media}</div></fieldset>
      <div class="field"><label class="field__label" for="mysb">The Starboard you have</label><select class="select" id="mysb"><option value="">Any, do not mark plug-ins</option>{sbs}</select></div>
      <div class="field"><label class="field__label" for="sort">Sort by</label><select class="select" id="sort">{sorts}</select></div>
      <button class="btn" type="button" id="clear-filters">Clear the filters</button>
    </section>
  </div>'''


def search_form(pid, hint, scope):
    """The search box. It filters the list on the page as you type, reads only the page's own data and sends nothing anywhere."""
    return f'''<form class="banner__search js-only" id="search-form" role="search" aria-label="Search {esc(scope)}" hidden>
      <div class="field"><label class="field__label" for="q">Search {esc(scope)}</label><input class="input" id="q" type="search" autocomplete="off" aria-describedby="q-hint" aria-controls="{pid}"><p class="hint" id="q-hint">{esc(hint)} Results update as you type.</p></div>
    </form>
    <button class="btn filters__open js-only" type="button" id="filters-open" aria-haspopup="dialog" aria-expanded="false" aria-controls="filters" hidden>{icon("sliders")}Filters<span id="filters-n"></span></button>'''


def results_block(pid, total, heading_id="results-h"):
    return f'''<ul class="active js-only" id="active" aria-label="Active filters" hidden></ul>
    <p class="results-note" id="results-status" role="status" data-total="{total}"></p>
    <div class="blank" id="none" hidden><p data-s="mt0">Nothing matches that.</p><button class="btn" type="button" id="clear">Clear the search and the filters</button></div>'''


def has_test_sort(plugins):
    return any(p.get("test_mem") is not None for p in plugins)


def home(plugins, depth_releases, sb, apps=()):
    P = sorted(plugins, key=lambda p: p["name"].lower())
    tiles = "".join(tile(p, 0) for p in P)
    n = len(P)
    latest = sb["latest"]
    app_line = (" Apps that work with Starboard: " + ", ".join(f'<a href="{esc(a["id"])}.html">Works with Starboard: {esc(a["name"])}</a>' for a in apps) + ".") if apps else ""
    return f'''
<main id="main">
<section class="banner" aria-labelledby="hero-h"><div class="wrap banner__in">
  <div><h1 id="hero-h">Plug-ins for Starboard</h1><p class="banner__sub">{n} plug-ins, each checked and then read by a person. New to Starboard? <a href="starboard.html">Start here{f", with release {esc(latest['version'])}" if latest else ""}</a>.{app_line}</p></div>
  <div class="banner__tools">{search_form("all-list", "Try backups, Jellyfin or lights.", "the plug-ins")}</div>
</div></section>
<div class="wrap store-layout">
  {rail(P, depth_releases, "all", 0, has_test_sort(P))}
  <section class="store-layout__main" id="all-plug-ins" aria-labelledby="all-h"><h2 id="all-h" tabindex="-1">All plug-ins</h2>
    {results_block("all-list", n)}
    <ul class="grid tiles" id="all-list">{tiles}</ul>
  </section>
</div>
</main>'''


def category_page(kind, plugins, releases=()):
    slug, ic, line = KINDS[kind]
    ps = sorted([p for p in plugins if p["kind"] == kind], key=lambda p: p["name"].lower())
    tiles = "".join(tile(p, 1) for p in ps)
    n = len(ps)
    return f'''
<main id="main">
<section class="banner banner--cat kind-{slug}" aria-labelledby="hero-h"><div class="wrap">
  <nav class="crumbs" aria-label="Breadcrumb"><ol><li><a href="../index.html">Home</a></li><li><a href="index.html">Categories</a></li><li><span aria-current="page">{esc(kind)}</span></li></ol></nav>
  <div class="banner__in">
  <div><h1 id="hero-h">{esc(kind)}</h1><p class="banner__sub">{esc(KIND_ABOUT[kind])} {plural(n)}.</p></div>
  <div class="banner__tools">{search_form("cat-list", "Try a name or a word such as backups.", "this category")}</div></div>
</div></section>
<div class="wrap store-layout">
  {rail(plugins, releases, kind, 1, has_test_sort(plugins))}
  <section class="store-layout__main" aria-labelledby="results-h"><h2 id="results-h" tabindex="-1">Plug-ins in this category</h2>
    {results_block("cat-list", n)}
    <ul class="grid tiles" id="cat-list">{tiles}</ul>
  </section>
</div>
</main>'''


def category_index(plugins):
    cards = "".join(
        f'<li><a class="cat kind-{KINDS[k][0]}" href="{KINDS[k][0]}.html"><span class="cat__icon">{icon(KINDS[k][1])}</span><span class="cat__text"><span class="cat__name">{esc(k)}</span><span class="cat__line">{esc(KIND_ABOUT[k])}</span></span><span class="cat__count">{plural(n)} {icon("chevron-right")}</span></a></li>'
        for k in KINDS for n in [sum(1 for p in plugins if p["kind"] == k)] if n)
    return f'''
<main id="main">
<section class="banner" aria-labelledby="hero-h"><div class="wrap">
  <nav class="crumbs" aria-label="Breadcrumb"><ol><li><a href="../index.html">Home</a></li><li><span aria-current="page">Categories</span></li></ol></nav>
  <h1 id="hero-h">Categories</h1><p class="banner__sub">Every plug-in sits in one category. Each category has a page, with a search of its own.</p>
</div></section>
<div class="wrap section"><h2 class="visually-hidden">The categories</h2><ul class="cats">{cards}</ul>
<p data-s="mt2"><a class="btn" href="../index.html#all-plug-ins">Search every plug-in</a></p></div></main>'''


# ------------------------------------------------------------------ a plug-in


def pictures(p, depth):
    k = KINDS[p["kind"]][0]
    logo = f'<image href="{rel(depth)}{p["logo_file"]}" x="20" y="20" width="44" height="44"/>'

    def base(inner, i, title):
        return f'<svg viewBox="0 0 320 200" role="img" aria-labelledby="pic{i}"><title id="pic{i}">{esc(title)}</title><rect width="320" height="200" fill="var(--color-bg)"/>{inner}</svg>'

    def bar(x, y, w, o=1):
        return f'<rect x="{x}" y="{y}" width="{w}" height="8" rx="4" fill="var(--color-text)" opacity="{o}"/>'
    card = '<rect x="12" y="12" width="296" height="176" rx="14" fill="var(--color-surface)" stroke="var(--ink)" stroke-width="2"/>'
    s1 = base(f'{card}<rect x="12" y="12" width="296" height="64" rx="14" fill="var(--c-{k}-bg)"/><rect x="12" y="60" width="296" height="16" fill="var(--c-{k}-bg)"/>{logo}<rect x="76" y="30" width="110" height="12" rx="6" fill="var(--c-{k}-fg)"/><rect x="76" y="50" width="70" height="8" rx="4" fill="var(--c-{k}-fg)" opacity=".7"/>{bar(28, 98, 220)}{bar(28, 118, 180, .6)}<rect x="28" y="146" width="84" height="26" rx="13" fill="var(--color-accent)"/><rect x="124" y="146" width="64" height="26" rx="13" fill="none" stroke="var(--ink)" stroke-width="2"/>',
              1, f"A drawing of {p['name']} as a card on the Starboard home page: its logo, name and two buttons.")
    s2 = base(f'{card}{bar(28, 30, 100)}<rect x="28" y="52" width="264" height="28" rx="8" fill="none" stroke="var(--color-border)" stroke-width="2"/><rect x="28" y="92" width="264" height="28" rx="8" fill="none" stroke="var(--color-border)" stroke-width="2"/><circle cx="270" cy="106" r="9" fill="var(--color-accent)"/>{bar(40, 62, 90, .6)}{bar(40, 102, 120, .6)}<rect x="28" y="140" width="84" height="26" rx="13" fill="var(--color-accent)"/>',
              2, f"A drawing of the settings page of {p['name']}: two settings boxes and a Save button.")
    s3 = base(f'{card}{logo}{bar(80, 34, 150)}{bar(28, 84, 240, .7)}{bar(28, 102, 200, .7)}{bar(28, 120, 220, .7)}<rect x="28" y="146" width="96" height="26" rx="13" fill="var(--color-accent)"/><rect x="136" y="146" width="64" height="26" rx="13" fill="none" stroke="var(--ink)" stroke-width="2"/>',
              3, f"A drawing of the question Starboard asks before adding {p['name']}: the plug-in's logo, a list of what it asks for and two buttons.")
    caps = ["Its card on the Starboard home page.", "Its settings, where you choose how it behaves.", "The question Starboard asks before it is added."]
    return "".join(f"<figure>{s}<figcaption>{esc(c)}</figcaption></figure>" for s, c in zip((s1, s2, s3), caps))


def gallery(p, depth):
    shots = p.get("shots") or []
    if not shots:
        return f'''<section id="pictures" aria-labelledby="pictures-h"><h2 id="pictures-h">Pictures</h2><div class="pics">{pictures(p, depth)}</div><p class="muted">These are drawings of the screens, not screenshots. Real screenshots of this plug-in have not been added yet.</p></section>'''
    figs = "".join(f'<figure><a href="{rel(depth)}{esc(x["file"])}"><img src="{rel(depth)}{esc(x["file"])}" alt="{esc(x["alt"])}" loading="lazy" decoding="async"{f" width={x["w"]} height={x["h"]}" if x.get("w") and x.get("h") else ""}></a>{f"<figcaption>{esc(x["caption"])}</figcaption>" if x.get("caption") else ""}</figure>' for x in shots)
    return f'''<section id="pictures" aria-labelledby="pictures-h"><h2 id="pictures-h">Pictures</h2><div class="pics pics--wide" role="group" aria-label="Screenshots of {esc(p["name"])}">{figs}</div><p class="muted">Real screenshots from a test copy of Starboard that holds made-up data only. Select a picture to open it full size.</p></section>'''


def issue_address(p):
    m = p["manifest"]
    title = urllib.parse.quote(f"Problem with {m['name']} {m['version']}")
    sup, home = m["support_url"], m["homepage"]
    g = re.match(r"^(https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/?$", sup)
    if g:
        return f"{g.group(1)}/issues/new?title={title}"
    h = re.match(r"^(https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)(/|$)", home)
    if sup and mf.https_or_empty(sup):
        return sup
    if h:
        return f"{h.group(1)}/issues/new?title={title}"
    return ""


def test_section(p):
    """Memory use, Processor and Image size as measured on a test Starboard with made-up data (kept apart from figures from a real server)."""
    t = p.get("test")
    if not t:
        return '<h3 id="test-h">On a test server</h3><p class="muted">Not measured on a test server yet.</p>'
    when = esc(nice_date(t["measured_at"][:10]))
    sb = f", Starboard {esc(t['starboard_version'])}" if t["starboard_version"] else ""
    label = f'Measured on a test server with made-up data, {when}{sb}.' + (f' Machine: {esc(t["machine"])}.' if t["machine"] else "")
    if t["no_container"]:
        return f'<h3 id="test-h">Measured on a test server</h3><p><strong>No container.</strong> This plug-in runs nothing of its own, so it has no memory, processor or image to measure. Read from its manifest, {when}.</p>'
    if t.get("problem"):
        return f'<h3 id="test-h">On a test server</h3><p><strong>It did not run cleanly on the test server.</strong> {esc(t["problem"])} {esc(label)}</p>'
    x = tb.totals(t)
    f = lambda v, unit: ("<span class=muted>Not read</span>" if v is None else f"About {rs.fmt(v)} {unit}")  # noqa: E731
    rows = [("Memory use, idle after start", f(x["memory_start"], "MB")), ("Memory use, after it was used", f(x["memory_used"], "MB")),
            ("Processor, averaged over 60 seconds idle", f(x["cpu"], "% of one core")), ("Image size, unpacked", f(x["image"], "MB")),
            ("Containers", str(x["count"]))]
    body = "".join(f'<tr><th scope="row">{esc(a)}</th><td>{b}</td></tr>' for a, b in rows)
    return (f'<h3 id="test-h">Measured on a test server</h3><p>{label} These are not figures from a real server.</p>'
            f'<div class="table-wrap" role="region" aria-labelledby="test-h" tabindex="0"><table class="table"><caption class="visually-hidden">What {esc(p["name"])} used on a test server</caption>'
            f'<thead><tr><th scope="col">What</th><th scope="col">Figure</th></tr></thead><tbody>{body}</tbody></table></div>')


def test_line(p):
    """One short line for the facts strip: what the test server showed, kept apart from the Memory use cell."""
    t = p.get("test")
    if not t:
        return "Not measured on a test server yet"
    if t["no_container"]:
        return "No container, nothing to measure"
    if t.get("problem"):
        return "It did not run on the test server"
    x = tb.totals(t)
    v = x and (x["memory_used"] if x["memory_used"] is not None else x["memory_start"])
    return "Not read on the test server" if v is None else f"About {rs.fmt(v)} MB of memory on a test server"


def use_section(p):
    """What it uses: a plain table, Declared and Measured kept apart, never invented."""
    m = p["manifest"]
    dec = rs.declared(m)
    tot = p["measured_totals"]
    meas = p["measured"]
    maker = p["maker_figures"]
    nm = '<span class="muted">Not measured yet</span>'
    rows = []

    def row(what, value, kind, note=""):
        rows.append(f'<tr><th scope="row">{esc(what)}</th><td data-label="Figure">{value}</td><td data-label="Kind"><span class="chip" data-tone="{"success" if kind == "Measured" else "info" if kind == "Maker" else ""}">{esc({"Measured": "Measured", "Declared": "Declared", "Maker": "Maker\'s figure", "None": "Not measured"}[kind])}</span></td><td data-label="Note">{note}</td></tr>')
    if tot and tot["memory"] is not None:
        row("Memory at rest", f'About {rs.fmt(tot["memory"])} MB', "Measured", "The middle of the samples taken.")
        row("Most memory seen", f'{rs.fmt(tot["memory_max"])} MB' if tot["memory_max"] is not None else nm, "Measured" if tot["memory_max"] is not None else "None", "The largest of the samples.")
    elif maker:
        row("Memory at rest", f'About {rs.fmt(maker["memory_mib"])} MB', "Maker", "Not measured by the reviewer.")
        row("Most memory seen", nm, "None")
    else:
        row("Memory at rest", nm, "None")
        row("Most memory seen", nm, "None")
    if dec["memory_mb"] is not None:
        note = "Starboard's default of 128 MB is used for each container that names no limit." if dec["default_used"] else "The most it may use before Docker stops it."
        row("Memory limit it is given", f'{rs.fmt(dec["memory_mb"])} MB', "Declared", note)
    if tot and tot["cpu"] is not None:
        row("Processor at rest", f'About {tot["cpu"]:g}% of one core', "Measured", "")
    elif maker:
        row("Processor at rest", f'About {maker["cpu_percent"]:g}% of one core', "Maker", "Not measured by the reviewer.")
    else:
        row("Processor at rest", nm, "None")
    if dec["cpus"] is not None:
        row("Processor limit", f'{dec["cpus"]:g} of a core', "Declared", "")
    if dec["pids"] is not None:
        row("Process limit", f'{rs.fmt(dec["pids"])}', "Declared", "The most programs it can run at once.")
    if tot and tot["image"] is not None:
        row("Image on disk, unpacked", f'{rs.fmt(tot["image"])} MB', "Measured", "The size of the container's image on the server. The smaller size it downloads at is not read.")
    else:
        row("Image on disk, unpacked", nm, "None")
    row("Disk for its own data", f'{rs.fmt(tot["data"])} MB' if tot and tot.get("data") is not None else nm, "Measured" if tot and tot.get("data") is not None else "None", "Its folder in Starboard's data.")
    cs = m["containers"]
    ports = [f'{c["name"]}: port {int(c["port"])}' for c in cs if c.get("port")]
    perms = m["permissions"]
    reach = ("Your home network and the internet" if "network:lan" in perms else "Through your VPN" if "network:vpn" in perms else "Only Starboard: it has no way out to your network or the internet") if cs else "None: it runs nothing of its own"
    row("Network", esc(reach) + (f'. Opens its own web page on your home network.' if "network:port" in perms else "."), "Declared", esc("; ".join(ports)) if ports else "")
    row("Containers", f'{len(cs)}' + (" (" + esc(", ".join(c["name"] for c in cs)) + ")" if cs else ""), "Declared", "")
    when = [c for c in cs if c["start"] == "when_needed"]
    if cs:
        if len(when) == len(cs):
            mins = [c["idle_stop_minutes"] for c in when if c["idle_stop_minutes"]]
            row("Runs", "Only when needed" + (f", and rests after {rs.fmt(min(mins))} minutes with nothing to do" if mins else ""), "Declared", "")
        elif when:
            row("Runs", "Some containers only when needed, the rest all the time", "Declared", "")
        else:
            row("Runs", "All the time", "Declared", "")
    row("Asks to read or change", f'{len(perms)} thing{"" if len(perms) == 1 else "s"}: <a href="#access">the list above</a>', "Declared", "")
    how = ""
    if meas:
        how = f'<p class="muted">Measured on {esc(nice_date(meas["measured_at"][:10]))}. {esc(meas["how"])}.</p>'
    elif maker:
        how = '<p class="muted">The memory and processor figures are the maker\'s, not measured by the reviewer. They are shown until a reviewer measures them.</p>'
    else:
        how = '<p class="muted">Nobody has measured this plug-in on a running server yet, so no memory or processor figure is shown. The limits marked Declared are what its manifest allows, not what it uses.</p>'
    return f'''<section id="uses" aria-labelledby="uses-h"><h2 id="uses-h">What it uses</h2>
          <p>Two kinds of figure appear here, and each row says which. <strong>Measured</strong> figures were read from a running plug-in. <strong>Declared</strong> figures are limits written in its manifest. Where nothing is measured, it says so.</p>
          <div class="table-wrap" data-stack role="region" aria-label="What {esc(m["name"])} uses" tabindex="0"><table class="table"><caption class="visually-hidden">What {esc(m["name"])} uses</caption><thead><tr><th scope="col">What</th><th scope="col">Figure</th><th scope="col">Kind</th><th scope="col">Note</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>{how}{test_section(p)}</section>'''


def plugin_page(p, sb, plugins=()):
    m = p["manifest"]
    depth = 1
    apps = needs_apps(p)
    perm_items = []
    for c in m["permissions"]:
        t, d, lv = PERM.get(c, (c, "Not described yet.", "both"))
        lw, li = LEVEL[lv]
        perm_items.append({"c": c, "t": t, "d": d, "lv": lv, "lw": lw, "li": li})
    web = "network:port" in m["permissions"]
    sb_text, sb_upto = sb_need_text(p)
    versions_src = m["versions"] or [{"version": m["version"], "date": "", "groups": []}]
    vers = []
    for i, v in enumerate(versions_src):
        notes = "".join(f'<h4>{esc(lab)}</h4><ul>{"".join(f"<li>{esc(x)}</li>" for x in items)}</ul>' for lab, items in v["groups"]) or "<p>No notes were recorded for this version.</p>"
        vers.append(f'<li><div class="vers__head"><h3>Version {esc(v["version"])}</h3>{f"""<span class="chip" data-tone="success">{icon("circle-check")}Latest</span>""" if i == 0 else ""}<span class="muted">{esc(nice_date(v["date"])) if v["date"] else "Date not recorded"}</span></div>{notes}</li>')
    notice = ""
    if p["reviewed"]["version"] != m["version"]:
        notice = f'<div class="notice" data-tone="info" role="note">{icon("info")}<div class="notice__body"><span class="notice__title">A newer version has not been reviewed</span><p>A person reviewed version {esc(p["reviewed"]["version"])}. The maker has since published {esc(m["version"])}. Starboard shows what it asks for before you add it.</p></div></div>'
    own = own_chip() if p["own"] else ""
    help_addr = addr(p["help"]) or ""
    if help_addr:
        help_btn = f'<a class="btn" href="{help_addr}" target="_blank" rel="noopener">{icon("help-new-tab")}Help for this plug-in<span class="visually-hidden"> (opens in a new tab)</span></a>'
        help_sec = f'<p>The plug-in help centre explains what {esc(m["name"])} does, how to set it up and what to do when it does not work.</p><p><a class="btn" href="{help_addr}" target="_blank" rel="noopener">{icon("help-new-tab")}Help for {esc(m["name"])}<span class="visually-hidden"> (opens in a new tab)</span></a></p>'
    else:
        help_btn = ""
        help_sec = f'<p>This plug-in has no help pages of its own in the plug-in help centre.</p>' + (f'<p><a class="btn" href="{addr(m["homepage"])}" target="_blank" rel="noopener">{icon("external-link")}The maker\'s page<span class="visually-hidden"> (opens in a new tab)</span></a></p>' if addr(m["homepage"]) else "")
    issue = issue_address(p)
    if issue:
        report = f'<p>Something wrong with {esc(m["name"])} itself? Tell its maker. The report goes to the plug-in\'s own issue page, not to Stallboard.</p><p><a class="btn btn--primary" href="{esc(issue)}" target="_blank" rel="noopener">{icon("external-link")}Report a problem with this plug-in<span class="visually-hidden"> (opens in a new tab)</span></a></p>'
    else:
        report = f'<p>{esc(m["name"])} does not give a place to report problems, so there is no link here. Ask its maker, {esc(p["maker"])}, in the place you found it.</p>'
    mfy_line = esc(p["mem_line"])
    sf = p.get("sf")
    does_html = "".join(f"<p>{esc(x)}</p>" for x in sf["does"]) if sf else f'<p>{esc(m["description"])}</p>'
    who_html = f'<section id="who" aria-labelledby="who-h"><h2 id="who-h">Who it is for</h2><p>{esc(sf["for"])}</p></section>' if sf else ""
    sees_html = f'<section id="sees" aria-labelledby="sees-h"><h2 id="sees-h">What you will see</h2><p>{esc(sf["shows"])}</p></section>' if sf else ""
    sys_tags = ", ".join(m.get("needs") or [])
    needs_extra = ""
    if sf:
        needs_extra = f'<div><dt>In practice</dt><dd>{esc(sf["needs"])}</dd></div>'
    if sys_tags:
        needs_extra += f'<div><dt>System tags</dt><dd>{esc(sys_tags)}. These are the names in the manifest that Starboard checks before it adds the plug-in.</dd></div>'
    tags_html = f'<ul class="chiprow" aria-label="Tags">{"".join(f"<li><span class=chip>{esc(t)}</span></li>" for t in sf["tags"])}</ul>' if sf and sf["tags"] else ""
    old = ""
    if p["older_versions"]:
        old = f'<p class="muted">Older versions Starboard can fall back to: {esc(", ".join(v["version"] for v in p["older_versions"]))}.</p>'
    same = [x for x in sorted(plugins, key=lambda x: x["name"].lower()) if x["kind"] == p["kind"] and x["id"] != p["id"]][:4]
    more_html = f'<section class="wrap more" aria-labelledby="more-h"><h2 id="more-h">More in {esc(p["kind"])}</h2><ul class="grid tiles">{"".join(tile(x, 1, data=False) for x in same)}</ul></section>' if same else ""
    body = f'''
<main id="main"><div id="plugin">
    <header class="phead kind-{KINDS[p["kind"]][0]}"><div class="wrap">
      <nav class="crumbs" aria-label="Breadcrumb"><ol><li><a href="../index.html">Home</a></li><li><a href="../category/{KINDS[p["kind"]][0]}.html">{esc(p["kind"])}</a></li><li><span aria-current="page">{esc(m["name"])}</span></li></ol></nav>
      <div class="phead__in">
        {plate(p, 1, 112)}
        <div class="phead__text">
          <p class="kicker">{esc(p["kind"])}</p>
          <h1>{esc(m["name"])}</h1>
          <p class="phead__pitch">{esc(pitch_of(p))}</p>
          <ul class="chiprow" aria-label="Marks and version"><li>{reviewed_chip()}</li>{f"<li>{own}</li>" if own else ""}<li><span class="chip">Version {esc(m["version"])}</span></li></ul>
        </div>
        <div class="phead__actions"><a class="btn btn--primary btn--big" href="#install" data-dialog="install-dialog">{icon("plus")}How to install in Starboard</a>{help_btn}</div>
      </div></div></header>
    <div class="wrap">{notice}
      <section class="glance" aria-labelledby="glance-h"><h2 class="visually-hidden" id="glance-h">At a glance</h2><dl class="strip">
        <div><dt>Reviewed</dt><dd>{esc(nice_date(p["reviewed"]["at"]))}, version {esc(p["reviewed"]["version"])}</dd></div>
        <div><dt>Works with</dt><dd>{media_chips(p)}</dd></div>
        <div><dt>Starboard</dt><dd><a href="../starboard.html#plugin-api">{esc(sb_text)}</a></dd></div>
        <div><dt>Memory use</dt><dd>{mfy_line}</dd></div>
        <div><dt>On a test server</dt><dd><a href="#uses">{esc(test_line(p))}</a></dd></div></dl></section></div>
    <div class="wrap layout">
      <nav class="toc" aria-label="On this page"><h2>On this page</h2><ol>
        <li><a href="#what">What it does</a></li><li><a href="#who">Who it is for</a></li><li><a href="#sees">What you will see</a></li><li><a href="#pictures">Pictures</a></li><li><a href="#access">What it can read and change</a></li><li><a href="#needs">What it needs</a></li><li><a href="#uses">What it uses</a></li><li><a href="#versions">Versions and notes</a></li><li><a href="#help">Help</a></li><li><a href="#install">How to install</a></li><li><a href="#review">Who reviewed it</a></li><li><a href="#report">Report a problem</a></li></ol></nav>
      <div class="doc">
        <section id="what" aria-labelledby="what-h"><h2 id="what-h">What it does</h2>{does_html}<p class="muted">Made by {esc(p["maker"])}.{f" Licence: {esc(m['licence'])}." if m["licence"] else ""}</p>{f'<p>{esc(p["notes"])}</p>' if p["notes"] else ""}{tags_html}</section>
        {who_html}{sees_html}
        {gallery(p, depth)}
        <section id="access" aria-labelledby="access-h"><h2 id="access-h">What it can read and change</h2>
          <p>Starboard asks you before it gives a plug-in any of these. You can take one away later in Settings, then Plug-ins.</p>
          {"<ul class=&quot;perm&quot;>".replace("&quot;", '"') + "".join(f'<li><span class="chip">{icon(x["li"])}{x["lw"]}</span><div><strong>{esc(x["t"])}</strong><p>{esc(x["d"])}</p></div><p><code>{esc(x["c"])}</code></p></li>' for x in perm_items) + "</ul>" if perm_items else "<p>It asks for nothing: it cannot read or change anything in Starboard.</p>"}
          <div class="rw"><div><h3>{icon("eye")} It can read</h3>{"<ul>" + "".join(f'<li>{esc(x["t"])}</li>' for x in perm_items if x["lv"] != "change") + "</ul>" if any(x["lv"] != "change" for x in perm_items) else "<p>Nothing.</p>"}</div><div><h3>{icon("pencil")} It can change</h3>{"<ul>" + "".join(f'<li>{esc(x["t"])}</li>' for x in perm_items if x["lv"] != "read") + "</ul>" if any(x["lv"] != "read" for x in perm_items) else "<p>Nothing.</p>"}</div></div></section>
        <section id="needs" aria-labelledby="needs-h"><h2 id="needs-h">What it needs</h2><dl class="spec">
          <div><dt>Starboard</dt><dd><a href="../starboard.html#plugin-api">{esc(sb_text)}</a>{f". {esc(sb_upto)}" if sb_upto else ""}. Its manifest asks for {api_words(m["starboard_api"])}.</dd></div>
          <div><dt>Other apps</dt><dd>{esc(join_words(apps)) + ", already set up." if apps else "Nothing else."}</dd></div>{needs_extra}
          <div><dt>A web page</dt><dd>{"It opens its own page on your server." if web else "No. It shows on the Starboard dashboard."}</dd></div></dl></section>
        {use_section(p)}
        <section id="versions" aria-labelledby="versions-h"><h2 id="versions-h">Versions and notes</h2><ul class="vers">{"".join(vers)}</ul>{old}</section>
        <section id="help" aria-labelledby="help-h"><h2 id="help-h">Help</h2>{help_sec}</section>
        <section id="install" aria-labelledby="install-h"><h2 id="install-h">How to install in Starboard</h2>
          <div class="tabs" data-activation="manual"><div class="tabs__list js-only" role="tablist" aria-label="Ways to install {esc(m["name"])}" hidden>
            <button class="tabs__tab" type="button" role="tab" id="t-1" aria-controls="tp-1" aria-selected="true">From Starboard</button>
            <button class="tabs__tab" type="button" role="tab" id="t-2" aria-controls="tp-2" aria-selected="false" tabindex="-1">By address</button></div>
            <div class="tabs__panel" role="tabpanel" id="tp-1" aria-labelledby="t-1" tabindex="0"><h3 class="nojs-h">From Starboard</h3><ol class="how"><li>In Starboard, open Settings, then Plug-ins, then Catalogue.</li><li>Under Catalogue sources, paste <code>{esc(CATALOGUE_URL)}</code> and select Add catalogue. You do this once.</li><li>Find {esc(m["name"])} in the Catalogue and select Install. Starboard shows what it asks for, and you choose.</li></ol></div>
            <div class="tabs__panel" role="tabpanel" id="tp-2" aria-labelledby="t-2" tabindex="0"><h3 class="nojs-h">By address</h3><p>Or give Starboard this plug-in's address: in Settings, then Plug-ins, then Catalogue, paste it under Add one from elsewhere.</p><p><code id="manifest">{esc(p["manifest_url"])}</code></p><p class="js-only" hidden><button class="btn" type="button" id="copy-manifest">{icon("copy")}Copy the address</button> <span role="status" id="copy-status" class="muted"></span></p></div></div></section>
        <section id="review" aria-labelledby="review-h"><h2 id="review-h">Who reviewed it</h2><p>Reviewed by <strong>{esc(p["reviewed"]["by"])}</strong> on {esc(nice_date(p["reviewed"]["at"]))}, version {esc(p["reviewed"]["version"])}. Listed on {esc(nice_date(p["listed_at"]))}. Its manifest was last read on {esc(nice_date(p["snapshot_date"]))}. <a href="../what-reviewed-means.html">What Reviewed means</a>.</p></section>
        <section id="report" aria-labelledby="report-h"><div class="callout"><h2 id="report-h" data-s="m0">Report a problem with this plug-in</h2>{report}<p class="muted">A problem with Stallboard, such as this page? Use the Send feedback button.</p></div></section>
      </div></div>
    {more_html}
    <dialog class="dialog" id="install-dialog" aria-labelledby="install-dialog-h">
      <div class="panel-header"><h2 class="panel-header__title" id="install-dialog-h">Add {esc(m["name"])} to Starboard</h2><button class="icon-btn" type="button" data-closes aria-label="Close">{icon("x")}</button></div>
      <div class="dialog__body"><p>Stallboard cannot install anything: only your own Starboard can, and it asks for your password first. Add Stallboard to Starboard once, then install from its Catalogue.</p><ol class="how"><li>In Starboard, open Settings, then Plug-ins, then Catalogue.</li><li>Under Catalogue sources, paste <code>{esc(CATALOGUE_URL)}</code> and select Add catalogue.</li><li>Find {esc(m["name"])} and select Install.</li></ol><p>It will ask to: {esc(join_words([x["t"][0].lower() + x["t"][1:] for x in perm_items]) if perm_items else "nothing")}.</p></div>
      <div class="dialog__foot"><a class="btn btn--primary" href="../starboard.html">New to Starboard? Start here</a><button class="btn btn--quiet" type="button" data-closes>Close</button></div>
    </dialog>
</div></main>'''
    return body
