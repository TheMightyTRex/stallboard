"""Fetches an address as DATA ONLY, for the submission checks and the snapshot refresh.

What it will do:    one GET of an https address, at most MAX_BYTES, in at most TIMEOUT seconds in total.
What it refuses:    anything but https; a user name in the address; any port but 443; a host that resolves to a private,
                    loopback, link-local, reserved, multicast or metadata address (169.254.169.254, fd00:ec2::254 and
                    the rest); a redirect to any host that is not on ALLOWED_REDIRECT_HOSTS.
How the address is kept to what was checked: the name is resolved ONCE, every address it gives is checked, and the
connection is made to that address itself (the name is used only for the TLS check), so the name cannot be
answered differently between the check and the connection (a DNS rebinding trick).

It never runs, imports, unpacks or pulls anything it fetches: the caller gets bytes.
"""
import http.client
import ipaddress
import socket
import ssl
import time
import urllib.parse

MAX_BYTES = 256 * 1024
TIMEOUT = 10.0
MAX_REDIRECTS = 3
ALLOWED_REDIRECT_HOSTS = ("github.com", "raw.githubusercontent.com", "codeload.github.com",
                          "objects.githubusercontent.com")
USER_AGENT = "Stallboard-checks (+https://github.com/TheMightyTRex/stallboard)"


class FetchError(Exception):
    """A refusal or a failure, in a plain sentence that is safe to show the person who submitted the address."""


def check_address(url):
    """(host, path) of an acceptable https address, or FetchError."""
    if not isinstance(url, str) or not url or len(url) > 500 or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in url):
        raise FetchError("The address must be one line of text without spaces, up to 500 characters")
    try:
        u = urllib.parse.urlsplit(url)
        port = u.port
    except ValueError:
        raise FetchError("That is not a web address") from None
    if u.scheme != "https":
        raise FetchError("The address must start with https://")
    if not u.hostname or u.username is not None or u.password is not None:
        raise FetchError("The address must name a web site and must not contain a user name or password")
    if port not in (None, 443):
        raise FetchError("The address must use the usual https port (443)")
    host = u.hostname.lower().rstrip(".")
    if host.replace(".", "").isdigit() or ":" in host or host.startswith("0x"):
        # A bare IP address (any spelling) is never a plug-in's home: use a name that others can check.
        raise FetchError("Use the site's name, not a number address")
    if "." not in host or host.endswith((".local", ".internal", ".localhost", ".lan", ".home", ".corp")) or host == "localhost":
        raise FetchError("That name is not a public web site")
    path = u.path or "/"
    if u.query:
        path += "?" + u.query
    return host, path


def is_public(ip):
    """True for an address on the open internet. IPv4 addresses inside IPv6 are checked as IPv4."""
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if isinstance(a, ipaddress.IPv6Address):
        if a.ipv4_mapped is not None:
            a = a.ipv4_mapped
        elif a.sixtofour is not None:
            a = a.sixtofour
        elif a.teredo is not None:
            return False
        elif a in ipaddress.ip_network("64:ff9b::/96"):  # NAT64: the address inside is the one reached
            a = ipaddress.IPv4Address(int(a) & 0xFFFFFFFF)
    return a.is_global and not a.is_multicast


def resolve_once(host, resolver=socket.getaddrinfo):
    """The one address to connect to: every address the name gives must be public, else a refusal."""
    try:
        infos = resolver(host, 443, type=socket.SOCK_STREAM)
    except OSError:
        raise FetchError("The address did not answer: the name could not be found") from None
    ips = []
    for info in infos:
        ip = info[4][0]
        if ip not in ips:
            ips.append(ip)
    if not ips:
        raise FetchError("The address did not answer: the name could not be found")
    for ip in ips:
        if not is_public(ip):
            raise FetchError("The address points to a private or internal computer, so it was not fetched")
    return ips[0]


class _PinnedHTTPS(http.client.HTTPSConnection):
    """Connects to one chosen IP address, and checks the certificate for the real name."""

    def __init__(self, host, ip, timeout):
        super().__init__(host, 443, timeout=timeout, context=ssl.create_default_context())
        self._ip = ip

    def connect(self):
        sock = socket.create_connection((self._ip, 443), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


def _transport(host, ip, path, timeout, max_bytes, deadline):
    """The real network step: (status, headers, body up to max_bytes + 1). Tests replace it."""
    conn = _PinnedHTTPS(host, ip, timeout)
    try:
        conn.request("GET", path, headers={"Host": host, "User-Agent": USER_AGENT, "Accept": "*/*",
                                           "Accept-Encoding": "identity", "Connection": "close"})
        r = conn.getresponse()
        headers = {k.lower(): v for k, v in r.getheaders()}
        if r.status in (301, 302, 303, 307, 308):
            return r.status, headers, b""
        declared = headers.get("content-length", "")
        if declared.isdigit() and int(declared) > max_bytes:
            raise FetchError("That file is too large")
        body = b""
        while len(body) <= max_bytes:
            if time.monotonic() > deadline:
                raise FetchError("The address took too long to answer")
            chunk = r.read(min(16384, max_bytes + 1 - len(body)))
            if not chunk:
                break
            body += chunk
        return r.status, headers, body
    except FetchError:
        raise
    except (OSError, http.client.HTTPException, ssl.SSLError):
        raise FetchError("The address did not answer, or its certificate could not be checked") from None
    finally:
        conn.close()


def fetch(url, max_bytes=MAX_BYTES, timeout=TIMEOUT, resolver=socket.getaddrinfo, transport=_transport,
          allowed_redirect_hosts=ALLOWED_REDIRECT_HOSTS):
    """The body (bytes) at an https address. Raises FetchError with a plain sentence."""
    deadline = time.monotonic() + timeout
    first = True
    for _ in range(MAX_REDIRECTS + 1):
        host, path = check_address(url)
        if not first and host not in allowed_redirect_hosts:
            raise FetchError("The address sent us to another web site (" + host[:60] + "), which is not on the short list "
                             "of places Stallboard follows")
        first = False
        ip = resolve_once(host, resolver)
        status, headers, body = transport(host, ip, path, max(0.5, deadline - time.monotonic()), max_bytes, deadline)
        if status in (301, 302, 303, 307, 308):
            loc = headers.get("location", "")
            url = urllib.parse.urljoin("https://" + host + path, loc) if loc else ""
            if not url:
                raise FetchError("The address redirected without saying where")
            continue
        if status != 200:
            raise FetchError(f"The address answered with the error {status}")
        if len(body) > max_bytes:
            raise FetchError("That file is too large")
        return body
    raise FetchError("The address redirected too many times")
