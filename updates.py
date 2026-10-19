import json
import re
from dataclasses import dataclass
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from app_version import APP_VERSION

REPOSITORY = 'hypnomalice/reskate-deck-tool'
RELEASES_API = f'https://api.github.com/repos/{REPOSITORY}/releases?per_page=20'


def version_key(tag):
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)(?:-(alpha|beta|rc)(?:[.-]?(\d+))?)?', str(tag))
    if not match:
        return None
    major, minor, patch, stage, revision = match.groups()
    return (int(major), int(minor), int(patch),
            {'alpha': 0, 'beta': 1, 'rc': 2, None: 3}[stage], int(revision or 0))


@dataclass(frozen=True)
class Release:
    version: str
    url: str


def newer_release(releases, current=APP_VERSION):
    current_key = version_key(current)
    if current_key is None or not isinstance(releases, list):
        return None
    candidates = []
    for item in releases:
        if not isinstance(item, dict) or item.get('draft'):
            continue
        tag = item.get('tag_name', '')
        key = version_key(tag)
        if key is None or key <= current_key:
            continue
        if current_key[3] == 3 and (item.get('prerelease') or key[3] != 3):
            continue
        url = item.get('html_url', '')
        if not isinstance(url, str):
            continue
        parsed = urlsplit(url)
        if (parsed.scheme != 'https' or parsed.netloc != 'github.com'
                or parsed.path != f'/{REPOSITORY}/releases/tag/{tag}'
                or parsed.query or parsed.fragment):
            continue
        candidates.append((key, Release(tag, url)))
    return max(candidates, key=lambda pair: pair[0])[1] if candidates else None


def check_for_update(current=APP_VERSION):
    request = Request(RELEASES_API, headers={
        'User-Agent': f'ReSkate-Deck-Tool/{current}',
        'Accept': 'application/vnd.github+json',
    })
    try:
        with urlopen(request, timeout=5) as response:
            payload = response.read(1_000_001)
        if len(payload) > 1_000_000:
            return None
        return newer_release(json.loads(payload), current)
    except (URLError, OSError, ValueError):
        return None
