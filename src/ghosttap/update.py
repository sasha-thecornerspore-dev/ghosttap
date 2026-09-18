"""Self-update check against GitHub Releases.

The app compares its own version to the latest published release and offers to
download a newer build. All network/parse errors are swallowed — an update
check must never crash or block the app beyond its timeout.
"""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field

GITHUB_REPO = "sasha-thecornerspore-dev/ghosttap"


@dataclass
class Release:
    tag: str
    version: tuple[int, ...]
    url: str                                  # release page (html_url)
    assets: list[tuple[str, str]] = field(default_factory=list)  # (name, download_url)


def parse_version(s: str) -> tuple[int, ...]:
    """Turn a tag like 'v0.2.1' into (0, 2, 1). Non-numeric suffixes on a
    component are dropped ('2.0.0-beta' -> (2, 0, 0)); junk yields (0,)."""
    s = s.strip().lstrip("vV")
    parts: list[int] = []
    for chunk in s.split("."):
        digits = ""
        for ch in chunk:
            if ch.isdigit():
                digits += ch
            else:
                break
        parts.append(int(digits) if digits else 0)
    return tuple(parts) or (0,)


def is_newer(latest: str, current: str) -> bool:
    return parse_version(latest) > parse_version(current)


def _default_fetch(url: str, timeout: float = 5.0) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "ghosttap-updater",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def latest_release(repo: str = GITHUB_REPO, fetch=_default_fetch) -> Release | None:
    data = fetch(f"https://api.github.com/repos/{repo}/releases/latest")
    tag = data.get("tag_name")
    if not tag:
        return None
    assets = [
        (a["name"], a["browser_download_url"])
        for a in data.get("assets", [])
        if a.get("name") and a.get("browser_download_url")
    ]
    return Release(tag=tag, version=parse_version(tag), url=data.get("html_url", ""), assets=assets)


def check_for_update(current: str, repo: str = GITHUB_REPO, fetch=_default_fetch) -> Release | None:
    """Return the latest Release iff it is newer than `current`, else None.
    Swallows every error (offline, rate-limited, malformed) by returning None."""
    try:
        rel = latest_release(repo, fetch)
    except Exception:
        return None
    if rel is None:
        return None
    return rel if is_newer(rel.tag, current) else None
