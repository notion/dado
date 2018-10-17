"""Tests for dado."""


# [ Imports ]
import importlib
import pathlib
import sys


# [ Internals ]
def _get_example_module_path():
    return pathlib.Path(__file__).parent / 'example_module.py'


def _add_to_discoverable_modules(module):
    sys.modules[module.__name__] = module


def _get_example_module():
    path = _get_example_module_path()
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    _add_to_discoverable_modules(module)
    spec.loader.exec_module(module)
    return module


def _get_funcs_from(module):
    names = dir(module)
    attributes = {n: getattr(module, n) for n in names}
    funcs = {n: f for n, f in attributes.items() if callable(f)}
    return funcs


def _get_all_from(module):
    names = dir(module)
    attributes = {n: getattr(module, n) for n in names}
    return attributes


def test_data_driven_functions_created():
    # Given the example module
    module = _get_example_module()

    # When the module's functions are retrieved
    functions = _get_funcs_from(module)

    # Then the expected functions are there
    actual = sorted(list(functions.keys()))
    expected = sorted(['func_one_two', 'func_a_b'])
    message = f"The actual functions found ({actual}) != the expected functions found ({expected})"
    assert actual == expected, message


def test_data_driven_functions_work():
    # Given the example module
    module = _get_example_module()

    # When the module's functions are retrieved
    functions = _get_funcs_from(module)

    # Then the expected functions are there
    assert functions['func_one_two']() == (1, 2)
    assert functions['func_a_b']() == ('a', 'b')


def test_original_function_is_lists():
    # Given the example module
    module = _get_example_module()

    # When the module's attributes are retrieved
    attributes = _get_all_from(module)

    # Then the original function name now returns a list of the new functions
    assert all(callable(f) for f in attributes['func'])
    assert sorted(f.__name__ for f in attributes['func']) == sorted(['func_one_two', 'func_a_b'])
