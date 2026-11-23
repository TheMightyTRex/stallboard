#!/usr/bin/env python3
"""A plain HTML check of the built site, with the standard library: python3 tools/check_html.py site
For every .html file: tags are balanced, ids are unique, each img has an alt, each form control with an id has a label,
the page has one h1, a title, a lang and a main landmark, and every internal link and fragment points at something that
exists. Exit code 1 and a list of what is wrong, if anything is."""
import html.parser
import pathlib
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

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag not in VOID:
            self.stack.append(tag)
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

    def handle_data(self, data):
        if self.in_title and data.strip():
            self.title = True


def main(root):
    root = pathlib.Path(root)
    pages, bad = {}, []
    for f in sorted(root.rglob("*.html")):
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
