"""Tests for pw_foundation.services.Service base class."""

from pw_foundation.config import AppConfig
from pw_foundation.services import Service


class _Repo:
    """Stands in for pw_core.db.repository.Repository: ``_repo`` only calls ``cls(conn)``."""

    def __init__(self, conn=None):
        self.conn = conn


class ItemService(Service):
    def repo(self) -> _Repo:
        return self._repo(_Repo)


class TestServiceLogger:
    def test_has_logger(self):
        svc = ItemService()
        assert svc._log is not None

    def test_logger_uses_concrete_module(self):
        svc = ItemService()
        # Bind forces lazy resolution; name should reflect this test module
        bound = svc._log.bind()
        assert bound._logger.name == __name__


class TestServiceConfig:
    def test_config_is_none_by_default(self):
        svc = ItemService()
        assert svc._config is None

    def test_config_accessible(self):
        cfg = AppConfig()
        svc = ItemService(config=cfg)
        assert svc._config is cfg

    def test_config_attributes_accessible(self):
        cfg = AppConfig(overrides={"APP_NAME": "TestApp"})
        svc = ItemService(config=cfg)
        assert svc._config.APP_NAME == "TestApp"


class TestServiceRepo:
    def test_repo_receives_the_service_connection(self):
        svc = ItemService(conn="conn-token")
        assert svc.repo().conn == "conn-token"

    def test_repo_without_conn_gets_none(self):
        assert ItemService().repo().conn is None
