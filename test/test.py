"""Tests for dado."""


# [ Imports:Python ]
import functools
import importlib
import json
import pathlib
import shutil
import subprocess
import sys
import typing

# [ Imports:Third Party ]
import pipe


def tagged(tag: str) -> typing.Callable:
    def decorator(func: typing.Callable) -> typing.Callable:
        # mypy doesn't ack that a func is arbitrarily extensible
        func.tag = tag  # type: ignore
        # vulture whitelist
        # pylint: disable=pointless-statement
        func.tag  # type: ignore
        # pylint: enable=pointless-statement
        return func
    return decorator


@pipe.Pipe  # type: ignore
def is_multiline(string: str) -> bool:
    return 1 < len(string.splitlines())


def indent(string: str) -> str:
    return '  ' + '\n  '.join(string.splitlines())


def limit_lines(string: str, *, max_lines: int) -> str:
    lines = string.splitlines()
    allowed_lines = lines[:max_lines]
    lines_left = len(lines) - len(allowed_lines)
    if lines_left:
        allowed_lines.append(f"<<<< +{lines_left} more >>>>")
    return '\n'.join(allowed_lines)


def _format_assertion(**message_kwargs: typing.Any) -> str:
    message = f"`Assertion failed!"
    for key, value in message_kwargs.items():
        value_string = f"{value}"
        if value_string | is_multiline:
            value_string = limit_lines(value_string, max_lines=20)
            value_string = "\n" + indent(value_string)
        message += f"\n{key}: {value_string}"
    return message


def _raise_assertion(**message_kwargs: typing.Any) -> None:
    message = _format_assertion(**message_kwargs)
    raise AssertionError(message)


def _assert(success: bool, **message_kwargs: typing.Any) -> None:
    if not success:
        _raise_assertion(**message_kwargs)


def sub(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True)


@tagged('packaging')
def test_imports() -> None:
    assert_sub('python', 'check-imports.py')


def assert_sub(*args: typing.Any) -> None:
    result = sub(*args)
    output = {}
    if result.stdout:
        output['stdout'] = result.stdout
    if result.stderr:
        output['stderr'] = result.stderr
    _assert(
        result.returncode == 0,
        command=result.args,
        rc=result.returncode,
        **output,
    )


@tagged('security')
def test_security() -> None:
    assert_sub('bandit', '-r', '.')


@tagged('typing')
def test_types() -> None:
    assert_sub('mypy', '--strict', '.')


@tagged('live')
def test_live() -> None:
    assert_sub('vulture', '.')
    assert_sub('python', 'find-commented-code.py')
    assert_sub('python', 'find-unused-classes.py')


@tagged('standards')
def test_flake8() -> None:
    assert_sub('flake8', '--exclude', '*/test*.py,test*.py', '--config', '.flake8')


@tagged('standards')
def test_flake8_tests() -> None:
    assert_sub('flake8', '--filename', '*/test*.py,test*.py', '--config', '.flake8.test')


@tagged('standards')
def test_pylint() -> None:
    assert_sub('pylint', *pathlib.Path.cwd().glob('*.py'))
    assert_sub('isort', '-rc', '.', '--check-only', '--diff', '-lai', '2')


@tagged('standards')
def test_isort() -> None:
    # XXX mutpy
    # XXX afl python
    # XXX layer linter
    # XXX flake8-eradicate
    assert_sub('isort', '-rc', '.', '--check-only', '--diff', '-lai', '2')


def _get_installed_packages_str() -> str:
    # sub runs with stdout = subprocess.PIPE and text mode, this is a string
    return typing.cast(str, sub('pip', 'list', '--format', 'json').stdout)


def _get_installed_package_names() -> typing.List[str]:
    installed_packages_str = _get_installed_packages_str()
    installed_package_data = json.loads(installed_packages_str)
    return [d['name'] for d in installed_package_data]


def _install_wheel() -> None:
    sub('pip', 'install', 'wheel').check_returncode()


def _ensure_wheel_installed() -> None:
    installed_package_names = _get_installed_package_names()
    if 'wheel' not in installed_package_names:
        _install_wheel()


def _build_distribution_files() -> None:
    assert_sub('python', 'setup.py', 'sdist', 'bdist_wheel')


def _get_possible_build_dirs() -> typing.Tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
    project_dir = _get_package_dir()
    build_dir = project_dir / 'build'
    dist_dir = project_dir / 'dist'
    egg_dir = project_dir / 'web_must.egg-info'
    return (build_dir, dist_dir, egg_dir)


def _get_package_dir() -> pathlib.Path:
    filename = __file__
    path = pathlib.Path(filename).parent
    while 'setup.py' not in (p.name for p in path.iterdir()):
        if path == path.root:
            raise RuntimeError("got all the way up to the test's root dir, and never found package dir.")
        path = path.parent
    return path


def _get_expected_dist_paths() -> typing.Tuple[pathlib.Path, pathlib.Path]:
    project_dir = _get_package_dir()
    dist_dir = project_dir / 'dist'
    sdist_path = dist_dir / 'dado-0.1.4.tar.gz'
    bdist_path = dist_dir / 'dado-0.1.4-py3-none-any.whl'
    return (sdist_path, bdist_path)


def _build_package() -> None:
    _ensure_wheel_installed()
    _build_distribution_files()


def _with_teardown(teardown_func: typing.Callable) -> typing.Callable:
    def _decorator(func: typing.Callable) -> typing.Callable:
        @functools.wraps(func)
        def _wrapper(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
            try:
                return func(*args, **kwargs)
            finally:
                teardown_func()
        return _wrapper
    return _decorator


def _clean_out_build_artifacts() -> None:
    possible_build_dirs = _get_possible_build_dirs()
    existing_dirs = [d for d in possible_build_dirs if d.exists()]
    for directory in existing_dirs:
        shutil.rmtree(directory)


@_with_teardown(_clean_out_build_artifacts)
@tagged('packaging')
def test_build() -> None:
    """
    Validate the tool can be built for deployment.

    * given any pre-existing build artifacts are cleaned out
    * when a build is run
    * the correct build artifacts exist
    """
    # Given
    _clean_out_build_artifacts()
    expected_dist_paths = _get_expected_dist_paths()

    # When
    _build_package()

    # Then
    for path in expected_dist_paths:
        _assert(path.exists(), missing_path=path, paths=list(pathlib.Path('dist').iterdir()))


# [ Behavior ]
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


def test_original_function_is_none():
    # Given the example module
    module = _get_example_module()

    # When the module's attributes are retrieved
    attributes = _get_all_from(module)

    # Then the original function name now returns None
    assert attributes['func'] is None, f"attributes['func'] is {attributes['func']}, but we expected None"
