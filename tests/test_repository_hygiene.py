"""Guards for repository hygiene (issue #6, P1)."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_license_is_the_full_unmodified_apache_text():
    text = (ROOT / "LICENSE").read_bytes()
    # The standard Apache-2.0 text is 202 lines and 11,358 bytes. Project
    # copyright goes in NOTICE; the licence text itself must not be edited.
    assert len(text) == 11358
    assert text.count(b"\n") == 202
    for marker in (b"Apache License\n", b"Version 2.0, January 2004",
                   b"TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION",
                   b"END OF TERMS AND CONDITIONS", b"APPENDIX: How to apply the Apache License",
                   b"Copyright [yyyy] [name of copyright owner]"):
        assert marker in text


def test_notice_names_the_copyright_holder():
    assert "Copyright 2026 OpenWave contributors" in (ROOT / "NOTICE").read_text(encoding="utf-8")


def test_package_metadata_matches_the_documented_scope():
    metadata = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "HFSS" not in metadata, "package description should match the README scope"
    assert "License :: OSI Approved :: Apache Software License" in metadata


@pytest.mark.skipif(shutil.which("git") is None or not (ROOT / ".git").exists(), reason="needs a git checkout")
def test_no_compiled_bytecode_is_tracked():
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    offenders = [line for line in tracked.splitlines() if line.endswith((".pyc", ".pyo"))]
    assert not offenders, offenders
