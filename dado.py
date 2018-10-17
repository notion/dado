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


# [ Imports ]
import sys
from functools import partial
import inspect
import types


# [ Exports ]
__all__ = ['data_driven']


def __dir__():
    return sorted(__all__)


# [ Interactors ]
def get_module(level=2, get_stack=inspect.stack, module_dict=None):
    """Get the module <level> levels up the call stack."""
    if module_dict is None:
        module_dict = sys.modules
    frames = get_stack()
    caller_frame = frames[level].frame
    caller_module_name = caller_frame.f_globals['__name__']
    caller_module = module_dict[caller_module_name]
    return caller_module


# [ Sub-components ]
def build_test(test, suffix, arg_names, args):
    """Build data driven tests from original test."""
    # assign the args for this iteration of the test
    # to the given arg names, so there's no ambiguity or ordering
    # issues, and so that if the args are wrong, an error occurs.
    test_name = test.__name__
    kwargs = {k: v for k, v in zip(arg_names, args)}
    new_test_name = '_'.join((test_name, suffix))
    return partial(test, **kwargs), new_test_name


# [ Core Components ]
def dd_decorator(names, test_dict, test, build_test=build_test, get_module=get_module):
    """
    A decorator for data-driven tests.

    Builds data-driven tests, sets them to the calling module, and unsets the original test function.
    """
    new_funcs = []
    for suffix, args in test_dict.items():
        new_test, new_name = build_test(test, suffix, names, args)
        new_test.__name__ = new_name
        new_test.__code__ = types.SimpleNamespace()
        new_test.__code__.co_filename = test.__code__.co_filename
        setattr(get_module(), new_name, new_test)
        new_funcs.append(new_test)
    # return None so that the original function will be overwritten
    # by a non-callable, and therefor will be ignored by foot.
    return new_funcs


# [ API ]
def data_driven(names, test_dict, decorator=dd_decorator):
    """A decorator builder for data-driven tests."""
    # Could do things this way:
    #   data_driven = partial(partial, dd_decorator)
    #     the outer partial returns a partial of a partial with dd_decorator as the first arg
    #     data_driven(*args) will now call partial(dd_decorator, *args)
    #     which returns a partial of dd_decorator with *args as the first args.
    #     whoa terrible:
    #     - difficult to reason about
    #     - args are not controlled at the different levels
    #     - altogether too clever
    # instead, just return the decorator
    return partial(decorator, names, test_dict)
