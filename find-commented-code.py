"""Find commented code."""  # pylint: disable=invalid-name


# [ Imports:Python ]
import pathlib
import re

# [ Imports:Third Party ]
import click


# [ API ]
@click.command()
def cli() -> None:
    """Find commented code."""
    if not (pathlib.Path.cwd() / '.ok_comments').is_file():
        (pathlib.Path.cwd() / '.ok_comments').touch()
    ok_patterns = (pathlib.Path.cwd() / '.ok_comments').read_text().splitlines()
    ok_patterns = [l for l in ok_patterns if l and not l.startswith('#')]
    paths = pathlib.Path.cwd().glob('**/*.py')
    num_lines = 0
    for this_path in paths:
        lines = enumerate(this_path.read_text().splitlines())
        comment_lines = (l for l in lines if re.match(r'^\s*#', l[1]))
        commented_code_lines = (l for l in comment_lines if re.search(r'[@()[\]{},.:\'"]', l[1]))
        filtered_commented_code_lines = (l for l in commented_code_lines if not any(re.search(p, l[1]) for p in ok_patterns))
        short_path = this_path.relative_to(pathlib.Path.cwd())
        for index, this_line in filtered_commented_code_lines:
            print(f'{short_path}:{index+1} -> {this_line}')
            num_lines += 1
    print(f"Found {num_lines} possible lines of commented code!")
    if num_lines:
        exit(1)


# [ Script ]
if __name__ == '__main__':
    cli()
