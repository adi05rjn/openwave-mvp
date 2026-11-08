"""README images must exist, be the file type they claim, and stay small."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
LOCAL_IMAGES = sorted(set(re.findall(r'src="(docs/images/[^"]+)"', README)))
MAGIC = {".png": b"\x89PNG\r\n\x1a\n", ".gif": b"GIF89a"}
MAX_BYTES = 1_000_000  # keep the repository and the README page light


def test_readme_references_images():
    assert LOCAL_IMAGES, "expected README images under docs/images/"


@pytest.mark.parametrize("relative", LOCAL_IMAGES)
def test_image_exists_and_is_valid(relative):
    path = ROOT / relative
    assert path.is_file(), f"README links to missing file {relative}"
    assert path.read_bytes()[:8].startswith(MAGIC[path.suffix]), f"{relative} is not a real {path.suffix}"
    assert path.stat().st_size < MAX_BYTES


def test_every_readme_image_has_alt_text():
    tags = re.findall(r"<img\b[^>]*>", README)
    assert tags
    for tag in tags:
        alt = re.search(r'alt="([^"]*)"', tag)
        assert alt and len(alt.group(1)) > 20, f"missing or token alt text in {tag[:60]}"
