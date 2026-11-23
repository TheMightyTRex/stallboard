import unittest

import helpers  # noqa: F401
import contrast


class Contrast(unittest.TestCase):
    def test_every_pair_passes(self):
        n = 0
        for name, T, C in (("light", contrast.L, contrast.CATL), ("dark", contrast.D, contrast.CATD)):
            for label, a, b, ratio, need in contrast.pairs(T, C):
                n += 1
                self.assertGreaterEqual(ratio, need, f"{name}: {label} {a} on {b} is {ratio:.2f}:1, needs {need}:1")
        self.assertGreater(n, 40)

    def test_the_css_uses_the_measured_colours(self):
        import helpers as h
        css = (h.ROOT / "assets" / "store.css").read_text().upper()
        for k in ("ink", "bg", "accent", "muted"):
            self.assertIn(contrast.L[k].upper(), css, k)
        for k in ("bg", "ink", "accent"):
            self.assertIn(contrast.D[k].upper(), css, k)


if __name__ == "__main__":
    unittest.main()
