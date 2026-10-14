from urllib.parse import urlparse


def is_valid_url(url):
    try:
        if not isinstance(url, str) or not url.strip():
            return False

        result = urlparse(url.strip())
        # urlparse.hostname handles DNS names, IPv4, IPv6 and localhost.
        return result.scheme.lower() in {"http", "https"} and bool(result.hostname)
    except (TypeError, ValueError):
        return False
