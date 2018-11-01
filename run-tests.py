"""Test runner for rototiller."""  # pylint: disable=invalid-name
# The module is just a script - having a hyphen in the name is fine.


# [ Imports:Python ]
import collections
import contextlib
import importlib
import importlib.util
import os
import pathlib
import sys
import types
import typing

# [ Imports:Third Party ]
import better_exceptions  # type: ignore
import blessed  # type: ignore
import click


def _sort_tests_by_tag(test_dict: typing.Dict[str, typing.Callable], *, order: typing.Tuple[str, ...]) -> typing.Dict[str, typing.Callable]:
    by_tag: collections.defaultdict = collections.defaultdict(dict)
    for name, func in test_dict.items():
        tag = getattr(func, 'tag', 'behavior')
        if tag not in order:
            raise RuntimeError(f"Tag {tag} was found on {name} ({func}), but was not specified in the ordering ({order})")
        by_tag[tag][name] = func
    sorted_test_dict = {n: f for t in order for n, f in by_tag[t].items()}
    return sorted_test_dict


def _import_module(name: str) -> types.ModuleType:
    path = pathlib.Path(name).resolve()
    module_name = pathlib.Path(name).stem
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    if spec.loader:
        spec.loader.exec_module(module)
    else:
        raise RuntimeError(f"Module {name} cannot be loaded!")
    return module


def _get_package_dir(test: typing.Callable) -> str:
    filename = test.__code__.co_filename
    if not filename:
        raise RuntimeError(f"Cannot find the underlying file for {test}!")
    path = pathlib.Path(filename).parent
    while 'setup.py' not in (p.name for p in path.iterdir()):
        if path == path.root:
            raise RuntimeError("got all the way up to the test's root dir, and never found package dir.")
        path = path.parent
    return str(path)


@contextlib.contextmanager
def _current_dir(path: str) -> typing.Generator:
    original = pathlib.Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(original)


def _run_test_in_dir(test: typing.Callable) -> None:
    with _current_dir(_get_package_dir(test)):
        test()


def _report_not_implemented() -> None:
    print(blessed.Terminal().magenta("not yet implemented"))


def _handle_failure(error: AssertionError) -> typing.NoReturn:
    terminal = blessed.Terminal()
    print(terminal.bold_red("FAILED!"))
    if not str(error):
        error = terminal.red_on_white("No assertion message provided!!  (╯°□°)╯︵ ┻━┻ ...")
    print()
    print(error)
    sys.exit("early exit due to test failure")


def _report_error() -> None:
    print(blessed.Terminal().white_on_red("ERRORED!"))
    print()


def _report_pass() -> None:
    print(blessed.Terminal().bold_green("PASSED"))


def _report_test_run_summary(results: typing.Dict[str, int]) -> None:
    terminal = blessed.Terminal()
    num_total = results['total']
    num_passed = results['passed']
    num_failed = results['failed']
    num_ignored = results['ignored']
    num_errored = results['errored']
    num_not_run = num_total - num_passed - num_failed - num_ignored - num_errored
    passed = terminal.bold_green(str(num_passed)) if num_passed else "0"
    failed = terminal.bold_red(str(num_failed)) if num_failed else "0"
    ignored = terminal.magenta(str(num_ignored)) if num_ignored else "0"
    errored = terminal.white_on_red(str(num_errored)) if num_errored else "0"
    not_run = terminal.bold_white(str(num_not_run)) if num_not_run else "0"
    print(f"\nPassed: {passed} | Failed: {failed} | Ignored: {ignored} | Errored: {errored} | Not Run: {not_run}\n")


def _enable_better_exceptions() -> None:
    better_exceptions.hook()
    better_exceptions.MAX_LENGTH = None
    # vulture whitelisting
    better_exceptions.MAX_LENGTH  # pylint: disable=pointless-statement


def _discover_test_funcs(test_module_name: str) -> typing.Dict[str, typing.Callable]:
    this_module = _import_module(test_module_name)
    public_names = dir(this_module)
    test_names = (n for n in public_names if n.startswith('test_'))
    test_attrs = {n: getattr(this_module, n) for n in test_names}
    test_funcs = {n: t for n, t in test_attrs.items() if callable(t)}
    test_funcs = _sort_tests_by_tag(test_funcs, order=(
        'packaging',  # does it build?
        'behavior',  # does it do what it should?
        'live',  # no dead/commented code
        'security',  # is it safe?
        'typing',  # is it correct?
        # is it simple?
        'standards',
    ))
    return test_funcs


def _report_discovered_tests(test_funcs: typing.Dict[str, typing.Callable]) -> None:
    print(f"{len(test_funcs)} tests discovered...\n")


def _report_test_start(index: int, *, total: int, name: str) -> None:
    print(f"({index+1}/{total}) {name}: ", end='')
    sys.stdout.flush()


@click.command()
@click.argument('test-module-name')
def _run(test_module_name: str) -> None:
    _enable_better_exceptions()
    test_funcs = _discover_test_funcs(test_module_name)
    _report_discovered_tests(test_funcs)
    results = {
        'passed': 0,
        'failed': 0,
        'errored': 0,
        'ignored': 0,
        'total': len(test_funcs),
    }
    try:
        for index, (name, test) in enumerate(test_funcs.items()):
            _report_test_start(index, total=len(test_funcs), name=name)
            try:
                _run_test_in_dir(test)
            except NotImplementedError:
                results['ignored'] += 1
                _report_not_implemented()
            except AssertionError as error:
                results['failed'] += 1
                _handle_failure(error)
            except Exception:
                results['errored'] += 1
                _report_error()
                raise
            else:
                results['passed'] += 1
                _report_pass()
    finally:
        _report_test_run_summary(results)


if __name__ == "__main__":
    _run()
