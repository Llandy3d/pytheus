class PytheusException(Exception):
    pass


class UnobservableMetricException(PytheusException):
    pass


class InvalidBackendClassException(PytheusException):
    pass


class InvalidBackendConfigException(PytheusException):
    pass


class LabelValidationException(PytheusException):
    pass


class BucketException(PytheusException):
    pass
