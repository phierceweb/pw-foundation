"""Tests for pw_foundation.utils.ids."""

from __future__ import annotations

import re

from pw_foundation.utils.ids import generate_id


class TestGenerateId:
    def test_default_length(self):
        result = generate_id()
        assert len(result) == 12

    def test_custom_length(self):
        result = generate_id(size=8)
        assert len(result) == 8

    def test_url_safe_characters(self):
        for _ in range(50):
            result = generate_id()
            assert re.match(r"^[A-Za-z0-9_-]+$", result)

    def test_uniqueness(self):
        ids = {generate_id() for _ in range(100)}
        assert len(ids) == 100

    def test_respects_env_var(self, monkeypatch):
        monkeypatch.setenv("ID_LENGTH", "20")
        result = generate_id()
        assert len(result) == 20

    def test_env_var_clamped_low(self, monkeypatch):
        monkeypatch.setenv("ID_LENGTH", "3")
        result = generate_id()
        assert len(result) == 8  # clamped to minimum

    def test_env_var_clamped_high(self, monkeypatch):
        monkeypatch.setenv("ID_LENGTH", "100")
        result = generate_id()
        assert len(result) == 36  # clamped to maximum

    def test_explicit_size_overrides_env(self, monkeypatch):
        monkeypatch.setenv("ID_LENGTH", "20")
        result = generate_id(size=8)
        assert len(result) == 8
