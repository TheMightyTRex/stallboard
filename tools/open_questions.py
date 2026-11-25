#!/usr/bin/env python3
"""Prints what the owner still has to say about each plug-in's storefront text (the 'unclear' lists in data/storefront).
Never shown on the site. Usage: python3 tools/open_questions.py"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lib"))
import storefront  # noqa: E402

q = storefront.open_questions(HERE.parent / "data" / "storefront")
for pid, items in q.items():
    print(f"{pid}")
    for x in items:
        print(f"  - {x}")
print(f"\n{sum(len(v) for v in q.values())} questions about {len(q)} plug-ins")
