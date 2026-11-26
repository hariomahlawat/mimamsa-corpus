"""Offline guard for CA-01B exact URL scope proposals; not a downloader."""
from urllib.parse import urlsplit

def safe_url(url):
    if not isinstance(url, str) or not url or not url.isascii():
        return False
    if any(ord(c) <= 32 or ord(c) == 127 for c in url):
        return False
    if any(c in url for c in ("%", "\\", "?", "#", "@")):
        return False
    try:
        p = urlsplit(url)
        host = p.hostname
        if (p.scheme != "https" or not host or p.netloc != host
                or p.username is not None or p.password is not None
                or host == "aftjabalpur.in" or host.endswith(".aftjabalpur.in")
                or not p.path.startswith("/") or "//" in p.path
                or any(s in (".", "..") for s in p.path.split("/"))):
            return False
        return url == "https://" + host + p.path
    except ValueError:
        return False

def permitted(target, url, *, redirect=False):
    """No network. Exact target-specific URLs only; disabled proposals always deny."""
    if target.get("enabled") is not True or not safe_url(url):
        return False
    if not redirect:
        return url == target.get("initial_url")
    return any(url == row.get("url") and row.get("fresh_probe_approved") is True
               for row in target.get("redirect_url_candidates", []))

def self_test():
    start = "https://archive.org/download/item/1.pdf"
    dest = "https://ia123.us.archive.org/9/items/item/1.pdf"
    target = {"enabled": False, "initial_url": start,
              "redirect_url_candidates": [{"url": dest, "fresh_probe_approved": True}]}
    assert not permitted(target, start)
    target["enabled"] = True
    assert permitted(target, start)
    assert permitted(target, dest, redirect=True)
    assert not permitted(target, dest)
    assert not permitted(target, start, redirect=True)
    for bad in (dest.replace("/item/", "/other/"),
                dest.replace("1.pdf", "2.pdf"),
                dest.replace("/1.pdf", "/../1.pdf"),
                dest.replace("/1.pdf", "/%2e%2e/1.pdf"),
                dest.replace("/1.pdf", "/%252e%252e/1.pdf"),
                dest.replace("/1.pdf", "/%2f1.pdf"),
                dest.replace("/1.pdf", "/\\1.pdf"),
                dest.replace("https:", "http:"),
                dest.replace("ia123.", "ia124."),
                dest.replace("ia123.", "ia123@"),
                dest.replace(".org/", ".org:443/"),
                dest + "?x=1", dest + "#fragment", " " + dest,
                dest.replace("ia123.us.archive.org", "aftjabalpur.in"),
                dest.replace("ia123.us.archive.org", "x.aftjabalpur.in")):
        assert not permitted(target, bad, redirect=True), bad
    target["redirect_url_candidates"][0]["fresh_probe_approved"] = False
    assert not permitted(target, dest, redirect=True)
    print("Offline synthetic scope assertions passed.")

if __name__ == "__main__":
    self_test()
