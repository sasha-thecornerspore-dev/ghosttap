from ghosttap.update import (
    parse_version,
    is_newer,
    latest_release,
    check_for_update,
    Release,
)


def test_parse_version_strips_v_prefix():
    assert parse_version("v0.1.0") == (0, 1, 0)
    assert parse_version("1.2") == (1, 2)


def test_parse_version_drops_suffix_and_junk():
    assert parse_version("2.0.0-beta") == (2, 0, 0)
    assert parse_version("garbage") == (0,)


def test_is_newer_compares_semantically():
    assert is_newer("v0.2.0", "0.1.0") is True
    assert is_newer("0.1.0", "0.1.0") is False
    assert is_newer("v0.1.0", "0.2.0") is False


def _fake(data):
    return lambda url, timeout=5.0: data


def test_latest_release_parses_tag_and_assets():
    data = {
        "tag_name": "v0.2.0",
        "html_url": "https://example/releases/v0.2.0",
        "assets": [
            {"name": "GhostTap-win.exe", "browser_download_url": "https://example/win.exe"},
            {"name": "GhostTap-mac.dmg", "browser_download_url": "https://example/mac.dmg"},
            {"name": "incomplete"},  # missing url -> skipped
        ],
    }
    rel = latest_release("owner/repo", fetch=_fake(data))
    assert isinstance(rel, Release)
    assert rel.tag == "v0.2.0"
    assert rel.version == (0, 2, 0)
    assert ("GhostTap-win.exe", "https://example/win.exe") in rel.assets
    assert len(rel.assets) == 2  # the incomplete asset is dropped


def test_check_for_update_returns_release_when_newer():
    data = {"tag_name": "v0.2.0", "html_url": "u", "assets": []}
    rel = check_for_update("0.1.0", "owner/repo", fetch=_fake(data))
    assert rel is not None and rel.tag == "v0.2.0"


def test_check_for_update_none_when_same_or_older():
    data = {"tag_name": "v0.1.0", "html_url": "u", "assets": []}
    assert check_for_update("0.1.0", "owner/repo", fetch=_fake(data)) is None


def test_check_for_update_swallows_fetch_errors():
    def boom(url, timeout=5.0):
        raise OSError("offline")

    assert check_for_update("0.1.0", "owner/repo", fetch=boom) is None
