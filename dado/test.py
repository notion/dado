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
import unittest
from unittest.mock import sentinel, MagicMock
from .dado import get_module, build_test, dd_decorator, data_driven


# [ Unittest Assertions ]
# XXX pull out into own module and publish to pypi
T = unittest.TestCase()


# [ Interactor Tests ]
def test_get_module():
    """
    Test get module.

    Test it:
        makes the right calls

    I/O boundaries:
        get_stack - get the call stack
        module_dict - the dict of {name: module} pairs

    Function I/O:
        args:
            level - the module level to go back to
            get_stack
            module_dict

        returns - the module at the given level in the call stack
    """
    # Given
    get_stack = MagicMock(return_value=[sentinel.l1, sentinel.l2, sentinel.l3])
    module = sentinel.module
    sentinel.l2.frame = sentinel.frame
    sentinel.frame.f_globals = {
        '__name__': 'module'
    }
    module_dict = {'module': module}

    # When
    returned_module = get_module(level=1, get_stack=get_stack, module_dict=module_dict)

    # Then
    T.assertEqual(returned_module, module)


# [ Sub-component Tests ]
def test_build_test():
    """
    Test build_test.

    Test it:
        build the specified test

    I/O boundaries - None

    Function I/O:
        args:
            test - the original test
            test_name - the original test name
            suffix - the new test suffix
            arg_names - the names of the args
            args - actual args

        returns - None
    """
    # Given
    test = MagicMock
    test_name = "test_name"
    test.__name__ = test_name
    suffix = "foo"
    arg_names = ['a', 'b']
    args = (sentinel.a, sentinel.b)

    # When
    new_test, new_test_name = build_test(test, suffix, arg_names, args)

    # Then
    T.assertEqual(new_test_name, test_name + '_' + suffix)
    T.assertEqual(new_test.func, test)
    T.assertEqual(new_test.keywords, {
        'a': sentinel.a,
        'b': sentinel.b,
    })


# [ Core Component Tests ]
def test_dd_decorator():
    """
    Test dd_decorator.

    Test it:
        adds the right tests.

    I/O boundaries - None

    Function I/O:
        args:
            names - the names of the args
            test_dict - the dictionary of suffixes to actual args
            test - the original test
            add_test - the function that actually adds a new test.

        returns - None
    """
    # Given
    names = [sentinel.arg1_name, sentinel.arg2_name]
    test_dict = {
        'suffix_a': [sentinel.arg1_a, sentinel.arg2_a],
        'suffix_b': [sentinel.arg1_b, sentinel.arg2_b],
    }
    test = MagicMock()
    test.__name__ = "test"
    get_mock_module = MagicMock(return_value=sentinel.mock_module)

    # When
    dd_decorator(names, test_dict, test, build_test, get_mock_module)

    # Then
    T.assertTrue(hasattr(sentinel.mock_module, 'test_suffix_a'))
    new_test = sentinel.mock_module.test_suffix_a
    T.assertEqual(new_test.func, test)
    T.assertEqual(new_test.keywords, {
        sentinel.arg1_name: sentinel.arg1_a,
        sentinel.arg2_name: sentinel.arg2_a,
    })
    T.assertTrue(hasattr(sentinel.mock_module, 'test_suffix_b'))
    new_test = sentinel.mock_module.test_suffix_b
    T.assertEqual(new_test.func, test)
    T.assertEqual(new_test.keywords, {
        sentinel.arg1_name: sentinel.arg1_b,
        sentinel.arg2_name: sentinel.arg2_b,
    })


# [ API Tests ]
def test_data_driven_builder():
    """
    Test data_driven decorator builder.

    Test it:
        returns the given decorator supplied with the given args.

    I/O boundaries - none.

    Function I/O:
        args:
            decorator - the decorator to supply with the args
            names - field names
            test_dict - a dictionary with {test_suffix: *args}

        returns - a partial of the decorator with the names & test_dict
    """
    # Given
    mock_decorator = MagicMock()
    names = sentinel.names
    test_dict = sentinel.test_dict

    # When
    mock_dd = data_driven(names, test_dict, decorator=mock_decorator)

    # Then
    T.assertEqual(mock_dd.func, mock_decorator)
    T.assertEqual(mock_dd.args, (names, test_dict))
