"""The pages that are words: Starboard, Submit, What Reviewed means, accessibility, privacy and the 404."""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from render import (CATALOGUE_URL, HELP_CENTRE, REPO_URL, SITE_PATH, STARBOARD_REPO, SITE_URL, addr, esc, footer, head, header,  # noqa: E402
                    icon, nice_date, tail)
import releases as rl  # noqa: E402

ISSUES_NEW = REPO_URL + "/issues/new"
SUBMIT_FORM = REPO_URL + "/issues/new?template=submit-a-plug-in.yml"
HELP = "https://themightytrex.github.io/starboard/help/"


def wrap(inner):
    return f'<main id="main"><div class="wrap section prose-page">{inner}</div></main>'


def starboard_page(sb, plugins):
    rels, latest, shots = sb["releases"], sb["latest"], sb["shots"]
    notes = addr(latest["url"]) if latest else REPO_URL + "/releases"
    # The first release that has each plug-in API a plug-in on the store asks for.
    apis = []
    for r in rels:
        if not apis or apis[-1][0] != r["api"]:
            apis.append((r["api"], r))
    first_rows = "".join(f'<tr><th scope="row">{esc(rl.short(api))}</th><td>Starboard {esc(r["version"])}</td><td>{esc(nice_date(r["date"])) if r["date"] else "Date not recorded"}</td></tr>' for api, r in apis[::-1][:10])
    need_rows = {}
    for p in plugins:
        need_rows.setdefault(p["needs_sb"]["first"] or "not yet released", []).append(p)
    need_html = "".join(
        f'<li><strong>Starboard {esc(k)} or later</strong>: ' + ", ".join(f'<a href="plugins/{esc(p["id"])}.html">{esc(p["name"])}</a>' for p in sorted(v, key=lambda p: p["name"].lower())) + "</li>"
        for k, v in sorted(need_rows.items(), key=lambda kv: rl.ver(kv[0]) or (999,)))
    figs = "".join(f'<figure><img src="assets/starboard/{esc(s["file"])}" alt="{esc(s["alt"])}" width="640" height="400" loading="lazy"><figcaption>{esc(s["alt"])}</figcaption></figure>' for s in shots)
    recent = "".join(f'<li><a href="{addr(r["url"])}" target="_blank" rel="noopener">Starboard {esc(r["version"])}<span class="visually-hidden"> release notes (opens in a new tab)</span></a>, {esc(nice_date(r["date"])) if r["date"] else "date not recorded"}, plug-in API {esc(r["api"])}</li>' for r in rels[::-1][:8])
    inner = f'''
<h1 class="display">Starboard</h1>
<p class="lede">Every plug-in here is a plug-in for Starboard, so Starboard comes first. It installs and runs a whole home media server from one accessible dashboard, and is light enough for an old laptop or a Raspberry Pi.</p>
<section aria-labelledby="ver-h"><h2 id="ver-h">The current version</h2>
{f'<p><strong>Starboard {esc(latest["version"])}</strong>, released {esc(nice_date(latest["date"])) if latest["date"] else "recently"}, with plug-in API {esc(latest["api"])}. <a href="{notes}" target="_blank" rel="noopener">Release notes for {esc(latest["version"])}<span class="visually-hidden"> (opens in a new tab)</span></a>.</p>' if latest else "<p>The version could not be read when this page was built.</p>"}
<p>Starboard is open source. <a href="{STARBOARD_REPO}" target="_blank" rel="noopener">Starboard on GitHub<span class="visually-hidden"> (opens in a new tab)</span></a> has the code, and <a href="{STARBOARD_REPO}/releases" target="_blank" rel="noopener">every release<span class="visually-hidden"> (opens in a new tab)</span></a>.</p></section>
<section aria-labelledby="inst-h"><h2 id="inst-h">How to install it</h2>
<p>Starboard runs on Linux Mint, Debian, Ubuntu Server and Raspberry Pi OS (64-bit). Start with the Run first script. On one of those systems, open a terminal and enter:</p>
<pre class="code" tabindex="0"><code>curl -fsSL https://raw.githubusercontent.com/TheMightyTRex/starboard/main/run-first.sh | bash</code></pre>
<p>It checks the computer, installs Docker and anything else missing after you say yes, downloads Starboard and starts its installer. These are the step by step guides, written for each system:</p>
<ul>
<li><a href="{HELP}topics/start-on-linux-mint.html" target="_blank" rel="noopener">Start Starboard on Linux Mint<span class="visually-hidden"> (opens in a new tab)</span></a> (recommended)</li>
<li><a href="{HELP}topics/start-on-debian.html" target="_blank" rel="noopener">Start Starboard on Debian<span class="visually-hidden"> (opens in a new tab)</span></a></li>
<li><a href="{HELP}topics/start-on-ubuntu-server.html" target="_blank" rel="noopener">Start Starboard on Ubuntu Server<span class="visually-hidden"> (opens in a new tab)</span></a></li>
<li><a href="{HELP}topics/start-on-raspberry-pi-os.html" target="_blank" rel="noopener">Start Starboard on Raspberry Pi OS<span class="visually-hidden"> (opens in a new tab)</span></a></li></ul>
<p>The <a href="{STARBOARD_REPO}#quick-start" target="_blank" rel="noopener">quick start in the README<span class="visually-hidden"> (opens in a new tab)</span></a> has what each system needs and the commands in full.</p></section>
<section id="plugin-api" aria-labelledby="api-h"><h2 id="api-h">What every plug-in needs from it</h2>
<p>A plug-in asks for a plug-in API range in its manifest, such as 1.14 or later. Each Starboard release has one plug-in API version. Stallboard turns the range into the first Starboard release that has it, so each plug-in says "Needs Starboard 0.26 or later". If your Starboard is older, update it first: Starboard also offers an older version of a plug-in that suits it, where one exists.</p>
<div class="table-wrap" role="region" aria-label="The first Starboard release for each plug-in API" tabindex="0"><table class="table"><caption class="visually-hidden">The first Starboard release for each plug-in API</caption><thead><tr><th scope="col">Plug-in API</th><th scope="col">First release</th><th scope="col">Released</th></tr></thead><tbody>{first_rows}</tbody></table></div>
<h3>Which plug-ins need which</h3><ul>{need_html}</ul></section>
{f'<section aria-labelledby="shots-h"><h2 id="shots-h">What it looks like</h2><div class="pics pics--wide">{figs}</div><p class="muted">The pictures are from Starboard\'s own README and use example data.</p></section>' if shots else ""}
<section aria-labelledby="cat-h"><h2 id="cat-h">Add Stallboard to Starboard</h2>
<p>Once you have Starboard, add this store as a catalogue, and its plug-ins appear in your Catalogue.</p>
<ol class="how"><li>In Starboard, open Settings, then Plug-ins, then Catalogue.</li><li>Under Catalogue sources, paste <code>{esc(CATALOGUE_URL)}</code> into Catalogue address.</li><li>Select Add catalogue. Adding a catalogue installs nothing: each plug-in still shows what it asks for before you choose to install it.</li></ol></section>
<section aria-labelledby="rel-h"><h2 id="rel-h">Recent releases</h2><ul>{recent}</ul></section>'''
    return head("Starboard: start here | Stallboard", "What Starboard is, its current version, how to install it and what every plug-in needs from it.", 0, "starboard.html", "starboard") + header(0, "starboard") + wrap(inner) + footer(0) + tail(0)


def submit_page(repo_checks):
    inner = f'''<div class="grid2">
  <div>
    <h1 class="display">Submit a plug-in</h1>
    <p class="lede">Made a plug-in for Starboard? Send us its address. It costs nothing, and nobody is paid to say yes or no.</p>
    <p>Submissions go through GitHub, with no server of ours in between. You need a GitHub account. The form below checks your answers, then opens GitHub's own form for you to read and post. <strong>Nothing is sent until you post it there</strong>, and what you post is public.</p>
    <div class="sheet" style="margin-top:2rem" id="form-area">
      <form id="submit-form" class="form-stack" novalidate action="{SUBMIT_FORM}" method="get" target="_blank">
        <input type="hidden" name="template" value="submit-a-plug-in.yml">
        <div class="field"><label class="field__label" for="address">Address of your plug-in<span class="field__required" aria-hidden="true">*</span></label><p class="hint" id="address-hint">The web address of its Starboard plug-in file, <code>starboard-plugin.json</code>, starting with https://. On GitHub, use the Raw button to get it.</p><input class="input" id="address" name="manifest" type="text" inputmode="url" autocomplete="off" spellcheck="false" required aria-describedby="address-hint"></div>
        <div class="field"><label class="field__label" for="who">Your name or GitHub name</label><p class="hint" id="who-hint">So the page can say who made it. It is public.</p><input class="input" id="who" name="maker" type="text" autocomplete="off" aria-describedby="who-hint"></div>
        <div class="field"><label class="check"><input type="checkbox" id="mine" required><span class="check__text">This plug-in is mine to share, or I have the right to submit it.<span class="field__required" aria-hidden="true">*</span></span></label></div>
        <div class="actions"><button class="btn btn--primary btn--big" type="submit">Check and open the GitHub form<span class="visually-hidden"> (opens in a new tab)</span></button></div>
      </form>
    </div>
    <p class="muted">Without JavaScript, the button above opens GitHub's form directly, and GitHub asks for everything. You can also <a href="{SUBMIT_FORM}" target="_blank" rel="noopener">open the form on GitHub<span class="visually-hidden"> (opens in a new tab)</span></a> yourself.</p>
    <section class="sheet success" id="success" aria-labelledby="success-h" hidden>
      <div class="notice" data-tone="success" role="status">{icon("circle-check")}<div class="notice__body"><span class="notice__title">Ready to post on GitHub</span><p>GitHub's form opened in a new tab. The rest of the form is there, and nothing is sent until you select Submit new issue.</p></div></div>
      <h2 class="display" id="success-h" tabindex="-1" style="font-size:2rem"><span id="success-name">Thank you</span></h2>
      <p>Your address, <code id="success-addr"></code>, is filled in. If the tab did not open, <a id="success-link" href="{SUBMIT_FORM}" target="_blank" rel="noopener">open the form on GitHub<span class="visually-hidden"> (opens in a new tab)</span></a>.</p>
      <p><button class="btn" type="button" id="again">Submit another plug-in</button> <a class="btn" href="index.html">Back to browse</a></p>
    </section>
  </div>
  <section aria-labelledby="next-h">
    <h2 class="display" id="next-h" style="font-size:2rem;margin-bottom:1.25rem">What happens next</h2>
    <ol class="next" id="next">
      <li><h3>Automatic checks</h3><p>A robot reads your plug-in file as plain text, never running anything, and runs the same manifest check Starboard runs ({esc(repo_checks)}). It comments on your issue with what passed and what to fix.</p></li>
      <li><h3>Safety review</h3><p>A person checks everything it asks to read and change. Anything it asks for and does not need is raised with you.</p></li>
      <li><h3>A person reviews it</h3><p>A maintainer works through the <a href="{REPO_URL}/blob/main/REVIEWING.md" target="_blank" rel="noopener">review checklist<span class="visually-hidden"> (opens in a new tab)</span></a>: what it asks for against what it says it does, its licence, its image, its repository, secrets, its help and where to report problems.</p></li>
      <li><h3>Listed, with a Reviewed mark</h3><p>A maintainer approves it, a pull request adds it, and a person merges that. It appears in Stallboard with the mark <span class="chip" data-tone="success">{icon("shield-check")}Reviewed</span>, the date and who reviewed it.</p></li>
    </ol>
    <p><a href="what-reviewed-means.html">What Reviewed means</a></p>
  </section>
</div>'''
    return head("Submit a plug-in | Stallboard", "Send the address of your plug-in to be listed in Stallboard after checks and a review by a person.", 0, "submit.html", "submit") + header(0, "submit") + wrap(inner) + footer(0) + tail(0)


def reviewed_page(repo_checks):
    inner = f'''<h1 class="display">What Reviewed means</h1>
<p class="lede">Every plug-in on Stallboard carries the Reviewed mark, with who reviewed it and when. Here is what stands behind it, and what does not.</p>
<section aria-labelledby="r1"><h2 id="r1">What happens before a plug-in is listed</h2>
<ol class="how"><li><strong>Automatic checks.</strong> The plug-in's file is read as plain text, and never run. Starboard's own manifest check runs on it ({esc(repo_checks)}): the fields, the permission names, limits, images pinned by digest, and the logo. A plug-in that would not install in Starboard is not listed.</li>
<li><strong>A safety check of what it asks for.</strong> Each permission is listed in plain words on the plug-in's page, with whether it reads or changes things. A reviewer compares them with what the plug-in says it does.</li>
<li><strong>A person reads it.</strong> The reviewer follows a written checklist: what it asks for against what it says it does, the licence, that its image is pinned by digest, the maker's repository, that no secrets are in it, and that its help and its place to report problems exist.</li>
<li><strong>The listing says who and when.</strong> The reviewer's name and the date are in the listing, which anyone can read in the repository.</li></ol></section>
<section aria-labelledby="r2"><h2 id="r2">What the mark does not mean</h2>
<ul><li>It is not a guarantee, a security audit or a promise of support. It means a person looked, on that date, at that version.</li>
<li>A newer version has not been reviewed. When the maker publishes one, the plug-in's page says so until a person reads it.</li>
<li>Starboard still asks you before it adds anything, and shows what the plug-in can read, change and reach. It runs plug-ins in containers with few rights.</li></ul></section>
<section aria-labelledby="r3"><h2 id="r3">After it is listed</h2>
<p>Once a day, Stallboard reads each plug-in's file again and opens a pull request if anything changed. A person reads that pull request first, and anything that asks for more than before is called out. A listing whose last read is too old is taken off the site until it is read again, and the page of a plug-in that no longer passes Starboard's check is not published.</p></section>
<section aria-labelledby="r4"><h2 id="r4">The owner's own plug-ins</h2>
<p>Plug-ins made by TheMightyTRexUK carry the extra mark "Starboard's own". They go through the same checks. The owner reviews their own plug-ins, and each page says so by naming the reviewer. As other reviewers join, someone else will read them too.</p></section>
<p><a class="btn btn--primary" href="submit.html">Submit a plug-in</a> <a class="btn" href="{REPO_URL}/blob/main/REVIEWING.md" target="_blank" rel="noopener">The review checklist<span class="visually-hidden"> (opens in a new tab)</span></a></p>'''
    return head("What Reviewed means | Stallboard", "What checks and review stand behind the Reviewed mark on a Stallboard plug-in, and what they do not cover.", 0, "what-reviewed-means.html", "reviewed") + header(0, "") + wrap(inner) + footer(0) + tail(0)


STATEMENT_DATE = "2026-11-23"


def accessibility_page(axe_version, today=STATEMENT_DATE):
    today = STATEMENT_DATE
    inner = f'''<h1 class="display">Accessibility statement</h1>
<p class="lede">Stallboard is built to meet WCAG 2.2 level AA, because the people who use Starboard include people who use a screen reader, a keyboard, a switch or a large text size.</p>
<section aria-labelledby="a1"><h2 id="a1">What it does</h2>
<ul><li>Every page can be read without JavaScript. Search, filters, sorting and the colour switch are extras.</li>
<li>Everything works with a keyboard, with a visible focus ring and a link to skip to the main content.</li>
<li>Targets are at least 44 by 44 pixels. Text can grow to 175%, and the pages work at 200% and 400% zoom without scrolling sideways.</li>
<li>There are light and dark colours, and the pages follow forced colours (high contrast). Colour is never the only signal: each category, mark and error also has an icon and words.</li>
<li>Nothing moves on its own. There are no carousels, no autoplay and no animation that cannot be turned off.</li>
<li>Every picture has a text alternative, or is marked as decoration where the words are beside it. Plug-in logos use the description their maker gave.</li>
<li>The site loads nothing from outside: no web fonts, no analytics, no adverts.</li></ul></section>
<section aria-labelledby="a2"><h2 id="a2">How it is checked</h2>
<p>Every change is checked automatically before it is merged: axe-core {esc(axe_version)} at WCAG 2.2 AA plus best practice, in light, dark, forced colours and on a 375 pixel wide phone; a keyboard walk of each page; 175% text; 200% and 400% zoom; and the size of every target. The colour pairs are measured by a test. The checks must find no violations. Automatic checks find only some problems, so a person also tries the pages with a keyboard.</p></section>
<section aria-labelledby="a3"><h2 id="a3">Known limits</h2>
<ul><li>The pictures on a plug-in's page are drawings of its screens, not screenshots, and say so.</li>
<li>The Send feedback button is Snaglist, made by the same owner. It follows its own accessibility checks: keyboard first, 44 pixel targets and forced colours.</li>
<li>Text from a plug-in's maker, such as its description and notes, is shown as written. We do not rewrite it.</li>
<li>Links to the Starboard and plug-in help centres, and to GitHub, are other people's pages with their own statements.</li></ul></section>
<section aria-labelledby="a4"><h2 id="a4">Tell us about a problem</h2>
<p>Use the Send feedback button on any page and choose "Does not work with my tools or needs", or <a href="{ISSUES_NEW}" target="_blank" rel="noopener">open an issue on GitHub<span class="visually-hidden"> (opens in a new tab)</span></a>. We aim to answer within a week.</p></section>
<p class="muted">This statement was written on {esc(nice_date(today))}.</p>'''
    return head("Accessibility statement | Stallboard", "How Stallboard meets WCAG 2.2 AA, how it is checked and what its known limits are.", 0, "accessibility.html", "a11y") + header(0, "") + wrap(inner) + footer(0) + tail(0)


def privacy_page(today=STATEMENT_DATE):
    today = STATEMENT_DATE
    inner = f'''<h1 class="display">Privacy</h1>
<p class="lede">Stallboard keeps no account for you, sets no cookies and has no analytics. This page says what the Send feedback button holds and never holds, in the words of Snaglist, the tool that makes it.</p>
<section aria-labelledby="p1"><h2 id="p1">The site itself</h2>
<ul><li>No cookies, no analytics, no adverts, no web fonts and no requests to other sites when a page loads.</li>
<li>If you choose dark colours, your choice is saved in your browser (in local storage under the name stallboard-theme) and nowhere else.</li>
<li>The site is hosted on GitHub Pages, so GitHub receives what it receives for any page it serves, such as your internet address. We do not see it.</li></ul></section>
<section aria-labelledby="p2"><h2 id="p2">What a feedback report holds, and what it never holds</h2>
<p>Snaglist is built so that a report says what is wrong and where, and nothing about who found it.</p>
<h3>Never collected</h3>
<ul><li>Anything entered in the page's fields, including search boxes. A field is named by its label, and a recorded step says "Entered text in field Your name", never the text.</li>
<li>The choice made in a field: the option chosen in a list, or which tick boxes were selected.</li>
<li>Cookies, local storage (other than Snaglist's own on and off switch), session ids or tokens.</li>
<li>The query string and the hash of the address.</li>
<li>The full browser identification string: only the browser and system family and the browser's main version.</li>
<li>The IP address: Snaglist runs in your browser and sends nothing by itself.</li></ul>
<h3>Technical details, and how they are cleaned</h3>
<p>For some kinds of report, Snaglist adds details that developers need, such as script errors, failed requests, the part of the page's structure you chose, and page speed. Each is cleaned first: query strings and hashes are removed, emails, long numbers and keys are replaced, and the text of the page's structure is replaced by its length. These stay in memory on the page and only leave it when you send a report.</p>
<h3>Hidden before anyone reads it</h3>
<p>An email address becomes [email], a phone or card number or any long number becomes [number], an IP address becomes [address], a UUID becomes [id], and a key or token becomes [key].</p></section>
<section aria-labelledby="p3"><h2 id="p3">You see everything first</h2>
<p>Before anything is sent, Snaglist shows you the whole report, exactly as it will be sent, with this statement: "This report keeps no account, cookies or anything entered in the page's fields, and anything in the form of an email, a long number or a key is replaced. The page title and the text on the page are copied as they are, so check they show nothing personal." You can untick any part, and nothing is sent until you choose a way to send it.</p></section>
<section aria-labelledby="p4"><h2 id="p4">Where a report goes, and who can tell it was you</h2>
<p>On Stallboard, a report opens a new issue on GitHub, in <a href="{REPO_URL}" target="_blank" rel="noopener">{esc(REPO_URL.split("github.com/")[1])}<span class="visually-hidden"> (opens in a new tab)</span></a>, with the label feedback. <strong>You post it from your own GitHub account, so GitHub shows your user name, and the issue is public.</strong> The report itself holds nothing about you. You can also copy it as Markdown or download it as JSON, and then nobody can tell who you are, because it stays with you.</p></section>
<section aria-labelledby="p5"><h2 id="p5">Submitting a plug-in</h2>
<p>A submission is a public GitHub issue. It holds the address of the plug-in's file, the name you give, a one sentence description, what the plug-in asks to read or change and why, and its licence. Do not put anything private in it, including an email address you do not want shown. If you give a way to contact you, it is public too.</p></section>
<section aria-labelledby="p6"><h2 id="p6">Plug-in makers' pages</h2>
<p>The link "Report a problem with this plug-in" goes to the maker's own issue page on a site we do not control. What you send there follows that site's rules.</p></section>
<p class="muted">Written on {esc(nice_date(today))}. Snaglist's own text is in its <a href="https://themightytrex.github.io/snaglist/help/topics/what-a-report-holds.html" target="_blank" rel="noopener">help centre<span class="visually-hidden"> (opens in a new tab)</span></a>.</p>'''
    return head("Privacy | Stallboard", "What Stallboard and its Send feedback button hold and never hold.", 0, "privacy.html", "privacy") + header(0, "") + wrap(inner) + footer(0) + tail(0)


def not_found_page():
    """Served at any address, so every link starts from the site's own path."""
    p = SITE_PATH
    h = head("That page is not here | Stallboard", "The page you asked for is not on Stallboard.", 0, "404.html", "404")
    h = h.replace('href="assets/', f'href="{p}assets/').replace('src="assets/', f'src="{p}assets/')
    hd = header(0, "").replace('href="index.html', f'href="{p}index.html').replace('href="starboard.html', f'href="{p}starboard.html').replace('href="submit.html', f'href="{p}submit.html')
    ft = footer(0)
    for f in ("what-reviewed-means.html", "privacy.html", "starboard.html", "index.html", "submit.html", "accessibility.html"):
        ft = ft.replace(f'href="{f}', f'href="{p}{f}')
    t = tail(0).replace('src="assets/', f'src="{p}assets/')
    inner = f'<h1 class="display">That page is not here</h1><p class="lede">The address may have a typing mistake, or the plug-in may have been taken off.</p><p><a class="btn btn--primary" href="{p}index.html#all-plug-ins">Browse all plug-ins</a> <a class="btn" href="{p}index.html">Go to the home page</a></p>'
    return h + hd + wrap(inner) + ft + t
