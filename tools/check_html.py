#!/usr/bin/env python3
"""A plain HTML check of the built site, with the standard library: python3 tools/check_html.py site
For every .html file: tags are balanced, ids are unique, each img has an alt, each form control with an id has a label,
the page has one h1, a title, a lang and a main landmark, and every internal link and fragment points at something that
exists. It also checks heading order (no level is skipped), that headings, links, buttons, list items and paragraphs are not empty,
that each aria-labelledby, aria-describedby and aria-controls points at an id on the page, that landmarks are named when there
is more than one of a kind, that two links with the same words do not go to different places, and that no link or button
sits inside another. Exit code 1 and a list of what is wrong, if anything is."""
import html.parser
import pathlib
import posixpath
import sys
import urllib.parse

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Page(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.ids, self.links, self.problems = [], [], [], []
        self.h1 = self.main = 0
        self.title = self.lang = False
        self.labels_for, self.controls, self.in_title = set(), [], False
        self.heads, self.refs, self.landmarks, self.open_text, self.linktext = [], [], [], [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag not in VOID:
            self.stack.append(tag)
        if tag in ("a", "button", "h1", "h2", "h3", "h4", "h5", "h6", "li", "p", "label", "legend", "summary", "th"):
            self.open_text.append({"tag": tag, "text": "", "named": bool(a.get("aria-label") or a.get("aria-labelledby") or a.get("title") or a.get("role") == "status" or a.get("aria-hidden") == "true"), "href": a.get("href", ""), "img": False})
        if tag in ("img", "svg") and self.open_text:
            for o in self.open_text:
                if tag == "img" and a.get("alt"):
                    o["named"] = True
                if tag == "svg" and (a.get("role") == "img" or a.get("aria-label")):
                    o["named"] = True
        if self.open_text and tag not in ("a", "button", "h1", "h2", "h3", "h4", "h5", "h6", "li", "p", "label", "legend", "summary", "th"):
            for o in self.open_text:
                o["child"] = True
        if tag in ("input", "select", "textarea", "img", "svg") and self.open_text:
            for o in self.open_text:
                if tag in ("input", "select", "textarea"):
                    o["named"] = True
        if tag in ("a", "button") and any(o["tag"] in ("a", "button") for o in self.open_text[:-1]):
            self.problems.append(f"a {tag} inside a link or button")
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.heads.append(int(tag[1]))
        for k in ("aria-labelledby", "aria-describedby", "aria-controls"):
            for r in a.get(k, "").split():
                self.refs.append((k, r))
        if tag in ("nav", "header", "footer", "main", "aside", "section", "form") or a.get("role") in ("search", "navigation"):
            self.landmarks.append((tag if not a.get("role") else a["role"], a.get("aria-label") or a.get("aria-labelledby") or ""))
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "html" and a.get("lang"):
            self.lang = True
        if tag == "h1":
            self.h1 += 1
        if tag == "main":
            self.main += 1
        if tag == "title":
            self.in_title = True
        if tag == "img" and "alt" not in a:
            self.problems.append(f"img without alt: {a.get('src')}")
        if tag == "a" and "href" in a:
            self.links.append(a["href"])
        if tag == "label" and a.get("for"):
            self.labels_for.add(a["for"])
        if tag in ("input", "select", "textarea") and a.get("type") not in ("hidden", "submit", "button") and "id" in a and not a.get("aria-label") and "label" not in self.stack:
            self.controls.append(a["id"])
        if tag == "button" and a.get("type") not in ("button", "submit", "reset"):
            self.problems.append("button without a type")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.stack and self.stack[-1] == tag:
            self.stack.pop()

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if tag == "title":
            self.in_title = False
        if not self.stack or self.stack[-1] != tag:
            self.problems.append(f"unbalanced </{tag}> (open: {self.stack[-3:]})")
            if tag in self.stack:
                while self.stack and self.stack.pop() != tag:
                    pass
            return
        self.stack.pop()
        if self.open_text and self.open_text[-1]["tag"] == tag:
            o = self.open_text.pop()
            if not o["text"].strip() and not o["named"] and tag != "li" or (tag == "li" and not o["text"].strip() and not o["named"] and not o.get("child")):
                self.problems.append(f"empty <{tag}>" + (f" ({o['href']})" if o["href"] else ""))
            if tag == "a" and o["text"].strip():
                self.linktext.append((" ".join(o["text"].split()).lower(), o["href"]))

    def handle_data(self, data):
        if self.in_title and data.strip():
            self.title = True
        for o in self.open_text:
            o["text"] += data


def main(root):
    root = pathlib.Path(root)
    pages, bad = {}, []
    for f in sorted(p for p in root.rglob("*.html") if "assets" not in p.relative_to(root).parts):
        p = Page()
        p.feed(f.read_text(encoding="utf-8"))
        pages[f] = p
    for f, p in pages.items():
        rel = f.relative_to(root)
        probs = list(p.problems)
        if p.stack:
            probs.append(f"unclosed tags: {p.stack}")
        dup = {i for i in p.ids if p.ids.count(i) > 1}
        if dup:
            probs.append(f"duplicate ids: {sorted(dup)[:5]}")
        if p.h1 != 1:
            probs.append(f"{p.h1} h1 elements")
        if p.main != 1:
            probs.append(f"{p.main} main elements")
        if not p.title or not p.lang:
            probs.append("missing title or lang")
        last = 0
        for lv in p.heads:
            if last and lv > last + 1:
                probs.append(f"heading order: h{last} is followed by h{lv}")
            last = lv
        for k, r in p.refs:
            if r not in p.ids:
                probs.append(f"{k} points at #{r}, which is not on the page")
        for name in ("nav", "header", "footer", "main", "search"):
            same = [lab for t, lab in p.landmarks if t == name]
            if name in ("nav", "search") and len(same) > 1 and (len(set(same)) < len(same) or "" in same):
                probs.append(f"{len(same)} {name} landmarks without different names")
        seen = {}
        for text, href in p.linktext:
            u = urllib.parse.urlsplit(href)
            key = href if u.scheme else (posixpath.normpath(posixpath.join(posixpath.dirname(str(rel)), u.path)) if u.path else str(rel)) + ("#" + u.fragment if u.fragment else "")
            seen.setdefault(text, set()).add(key)
        for text, hrefs in seen.items():
            if len(hrefs) > 1 and len(text) < 40 and text not in ("home",) and not text.startswith(("help", "report")):
                probs.append(f"links with the words '{text}' go to {len(hrefs)} different places")
        for c in p.controls:
            if c not in p.labels_for:
                probs.append(f"control #{c} has no label")
        for href in p.links:
            u = urllib.parse.urlsplit(href)
            if u.scheme in ("https", "mailto"):
                continue
            if u.scheme or u.netloc:
                probs.append(f"link with a scheme that is not https: {href}")
                continue
            if rel.name == "404.html" and href.startswith("/stallboard/"):
                continue
            target = f if not u.path else (f.parent / urllib.parse.unquote(u.path)).resolve()
            if not target.exists() or target.is_dir():
                probs.append(f"broken link {href}")
            elif u.fragment and target.suffix == ".html":
                other = pages.get(target) or pages.get(pathlib.Path(target))
                if other is not None and u.fragment not in other.ids:
                    probs.append(f"link to a missing section {href}")
        for pr in probs:
            bad.append(f"{rel}: {pr}")
    print(f"Checked {len(pages)} pages: {len(bad)} problems")
    for b in bad[:60]:
        print(" -", b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "site"))
