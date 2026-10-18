"""Tests for pw_foundation.config — centralized configuration loader."""

from __future__ import annotations

import pytest

from pw_foundation.config import AppConfig, _to_bool, _to_list
from pw_foundation.exceptions import ConfigurationError


class _Cfg(AppConfig):
    """A consumer-shaped subclass: the typed fields the coercion and isolation tests exercise."""

    PORT: int = 8000
    ORIGINS: list[str] = []
    IGNORE: list[str] = []


class TestToBool:
    @pytest.mark.parametrize("val", ["1", "true", "True", "TRUE", "yes", "Yes", "on", "ON"])
    def test_truthy_values(self, val):
        assert _to_bool(val) is True

    @pytest.mark.parametrize("val", ["0", "false", "False", "no", "off", "", "anything"])
    def test_falsy_values(self, val):
        assert _to_bool(val) is False

    def test_strips_whitespace(self):
        assert _to_bool("  true  ") is True
        assert _to_bool("  false  ") is False


class TestToList:
    def test_comma_separated(self):
        assert _to_list("a,b,c") == ["a", "b", "c"]

    def test_strips_whitespace(self):
        assert _to_list(" a , b , c ") == ["a", "b", "c"]

    def test_empty_string(self):
        assert _to_list("") == []

    def test_single_value(self):
        assert _to_list("only") == ["only"]

    def test_custom_separator(self):
        assert _to_list("a|b|c", sep="|") == ["a", "b", "c"]

    def test_trailing_separator(self):
        assert _to_list("a,b,") == ["a", "b"]

    def test_empty_segments_skipped(self):
        assert _to_list("a,,b") == ["a", "b"]


class TestAppConfigDefaults:
    def test_default_values(self):
        cfg = AppConfig()
        assert cfg.LOG_LEVEL == "INFO"
        assert cfg.LOG_FILE == ""
        assert cfg.APP_NAME == "App"
        assert cfg.APP_URL == ""

    def test_base_settings_are_exactly_the_generic_four(self):
        """Database, provider, web, API and pool knobs belong to pw-core's AppConfig subclass, so
        a new framework setting never needs a pw-foundation release."""
        declared = {k for k in vars(AppConfig) if k.isupper()}
        assert declared == {"LOG_LEVEL", "LOG_FILE", "APP_NAME", "APP_URL"}

    def test_subclass_with_property_and_classmethod_constructs(self):
        class MyConfig(AppConfig):
            TIMEOUT: int = 5

            @property
            def timeout_ms(self) -> int:
                return self.TIMEOUT * 1000

            @classmethod
            def build(cls) -> "MyConfig":
                return cls()

        cfg = MyConfig.build()
        assert cfg.timeout_ms == 5000

    def test_yaml_empty_by_default(self):
        cfg = AppConfig()
        assert cfg.yaml == {}


class TestAppConfigEnvOverrides:
    def test_string_from_env(self, monkeypatch):
        monkeypatch.setenv("APP_NAME", "TestApp")
        cfg = _Cfg()
        assert cfg.APP_NAME == "TestApp"

    def test_int_from_env(self, monkeypatch):
        monkeypatch.setenv("PORT", "9000")
        cfg = _Cfg()
        assert cfg.PORT == 9000

    def test_invalid_int_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("PORT", "not_a_number")
        cfg = _Cfg()
        assert cfg.PORT == 8000

    def test_bool_from_env(self, monkeypatch):
        class MyConfig(AppConfig):
            DEBUG: bool = False

        monkeypatch.setenv("DEBUG", "true")
        cfg = MyConfig()
        assert cfg.DEBUG is True

    def test_list_from_env(self, monkeypatch):
        monkeypatch.setenv("ORIGINS", "http://localhost:3000,http://localhost:5000")
        cfg = _Cfg()
        assert cfg.ORIGINS == ["http://localhost:3000", "http://localhost:5000"]

    def test_wildcard_cors_origin_reaches_the_list(self, monkeypatch):
        # Nothing filters "*" out here — create_app is what refuses it.
        monkeypatch.setenv("ORIGINS", "*")
        assert _Cfg().ORIGINS == ["*"]

    def test_string_stripped(self, monkeypatch):
        monkeypatch.setenv("APP_NAME", "  Padded  ")
        cfg = _Cfg()
        assert cfg.APP_NAME == "Padded"


class TestAppConfigOverrides:
    def test_overrides_win_over_defaults(self):
        cfg = _Cfg(overrides={"APP_NAME": "Overridden"})
        assert cfg.APP_NAME == "Overridden"

    def test_overrides_win_over_env(self, monkeypatch):
        monkeypatch.setenv("APP_NAME", "FromEnv")
        cfg = _Cfg(overrides={"APP_NAME": "FromOverride"})
        assert cfg.APP_NAME == "FromOverride"


class TestAppConfigYaml:
    def test_loads_yaml_file(self, tmp_path):
        yf = tmp_path / "config.yaml"
        yf.write_text("name: test\nsettings:\n  debug: true\n")
        cfg = _Cfg(yaml_file=yf)
        assert cfg.yaml["name"] == "test"
        assert cfg.yaml["settings"]["debug"] is True

    def test_missing_yaml_file_ignored(self, tmp_path):
        cfg = _Cfg(yaml_file=tmp_path / "nonexistent.yaml")
        assert cfg.yaml == {}

    def test_malformed_yaml_raises_configuration_error(self, tmp_path):
        yf = tmp_path / "bad.yaml"
        yf.write_text(":\n  - [\n")
        with pytest.raises(ConfigurationError, match="bad.yaml"):
            _Cfg(yaml_file=yf)


class TestAppConfigYamlResolution:
    """Top-level YAML keys matching a declared setting resolve env > yaml > default."""

    @staticmethod
    def _write(tmp_path, text):
        yf = tmp_path / "config.yaml"
        yf.write_text(text)
        return yf

    def test_yaml_beats_class_default(self, tmp_path):
        yf = self._write(tmp_path, "APP_NAME: FromYaml\n")
        cfg = _Cfg(yaml_file=yf)
        assert cfg.APP_NAME == "FromYaml"

    def test_env_beats_yaml(self, tmp_path, monkeypatch):
        monkeypatch.setenv("APP_NAME", "FromEnv")
        yf = self._write(tmp_path, "APP_NAME: FromYaml\n")
        cfg = _Cfg(yaml_file=yf)
        assert cfg.APP_NAME == "FromEnv"

    def test_override_beats_yaml(self, tmp_path):
        yf = self._write(tmp_path, "APP_NAME: FromYaml\n")
        cfg = _Cfg(yaml_file=yf, overrides={"APP_NAME": "FromOverride"})
        assert cfg.APP_NAME == "FromOverride"

    def test_typed_yaml_values_pass_through(self, tmp_path):
        yf = self._write(tmp_path, "PORT: 9000\nORIGINS:\n  - http://a\n")
        cfg = _Cfg(yaml_file=yf)
        assert cfg.PORT == 9000
        assert cfg.ORIGINS == ["http://a"]

    def test_yaml_string_coerced_like_env(self, tmp_path):
        yf = self._write(tmp_path, 'PORT: "9001"\nORIGINS: "a, b"\n')
        cfg = _Cfg(yaml_file=yf)
        assert cfg.PORT == 9001
        assert cfg.ORIGINS == ["a", "b"]

    def test_yaml_bool_for_subclass_setting(self, tmp_path):
        class MyConfig(AppConfig):
            DEBUG: bool = False

        yf = self._write(tmp_path, "DEBUG: true\n")
        cfg = MyConfig(yaml_file=yf)
        assert cfg.DEBUG is True

    def test_non_attr_yaml_keys_stay_inert(self, tmp_path):
        yf = self._write(tmp_path, "widget_order:\n  - header\n")
        cfg = _Cfg(yaml_file=yf)
        assert not hasattr(cfg, "widget_order")
        assert cfg.yaml["widget_order"] == ["header"]

    def test_lowercase_yaml_key_does_not_map_to_upper_attr(self, tmp_path):
        yf = self._write(tmp_path, "port: 9999\n")
        cfg = _Cfg(yaml_file=yf)
        assert cfg.PORT == 8000
        assert cfg.yaml["port"] == 9999

    def test_resolved_keys_remain_in_raw_yaml_dict(self, tmp_path):
        yf = self._write(tmp_path, "APP_NAME: FromYaml\n")
        cfg = _Cfg(yaml_file=yf)
        assert cfg.yaml["APP_NAME"] == "FromYaml"


class TestMutableDefaultIsolation:
    def test_instances_do_not_share_mutable_defaults(self):
        a = _Cfg()
        b = _Cfg()
        a.ORIGINS.append("http://one")
        a.IGNORE.append("prov")
        assert b.ORIGINS == []
        assert b.IGNORE == []
        assert _Cfg.ORIGINS == []
        assert _Cfg.IGNORE == []


class TestAppConfigSubclass:
    def test_subclass_defaults(self):
        class MyConfig(AppConfig):
            CUSTOM_SETTING: str = "default_value"
            CUSTOM_INT: int = 42

        cfg = MyConfig()
        assert cfg.CUSTOM_SETTING == "default_value"
        assert cfg.CUSTOM_INT == 42
        assert cfg.APP_NAME == "App"  # parent defaults still work

    def test_subclass_env_override(self, monkeypatch):
        class MyConfig(AppConfig):
            CUSTOM_SETTING: str = "default"

        monkeypatch.setenv("CUSTOM_SETTING", "from_env")
        cfg = MyConfig()
        assert cfg.CUSTOM_SETTING == "from_env"

    def test_subclass_overrides_parent_default(self):
        class MyConfig(AppConfig):
            APP_NAME: str = "MyApp"

        cfg = MyConfig()
        assert cfg.APP_NAME == "MyApp"


class TestAppConfigGet:
    def test_get_existing_key(self):
        cfg = _Cfg()
        assert cfg.get("APP_NAME") == "App"

    def test_get_missing_key_returns_default(self):
        cfg = _Cfg()
        assert cfg.get("NONEXISTENT") is None
        assert cfg.get("NONEXISTENT", "fallback") == "fallback"


class TestAppConfigFloat:
    def test_float_from_env(self, monkeypatch):
        class MyConfig(AppConfig):
            THRESHOLD: float = 0.5

        monkeypatch.setenv("THRESHOLD", "0.75")
        cfg = MyConfig()
        assert cfg.THRESHOLD == 0.75

    def test_invalid_float_falls_back(self, monkeypatch):
        class MyConfig(AppConfig):
            THRESHOLD: float = 0.5

        monkeypatch.setenv("THRESHOLD", "not_a_float")
        cfg = MyConfig()
        assert cfg.THRESHOLD == 0.5
