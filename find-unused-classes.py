"""Find unused classes."""  # pylint: disable=invalid-name


# [ Imports:Python ]
import itertools
import pathlib
import re
import typing

# [ Imports:Third Party ]
import click


# [ API ]
@click.command()
def cli() -> None:
    """Find unused classes."""
    paths = pathlib.Path.cwd().glob('**/*.py')
    # flake says this is a multiple statement line...
    defined_classes: typing.List[typing.Tuple[pathlib.Path, int, str]] = []  # noqa
    instantiated_classes: typing.List[str] = []

    for this_path in paths:
        short_path = this_path.relative_to(pathlib.Path.cwd())
        lines = list(enumerate(this_path.read_text().splitlines()))

        class_definition_lines = (l for l in lines if re.match(r'^\s*class \w+', l[1]))
        # we know there's a string that matches group 1, because we restricted that ^v
        defined_classes += [
            (short_path, l[0], typing.cast(
                str, typing.cast(typing.Match, re.search(r'class (\w+)', l[1])).group(1),
            ))
            for l in class_definition_lines
        ]

        # use `Class` for public or `_Class` for private
        # use `Class(` for default constructor or `Class.` for custom constructor
        class_instantiation_lines = (l for l in lines if re.search(r'_?[A-Z]\w+[(.]', l[1]))
        instantiated_classes += list(itertools.chain.from_iterable(re.findall(r'(_?[A-Z]\w+)[(.]', l[1]) for l in class_instantiation_lines))
    instantiated_classes = list(set(instantiated_classes))

    unused_classes = sorted(d for d in defined_classes if d[2] not in instantiated_classes)
    for path, index, class_name in unused_classes:
        print(f'{path}:{index+1} -> {class_name}')
    print(f"Found {len(unused_classes)} possible unused classes!")
    if unused_classes:
        exit(1)


# [ Script ]
if __name__ == '__main__':
    cli()
