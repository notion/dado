"""Check for import problems."""  # pylint: disable=invalid-name


# [ Imports:Python ]
import ast
import contextlib
import os
import pathlib
import re
import sys
import types
import typing

# [ Imports:Third Party ]
import setuptools  # type: ignore


# [ Types ]
IndexedStrings = typing.List[typing.Tuple[int, str]]


# [ Internals ]
def _get_package_parent_path(path: pathlib.Path) -> pathlib.Path:
    parts = path.parts
    for index in range(len(parts)):
        current_parts = parts[:index + 1]
        root, *others = current_parts
        upstream_path = pathlib.Path(root).joinpath(*others)
        if (upstream_path / '__init__.py').exists():
            if not others:
                raise RuntimeError("can't get the package parent - the root dir has an __init__.py!")
            return upstream_path.parent
    return path.parent


def _to_module(path: pathlib.Path) -> str:
    parts = path.parts
    index = 0
    for index in range(len(parts)):
        current_parts = parts[:index + 1]
        root, *others = current_parts
        upstream_path = pathlib.Path(root).joinpath(*others)
        if (upstream_path / '__init__.py').exists():
            break
    module_parts = list(parts[index:])
    if module_parts[-1] == '__init__.py':
        module_parts = module_parts[:-1]
    if module_parts[-1].endswith('.py'):
        *others, final = module_parts
        final = final[:-3]
        module_parts = [*others, final]
    return '.'.join(module_parts)


def _rebuild_source_module(module_name: str, *, level: int, path_str: str) -> str:
    """
    Rebuild the source module.

    If not level, there must be a module name (otherwise we have "from import foo", which is invalid syntax)
    If level, we may or may not have a module name:
       "from .. import foo" is level 2, no module name
       "from .bar import foo" is level 1, module name "bar"
    """
    if not level:
        return module_name
    parent_path = pathlib.Path(path_str)
    for _ in range(level):
        parent_path = parent_path.parent
    relative_module_parent = _to_module(parent_path)
    if not module_name:
        return relative_module_parent
    return f"{relative_module_parent}.{module_name}"


def _parse_imports(path: pathlib.Path) -> typing.List[typing.Tuple[pathlib.Path, int, str]]:
    path_str = str(path)
    source = path.read_text()
    this_ast = ast.parse(source, filename=path_str)
    import_nodes = [n for n in this_ast.body if isinstance(n, ast.Import)]
    import_from_nodes = [n for n in this_ast.body if isinstance(n, ast.ImportFrom)]
    import_from_nodes = [n for n in import_from_nodes if n.module]

    imports = []
    for this_import_node in import_nodes:
        line_number = this_import_node.lineno
        for this_name in this_import_node.names:
            imports.append((path, line_number, this_name.name))
    for this_import_from_node in import_from_nodes:
        if not this_import_from_node.module or not this_import_from_node.level:
            # "filtering" here because mypy doesn't recognize it if we filter it in the
            # list comprehension
            continue
        line_number = this_import_from_node.lineno
        source_module = _rebuild_source_module(this_import_from_node.module, level=this_import_from_node.level, path_str=path_str)
        import_source = False
        for this_name in this_import_from_node.names:
            full_name = f"{source_module}.{this_name.name}"
            try:
                # validating import
                # pylint: disable=exec-used
                exec(f"import {full_name}")  # nosec
                # pylint: enable=exec-used
            except ModuleNotFoundError:
                import_source = True
            else:
                imports.append((path, line_number, f"{full_name}"))
        if import_source:
            imports.append((path, line_number, f"{source_module}"))
    return imports


def _is_python_module(module: types.ModuleType) -> bool:
    return (
        not hasattr(module, '__file__') or
        not module.__file__ or
        (
            'lib/python' in module.__file__ and
            'packages' not in module.__file__
        )
    )


def _is_project_module(module: types.ModuleType, project_paths: typing.List[pathlib.Path]) -> bool:
    return (
        not _is_python_module(module) and
        pathlib.Path(module.__file__) in project_paths
    )


def _is_third_party_module(module: types.ModuleType, project_paths: typing.List[pathlib.Path]) -> bool:
    return (
        not _is_python_module(module) and
        not _is_project_module(module, project_paths=project_paths)
    )


def _get_module_names(
        all_python_paths: typing.List[pathlib.Path],
) -> typing.List[typing.Tuple[pathlib.Path, int, str]]:
    all_module_names: typing.List[typing.Tuple[pathlib.Path, int, str]] = []
    for this_path in all_python_paths:
        all_module_names += _parse_imports(this_path)
    return all_module_names


def _get_unique_imports(
    all_python_paths: typing.List[pathlib.Path],
) -> typing.Dict[str, typing.Tuple[pathlib.Path, int]]:
    all_module_names = _get_module_names(all_python_paths)
    unique_imports: typing.Dict[str, typing.Tuple[pathlib.Path, int]] = {}
    for this_path, line_number, module_name in all_module_names:
        if module_name not in unique_imports:
            unique_imports[module_name] = (this_path, line_number)
    return unique_imports


def _identify_unused_local_modules(
    all_python_paths: typing.List[pathlib.Path],
    *,
    all_project_modules: typing.Dict[str, typing.Tuple[pathlib.Path, int, types.ModuleType]],
) -> typing.List[str]:
    # a '-' in a name means it's not importable as a module - this would just be a script someone calls.
    local_modules = [_to_module(p) for p in all_python_paths if '-' not in str(p)]
    return [
        this_module
        for this_module in local_modules
        if (
            this_module not in all_project_modules and
            not any(a.startswith(f"{this_module}.") for a in all_project_modules) and
            this_module not in (
                'setup',  # setup.py
                'example_module',  # imported by string in test
                'test',  # the test package
            )
        )
    ]


def _load_modules(unique_top_level_imports: typing.Dict[str, typing.Tuple[pathlib.Path, int]]) -> typing.Tuple[typing.Dict[str, typing.Tuple[pathlib.Path, int]], typing.Dict[str, typing.Tuple[pathlib.Path, int, types.ModuleType]]]:
    missing_modules = {}
    loadable_modules = {}
    for module_name, source_data in unique_top_level_imports.items():
        try:
            # validating import
            original_dir = pathlib.Path.cwd()
            path = _get_package_parent_path(source_data[0])
            if path != original_dir:
                sys.path.append(str(path))
            # pylint: disable=exec-used
            exec(f"import {module_name}")  # nosec
            # pylint: enable=exec-used
        except ModuleNotFoundError:
            missing_modules[module_name] = source_data
        else:
            loadable_modules[module_name] = source_data
        finally:
            if path != original_dir:
                sys.path.remove(str(path))
    # all imported modules
    actual_modules = {m: (loadable_modules[m][0], loadable_modules[m][1], sys.modules[m]) for m in loadable_modules}
    return missing_modules, actual_modules


def _identify_missing_third_party_modules(
    third_party_modules: typing.Dict[str, typing.Tuple[pathlib.Path, int, types.ModuleType]],
    *,
    installed_modules: IndexedStrings,
) -> typing.Dict[str, typing.Tuple[pathlib.Path, int, types.ModuleType]]:
    return {
        m: s
        for m, s in third_party_modules.items()
        if (
            m not in [m[1] for m in installed_modules] and
            m not in (
                'setuptools',  # included by pip
            )
        )
    }


def _identify_unused_third_party_modules(
    third_party_modules: typing.Dict[str, typing.Tuple[pathlib.Path, int, types.ModuleType]],
    *,
    installed_modules: IndexedStrings,
) -> IndexedStrings:
    return [
        (index, module_name)
        for index, module_name in installed_modules
        if (
            module_name not in third_party_modules and
            module_name not in (
                # module names which differ from import names
            )
        )
    ]


def _report_package_problems(
    *,
    missing_modules: typing.Dict[str, typing.Tuple[pathlib.Path, int]],
    missing_third_party: typing.Dict[str, typing.Tuple[pathlib.Path, int, types.ModuleType]],
    unused_third_party: IndexedStrings,
    unused_local: typing.List[str],
) -> bool:
    # Error if any missing or unused modules exist.
    errors_found = bool(missing_modules or missing_third_party or unused_third_party or unused_local)
    # unimportable modules
    for name, source_data in missing_modules.items():
        print(f"{source_data[0]}:{source_data[1]} -> {name} (unimportable)")
    # third-party modules missing from install requires
    for name, extended_source_data in missing_third_party.items():
        print(f"{extended_source_data[0]}:{extended_source_data[1]} -> {name} (missing-from-install-requires)")
    # install requires modules not used
    for index, module_name in unused_third_party:
        print(f"setup.py:{index} -> {module_name} (unused-install-requires)")
    # local modules not imported
    for this_path_str in unused_local:
        print(f"{this_path_str} (unused-project-module)")

    return errors_found


def _report_test_problems(
    *,
    missing_modules: typing.Dict[str, typing.Tuple[pathlib.Path, int]],
    missing_third_party: typing.Dict[str, typing.Tuple[pathlib.Path, int, types.ModuleType]],
    unused_third_party: IndexedStrings,
    unused_local: typing.List[str],
) -> bool:
    # Error if any missing or unused modules exist.
    errors_found = bool(missing_modules or missing_third_party or unused_third_party or unused_local)
    # unimportable modules
    for name, source_data in missing_modules.items():
        print(f"{source_data[0]}:{source_data[1]} -> {name} (unimportable)")
    # third-party modules missing from install requires
    for name, extended_source_data in missing_third_party.items():
        print(f"{extended_source_data[0]}:{extended_source_data[1]} -> {name} (missing-from-extras-require)")
    # install requires modules not used
    for index, module_name in unused_third_party:
        print(f"setup.py:{index} -> {module_name} (unused-extras-require)")
    # local modules not imported
    for this_path_str in unused_local:
        print(f"{this_path_str} (unused-test-module)")

    return errors_found


def _get_names_of_items_in(target_dir: pathlib.Path) -> typing.Tuple[str, ...]:
    local_items = target_dir.iterdir()
    local_names = tuple(i.name for i in local_items)
    return local_names


def _get_package_dir() -> pathlib.Path:
    here = __file__
    target_dir = pathlib.Path(here).parent
    local_names = _get_names_of_items_in(target_dir)
    setup_name = 'setup.py'
    while setup_name not in local_names:
        target_dir = target_dir.parent
        local_names = _get_names_of_items_in(target_dir)
    return target_dir


def _get_setup_packages() -> typing.List[str]:
    packages = []
    for this_package in setuptools.find_packages():
        if not isinstance(this_package, str):
            raise TypeError(f"Got non-str response from setuptools.find_packages: ({type(this_package)}) {this_package}")
        packages.append(this_package)
    return packages


def _to_indexed_module_names(indexed_section_lines: IndexedStrings) -> IndexedStrings:
    module_name_pattern = r'.*[\'"]([a-zA-Z_\-0-9]+)[\'"],'
    indexed_module_names = []
    for index, line in indexed_section_lines:
        match = re.match(module_name_pattern, line)
        if not match:
            continue
        if '# no-import' in line:
            continue
        matched_name = match.group(1)
        indexed_module_names.append((index, matched_name))
    return indexed_module_names


def _get_setup_modules(section: str) -> IndexedStrings:
    setup_path = _get_package_dir() / 'setup.py'
    setup_lines = setup_path.read_text().splitlines()
    start_line_number = None
    stop_line_number = len(setup_lines) - 1
    indentation = None
    enumerated = enumerate(setup_lines)
    for index, this_line in enumerated:
        if not re.search(f'{section}.*[:=]', this_line):
            continue
        start_line_number = index
        match = re.search(r'^(\s*)', this_line)
        # match is guaranteed, because we're asking for *any* space, even none.
        match = typing.cast(typing.Match, match)
        indentation = match.group(1)
        break
    else:
        # XXX EARLY RETURN
        return []

    for index, this_line in enumerated:
        match = re.search(r'^(\s*)', this_line)
        # match is guaranteed, because we're asking for *any* space, even none.
        match = typing.cast(typing.Match, match)
        this_indentation = match.group(1)
        if len(this_indentation) <= len(indentation):
            stop_line_number = index
            break

    enumerated_setup_lines = list(enumerate(setup_lines))
    indexed_section_lines = enumerated_setup_lines[start_line_number:stop_line_number]
    return _to_indexed_module_names(indexed_section_lines)


@contextlib.contextmanager
def _change_dir(directory: pathlib.Path) -> typing.Generator[None, None, None]:
    original_dir = os.curdir
    os.chdir(directory)
    try:
        yield
    finally:
        os.chdir(original_dir)


def _modules_to_paths(module_names: typing.Iterable[str]) -> typing.List[pathlib.Path]:
    current_dir = pathlib.Path.cwd()
    paths = []
    for name in module_names:
        as_module_path = current_dir / f"{name}.py"
        if as_module_path.exists():
            paths.append(as_module_path)
            continue
        as_package_path = current_dir / f"{name}"
        python_files = [*as_package_path.glob('*.py'), *as_package_path.glob('**/*.py')]
        paths += python_files

    return paths


def _get_package_python_paths() -> typing.List[pathlib.Path]:
    package_dir = _get_package_dir()
    with _change_dir(package_dir):
        setup_py_packages = _get_setup_packages()
        setup_py_modules = [l[1] for l in _get_setup_modules('py_modules')]
    return _modules_to_paths(setup_py_packages + setup_py_modules)


def _get_test_python_paths() -> typing.List[pathlib.Path]:
    package_dir = _get_package_dir()
    with _change_dir(package_dir):
        package_path = pathlib.Path.cwd()
        all_python_paths = list(package_path.glob('**/*.py'))
    package_python_paths = _get_package_python_paths()
    return [p for p in all_python_paths if p not in package_python_paths]


def _get_package_modules(package_python_paths: typing.List[pathlib.Path]) -> dict:
    imported_by_package = _get_unique_imports(package_python_paths)
    missing, installed = _load_modules(imported_by_package)
    third_party = {
        n: m for n, m in installed.items() if _is_third_party_module(m[2], project_paths=package_python_paths)
    }
    project = {n: m for n, m in installed.items() if _is_project_module(m[-1], project_paths=package_python_paths)}
    specified = _get_setup_modules('install_requires')

    return {
        'missing': missing,
        'third party': third_party,
        'project': project,
        'specified': specified,
    }


def _get_test_modules(test_python_paths: typing.List[pathlib.Path], *, package_python_paths: typing.List[pathlib.Path]) -> dict:
    imported_by_test = _get_unique_imports(test_python_paths)
    missing, installed = _load_modules(imported_by_test)
    third_party = {
        n: m for n, m in installed.items() if _is_third_party_module(m[2], project_paths=test_python_paths + package_python_paths)
    }
    project = {n: m for n, m in installed.items() if _is_project_module(m[-1], project_paths=test_python_paths)}
    specified = _get_setup_modules('test')

    return {
        'missing': missing,
        'third party': third_party,
        'project': project,
        'specified': specified,
    }


# [ API ]
def main() -> None:
    """Check the imports for the package."""
    # paths that might have imports
    package_python_paths = _get_package_python_paths()
    test_python_paths = _get_test_python_paths()

    # Package...
    package_modules = _get_package_modules(package_python_paths)

    # Test...
    test_modules = _get_test_modules(test_python_paths, package_python_paths=package_python_paths)

    # identify problems
    missing_third_party_used_by_package = _identify_missing_third_party_modules(
        package_modules['third party'],
        installed_modules=package_modules['specified'],
    )
    unused_third_party_installed_by_package = _identify_unused_third_party_modules(
        package_modules['third party'],
        installed_modules=package_modules['specified'],
    )
    unused_package_modules = _identify_unused_local_modules(package_python_paths, all_project_modules=package_modules['project'])

    missing_third_party_used_by_test = _identify_missing_third_party_modules(
        test_modules['third party'],
        installed_modules=test_modules['specified'],
    )
    unused_third_party_installed_by_test = _identify_unused_third_party_modules(
        test_modules['third party'],
        installed_modules=test_modules['specified'],
    )
    unused_test_modules = _identify_unused_local_modules(test_python_paths, all_project_modules=test_modules['project'])

    # report problems
    package_error = _report_package_problems(
        missing_modules=package_modules['missing'],
        missing_third_party=missing_third_party_used_by_package,
        unused_third_party=unused_third_party_installed_by_package,
        unused_local=unused_package_modules,
    )
    test_error = _report_test_problems(
        missing_modules=test_modules['missing'],
        missing_third_party=missing_third_party_used_by_test,
        unused_third_party=unused_third_party_installed_by_test,
        unused_local=unused_test_modules,
    )
    if package_error or test_error:
        exit(1)


# [ Script ]
if __name__ == '__main__':
    main()
