import re
from urllib.parse import urlparse


def is_valid_url(url):
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False
        url_pattern = re.compile(
            r"^(https?://)"
            r"([a-zA-Z0-9-]+\.)+[a-zA-Z0-9]{1,6}"
            r"(:\d+)?"
            r"(/\S*)?$"
        )
        return bool(url_pattern.match(url))
    except ValueError:
        return False