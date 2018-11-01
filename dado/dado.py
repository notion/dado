"""
Dado: Data Driven Test Decorator.

Decorate a test to create indepenent tests for each decorated data set.

Example:

    Given:
        @data_driven(['first', 'second'], {
            'letters': ['a', 'b'],
            'numbers': [0, 1],
        })
        def test_first_two(first, second): ...

    When you load the module, it will load as if you'd defined:
        def test_first_two_letters():
            return test_first_two('a', 'b')

        def test_first_two_numbers():
            return test_first_two(0, 1)

Author: toejough
Namer: soapko
"""


# [ Imports:Python ]
import functools
import inspect
import sys
import types
import typing


# [ Exports ]
__all__ = ['data_driven']


def __dir__() -> typing.Iterable[str]:
    return sorted(__all__)


# [ Interactors ]
def get_module(
    level: int = 2,
    get_stack: typing.Callable[[], typing.List[inspect.FrameInfo]] = inspect.stack,
    module_dict: typing.Optional[typing.Dict[str, types.ModuleType]] = None,
) -> types.ModuleType:
    """Get the module <level> levels up the call stack."""
    if module_dict is None:
        module_dict = sys.modules
    frames = get_stack()
    caller_frame = frames[level].frame
    caller_module_name = caller_frame.f_globals['__name__']
    caller_module = module_dict[caller_module_name]
    return caller_module


# [ Sub-components ]
def build_test(
    test: typing.Callable,
    suffix: str,
    arg_names: typing.Iterable[str],
    args: typing.Iterable[typing.Any],
) -> typing.Tuple[typing.Callable, str]:
    """Build data driven tests from original test."""
    # assign the args for this iteration of the test
    # to the given arg names, so there's no ambiguity or ordering
    # issues, and so that if the args are wrong, an error occurs.
    test_name = test.__name__
    kwargs = {k: v for k, v in zip(arg_names, args)}
    new_test_name = '_'.join((test_name, suffix))
    return functools.partial(test, **kwargs), new_test_name


# [ Core Components ]
def dd_decorator(
    names: typing.Iterable[str],
    test_dict: typing.Dict[str, typing.Iterable[typing.Any]],
    test: typing.Callable,
    build_test: typing.Callable = build_test,
    get_module: typing.Callable = get_module,
) -> None:
    """
    Build the data-driven tests.

    Builds data-driven tests, sets them to the calling module, and unsets the original test function.
    """
    for suffix, args in test_dict.items():
        new_test, new_name = build_test(test, suffix, names, args)
        new_test.__name__ = new_name
        new_test.__code__ = types.SimpleNamespace()
        new_test.__code__.co_filename = test.__code__.co_filename
        setattr(get_module(), new_name, new_test)
    # return None so that the original function will be overwritten
    # by a non-callable, and therefor will be ignored by foot.
    return None


# [ API ]
def data_driven(
    names: typing.Iterable[str],
    test_dict: typing.Dict[str, typing.Iterable[typing.Any]],
    decorator: typing.Callable = dd_decorator,
) -> typing.Callable:
    """Build the decorator for data-driven tests."""
    return functools.partial(decorator, names, test_dict)
