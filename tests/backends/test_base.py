import os
from unittest import mock

import pytest

from pytheus.backends import base
from pytheus.backends.base import (
    InvalidBackendClassException,
    SingleProcessBackend,
    _import_backend_class,
    load_backend,
)


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


class TestImportBackendClass:
    def test_with_correct_class_path(self):
        imported_class = _import_backend_class("pytheus.backends.base.SingleProcessBackend")
        assert imported_class is SingleProcessBackend

    def test_without_path_raises(self):
        with pytest.raises(InvalidBackendClassException):
            _import_backend_class("notaclasspath")

    def test_wrong_module_raises(self):
        with pytest.raises(InvalidBackendClassException):
            _import_backend_class("pytheus.doesntexists.Class")

    def test_class_not_in_module_raises(self):
        with pytest.raises(InvalidBackendClassException):
            _import_backend_class("pytheus.metrics.UnexistingProcessor")

    def test_class_not_a_backend_subclass_raises(self):
        with pytest.raises(InvalidBackendClassException):
            _import_backend_class("pytheus.metrics._MetricCollector")
