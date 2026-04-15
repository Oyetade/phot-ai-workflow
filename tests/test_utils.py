"""Smoke tests for pure utility functions — no I/O required."""
import base64
import tempfile
from pathlib import Path

import pytest
from photo_ai_workflow.utils import IMAGE_SUFFIXES, discover_images, to_base64, to_data_url


class TestImageSuffixes:
    def test_common_formats_present(self):
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            assert ext in IMAGE_SUFFIXES

    def test_all_lowercase(self):
        for ext in IMAGE_SUFFIXES:
            assert ext == ext.lower()


class TestDiscoverImages:
    def test_finds_images(self, tmp_path):
        (tmp_path / "a.jpg").write_bytes(b"fake")
        (tmp_path / "b.PNG").write_bytes(b"fake")
        (tmp_path / "note.txt").write_bytes(b"text")
        found = discover_images(tmp_path)
        names = {p.name for p in found}
        # case-insensitive suffix check — suffix stored lowercase in IMAGE_SUFFIXES
        assert any(n.lower().endswith(".jpg") for n in names)
        assert any(n.lower().endswith(".png") for n in names)
        assert all(not n.lower().endswith(".txt") for n in names)

    def test_returns_sorted(self, tmp_path):
        for name in ("z.jpg", "a.jpg", "m.jpg"):
            (tmp_path / name).write_bytes(b"fake")
        found = discover_images(tmp_path)
        names = [p.name for p in found]
        assert names == sorted(names, key=str.lower)

    def test_empty_dir(self, tmp_path):
        assert discover_images(tmp_path) == []

    def test_recurses_subdirs(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "deep.jpg").write_bytes(b"fake")
        found = discover_images(tmp_path)
        assert len(found) == 1


class TestBase64Helpers:
    def test_to_base64_round_trips(self, tmp_path):
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
        p = tmp_path / "sample.png"
        p.write_bytes(data)
        encoded = to_base64(p)
        assert base64.b64decode(encoded) == data

    def test_to_data_url_has_prefix(self, tmp_path):
        p = tmp_path / "photo.jpg"
        p.write_bytes(b"fake jpeg bytes")
        url = to_data_url(p)
        assert url.startswith("data:image/jpeg;base64,")
