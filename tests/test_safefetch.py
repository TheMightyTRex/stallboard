import unittest

import helpers  # noqa: F401
import safefetch as sf


def resolver_for(table):
    calls = []

    def r(host, port, type=None):
        calls.append(host)
        if host not in table:
            raise OSError("no such name")
        return [(2, 1, 6, "", (ip, port)) for ip in table[host]]
    r.calls = calls
    return r


class Address(unittest.TestCase):
    def refuse(self, url):
        with self.assertRaises(sf.FetchError, msg=url):
            sf.check_address(url)

    def test_refusals(self):
        for url in ["http://github.com/x", "ftp://github.com/x", "file:///etc/passwd", "https://user:pw@github.com/x", "https://user@github.com/x",
                    "https://github.com:8443/x", "https://169.254.169.254/latest/meta-data", "https://127.0.0.1/x", "https://[::1]/x",
                    "https://2130706433/x", "https://0x7f000001/x", "https://localhost/x", "https://printer.local/x", "https://nas.internal/x",
                    "https://intranet/x", "", "https://github.com/a b", "https://github.com/a\nGET /", "https://" + "a" * 600 + ".com/", None, 5]:
            self.refuse(url)

    def test_acceptable(self):
        self.assertEqual(sf.check_address("https://raw.githubusercontent.com/a/b/main/x.json"), ("raw.githubusercontent.com", "/a/b/main/x.json"))
        self.assertEqual(sf.check_address("https://Example.COM./p?q=1"), ("example.com", "/p?q=1"))


class Addresses(unittest.TestCase):
    def test_public_and_not(self):
        for ip in ["8.8.8.8", "140.82.112.3", "2606:50c0:8000::154"]:
            self.assertTrue(sf.is_public(ip), ip)
        for ip in ["169.254.169.254", "127.0.0.1", "10.0.0.5", "172.16.0.1", "192.168.1.1", "100.64.0.1", "0.0.0.0", "224.0.0.1", "::1", "fe80::1",
                   "fd00:ec2::254", "fc00::1", "::ffff:127.0.0.1", "::ffff:169.254.169.254", "64:ff9b::1", "2002:7f00:1::1", "not an address", ""]:
            self.assertFalse(sf.is_public(ip), ip)

    def test_every_answer_must_be_public(self):
        r = resolver_for({"mixed.example.com": ["8.8.8.8", "169.254.169.254"], "ok.example.com": ["8.8.8.8", "1.1.1.1"]})
        with self.assertRaises(sf.FetchError):
            sf.resolve_once("mixed.example.com", r)
        self.assertEqual(sf.resolve_once("ok.example.com", r), "8.8.8.8")
        with self.assertRaises(sf.FetchError):
            sf.resolve_once("missing.example.com", r)


class Fetching(unittest.TestCase):
    def fetch(self, url, replies, table=None, **kw):
        seen = []

        def transport(host, ip, path, timeout, max_bytes, deadline):
            seen.append((host, ip, path))
            return replies[len(seen) - 1]
        r = resolver_for(table or {"github.com": ["140.82.112.3"], "raw.githubusercontent.com": ["185.199.108.133"], "evil.example.com": ["8.8.4.4"], "meta.example.com": ["169.254.169.254"]})
        out = sf.fetch(url, resolver=r, transport=transport, **kw)
        return out, seen, r

    def test_connects_to_the_address_it_checked_and_resolves_once(self):
        body, seen, r = self.fetch("https://raw.githubusercontent.com/a/b.json", [(200, {}, b"{}")])
        self.assertEqual(body, b"{}")
        self.assertEqual(seen, [("raw.githubusercontent.com", "185.199.108.133", "/a/b.json")])
        self.assertEqual(r.calls, ["raw.githubusercontent.com"])

    def test_name_pointing_at_the_metadata_address_is_refused_before_connecting(self):
        with self.assertRaises(sf.FetchError):
            self.fetch("https://meta.example.com/x", [(200, {}, b"secret")])

    def test_redirect_inside_the_short_list_is_followed(self):
        body, seen, _ = self.fetch("https://github.com/a/b/raw/main/x.json", [(302, {"location": "https://raw.githubusercontent.com/a/b/main/x.json"}, b""), (200, {}, b"ok")])
        self.assertEqual(body, b"ok")
        self.assertEqual(seen[1][0], "raw.githubusercontent.com")

    def test_redirect_off_the_list_is_refused(self):
        for loc in ["https://evil.example.com/x", "http://github.com/x", "https://169.254.169.254/", "//evil.example.com/x", "https://github.com.evil.example.com/x"]:
            with self.assertRaises(sf.FetchError, msg=loc):
                self.fetch("https://github.com/a", [(302, {"location": loc}, b""), (200, {}, b"no")], table={"github.com": ["140.82.112.3"], "evil.example.com": ["8.8.4.4"], "github.com.evil.example.com": ["8.8.4.4"]})

    def test_a_first_address_on_another_public_site_is_allowed_but_its_redirects_are_not(self):
        body, _, _ = self.fetch("https://evil.example.com/plugin.json", [(200, {}, b"{}")])
        self.assertEqual(body, b"{}")
        with self.assertRaises(sf.FetchError):
            self.fetch("https://evil.example.com/plugin.json", [(301, {"location": "https://evil.example.com/other.json"}, b"")])

    def test_too_many_redirects_and_errors(self):
        hop = (302, {"location": "https://github.com/loop"}, b"")
        with self.assertRaises(sf.FetchError):
            self.fetch("https://github.com/loop", [hop] * 6)
        with self.assertRaises(sf.FetchError):
            self.fetch("https://github.com/x", [(404, {}, b"")])
        with self.assertRaises(sf.FetchError):
            self.fetch("https://github.com/x", [(302, {}, b"")])

    def test_size_limit(self):
        with self.assertRaises(sf.FetchError):
            self.fetch("https://github.com/x", [(200, {}, b"x" * 101)], max_bytes=100)
        body, _, _ = self.fetch("https://github.com/x", [(200, {}, b"x" * 100)], max_bytes=100)
        self.assertEqual(len(body), 100)

    def test_the_real_transport_enforces_the_declared_size_and_time(self):
        import http.client
        import time

        class Resp:
            status = 200

            def __init__(self, n, delay=0):
                self.n, self.delay = n, delay

            def getheaders(self):
                return [("Content-Length", str(self.n))]

            def read(self, k):
                time.sleep(self.delay)
                return b"x" * k

        class Conn:
            def __init__(self, resp):
                self.resp = resp

            def request(self, *a, **k):
                pass

            def getresponse(self):
                return self.resp

            def close(self):
                pass
        orig = sf._PinnedHTTPS
        try:
            sf._PinnedHTTPS = lambda host, ip, timeout: Conn(Resp(10 ** 9))
            with self.assertRaises(sf.FetchError):
                sf._transport("a.example.com", "8.8.8.8", "/", 5, 1000, time.monotonic() + 5)
            sf._PinnedHTTPS = lambda host, ip, timeout: Conn(Resp(0, delay=0.05))
            with self.assertRaises(sf.FetchError):
                sf._transport("a.example.com", "8.8.8.8", "/", 5, 10 ** 9, time.monotonic() - 1)
        finally:
            sf._PinnedHTTPS = orig
        self.assertTrue(http.client)


if __name__ == "__main__":
    unittest.main()


class TotalDeadline(unittest.TestCase):
    def test_slow_reads_add_up_to_the_limit(self):
        import time

        class Sock:
            timeouts = []

            def settimeout(self, t):
                Sock.timeouts.append(t)

        class Resp:
            status = 200

            def getheaders(self):
                return []

            def read(self, n):
                time.sleep(0.06)
                return b"x" * 10

        class Conn:
            sock = Sock()

            def request(self, *a, **k):
                pass

            def getresponse(self):
                return Resp()

            def close(self):
                pass
        orig = sf._PinnedHTTPS
        try:
            sf._PinnedHTTPS = lambda host, ip, timeout: Conn()
            start = time.monotonic()
            with self.assertRaises(sf.FetchError):
                sf._transport("a.example.com", "8.8.8.8", "/", 5, 10 ** 9, time.monotonic() + 0.3)
            self.assertLess(time.monotonic() - start, 1)
            self.assertTrue(all(t <= 0.31 for t in Sock.timeouts))
        finally:
            sf._PinnedHTTPS = orig


class Token(unittest.TestCase):
    """The workflow's token goes to api.github.com and nowhere else (24 and 25 November 2026: unauthenticated calls got a 403)."""
    TOKEN = "ghs_exampletoken123"
    H = {"Authorization": "Bearer ghs_exampletoken123", "Accept": "application/vnd.github+json"}
    TABLE = {"api.github.com": ["140.82.112.5"], "github.com": ["140.82.112.3"], "raw.githubusercontent.com": ["185.199.108.133"],
             "evil.example.com": ["8.8.4.4"]}

    def run_fetch(self, url, replies, headers=None, **kw):
        seen = []

        def transport(host, ip, path, timeout, max_bytes, deadline, headers=None):
            seen.append((host, headers))
            return replies[len(seen) - 1]
        out = sf.fetch(url, resolver=resolver_for(self.TABLE), transport=transport, headers=headers, **kw)
        return out, seen

    def test_sent_to_the_api_host(self):
        _, seen = self.run_fetch("https://api.github.com/repos/a/b/releases", [(200, {}, b"[]")], self.H)
        self.assertEqual(seen, [("api.github.com", self.H)])

    def test_not_sent_to_any_other_host(self):
        for url in ["https://github.com/a", "https://raw.githubusercontent.com/a/b", "https://evil.example.com/x"]:
            _, seen = self.run_fetch(url, [(200, {}, b"{}")], self.H)
            self.assertIsNone(seen[0][1], url)

    def test_not_forwarded_on_a_redirect(self):
        _, seen = self.run_fetch("https://api.github.com/x", [(302, {"location": "https://raw.githubusercontent.com/a/b"}, b""), (200, {}, b"ok")], self.H)
        self.assertEqual([h for _, h in seen], [self.H, None])

    def test_a_redirect_to_the_api_host_from_elsewhere_still_sends_it_only_there(self):
        _, seen = self.run_fetch("https://github.com/x", [(302, {"location": "https://api.github.com/y"}, b""), (200, {}, b"ok")], self.H,
                                 allowed_redirect_hosts=("github.com", "api.github.com"))
        self.assertEqual([h for _, h in seen], [None, self.H])

    def test_no_headers_means_the_old_call(self):
        _, seen = self.run_fetch("https://api.github.com/x", [(200, {}, b"[]")])
        self.assertIsNone(seen[0][1])

    def test_only_allowed_headers_one_line_each(self):
        for bad in [{"Cookie": "a=b"}, {"Host": "evil.example.com"}, {"Authorization": "Bearer x\r\nX-Evil: 1"}, {"Authorization": ""}]:
            with self.assertRaises(sf.FetchError, msg=str(bad)):
                self.run_fetch("https://api.github.com/x", [(200, {}, b"[]")], bad)

    def test_the_token_is_never_in_a_message(self):
        with self.assertRaises(sf.FetchError) as cm:
            self.run_fetch("https://api.github.com/x", [(403, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1764000000"}, b"")], self.H)
        msg = str(cm.exception)
        self.assertNotIn(self.TOKEN, msg)
        self.assertIn("403", msg)
        self.assertIn("rate limit: 0 calls left", msg)

    def test_rate_limit_words_take_digits_only(self):
        with self.assertRaises(sf.FetchError) as cm:
            self.run_fetch("https://api.github.com/x", [(403, {"x-ratelimit-remaining": "0 ::error::x", "x-ratelimit-reset": "soon"}, b"")])
        self.assertNotIn("::", str(cm.exception))
        self.assertNotIn("rate limit", str(cm.exception))

    def test_the_real_transport_sends_the_header(self):
        import http.client
        sent = {}

        class Conn:
            sock = None

            def __init__(self, host, ip, timeout):
                pass

            def request(self, method, path, headers=None):
                sent.update(headers)

            def getresponse(self):
                class R:
                    status = 200
                    def getheaders(self): return []
                    def read(self, n): return b""
                return R()

            def close(self):
                pass
        real = sf._PinnedHTTPS
        sf._PinnedHTTPS = Conn
        try:
            import time
            sf._transport("api.github.com", "140.82.112.5", "/x", 5, 100, time.monotonic() + 5, headers=self.H)
        finally:
            sf._PinnedHTTPS = real
        self.assertEqual(sent["Authorization"], "Bearer ghs_exampletoken123")
        self.assertEqual(sent["Host"], "api.github.com")
        self.assertEqual(sent["Accept"], "application/vnd.github+json")


class ReleasesToken(unittest.TestCase):
    def test_the_token_comes_from_the_environment_and_only_for_the_api(self):
        import os
        import refresh_releases as rr
        old = {k: os.environ.pop(k, None) for k in ("GH_TOKEN", "GITHUB_TOKEN")}
        try:
            self.assertIsNone(rr.api_headers())
            os.environ["GH_TOKEN"] = "ghs_abc"
            self.assertEqual(rr.api_headers()["Authorization"], "Bearer ghs_abc")
            import inspect
            src = inspect.getsource(rr.main)
            self.assertEqual(src.count("get_json("), 2)           # the releases and the tags: both with the token
            self.assertNotIn("headers=", src.replace("get_json", ""))  # the raw.githubusercontent.com reads carry none
        finally:
            os.environ.pop("GH_TOKEN", None)
            for k, v in old.items():
                if v is not None:
                    os.environ[k] = v
