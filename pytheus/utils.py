import importlib
from typing import Callable


def import_object_from_path(full_import_path: str) -> Callable:
    """
    Returns the python object if correctly imported.
    Raises:
        ValueError: if the given path has invalid syntax
        ImportError: if the module where the object is located can't be imported
        AttributeError: if object is not found in the given module path
    """
    module_path, class_name = full_import_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    obj = getattr(module, class_name)
    return obj
