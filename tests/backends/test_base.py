import os
from unittest import mock

from pytheus.backends import base
from pytheus.backends.base import SingleProcessBackend, load_backend


class DummyProcessBackend:
    def __init__(self, config, metric, histogram_bucket=None):
        pass

    @classmethod
    def _initialize(cls, config):
        pass

    def inc(self, value):
        pass

    def dec(self, value):
        pass

    def set(self, value):
        pass

    def get(self):
        pass


class TestLoadBackend:
    @mock.patch("pytheus.backends.base.BACKEND_CLASS", None)
    def test_call_without_args(self):
        load_backend()

        assert base.BACKEND_CLASS is SingleProcessBackend
        assert base.BACKEND_CONFIG == {}

    def test_with_arguments(self):
        config = {"bob": "bobby"}
        load_backend(DummyProcessBackend, config)

        assert base.BACKEND_CLASS is DummyProcessBackend
        assert base.BACKEND_CONFIG == config

    @mock.patch.dict(
        os.environ, {"PYTHEUS_BACKEND_CLASS": "tests.backends.test_base.DummyProcessBackend"}
    )
    def test_with_environment_variables(self, tmp_path):
        load_backend()

        assert base.BACKEND_CLASS.__name__ == DummyProcessBackend.__name__

    @mock.patch.dict(
        os.environ, {"PYTHEUS_BACKEND_CLASS": "tests.backends.test_base.DummyProcessBackend"}
    )
    def test_argument_has_priority_over_environment_variable(self):
        load_backend(SingleProcessBackend)

        assert base.BACKEND_CLASS is SingleProcessBackend

    @mock.patch.object(DummyProcessBackend, "_initialize")
    def test_initialization_hook(self, _initialize_mock):
        load_backend(DummyProcessBackend)
        _initialize_mock.assert_called()
